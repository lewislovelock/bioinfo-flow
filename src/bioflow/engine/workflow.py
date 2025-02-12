"""
Workflow executor implementation.
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from ..parser.models import Step, StepType, Workflow
from .dependency import ExecutionDependencyResolver
from .models import ExecutionContext, ExecutionStatus, StepExecutionState, ExecutionResult
from .exceptions import ExecutionError, DependencyError
from .executors.base import BaseExecutor
from .executors.command import CommandExecutor
from .executors.container import ContainerExecutor


class WorkflowExecutor:
    """Executor for workflows."""
    
    def __init__(self, workflow: Workflow, working_dir: Path, temp_dir: Optional[Path] = None):
        """
        Initialize the workflow executor.
        
        Args:
            workflow: Workflow to execute
            working_dir: Working directory for execution
            temp_dir: Temporary directory for execution
        """
        self.workflow = workflow
        self.working_dir = working_dir
        self.temp_dir = temp_dir or working_dir / "temp"
        
        # Create execution context
        self.context = ExecutionContext(
            workflow=workflow,
            working_dir=working_dir,
            temp_dir=self.temp_dir,
            env=workflow.env.copy()
        )
        
        # Initialize executors
        self.executors: List[BaseExecutor] = [
            CommandExecutor(self.context),
            ContainerExecutor(self.context)
        ]
        
        # Initialize dependency resolver
        self.dependency_resolver = ExecutionDependencyResolver()
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
    
    async def execute(self) -> ExecutionResult:
        """
        Execute the workflow.
        
        Returns:
            Execution result
            
        Raises:
            ExecutionError: If workflow execution fails
        """
        # Create working and temp directories
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create execution result
        result = ExecutionResult(
            workflow=self.workflow,
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            # Build dependency graph
            for step in self.workflow.steps:
                self.dependency_resolver.add_step(step)
            
            # Get execution layers (steps that can be executed in parallel)
            execution_layers = self.dependency_resolver.get_execution_layers()
            
            # Execute layers sequentially
            for layer in execution_layers:
                # Execute steps in layer in parallel
                states = await asyncio.gather(
                    *[self._execute_step(step) for step in layer],
                    return_exceptions=True
                )
                
                # Check for failures
                for step, state in zip(layer, states):
                    if isinstance(state, Exception):
                        raise ExecutionError(f"Step '{step.name}' failed: {str(state)}")
                    
                    result.step_states[step.name] = state
                    if state.status == ExecutionStatus.FAILED:
                        raise ExecutionError(
                            f"Step '{step.name}' failed: {state.error_message}"
                        )
            
            # Update result status
            result.status = ExecutionStatus.COMPLETED
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            self.logger.error(f"Workflow execution failed: {str(e)}")
            
        finally:
            result.end_time = datetime.now()
        
        return result
    
    async def _execute_step(self, step: Step) -> StepExecutionState:
        """
        Execute a workflow step.
        
        Args:
            step: Step to execute
            
        Returns:
            Execution state of the step
            
        Raises:
            ExecutionError: If no suitable executor is found or step execution fails
        """
        # Find suitable executor
        executor = self._find_executor(step)
        if not executor:
            raise ExecutionError(f"No suitable executor found for step '{step.name}'")
        
        try:
            # Execute step
            self.logger.info(f"Executing step '{step.name}'")
            state = await executor.execute(step)
            self.logger.info(
                f"Step '{step.name}' completed with status {state.status.name}"
            )
            
            return state
            
        except Exception as e:
            self.logger.error(f"Step '{step.name}' failed: {str(e)}")
            raise
    
    def _find_executor(self, step: Step) -> Optional[BaseExecutor]:
        """
        Find a suitable executor for a step.
        
        Args:
            step: Step to find executor for
            
        Returns:
            Suitable executor or None if not found
        """
        for executor in self.executors:
            if executor.can_execute(step):
                return executor
        return None 