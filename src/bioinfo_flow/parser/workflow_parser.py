"""
Workflow parser for loading and validating workflow definitions.
"""

import os
from pathlib import Path
from typing import Union, Dict, Any

import yaml
from pydantic import ValidationError

from bioinfo_flow.parser.model import BioinfoFlow


class WorkflowParser:
    """Parser for workflow definitions."""

    @staticmethod
    def load_workflow(workflow_path: Union[str, Path]) -> BioinfoFlow:
        """
        Load and validate a workflow definition from a YAML file.

        Args:
            workflow_path: Path to the workflow YAML file

        Returns:
            BioinfoFlow: Validated workflow object

        Raises:
            FileNotFoundError: If workflow file doesn't exist
            yaml.YAMLError: If YAML parsing fails
            ValidationError: If workflow validation fails
        """
        workflow_path = Path(workflow_path)
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

        try:
            with open(workflow_path, 'r') as f:
                workflow_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing workflow YAML: {e}")

        try:
            workflow = BioinfoFlow(**workflow_dict)
            return workflow
        except ValidationError as e:
            raise ValidationError(
                f"Error validating workflow: {e}",
                model=BioinfoFlow
            )

    @staticmethod
    def load_workflow_from_string(workflow_yaml: str) -> BioinfoFlow:
        """
        Load and validate a workflow definition from a YAML string.

        Args:
            workflow_yaml: YAML string containing workflow definition

        Returns:
            BioinfoFlow: Validated workflow object

        Raises:
            yaml.YAMLError: If YAML parsing fails
            ValidationError: If workflow validation fails
        """
        try:
            workflow_dict = yaml.safe_load(workflow_yaml)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing workflow YAML: {e}")

        try:
            workflow = BioinfoFlow(**workflow_dict)
            return workflow
        except ValidationError as e:
            raise ValidationError(
                f"Error validating workflow: {e}",
                model=BioinfoFlow
            )


if __name__ == "__main__":
    # When running as script, use relative imports for testing
    # from bioinfo_flow.parser.model import BioinfoFlow
    
    example_workflow = """
    name: test-workflow
    version: "1.0.0"
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
        workflow = WorkflowParser.load_workflow_from_string(example_workflow)
        print(f"Successfully loaded workflow: {workflow.name}")
    except (yaml.YAMLError, ValidationError) as e:
        print(f"Error loading workflow: {e}") 