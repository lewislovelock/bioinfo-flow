"""
Workflow executor implementation.
"""
import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from ..parser.models import Step, StepType, Workflow
from ..logging import setup_logging, WorkflowContext
from .dependency import ExecutionDependencyResolver
from .models import ExecutionContext, ExecutionStatus, StepExecutionState, ExecutionResult
from .exceptions import ExecutionError, DependencyError
from .executors.base import BaseExecutor
from .executors.command import CommandExecutor
from .executors.container import ContainerExecutor


class WorkflowEngine:
    """Executor for workflows."""
    
    def __init__(
        self,
        workflow: Workflow,
        working_dir: Path,
        temp_dir: Optional[Path] = None,
        log_dir: Optional[Path] = None
    ):
        """
        Initialize the workflow engine.
        
        Args:
            workflow: Workflow to execute
            working_dir: Working directory for execution
            temp_dir: Temporary directory for execution
            log_dir: Directory for log files
        """
        self.workflow = workflow
        self.working_dir = working_dir
        self.temp_dir = temp_dir or working_dir / "temp"
        self.log_dir = log_dir or working_dir / "logs"
        
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
        
        # Generate execution ID
        self.execution_id = str(uuid.uuid4())
        
        # Initialize workflow logger
        workflow_context = WorkflowContext(
            workflow_id=workflow.name,
            workflow_name=workflow.name,
            execution_id=self.execution_id
        )
        self.logger = setup_logging(
            name=f"workflow.{workflow.name}",
            log_dir=self.log_dir,
            context=workflow_context
        )
    
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
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create execution result
        result = ExecutionResult(
            workflow=self.workflow,
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now()
        )
        
        # Log workflow start
        self.logger.info(
            "Workflow started",
            metadata={
                "version": self.workflow.version,
                "working_dir": str(self.working_dir),
                "temp_dir": str(self.temp_dir)
            }
        )
        
        try:
            # Build dependency graph
            self.logger.debug("Building dependency graph")
            for step in self.workflow.steps:
                self.dependency_resolver.add_step(step)
            
            # Get execution layers
            execution_layers = self.dependency_resolver.get_execution_layers()
            self.logger.info(
                "Dependency graph built",
                metadata={
                    "total_steps": len(self.workflow.steps),
                    "execution_layers": len(execution_layers)
                }
            )
            
            # Execute layers sequentially
            for layer_idx, layer in enumerate(execution_layers):
                self.logger.info(
                    f"Executing layer {layer_idx + 1}/{len(execution_layers)}",
                    metadata={
                        "layer": layer_idx + 1,
                        "total_layers": len(execution_layers),
                        "steps": [step.name for step in layer]
                    }
                )
                
                # Execute steps in layer in parallel
                states = await asyncio.gather(
                    *[self._execute_step(step) for step in layer],
                    return_exceptions=True
                )
                
                # Check for failures
                for step, state in zip(layer, states):
                    if isinstance(state, Exception):
                        error_msg = f"Step '{step.name}' failed: {str(state)}"
                        self.logger.error(
                            error_msg,
                            metadata={"step": step.name},
                            exc_info=state
                        )
                        raise ExecutionError(error_msg)
                    
                    result.step_states[step.name] = state
                    if state.status == ExecutionStatus.FAILED:
                        error_msg = f"Step '{step.name}' failed: {state.error_message}"
                        self.logger.error(
                            error_msg,
                            metadata={
                                "step": step.name,
                                "exit_code": state.exit_code,
                                "duration": (state.end_time - state.start_time).total_seconds()
                            }
                        )
                        raise ExecutionError(error_msg)
            
            # Update result status
            result.status = ExecutionStatus.COMPLETED
            self.logger.info(
                "Workflow completed successfully",
                metadata={
                    "duration": (datetime.now() - result.start_time).total_seconds(),
                    "total_steps": len(self.workflow.steps)
                }
            )
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            self.logger.error(
                "Workflow execution failed",
                metadata={
                    "duration": (datetime.now() - result.start_time).total_seconds()
                },
                exc_info=e
            )
            
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
        # Create step logger
        step_logger = self.logger.with_step(step.name, step.name)
        
        # Find suitable executor
        executor = self._find_executor(step)
        if not executor:
            error_msg = f"No suitable executor found for step '{step.name}'"
            step_logger.error(error_msg)
            raise ExecutionError(error_msg)
        
        try:
            # Log step start
            step_logger.info(
                "Step started",
                metadata={
                    "type": step.type.name,
                    "command": step.command,
                    "container": step.container.image if step.container else None,
                    "dependencies": step.depends_on
                }
            )
            
            # Execute step
            state = await executor.execute(step)
            
            # Log step completion
            duration = (state.end_time - state.start_time).total_seconds() if state.end_time else None
            step_logger.info(
                f"Step completed with status {state.status.name}",
                metadata={
                    "status": state.status.name,
                    "exit_code": state.exit_code,
                    "duration": duration,
                    "outputs": state.outputs
                }
            )
            
            return state
            
        except Exception as e:
            step_logger.error(
                "Step execution failed",
                metadata={"type": step.type.name},
                exc_info=e
            )
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