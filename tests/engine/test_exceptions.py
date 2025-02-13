"""
Tests for execution exceptions.
"""
import pytest

from bioflow.engine.exceptions import (
    ExecutionError,
    StepExecutionError,
    DependencyError,
    ResourceError,
    ContainerError,
    ValidationError,
    HookError
)


def test_execution_error():
    """Test base execution error."""
    error = ExecutionError("Test error")
    assert str(error) == "Test error"
    assert error.step_name is None
    
    error = ExecutionError("Test error", "step1")
    assert str(error) == "Step 'step1': Test error"
    assert error.step_name == "step1"


def test_step_execution_error():
    """Test step execution error."""
    error = StepExecutionError("Command failed", "step1")
    assert str(error) == "Step 'step1': Command failed"
    assert error.step_name == "step1"
    assert error.exit_code is None
    
    error = StepExecutionError("Command failed", "step1", 1)
    assert str(error) == "Step 'step1': Command failed (exit code: 1)"
    assert error.step_name == "step1"
    assert error.exit_code == 1


def test_dependency_error():
    """Test dependency error."""
    error = DependencyError("Missing dependency", "step1")
    assert str(error) == "Step 'step1': Missing dependency"
    assert error.step_name == "step1"


def test_resource_error():
    """Test resource error."""
    error = ResourceError("Insufficient memory", "step1")
    assert str(error) == "Step 'step1': Insufficient memory"
    assert error.step_name == "step1"


def test_container_error():
    """Test container error."""
    error = ContainerError("Failed to pull image", "step1")
    assert str(error) == "Step 'step1': Failed to pull image"
    assert error.step_name == "step1"


def test_validation_error():
    """Test validation error."""
    error = ValidationError("Invalid input format", "step1")
    assert str(error) == "Step 'step1': Invalid input format"
    assert error.step_name == "step1"


def test_hook_error():
    """Test hook error."""
    error = HookError("Hook script failed", "step1")
    assert str(error) == "Step 'step1': Hook script failed"
    assert error.step_name == "step1"


def test_error_inheritance():
    """Test error class inheritance."""
    assert issubclass(StepExecutionError, ExecutionError)
    assert issubclass(DependencyError, ExecutionError)
    assert issubclass(ResourceError, ExecutionError)
    assert issubclass(ContainerError, ExecutionError)
    assert issubclass(ValidationError, ExecutionError)
    assert issubclass(HookError, ExecutionError) 