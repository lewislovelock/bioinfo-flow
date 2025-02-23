"""
Custom exceptions for BioinfoFlow.

This module contains all custom exceptions used throughout the package.
"""

class BioinfoFlowError(Exception):
    """Base exception for all BioinfoFlow errors."""
    pass

class ValidationError(BioinfoFlowError):
    """Raised when workflow validation fails."""
    pass

class WorkflowParseError(BioinfoFlowError):
    """Raised when workflow YAML parsing fails."""
    pass

class VariableResolutionError(BioinfoFlowError):
    """Raised when variable resolution fails."""
    pass

class PathResolutionError(BioinfoFlowError):
    """Raised when path resolution fails."""
    pass

class ExecutionError(BioinfoFlowError):
    """Raised when workflow execution fails."""
    pass

class ResourceError(BioinfoFlowError):
    """Raised when resource requirements cannot be met."""
    pass

class ContainerError(BioinfoFlowError):
    """Raised when container operations fail."""
    pass 