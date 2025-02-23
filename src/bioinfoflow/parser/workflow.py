"""
YAML parser for BioinfoFlow workflows.

This module provides functionality to parse workflow YAML files into
BioinfoFlow model objects and validate their structure.
"""

from pathlib import Path
from typing import Any, Dict, Union

import yaml
from yaml.parser import ParserError

from ..core.models import (
    Workflow,
    WorkflowConfig,
    Step,
    InputConfig,
    OutputConfig,
    ContainerConfig,
    ResourceRequirements,
    InputType,
)
from ..core.exceptions import WorkflowParseError
from ..validators.base import validate_workflow, ValidationError
from ..utils.logging import debug, info, error, set_workflow_context, clear_context

def _parse_resource_requirements(data: Dict[str, Any]) -> ResourceRequirements:
    """Parse resource requirements from YAML data."""
    try:
        return ResourceRequirements(
            cpu=data.get("cpu", 1),
            memory=data.get("memory", "1GB"),
            disk=data.get("disk", None),
            gpu=data.get("gpu", None),
        )
    except Exception as e:
        error("Failed to parse resource requirements: {}", str(e))
        raise WorkflowParseError(f"Invalid resource requirements: {str(e)}")

def _parse_container_config(data: Dict[str, Any]) -> ContainerConfig:
    """Parse container configuration from YAML data."""
    try:
        if isinstance(data, str):
            # Handle shorthand notation: container: "image:tag"
            image = data.split(":")[0]
            tag = data.split(":")[1] if ":" in data else "latest"
            debug("Parsing container shorthand notation: image={}, tag={}", image, tag)
            return ContainerConfig(image=image, tag=tag)
        
        return ContainerConfig(
            image=data["image"],
            tag=data.get("tag", "latest"),
            # volumes=data.get("volumes", []),
            # env=data.get("env", {}),
        )
    except Exception as e:
        error("Failed to parse container configuration: {}", str(e))
        raise WorkflowParseError(f"Invalid container configuration: {str(e)}")

def _parse_input_config(data: Dict[str, Any]) -> InputConfig:
    """Parse input configuration from YAML data."""
    try:
        input_type = InputType.SAMPLE_GROUP if data["type"] == "sample_group" else InputType.FILE
        debug("Parsing input configuration: type={}", input_type.value)
        return InputConfig(
            type=input_type,
            pattern=data["pattern"],
            format=data.get("format"),
            columns=data.get("columns"),
            description=data.get("description"),
        )
    except KeyError as e:
        error("Missing required field in input configuration: {}", str(e))
        raise WorkflowParseError(f"Missing required field in input configuration: {str(e)}")
    except Exception as e:
        error("Failed to parse input configuration: {}", str(e))
        raise WorkflowParseError(f"Invalid input configuration: {str(e)}")

def _parse_output_config(data: Union[str, Dict[str, Any]]) -> OutputConfig:
    """Parse output configuration from YAML data."""
    try:
        if isinstance(data, str):
            # Handle shorthand notation: output: "path"
            debug("Parsing output shorthand notation: path={}", data)
            return OutputConfig(path=data)
        
        return OutputConfig(
            path=data["path"],
            type=data.get("type", "file"),
            description=data.get("description"),
        )
    except Exception as e:
        error("Failed to parse output configuration: {}", str(e))
        raise WorkflowParseError(f"Invalid output configuration: {str(e)}")

def _parse_step(name: str, data: Dict[str, Any]) -> Step:
    """Parse workflow step from YAML data."""
    try:
        debug("Parsing step: {}", name)
        # Parse outputs, supporting both dict and string formats
        outputs = {}
        for out_name, out_data in data.get("outputs", {}).items():
            outputs[out_name] = _parse_output_config(out_data)
        
        return Step(
            name=name,
            container=_parse_container_config(data["container"]),
            command=data["command"],
            inputs=data.get("inputs", {}),
            outputs=outputs,
            resources=_parse_resource_requirements(data.get("resources", {})),
            after=data.get("after", []),
            foreach=data.get("foreach"),
        )
    except KeyError as e:
        error("Missing required field in step {}: {}", name, str(e))
        raise WorkflowParseError(f"Missing required field in step {name}: {str(e)}")
    except Exception as e:
        error("Failed to parse step {}: {}", name, str(e))
        raise WorkflowParseError(f"Invalid step configuration for {name}: {str(e)}")

def _parse_workflow_config(data: Dict[str, Any]) -> WorkflowConfig:
    """Parse workflow configuration from YAML data."""
    try:
        debug("Parsing workflow configuration")
        return WorkflowConfig(
            max_retries=data.get("max_retries", 3),
            # work_dir=Path(data.get("work_dir", "work_dir")),
            # ref_paths={k: Path(v) for k, v in data.get("ref_paths", {}).items()},
        )
    except Exception as e:
        error("Failed to parse workflow configuration: {}", str(e))
        raise WorkflowParseError(f"Invalid workflow configuration: {str(e)}")

def parse_workflow(yaml_path: Union[str, Path]) -> Workflow:
    """
    Parse and validate a workflow from a YAML file.
    
    Args:
        yaml_path: Path to the workflow YAML file
        
    Returns:
        Validated Workflow object
        
    Raises:
        WorkflowParseError: If YAML parsing fails
        ValidationError: If workflow validation fails
    """
    yaml_path = Path(yaml_path)
    clear_context()  # Clear any existing context
    
    info("Starting to parse workflow from: {}", yaml_path)
    
    if not yaml_path.exists():
        error("Workflow file not found: {}", yaml_path)
        raise WorkflowParseError(f"Workflow file not found: {yaml_path}")
    
    try:
        with yaml_path.open() as f:
            data = yaml.safe_load(f)
    except ParserError as e:
        error("Invalid YAML format: {}", str(e))
        raise WorkflowParseError(f"Invalid YAML format: {str(e)}")
    except Exception as e:
        error("Failed to read workflow file: {}", str(e))
        raise WorkflowParseError(f"Failed to read workflow file: {str(e)}")
    
    try:
        workflow = Workflow(
            name=data["name"],
            version=data["version"],
            description=data.get("description"),
            config=_parse_workflow_config(data.get("config", {})),
            inputs={name: _parse_input_config(input_data)
                   for name, input_data in data.get("inputs", {}).items()},
            steps={name: _parse_step(name, step_data)
                  for name, step_data in data.get("steps", {}).items()},
        )
    except KeyError as e:
        error("Missing required field in workflow: {}", str(e))
        raise WorkflowParseError(f"Missing required field: {str(e)}")
    except Exception as e:
        error("Failed to parse workflow: {}", str(e))
        raise WorkflowParseError(f"Failed to parse workflow: {str(e)}")
    
    # Set workflow context for validation
    set_workflow_context(workflow.name)
    info("Validating workflow: {} (v{})", workflow.name, workflow.version)
    
    try:
        # Validate the parsed workflow
        validate_workflow(workflow)
        info("Successfully validated workflow: {}", workflow.name)
    except ValidationError as e:
        error("Workflow validation failed: {}", str(e))
        raise
    
    return workflow 