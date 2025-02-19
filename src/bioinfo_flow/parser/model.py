"""
BioinfoFlow workflow specification models.
This module contains the Pydantic models that represent the workflow specification.
"""

from enum import Enum
from typing import Dict, List, Optional, Union, Annotated
from pydantic import BaseModel, Field, model_validator
import re


class StepType(str, Enum):
    """Step type enumeration."""
    SINGLE = "single"
    PARALLEL_GROUP = "parallel_group"
    SEQUENTIAL_GROUP = "sequential_group"


class ExecutionMode(str, Enum):
    """Execution mode enumeration."""
    CONTAINER = "container"
    LOCAL = "local"


class DataType(str, Enum):
    """Data type enumeration for inputs and outputs."""
    FILE = "file"
    DIRECTORY = "directory"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"


class NotificationConfig(BaseModel):
    """Notification configuration settings."""
    email: Optional[str] = None
    slack_webhook: Optional[str] = None
    discord_webhook: Optional[str] = None
    feishu_webhook: Optional[str] = None


class GlobalConfig(BaseModel):
    """Global configuration settings."""
    working_dir: str = Field(..., description="Working directory path")
    temp_dir: str = Field(..., description="Temporary directory path")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    notification: Optional[NotificationConfig] = Field(default_factory=NotificationConfig)


class ResourceConfig(BaseModel):
    """Resource configuration."""
    default: Dict[str, Union[int, str]] = Field(
        default_factory=lambda: {
            "cpu_units": 1,
            "memory": "1G",
            "time": None
        },
        description="Default resource settings"
    )
    gpu_support: bool = Field(default=False, description="Whether GPU is supported")


class ContainerVolume(BaseModel):
    """Container volume mount configuration."""
    host: str = Field(..., description="Host path")
    container: str = Field(..., description="Container path")


class ContainerConfig(BaseModel):
    """Container configuration."""
    image: str = Field(..., description="Container image")
    version: str = Field(..., description="Container version")
    volumes: List[ContainerVolume] = Field(default_factory=list, description="Volume mounts")


class StepResources(BaseModel):
    """Step resource requirements."""
    cpu: str = Field(default="1", description="CPU requirement")
    memory: str = Field(default="1G", description="Memory requirement")
    time: Optional[str] = Field(None, description="Time limit")
    gpu: Optional[str] = Field(None, description="GPU requirement")


class Checkpoint(BaseModel):
    """Checkpoint configuration."""
    enabled: bool = Field(default=False, description="Whether checkpoint is enabled")


class Hook(BaseModel):
    """Hook definition."""
    name: str = Field(..., description="Hook name")
    script: str = Field(..., description="Script to execute")


class Hooks(BaseModel):
    """Workflow hooks configuration."""
    before_step: List[Hook] = Field(default_factory=list)
    after_step: List[Hook] = Field(default_factory=list)
    on_success: List[Hook] = Field(default_factory=list)
    on_failure: List[Hook] = Field(default_factory=list)


class Condition(BaseModel):
    """Condition definition."""
    when: str = Field(..., description="Condition expression")
    skip: bool = Field(default=False, description="Whether to skip when condition is met")


class Parameter(BaseModel):
    """Workflow parameter definition."""
    name: str = Field(..., description="Parameter name")
    type: DataType = Field(..., description="Parameter type")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Union[str, int, float, bool]] = Field(None, description="Default value")
    description: Optional[str] = Field(None, description="Parameter description")


class IODefinition(BaseModel):
    """Input/Output definition."""
    name: str = Field(..., description="Name of the input/output")
    type: DataType = Field(..., description="Type of the input/output")
    value: Optional[str] = Field(None, description="Value or path")
    pattern: Optional[str] = Field(None, description="Glob pattern for matching files")
    description: Optional[str] = Field(None, description="Description")


