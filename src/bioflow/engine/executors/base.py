"""
Base executor implementation.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional, Any

from ...parser.models import Step
from ..models import ExecutionContext, StepExecutionState, ExecutionStatus


class BaseExecutor(ABC):
    """Base class for step executors."""
    
    def __init__(self, context: ExecutionContext):
        """
        Initialize the executor.
        
        Args:
            context: Execution context
        """
        self.context = context
    
    @abstractmethod
    def can_execute(self, step: Step) -> bool:
        """
        Check if this executor can execute the given step.
        
        Args:
            step: Step to check
            
        Returns:
            True if this executor can execute the step
        """
        pass
    
    @abstractmethod
    async def execute(self, step: Step) -> StepExecutionState:
        """
        Execute a workflow step.
        
        Args:
            step: Step to execute
            
        Returns:
            Execution state of the step
            
        Raises:
            ExecutionError: If the step execution fails
        """
        pass
    
    def _create_state(self, step: Step, **kwargs) -> StepExecutionState:
        """
        Create a new execution state for a step.
        
        Args:
            step: Step to create state for
            **kwargs: Additional state attributes
            
        Returns:
            New execution state
        """
        state = StepExecutionState(step=step)
        for key, value in kwargs.items():
            setattr(state, key, value)
        return state
    
    def _update_state(self, state: StepExecutionState, **kwargs) -> None:
        """
        Update an execution state.
        
        Args:
            state: State to update
            **kwargs: Attributes to update
        """
        for key, value in kwargs.items():
            setattr(state, key, value)
    
    def _prepare_env(self, step: Step) -> Dict[str, str]:
        """
        Prepare environment variables for step execution.
        
        Args:
            step: Step to prepare environment for
            
        Returns:
            Dictionary of environment variables
        """
        # Start with workflow-level environment
        env = self.context.env.copy()
        
        # Add step-specific environment variables
        if step.container and step.container.environment:
            env.update(step.container.environment)
            
        return env
    
    def _resolve_inputs(self, step: Step) -> Dict[str, Any]:
        """
        Resolve step input values.
        
        Args:
            step: Step to resolve inputs for
            
        Returns:
            Dictionary of resolved input values
        """
        inputs = {}
        for input_def in step.inputs:
            # TODO: Implement input value resolution from parameters,
            # previous step outputs, and environment variables
            inputs[input_def.name] = input_def.value
        return inputs
    
    def _validate_outputs(self, step: Step, outputs: Dict[str, Any]) -> bool:
        """
        Validate step outputs.
        
        Args:
            step: Step that produced the outputs
            outputs: Output values to validate
            
        Returns:
            True if outputs are valid
        """
        # TODO: Implement output validation based on step output definitions
        return True 