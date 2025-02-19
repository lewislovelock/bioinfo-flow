"""
BioinfoFlow workflow specification models.
This module contains the Pydantic models that represent the workflow specification.
"""

from enum import Enum
from typing import Dict, List, Optional, Union, Annotated, Any
from pathlib import Path
import json
from pydantic import BaseModel, Field, model_validator, ValidationError
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

    @model_validator(mode='after')
    def validate_notification_config(self):
        """Validate that at least one notification method is configured if any are present."""
        if any([self.email, self.slack_webhook, self.discord_webhook, self.feishu_webhook]):
            if self.email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', self.email):
                raise ValueError("Invalid email format")
            if self.slack_webhook and not self.slack_webhook.startswith('https://hooks.slack.com/'):
                raise ValueError("Invalid Slack webhook URL")
            if self.discord_webhook and not self.discord_webhook.startswith('https://discord.com/api/webhooks/'):
                raise ValueError("Invalid Discord webhook URL")
            if self.feishu_webhook and not self.feishu_webhook.startswith('https://open.feishu.cn/'):
                raise ValueError("Invalid Feishu webhook URL")
        return self


class GlobalConfig(BaseModel):
    """Global configuration settings."""
    working_dir: str = Field(..., description="Working directory path")
    temp_dir: str = Field(..., description="Temporary directory path")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    notification: Optional[NotificationConfig] = Field(default_factory=NotificationConfig)

    @model_validator(mode='after')
    def validate_directories(self):
        """Validate that working_dir and temp_dir are absolute paths."""
        if not Path(self.working_dir).is_absolute():
            raise ValueError("working_dir must be an absolute path")
        if not Path(self.temp_dir).is_absolute():
            raise ValueError("temp_dir must be an absolute path")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        return self


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

    @model_validator(mode='after')
    def validate_resources(self):
        """Validate resource values."""
        if "cpu_units" in self.default:
            cpu = self.default["cpu_units"]
            if isinstance(cpu, int) and cpu < 1:
                raise ValueError("cpu_units must be at least 1")
        
        if "memory" in self.default:
            memory = str(self.default["memory"])
            if not re.match(r'^\d+[KMGT]B?$', memory):
                raise ValueError("Invalid memory format (e.g., '1G', '512MB')")
        
        if "time" in self.default and self.default["time"]:
            time = str(self.default["time"])
            if not re.match(r'^\d+[smhd]$', time):
                raise ValueError("Invalid time format (e.g., '1h', '30m')")
        
        return self


class ContainerVolume(BaseModel):
    """Container volume mount configuration."""
    host: str = Field(..., description="Host path")
    container: str = Field(..., description="Container path")

    @model_validator(mode='after')
    def validate_paths(self):
        """Validate volume paths."""
        if not self.container.startswith('/'):
            raise ValueError("Container path must be absolute")
        return self


class ContainerConfig(BaseModel):
    """Container configuration."""
    image: str = Field(..., description="Container image")
    version: str = Field(..., description="Container version")
    volumes: List[ContainerVolume] = Field(default_factory=list, description="Volume mounts")

    @model_validator(mode='after')
    def validate_image(self):
        """Validate container image format."""
        if ':' in self.image and self.version != self.image.split(':')[1]:
            raise ValueError("Version in image tag must match version field")
        return self


class StepResources(BaseModel):
    """Step resource requirements."""
    cpu: str = Field(default="1", description="CPU requirement")
    memory: str = Field(default="1G", description="Memory requirement")
    time: Optional[str] = Field(None, description="Time limit")
    gpu: Optional[str] = Field(None, description="GPU requirement")

    @model_validator(mode='after')
    def validate_resources(self):
        """Validate resource values."""
        if not re.match(r'^\d+$', self.cpu):
            raise ValueError("Invalid CPU format (must be a number)")
        
        if not re.match(r'^\d+[KMGT]B?$', self.memory):
            raise ValueError("Invalid memory format (e.g., '1G', '512MB')")
        
        if self.time and not re.match(r'^\d+[smhd]$', self.time):
            raise ValueError("Invalid time format (e.g., '1h', '30m')")
        
        if self.gpu and not re.match(r'^\d+$', self.gpu):
            raise ValueError("Invalid GPU format (must be a number)")
        
        return self


class Checkpoint(BaseModel):
    """Checkpoint configuration."""
    enabled: bool = Field(default=False, description="Whether checkpoint is enabled")


class Hook(BaseModel):
    """Hook definition."""
    name: str = Field(..., description="Hook name")
    script: str = Field(..., description="Script to execute")

    @model_validator(mode='after')
    def validate_script(self):
        """Validate script path."""
        if not self.script.endswith(('.sh', '.py', '.pl', '.rb')):
            raise ValueError("Script must be a shell, Python, Perl, or Ruby script")
        return self


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

    @model_validator(mode='after')
    def validate_condition(self):
        """Validate condition expression format."""
        valid_prefixes = ['exists:', 'size:', 'env:', 'step:']
        if not any(self.when.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Condition must start with one of: {', '.join(valid_prefixes)}")
        return self


class Parameter(BaseModel):
    """Workflow parameter definition."""
    name: str = Field(..., description="Parameter name")
    type: DataType = Field(..., description="Parameter type")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Union[str, int, float, bool]] = Field(None, description="Default value")
    description: Optional[str] = Field(None, description="Parameter description")

    @model_validator(mode='after')
    def validate_default_value(self):
        """Validate that default value matches the parameter type."""
        if self.default is not None:
            if self.type == DataType.INTEGER and not isinstance(self.default, int):
                raise ValueError("Default value must be an integer")
            elif self.type == DataType.FLOAT and not isinstance(self.default, (int, float)):
                raise ValueError("Default value must be a number")
            elif self.type == DataType.BOOLEAN and not isinstance(self.default, bool):
                raise ValueError("Default value must be a boolean")
        return self


