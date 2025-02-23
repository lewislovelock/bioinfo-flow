"""
Path resolver for BioinfoFlow workflows.

This module provides functionality for resolving and normalizing paths
in workflow configurations.
"""

import os
from pathlib import Path
from typing import Union, Dict, List, Optional
from copy import deepcopy

from ..core.models import Workflow, Step, InputConfig, OutputConfig
from ..core.exceptions import PathResolutionError
from ..utils.logging import debug, error

def normalize_path(path: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
    """
    Normalize a path, resolving it against a base directory if provided.
    
    Args:
        path: Path to normalize
        base_dir: Optional base directory to resolve relative paths against
        
    Returns:
        Normalized Path object
    """
    try:
        path = Path(path)
        if base_dir and not path.is_absolute():
            path = base_dir / path
        return path.resolve()
    except Exception as e:
        error("Failed to normalize path: {} ({})", path, str(e))
        raise PathResolutionError(f"Failed to normalize path: {path}")

def _resolve_input_paths(input_config: InputConfig, base_dir: Path) -> InputConfig:
    """Resolve paths in an input configuration."""
    debug("Resolving paths in input configuration")
    
    input_config = deepcopy(input_config)
    
    # Normalize pattern path
    if input_config.pattern:
        try:
            # eg. input_config.pattern = "data/*.csv"
            # Don't resolve glob patterns, just normalize the directory part
            pattern_parts = input_config.pattern.split('/')
            if len(pattern_parts) > 1:
                # eg. pattern_parts = ["data", "*.csv"]
                dir_part = '/'.join(pattern_parts[:-1])
                # eg. dir_part = "data"
                dir_path = normalize_path(dir_part, base_dir)
                # eg. dir_path = "/absolute/path/to/data"
                input_config.pattern = str(dir_path / pattern_parts[-1])
                # eg. input_config.pattern = "/absolute/path/to/data/*.csv"
            else:
                input_config.pattern = str(base_dir / input_config.pattern)
                # TODO: eg. input_config.pattern = "/absolute/path/to/base_dir/workflow_name/v1.0.0/202403201234_xxxx/inputs/*.csv"
        except Exception as e:
            error("Failed to resolve input pattern: {} ({})", input_config.pattern, str(e))
            raise PathResolutionError(f"Failed to resolve input pattern: {input_config.pattern}")
        except Exception as e:
            error("Failed to resolve input pattern: {} ({})", input_config.pattern, str(e))
            raise PathResolutionError(f"Failed to resolve input pattern: {input_config.pattern}")
    
    return input_config

def _resolve_output_paths(output_config: OutputConfig, base_dir: Path) -> OutputConfig:
    """Resolve paths in an output configuration."""
    debug("Resolving paths in output configuration")
    
    output_config = deepcopy(output_config)
    
    # Normalize output path
    try:
        # Don't resolve variable references (${...}), they're handled by variable resolver
        if not "${" in output_config.path:
            output_config.path = str(normalize_path(output_config.path, base_dir))
    except Exception as e:
        error("Failed to resolve output path: {} ({})", output_config.path, str(e))
        raise PathResolutionError(f"Failed to resolve output path: {output_config.path}")
    
    return output_config

def _resolve_step_outputs(step: Step, base_dir: Path) -> Step:
    """
    Resolve output paths in a workflow step.
    
    Args:
        step: Step configuration to resolve
        base_dir: Base directory to resolve paths against
        
    Returns:
        Step with resolved output paths
    """
    debug("Resolving output paths in step: {}", step.name)
    
    step = deepcopy(step)
    
    # Resolve output paths
    resolved_outputs = {}
    for name, output in step.outputs.items():
        resolved_outputs[name] = _resolve_output_paths(output, base_dir)
    step.outputs = resolved_outputs
    
    return step

def resolve_paths(workflow: Workflow) -> Workflow:
    """
    Resolve all paths in a workflow configuration.
    
    This function:
    1. Normalizes all paths
    2. Resolves relative paths against the workflow directory
    3. Creates necessary directories for outputs
    
    Args:
        workflow: Workflow configuration to resolve
        
    Returns:
        Workflow with resolved paths
        
    Raises:
        PathResolutionError: If path resolution fails
    """
    debug("Starting path resolution for workflow: {}", workflow.name)
    
    workflow = deepcopy(workflow)
    
    # Get base directory (workflow file location or current directory)
    base_dir = workflow.config.work_dir
    if not base_dir.is_absolute():
        base_dir = Path.cwd() / base_dir
    base_dir = base_dir.resolve()
    
    try:
        # Create work directory if it doesn't exist
        base_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        error("Failed to create work directory: {} ({})", base_dir, str(e))
        raise PathResolutionError(f"Failed to create work directory: {base_dir}")
    
    # Resolve reference paths
    resolved_ref_paths = {}
    for name, path in workflow.config.ref_paths.items():
        resolved_ref_paths[name] = normalize_path(path, base_dir)
    workflow.config.ref_paths = resolved_ref_paths
    
    # Resolve input paths
    resolved_inputs = {}
    for name, input_config in workflow.inputs.items():
        resolved_inputs[name] = _resolve_input_paths(input_config, base_dir)
    workflow.inputs = resolved_inputs
    
    # Resolve step paths
    resolved_steps = {}
    for name, step in workflow.steps.items():
        resolved_steps[name] = _resolve_step_outputs(step, base_dir)
    workflow.steps = resolved_steps
    
    debug("Path resolution completed")
    return workflow