class Execution(BaseModel):
    """Step execution configuration."""
    mode: ExecutionMode = Field(..., description="Execution mode")
    command: str = Field(..., description="Command to execute")
    container: Optional[ContainerConfig] = Field(None, description="Container configuration")

    @model_validator(mode='after')
    def validate_container_config(self):
        """Validate that container config is present when mode is container."""
        if self.mode == ExecutionMode.CONTAINER and not self.container:
            raise ValueError("Container configuration is required when mode is 'container'")
        return self


# Regex pattern for valid names
name_pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')


class Step(BaseModel):
    """Workflow step definition."""
    name: str = Field(..., description="Step name")
    type: StepType = Field(..., description="Step type")
    inputs: List[IODefinition] = Field(default_factory=list, description="Input definitions")
    outputs: List[IODefinition] = Field(default_factory=list, description="Output definitions")
    execution: Execution = Field(..., description="Execution configuration")
    resources: StepResources = Field(default_factory=StepResources, description="Resource requirements")
    checkpoint: Checkpoint = Field(default_factory=Checkpoint, description="Checkpoint configuration")
    depends_on: List[str] = Field(default_factory=list, description="Dependencies")

    @model_validator(mode='after')
    def validate_name(self):
        """Validate step name format."""
        if not name_pattern.match(self.name):
            raise ValueError(
                "Step name must start with a letter and contain only letters, numbers, underscores, and hyphens"
            )
        return self


class Workflow(BaseModel):
    """Workflow definition."""
    steps: List[Step] = Field(..., description="Workflow steps")


class BioinfoFlow(BaseModel):
    """Root workflow specification."""
    name: str = Field(..., description="Workflow name")
    version: str = Field(..., description="Workflow version")
    description: Optional[str] = Field(None, description="Workflow description")
    global_config: GlobalConfig = Field(..., alias="global", description="Global configuration")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    resources: ResourceConfig = Field(default_factory=ResourceConfig, description="Resource configuration")
    workflow: Workflow = Field(..., description="Workflow definition")
    parameters: List[Parameter] = Field(default_factory=list, description="Workflow parameters")
    hooks: Optional[Hooks] = Field(default_factory=Hooks, description="Workflow hooks")
    conditions: Dict[str, Condition] = Field(default_factory=dict, description="Workflow conditions")

    @model_validator(mode='after')
    def validate_name(self):
        """Validate workflow name format."""
        if not name_pattern.match(self.name):
            raise ValueError(
                "Workflow name must start with a letter and contain only letters, numbers, underscores, and hyphens"
            )
        return self

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        json_encoders = {
            Enum: lambda v: v.value
        }


# Example usage:
if __name__ == "__main__":
    # Example workflow definition
    workflow_dict = {
        "name": "variant-calling",
        "version": "1.0.0",
        "description": "Germline variant calling pipeline",
        "global": {
            "working_dir": "/data/analysis",
            "temp_dir": "/tmp/variant_calling",
            "notification": {
                "email": "admin@example.com",
                "slack_webhook": "https://hooks.slack.com/services/xxx"
            }
        },
        "env": {
            "REFERENCE_GENOME": "/ref/hg38/genome.fa"
        },
        "workflow": {
            "steps": [
                {
                    "name": "fastqc",
                    "type": "single",
                    "inputs": [
                        {
                            "name": "reads",
                            "type": "file",
                            "pattern": "*.fastq.gz"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "qc_report",
                            "type": "directory",
                            "value": "qc_results"
                        }
                    ],
                    "execution": {
                        "mode": "container",
                        "command": "fastqc ${inputs.reads} -o ${outputs.qc_report}",
                        "container": {
                            "image": "quay.io/biocontainers/fastqc",
                            "version": "0.11.9--0"
                        }
                    }
                }
            ]
        },
        "conditions": {
            "file_exists": {
                "when": "exists:/path/to/file",
                "skip": False
            }
        }
    }

    # Parse and validate workflow
    try:
        workflow = BioinfoFlow(**workflow_dict)
        print(f"Successfully parsed workflow: {workflow.name}")
    except Exception as e:
        print(f"Error parsing workflow: {e}")
