"""
Exceptions for workflow execution.
"""
from typing import Optional


class ExecutionError(Exception):
    """Base class for execution errors."""
    
    def __init__(self, message: str, step_name: Optional[str] = None):
        """
        Initialize the error.
        
        Args:
            message: Error message
            step_name: Name of the step that failed
        """
        self.step_name = step_name
        super().__init__(f"Step '{step_name}': {message}" if step_name else message)


class StepExecutionError(ExecutionError):
    """Error during step execution."""
    
    def __init__(self, message: str, step_name: str, exit_code: Optional[int] = None):
        """
        Initialize the error.
        
        Args:
            message: Error message
            step_name: Name of the step that failed
            exit_code: Exit code of the failed command
        """
        self.exit_code = exit_code
        super().__init__(
            f"{message} (exit code: {exit_code})" if exit_code is not None else message,
            step_name
        )


class DependencyError(ExecutionError):
    """Error in step dependencies."""
    pass


class ResourceError(ExecutionError):
    """Error in resource allocation or management."""
    pass


class ContainerError(ExecutionError):
    """Error in container operations."""
    pass


class ValidationError(ExecutionError):
    """Error in validating step inputs or outputs."""
    pass


class HookError(ExecutionError):
    """Error in executing hooks."""
    pass 