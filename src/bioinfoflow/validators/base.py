"""
Base validator for BioinfoFlow workflows.

This module provides core validation functionality for workflow configurations.
"""

import re
from typing import Dict, Set

from ..core.models import (
    Workflow,
    Step,
    InputConfig,
    InputType,
)
from ..core.exceptions import ValidationError
from ..utils.logging import debug, info, error, set_step_context

from .resource import validate_resources
from .container import validate_containers
from .dependency import validate_dependencies

def validate_workflow_basics(workflow: Workflow) -> None:
    """Validate basic workflow attributes."""
    debug("Validating workflow basics")
    if not workflow.name:
        error("Workflow name is required")
        raise ValidationError("Workflow name is required")
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', workflow.name):
        error("Invalid workflow name: {}", workflow.name)
        raise ValidationError(
            "Workflow name must start with a letter and contain only letters, numbers, and underscores"
        )
    
    if not workflow.version:
        error("Workflow version is required")
        raise ValidationError("Workflow version is required")
    if not re.match(r'^\d+\.\d+\.\d+$', workflow.version):
        error("Invalid version format: {}", workflow.version)
        raise ValidationError("Version must be in format X.Y.Z")
    
    debug("Workflow basics validation passed")

def validate_input_config(input_config: InputConfig) -> None:
    """Validate input configuration."""
    if not isinstance(input_config.type, InputType):
        error("Invalid input type: {}", input_config.type)
        raise ValidationError(f"Invalid input type: {input_config.type}")
    
    if not input_config.pattern:
        error("Input pattern is required")
        raise ValidationError("Input pattern is required")
    
    if input_config.type == InputType.SAMPLE_GROUP:
        debug("Validating sample group input configuration")
        if not input_config.format:
            error("Format is required for sample group inputs")
            raise ValidationError("Format is required for sample group inputs")
        if input_config.format not in ["csv"]:
            error("Unsupported sample group input format: {}", input_config.format)
            raise ValidationError(
                f"Unsupported sample group input format: {input_config.format}. "
                "Currently only csv format is supported"
            )
        if not input_config.columns:
            error("Columns configuration is required for sample group inputs")
            raise ValidationError("Columns configuration is required for sample group inputs")
        
        # Validate column configuration
        for col in input_config.columns:
            if "name" not in col or "type" not in col:
                error("Invalid column configuration: missing name or type")
                raise ValidationError("Each column must have name and type")
            if col["type"] not in ["string", "file", "integer", "float"]:
                error("Invalid column type: {}", col["type"])
                raise ValidationError(f"Invalid column type: {col['type']}")

def validate_step(step: Step, available_steps: Set[str]) -> None:
    """Validate a workflow step."""
    set_step_context(step.name)
    debug("Validating step configuration")
    
    if not step.name:
        error("Step name is required")
        raise ValidationError("Step name is required")
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', step.name):
        error("Invalid step name: {}", step.name)
        raise ValidationError(
            "Step name must start with a letter and contain only letters, numbers, and underscores"
        )
    
    # Validate container configuration
    validate_containers(step.container)
    
    # Validate resource requirements
    validate_resources(step.resources)
    
    # Validate dependencies
    validate_dependencies(step, available_steps)
    
    # Validate command
    if not step.command:
        error("Step command is required")
        raise ValidationError("Step command is required")
    
    # Validate foreach
    if step.foreach and step.foreach not in ["samples"]:
        error("Invalid foreach target: {}", step.foreach)
        raise ValidationError(f"Invalid foreach target: {step.foreach}")
    
    debug("Step validation passed")

def validate_workflow(workflow: Workflow) -> None:
    """
    Validate entire workflow configuration.
    
    Args:
        workflow: Workflow configuration to validate
        
    Raises:
        ValidationError: If validation fails
    """
    info("Starting workflow validation")
    
    # Validate basic workflow attributes
    validate_workflow_basics(workflow)
    
    # Validate inputs
    debug("Validating workflow inputs")
    for input_name, input_config in workflow.inputs.items():
        debug("Validating input: {}", input_name)
        validate_input_config(input_config)
    
    # Collect all step names for dependency validation
    step_names = set(workflow.steps.keys())
    
    # Validate each step
    debug("Validating workflow steps")
    for step_name, step in workflow.steps.items():
        debug("Validating step: {}", step_name)
        validate_step(step, step_names)
    
    info("Workflow validation completed successfully") 