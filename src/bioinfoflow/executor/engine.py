"""
Execution engine for BioinfoFlow.

This module provides the main execution engine for running workflows,
coordinating between the scheduler, context, and container runtime.
"""

import os
import sys
import time
import signal
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, Future
import subprocess
from pathlib import Path

from ..core.models import Workflow, Step
from ..core.exceptions import ExecutionError
from ..utils.logging import debug, info, error, set_workflow_context
from .context import ExecutionContext
from .scheduler import TaskScheduler

class ExecutionEngine:
    """
    Main execution engine for running workflows.
    
    This class:
    - Coordinates workflow execution
    - Manages container lifecycle
    - Handles resource allocation
    - Provides execution monitoring
    """
    
    def __init__(self, workflow: Workflow, max_workers: Optional[int] = None):
        """
        Initialize execution engine.
        
        Args:
            workflow: Workflow to execute
            max_workers: Maximum number of concurrent steps (default: CPU count)
        """
        self.workflow = workflow
        self.max_workers = max_workers or os.cpu_count() or 1
        
        # Initialize context and scheduler
        self.context = ExecutionContext(workflow)
        self.scheduler = TaskScheduler(self.context)
        
        # Initialize thread pool
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.futures: Dict[str, Future] = {}
        
        # Initialize signal handling
        self._setup_signal_handlers()
        
        # Track container IDs for cleanup
        self.containers: Set[str] = set()
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def handler(signum, frame):
            info("Received signal {}, initiating shutdown...", signum)
            self.shutdown()
            sys.exit(1)
        
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
    
    def execute(self) -> bool:
        """
        Execute the workflow.
        
        Returns:
            True if workflow completed successfully, False otherwise
        """
        try:
            info("Starting workflow execution: {}", self.workflow.name)
            self.context.setup()
            
            # Main execution loop
            while not self.scheduler.is_complete():
                # Get next step to execute
                step_name = self.scheduler.get_next_step()
                if step_name:
                    # Submit step for execution
                    future = self.executor.submit(self._execute_step, step_name)
                    self.futures[step_name] = future
                
                # Clean up completed futures
                self._cleanup_futures()
                
                # Short sleep to prevent busy waiting
                time.sleep(0.1)
            
            # Wait for any remaining futures
            for future in self.futures.values():
                future.result()
            
            success = not self.scheduler.has_failed_steps()
            if success:
                info("Workflow completed successfully")
            else:
                error("Workflow failed. Failed steps: {}", 
                      ", ".join(self.scheduler.get_failed_steps()))
            
            return success
            
        except Exception as e:
            error("Workflow execution failed: {}", str(e))
            return False
            
        finally:
            self.shutdown()
    
    def _execute_step(self, step_name: str) -> None:
        """Execute a single workflow step."""
        step = self.workflow.steps[step_name]
        step_context = self.context.get_step_context(step_name)
        
        try:
            info("Executing step: {}", step_name)
            self.scheduler.mark_step_running(step_name)
            
            # Prepare container command
            container_cmd = self._prepare_container_command(step)
            
            # Execute container
            process = subprocess.Popen(
                container_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=dict(os.environ, **step_context.env_vars)
            )
            
            # Store container ID for cleanup
            if process.stdout:
                container_id = process.stdout.readline().strip()
                step_context.container_id = container_id
                self.containers.add(container_id)
            
            # Monitor execution
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            
            # Handle completion
            if exit_code == 0:
                self.scheduler.mark_step_completed(step_name, exit_code)
            else:
                error_msg = f"Step failed with exit code {exit_code}:\n{stderr}"
                self.scheduler.mark_step_failed(step_name, error_msg, exit_code)
            
            # Remove container ID
            if step_context.container_id:
                self.containers.remove(step_context.container_id)
            
        except Exception as e:
            error("Failed to execute step {}: {}", step_name, str(e))
            self.scheduler.mark_step_failed(step_name, str(e))
    
    def _prepare_container_command(self, step: Step) -> List[str]:
        """Prepare container execution command."""
        # Basic docker run command
        cmd = ["docker", "run", "-d"]  # Run in detached mode
        
        # Add resource limits
        resources = step.resources
        cmd.extend([
            "--cpu-count", str(resources.cpu),
            "--memory", resources.memory,
        ])
        if resources.gpu:
            cmd.extend(["--gpus", str(resources.gpu)])
        
        # Add volume mounts
        for volume in step.container.volumes:
            cmd.extend(["-v", volume])
        
        # Add environment variables
        for key, value in step.container.env.items():
            cmd.extend(["-e", f"{key}={value}"])
        
        # Add container image
        cmd.append(f"{step.container.image}:{step.container.tag}")
        
        # Add command
        cmd.extend(["/bin/sh", "-c", step.command])
        
        return cmd
    
    def _cleanup_futures(self) -> None:
        """Clean up completed futures."""
        completed = [
            name for name, future in self.futures.items()
            if future.done()
        ]
        for name in completed:
            # Get result to propagate any exceptions
            self.futures[name].result()
            del self.futures[name]
    
    def shutdown(self) -> None:
        """Shutdown the execution engine."""
        try:
            # Cancel running futures
            for future in self.futures.values():
                future.cancel()
            
            # Stop running containers
            for container_id in self.containers:
                try:
                    subprocess.run(["docker", "stop", container_id], check=True)
                    subprocess.run(["docker", "rm", container_id], check=True)
                except subprocess.CalledProcessError:
                    pass  # Ignore errors during cleanup
            
            # Shutdown thread pool
            self.executor.shutdown(wait=False)
            
            # Clean up context
            self.context.cleanup()
            
        except Exception as e:
            error("Error during shutdown: {}", str(e))

def execute_workflow(workflow: Workflow, max_workers: Optional[int] = None) -> bool:
    """
    Execute a workflow.
    
    Args:
        workflow: Workflow to execute
        max_workers: Maximum number of concurrent steps
        
    Returns:
        True if workflow completed successfully, False otherwise
    """
    engine = ExecutionEngine(workflow, max_workers)
    return engine.execute() 