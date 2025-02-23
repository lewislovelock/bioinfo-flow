"""
Task scheduler for BioinfoFlow.

This module provides task scheduling functionality for workflow execution,
managing dependencies and resource allocation.
"""

from typing import Dict, List, Set, Optional
from queue import Queue
from threading import Lock
import time

from ..core.models import Workflow, Step
from ..core.exceptions import SchedulerError
from ..utils.logging import debug, error
from .context import ExecutionContext, StepContext

class TaskScheduler:
    """
    Task scheduler for workflow execution.
    
    This class manages:
    - Task dependency resolution
    - Resource allocation
    - Task queuing and scheduling
    - Parallel execution management
    """
    
    def __init__(self, context: ExecutionContext):
        """
        Initialize task scheduler.
        
        Args:
            context: Execution context
        """
        self.context = context
        self.workflow = context.workflow
        
        # Initialize task queues
        self.pending: Queue[str] = Queue()  # Steps ready to run
        self.running: Set[str] = set()      # Currently running steps
        self.completed: Set[str] = set()    # Completed steps
        self.failed: Set[str] = set()       # Failed steps
        
        # Initialize dependency tracking
        self.dependencies: Dict[str, Set[str]] = {}  # step -> dependencies
        self.dependents: Dict[str, Set[str]] = {}    # step -> dependent steps
        
        # Thread safety
        self.lock = Lock()
        
        # Build dependency graph
        self._build_dependency_graph()
    
    def _build_dependency_graph(self) -> None:
        """Build the dependency graph for all steps."""
        try:
            for name, step in self.workflow.steps.items():
                # Initialize sets
                self.dependencies[name] = set(step.after or [])
                self.dependents[name] = set()
                
                # Add reverse dependencies
                for dep in self.dependencies[name]:
                    if dep not in self.workflow.steps:
                        raise SchedulerError(f"Unknown dependency: {dep} for step {name}")
                    self.dependents[dep].add(name)
            
            # Validate no cycles
            self._check_cycles()
            
            # Queue steps with no dependencies
            for name, deps in self.dependencies.items():
                if not deps:
                    self.pending.put(name)
            
            debug("Built dependency graph with {} steps", len(self.workflow.steps))
            
        except Exception as e:
            error("Failed to build dependency graph: {}", str(e))
            raise SchedulerError(f"Failed to build dependency graph: {str(e)}")
    
    def _check_cycles(self) -> None:
        """Check for cycles in the dependency graph."""
        visited = set()
        path = set()
        
        def dfs(step: str) -> None:
            if step in path:
                path_list = list(path)
                cycle_start = path_list.index(step)
                cycle = path_list[cycle_start:] + [step]
                raise SchedulerError(f"Circular dependency detected: {' -> '.join(cycle)}")
            
            if step in visited:
                return
            
            visited.add(step)
            path.add(step)
            
            for dep in self.dependents[step]:
                dfs(dep)
            
            path.remove(step)
        
        # Start DFS from each unvisited node
        for step in self.workflow.steps:
            if step not in visited:
                dfs(step)
    
    def get_next_step(self) -> Optional[str]:
        """
        Get the next step to execute.
        
        Returns:
            Step name if available, None otherwise
        """
        with self.lock:
            # Check pending queue
            while not self.pending.empty():
                step_name = self.pending.get()
                
                # Skip if already running or completed
                if step_name in self.running or step_name in self.completed:
                    continue
                
                # Check if dependencies are met
                if not self._are_dependencies_met(step_name):
                    self.pending.put(step_name)  # Put back in queue
                    continue
                
                # Check resource availability
                if not self.context.can_run_step(step_name):
                    self.pending.put(step_name)  # Put back in queue
                    continue
                
                return step_name
            
            return None
    
    def _are_dependencies_met(self, step_name: str) -> bool:
        """Check if all dependencies for a step are met."""
        return all(
            dep in self.completed
            for dep in self.dependencies[step_name]
        )
    
    def mark_step_running(self, step_name: str) -> None:
        """Mark a step as running."""
        with self.lock:
            if step_name in self.running:
                raise SchedulerError(f"Step already running: {step_name}")
            
            self.running.add(step_name)
            self.context.get_step_context(step_name).mark_running()
            self.context.allocate_resources(step_name)
            
            debug("Marked step as running: {}", step_name)
    
    def mark_step_completed(self, step_name: str, exit_code: int = 0) -> None:
        """Mark a step as completed."""
        with self.lock:
            if step_name not in self.running:
                raise SchedulerError(f"Step not running: {step_name}")
            
            self.running.remove(step_name)
            self.completed.add(step_name)
            self.context.get_step_context(step_name).mark_completed(exit_code)
            self.context.release_resources(step_name)
            
            # Queue dependent steps
            for dependent in self.dependents[step_name]:
                if self._are_dependencies_met(dependent):
                    self.pending.put(dependent)
            
            debug("Marked step as completed: {}", step_name)
    
    def mark_step_failed(self, step_name: str, error_msg: str, exit_code: int = 1) -> None:
        """Mark a step as failed."""
        with self.lock:
            if step_name not in self.running:
                raise SchedulerError(f"Step not running: {step_name}")
            
            self.running.remove(step_name)
            self.failed.add(step_name)
            self.context.get_step_context(step_name).mark_failed(error_msg, exit_code)
            self.context.release_resources(step_name)
            
            debug("Marked step as failed: {}", step_name)
    
    def is_complete(self) -> bool:
        """Check if workflow execution is complete."""
        return (
            len(self.completed) + len(self.failed) == len(self.workflow.steps)
            and len(self.running) == 0
        )
    
    def has_failed_steps(self) -> bool:
        """Check if any steps have failed."""
        return len(self.failed) > 0
    
    def get_failed_steps(self) -> List[str]:
        """Get list of failed steps."""
        return list(self.failed) 