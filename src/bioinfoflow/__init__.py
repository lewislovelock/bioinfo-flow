"""
BioinfoFlow - A powerful workflow engine for bioinformatics applications.

This package provides tools for creating, validating, and executing
bioinformatics workflows in a reproducible and scalable manner.
"""

from .core.models import (
    StepStatus,
    InputType,
    ResourceRequirements,
    ContainerConfig,
    InputConfig,
    OutputConfig,
    Step,
    WorkflowConfig,
    Workflow,
)

from .core.exceptions import (
    BioinfoFlowError,
    ValidationError,
    WorkflowParseError,
    VariableResolutionError,
    PathResolutionError,
    ExecutionError,
    ResourceError,
    ContainerError,
)

from .utils.logging import (
    debug,
    info,
    warning,
    error,
    critical,
    set_workflow_context,
    set_step_context,
    clear_context,
)

__version__ = "0.1.0"

__all__ = [
    # Core models
    "StepStatus",
    "InputType",
    "ResourceRequirements",
    "ContainerConfig",
    "InputConfig",
    "OutputConfig",
    "Step",
    "WorkflowConfig",
    "Workflow",
    
    # Exceptions
    "BioinfoFlowError",
    "ValidationError",
    "WorkflowParseError",
    "VariableResolutionError",
    "PathResolutionError",
    "ExecutionError",
    "ResourceError",
    "ContainerError",
    
    # Logging
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "set_workflow_context",
    "set_step_context",
    "clear_context",
] 