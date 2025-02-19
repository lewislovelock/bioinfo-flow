"""
Workflow parser for loading and validating workflow definitions.
"""

import os
from pathlib import Path
from typing import Union, Dict, Any, Optional, Tuple

import yaml
from loguru import logger
from pydantic import ValidationError
from packaging import version

from bioinfo_flow.parser.model import BioinfoFlow
from bioinfo_flow.parser.errors import (
    YAMLParseError,
    FileNotFoundError,
    SchemaValidationError,
    setup_logger
)

# Initialize logger
logger = setup_logger()


class WorkflowParser:
    """Parser for workflow definitions."""
    
    @classmethod
    def validate_workspace_directories(
        cls, 
        working_dir: Union[str, Path],
        temp_dir: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Validate workspace directories.
        
        Args:
            working_dir: Working directory path
            temp_dir: Optional temporary directory path
            
        Raises:
            SchemaValidationError: If directories are invalid
        """
        working_dir = Path(working_dir)
        context = {"working_dir": str(working_dir)}
        
        # Validate working directory
        if not working_dir.exists():
            try:
                working_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created working directory: {working_dir}")
            except Exception as e:
                raise SchemaValidationError(
                    f"Cannot create working directory: {e}",
                    [],
                    context
                )
        
        if not os.access(working_dir, os.W_OK):
            raise SchemaValidationError(
                f"Working directory is not writable: {working_dir}",
                [],
                context
            )
            
        # Validate temp directory if specified
        if temp_dir:
            temp_dir = Path(temp_dir)
            context["temp_dir"] = str(temp_dir)
            
            if not temp_dir.exists():
                try:
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created temp directory: {temp_dir}")
                except Exception as e:
                    raise SchemaValidationError(
                        f"Cannot create temp directory: {e}",
                        [],
                        context
                    )
            
            if not os.access(temp_dir, os.W_OK):
                raise SchemaValidationError(
                    f"Temp directory is not writable: {temp_dir}",
                    [],
                    context
                )

    @classmethod
    def validate_dict(cls, workflow_dict: Dict[str, Any]) -> None:
        """
        Validate workflow dictionary without loading it.
        
        Args:
            workflow_dict: Dictionary containing workflow definition
            
        Raises:
            SchemaValidationError: If validation fails
        """
        logger.debug("Validating workflow dictionary")
        
        # Validate version first
        if "version" not in workflow_dict:
            raise SchemaValidationError(
                "Missing required field: version",
                [],
                {"workflow_dict": workflow_dict}
            )
                
        # Validate workspace if present
        if "global" in workflow_dict:
            global_config = workflow_dict["global"]
            working_dir = global_config.get("working_dir")
            temp_dir = global_config.get("temp_dir")
            
            if working_dir:
                cls.validate_workspace_directories(working_dir, temp_dir)
        
        # Validate against schema without creating object
        try:
            BioinfoFlow.model_validate(workflow_dict)
            logger.debug("Workflow validation successful")
        except ValidationError as e:
            raise SchemaValidationError(
                "Workflow validation failed",
                e.errors(),
                {"workflow_dict": workflow_dict}
            )

    @staticmethod
    def dump_workflow(
        workflow: BioinfoFlow,
        output_path: Union[str, Path],
        exclude_unset: bool = True
    ) -> None:
        """
        Dump workflow to YAML file.
        
        Args:
            workflow: Workflow to dump
            output_path: Path to output file
            exclude_unset: Whether to exclude unset fields
            
        Raises:
            YAMLParseError: If YAML dumping fails
        """
        output_path = Path(output_path)
        logger.info(f"Dumping workflow to: {output_path}")
        
        try:
            # Convert to dict, excluding unset fields and handling enums
            workflow_dict = workflow.model_dump(
                exclude_unset=exclude_unset,
                exclude_none=True,
                mode='json'  # This ensures enums are serialized to their values
            )
            
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write YAML
            with open(output_path, 'w') as f:
                yaml.safe_dump(
                    workflow_dict,
                    f,
                    default_flow_style=False,
                    sort_keys=False
                )
            logger.info(f"Successfully dumped workflow to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to dump workflow: {e}")
            raise YAMLParseError(
                f"Failed to dump workflow to {output_path}",
                e,
                {"output_path": str(output_path)}
            )

    @classmethod
    def load_workflow(cls, workflow_path: Union[str, Path]) -> BioinfoFlow:
        """
        Load and validate a workflow definition from a YAML file.

        Args:
            workflow_path: Path to the workflow YAML file

        Returns:
            BioinfoFlow: Validated workflow object

        Raises:
            FileNotFoundError: If workflow file doesn't exist
            YAMLParseError: If YAML parsing fails
            SchemaValidationError: If workflow validation fails
        """
        workflow_path = Path(workflow_path)
        logger.info(f"Loading workflow from file: {workflow_path}")

        if not workflow_path.exists():
            logger.error(f"Workflow file not found: {workflow_path}")
            raise FileNotFoundError(str(workflow_path))

        try:
            with open(workflow_path, 'r') as f:
                workflow_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing failed: {e}")
            raise YAMLParseError(
                f"Error in file {workflow_path}",
                e,
                {"file_path": str(workflow_path)}
            )

        # Validate dictionary first
        cls.validate_dict(workflow_dict)

        try:
            workflow = BioinfoFlow(**workflow_dict)
            logger.info(f"Successfully loaded workflow '{workflow.name}' from file")
            return workflow
        except ValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            raise SchemaValidationError(
                "Workflow validation failed",
                e.errors(),
                {"file_path": str(workflow_path)}
            )

    @classmethod
    def load_workflow_from_string(cls, workflow_yaml: str) -> BioinfoFlow:
        """
        Load and validate a workflow definition from a YAML string.

        Args:
            workflow_yaml: YAML string containing workflow definition

        Returns:
            BioinfoFlow: Validated workflow object

        Raises:
            YAMLParseError: If YAML parsing fails
            SchemaValidationError: If workflow validation fails
        """
        logger.debug("Parsing workflow from string")
        
        try:
            workflow_dict = yaml.safe_load(workflow_yaml)
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing failed: {e}")
            raise YAMLParseError(
                "Failed to parse workflow string",
                e,
                {"yaml_preview": workflow_yaml[:100] + "..."}
            )

        # Validate dictionary first
        cls.validate_dict(workflow_dict)

        try:
            workflow = BioinfoFlow(**workflow_dict)
            logger.info(f"Successfully loaded workflow '{workflow.name}' from string")
            return workflow
        except ValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            raise SchemaValidationError(
                "Workflow validation failed",
                e.errors(),
                {"yaml_preview": workflow_yaml[:100] + "..."}
            )


if __name__ == "__main__":
    example_workflow = """
    name: test-workflow
    version: "0.1.0"
    global:
        working_dir: "/tmp/test"
        temp_dir: "/tmp/test/temp"
    workflow:
        steps:
            - name: step1
              type: single
              execution:
                mode: local
                command: "echo 'hello world'"
    """

    try:
        # Validate without loading
        workflow_dict = yaml.safe_load(example_workflow)
        WorkflowParser.validate_dict(workflow_dict)
        logger.info("Workflow validation successful")
        
        # Load workflow
        workflow = WorkflowParser.load_workflow_from_string(example_workflow)
        logger.info(f"Successfully loaded workflow: {workflow.name}")
        
        # Dump workflow
        WorkflowParser.dump_workflow(workflow, "/tmp/test/workflow.yaml")
        
    except (YAMLParseError, SchemaValidationError) as e:
        logger.error(f"Error processing workflow: {e}") 