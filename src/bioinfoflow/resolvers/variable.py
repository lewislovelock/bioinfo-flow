"""
Variable resolver for BioinfoFlow workflows.

This module provides functionality for resolving variable references
in workflow configurations.
"""

import re
from typing import Any, Dict, Optional, Union
from copy import deepcopy

from ..core.models import Workflow, Step, InputConfig, OutputConfig
from ..core.exceptions import VariableResolutionError
from ..utils.logging import debug, error

# Regex for finding ${...} references
VAR_PATTERN = re.compile(r'\${([^}]+)}')

class VariableContext:
    """Context for variable resolution."""
    
    def __init__(self, workflow: Workflow, step: Optional[Step] = None, sample: Optional[Dict[str, Any]] = None):
        self.workflow = workflow
        self.step = step
        self.sample = sample or {}
        
        # Build context dictionary
        self.context: Dict[str, Any] = {
            "config": workflow.config.__dict__,
            "workflow": {
                "name": workflow.name,
                "version": workflow.version,
            },
        }
        
        if step:
            self.context["step"] = {
                "name": step.name,
                "resources": step.resources.__dict__,
            }
            self.context["inputs"] = step.inputs
            self.context["outputs"] = {k: v.path for k, v in step.outputs.items()}
        
        if sample:
            self.context["sample"] = sample

def _resolve_reference(ref: str, context: Dict[str, Any]) -> Any:
    """
    Resolve a single variable reference.
    
    Example references:
    - ${config.ref_genome}
    - ${step.name}
    - ${sample.read1}
    - ${inputs.bam}
    - ${outputs.vcf}
    """
    try:
        parts = ref.split('.')
        value = context
        for part in parts:
            value = value[part]
        return value
    except KeyError:
        error("Unknown variable reference: {}", ref)
        raise VariableResolutionError(f"Unknown variable reference: {ref}")
    except Exception as e:
        error("Failed to resolve variable reference: {} ({})", ref, str(e))
        raise VariableResolutionError(f"Failed to resolve variable reference: {ref}")

def _resolve_string(text: str, context: Dict[str, Any]) -> str:
    """Resolve all variable references in a string."""
    def replace(match: re.Match) -> str:
        ref = match.group(1)
        value = _resolve_reference(ref, context)
        if not isinstance(value, (str, int, float)):
            error("Invalid variable reference type: {} ({})", ref, type(value))
            raise VariableResolutionError(
                f"Invalid variable reference type: {ref} ({type(value)}). "
                "Only strings and numbers can be interpolated."
            )
        return str(value)
    
    try:
        return VAR_PATTERN.sub(replace, text)
    except Exception as e:
        error("Failed to resolve variables in string: {} ({})", text, str(e))
        raise VariableResolutionError(f"Failed to resolve variables in string: {text}")

def resolve_step_variables(step: Step, context: VariableContext) -> Step:
    """Resolve variables in a workflow step."""
    debug("Resolving variables in step: {}", step.name)
    
    # Create a copy to avoid modifying the original
    step = deepcopy(step)
    
    # Resolve command
    step.command = _resolve_string(step.command, context.context)
    
    # Resolve input references
    resolved_inputs = {}
    for name, value in step.inputs.items():
        if isinstance(value, str):
            resolved_inputs[name] = _resolve_string(value, context.context)
        else:
            resolved_inputs[name] = value
    step.inputs = resolved_inputs
    
    # Resolve output paths
    for output in step.outputs.values():
        output.path = _resolve_string(output.path, context.context)
    
    return step

def resolve_variables(workflow: Workflow) -> Workflow:
    """
    Resolve all variable references in a workflow.
    
    Args:
        workflow: Workflow configuration to resolve
        
    Returns:
        Workflow with resolved variables
        
    Raises:
        VariableResolutionError: If variable resolution fails
    """
    debug("Starting variable resolution for workflow: {}", workflow.name)
    
    # Create a copy to avoid modifying the original
    workflow = deepcopy(workflow)
    
    # Create base context
    context = VariableContext(workflow)
    
    # Resolve variables in steps
    resolved_steps = {}
    for name, step in workflow.steps.items():
        step_context = VariableContext(workflow, step)
        resolved_steps[name] = resolve_step_variables(step, step_context)
    workflow.steps = resolved_steps
    
    debug("Variable resolution completed")
    return workflow 