class IODefinition(BaseModel):
    """Input/Output definition."""
    name: str = Field(..., description="Name of the input/output")
    type: DataType = Field(..., description="Type of the input/output")
    value: Optional[str] = Field(None, description="Value or path")
    pattern: Optional[str] = Field(None, description="Glob pattern for matching files")
    description: Optional[str] = Field(None, description="Description")

    @model_validator(mode='after')
    def validate_io(self):
        """Validate input/output configuration."""
        if self.type in [DataType.FILE, DataType.DIRECTORY] and self.pattern:
            if not any(c in self.pattern for c in '*?[]'):
                raise ValueError("File/directory pattern must contain at least one glob character")
        return self


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
        if self.mode == ExecutionMode.LOCAL and self.container:
            raise ValueError("Container configuration should not be present when mode is 'local'")
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
    def validate_step(self):
        """Validate step configuration."""
        # Validate name format
        if not name_pattern.match(self.name):
            raise ValueError(
                "Step name must start with a letter and contain only letters, numbers, underscores, and hyphens"
            )
        
        # Validate unique input/output names
        input_names = [i.name for i in self.inputs]
        if len(input_names) != len(set(input_names)):
            raise ValueError("Input names must be unique within a step")
        
        output_names = [o.name for o in self.outputs]
        if len(output_names) != len(set(output_names)):
            raise ValueError("Output names must be unique within a step")
        
        # Validate group types
        if self.type in [StepType.PARALLEL_GROUP, StepType.SEQUENTIAL_GROUP]:
            if not self.depends_on:
                raise ValueError(f"{self.type} must have at least one dependency")
        
        return self

    def get_input(self, name: str) -> Optional[IODefinition]:
        """Get input by name."""
        return next((i for i in self.inputs if i.name == name), None)

    def get_output(self, name: str) -> Optional[IODefinition]:
        """Get output by name."""
        return next((o for o in self.outputs if o.name == name), None)

    def has_dependency(self, step_name: str) -> bool:
        """Check if this step depends on another step."""
        return step_name in self.depends_on


class Workflow(BaseModel):
    """Workflow definition."""
    steps: List[Step] = Field(..., description="Workflow steps")

    @model_validator(mode='after')
    def validate_workflow(self):
        """Validate workflow configuration."""
        # Validate unique step names
        step_names = [s.name for s in self.steps]
        if len(step_names) != len(set(step_names)):
            raise ValueError("Step names must be unique within the workflow")
        
        # Validate dependencies exist
        all_steps = set(step_names)
        for step in self.steps:
            missing_deps = set(step.depends_on) - all_steps
            if missing_deps:
                raise ValueError(f"Step '{step.name}' has missing dependencies: {missing_deps}")
        
        return self

    def get_step(self, name: str) -> Optional[Step]:
        """Get step by name."""
        return next((s for s in self.steps if s.name == name), None)

    def get_dependent_steps(self, step_name: str) -> List[Step]:
        """Get steps that depend on the given step."""
        return [s for s in self.steps if step_name in s.depends_on]

    def get_root_steps(self) -> List[Step]:
        """Get steps with no dependencies."""
        return [s for s in self.steps if not s.depends_on]

    def get_leaf_steps(self) -> List[Step]:
        """Get steps that no other steps depend on."""
        dependent_steps = {dep for s in self.steps for dep in s.depends_on}
        return [s for s in self.steps if s.name not in dependent_steps]


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
    def validate_workflow(self):
        """Validate complete workflow configuration."""
        # Validate name format
        if not name_pattern.match(self.name):
            raise ValueError(
                "Workflow name must start with a letter and contain only letters, numbers, underscores, and hyphens"
            )
        
        # Validate parameter names are unique
        param_names = [p.name for p in self.parameters]
        if len(param_names) != len(set(param_names)):
            raise ValueError("Parameter names must be unique")
        
        # Validate condition names
        for name in self.conditions:
            if not name_pattern.match(name):
                raise ValueError(
                    f"Condition name '{name}' must start with a letter and contain only letters, numbers, underscores, and hyphens"
                )
        
        return self

    def get_step(self, name: str) -> Optional[Step]:
        """Get step by name."""
        return self.workflow.get_step(name)

    def get_parameter(self, name: str) -> Optional[Parameter]:
        """Get parameter by name."""
        return next((p for p in self.parameters if p.name == name), None)

    def get_condition(self, name: str) -> Optional[Condition]:
        """Get condition by name."""
        return self.conditions.get(name)

    def get_root_steps(self) -> List[Step]:
        """Get steps with no dependencies."""
        return self.workflow.get_root_steps()

    def get_leaf_steps(self) -> List[Step]:
        """Get steps that no other steps depend on."""
        return self.workflow.get_leaf_steps()

    @classmethod
    def generate_json_schema(cls, output_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Generate JSON schema for the workflow specification.
        
        Args:
            output_path: Optional path to write schema to
            
        Returns:
            Dictionary containing the JSON schema
        """
        schema = cls.model_json_schema()
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(schema, f, indent=2)
        
        return schema

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
