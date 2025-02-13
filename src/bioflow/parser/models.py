"""
Data models for workflow configuration.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from enum import Enum, auto
from pathlib import Path


class StepType(Enum):
    """Step types."""
    SINGLE = "single"
    PARALLEL_GROUP = "parallel_group"
    SEQUENTIAL_GROUP = "sequential_group"


class InputType(Enum):
    """Input types."""
    FILE = "file"
    DIRECTORY = "directory"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"


@dataclass
class Notification:
    """Notification configuration."""
    email: Optional[str] = None
    slack_webhook: Optional[str] = None


@dataclass
class Global:
    """Global configuration."""
    working_dir: Path
    temp_dir: Path
    max_retries: Optional[int] = None
    notification: Optional[Notification] = None


@dataclass
class Resources:
    """Resource requirements."""
    cpu: Optional[int] = None
    memory: Optional[str] = None
    time: Optional[str] = None


@dataclass
class Mount:
    """Container mount configuration."""
    host: str
    container: str
    options: List[str] = field(default_factory=list)


@dataclass
class Container:
    """Container configuration."""
    type: str
    image: str
    version: Optional[str] = None
    mounts: List[Mount] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)


@dataclass
class Tool:
    """Tool configuration."""
    container: Optional[str] = None
    version: Optional[str] = None


@dataclass
class Input:
    """Step input."""
    name: str
    type: InputType
    value: str
    description: Optional[str] = None


@dataclass
class Output:
    """Step output."""
    name: str
    path: Path
    description: Optional[str] = None


@dataclass
class Step:
    """Workflow step."""
    name: str
    type: str
    command: Optional[str] = None
    tool: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    resources: Optional[Resources] = None
    inputs: List[Input] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)
    container: Optional[Container] = None
    hooks: Dict[str, List['Hook']] = field(default_factory=dict)
    conditions: List[str] = field(default_factory=list)
    steps: List['Step'] = field(default_factory=list)


@dataclass
class Condition:
    """Step condition."""
    when: str
    skip: bool = False


@dataclass
class ErrorHandler:
    """Error handler configuration."""
    on_error: str
    action: str
    max_retries: Optional[int] = None
    wait_time: Optional[str] = None


@dataclass
class Hook:
    """Hook configuration."""
    script: str
    name: Optional[str] = None


@dataclass
class Hooks:
    """Workflow hooks."""
    before_step: List[Hook] = field(default_factory=list)
    after_step: List[Hook] = field(default_factory=list)
    on_success: List[Hook] = field(default_factory=list)
    on_failure: List[Hook] = field(default_factory=list)


@dataclass
class Parameter:
    """Workflow parameter."""
    type: str
    name: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None
    description: Optional[str] = None
    value: Optional[Any] = None
    enum: Optional[List[str]] = None


@dataclass
class Workflow:
    """Workflow configuration."""
    name: str
    version: str
    description: Optional[str] = None
    global_config: Optional[Global] = None
    env: Dict[str, str] = field(default_factory=dict)
    resources: Dict[str, Resources] = field(default_factory=dict)
    tools: Dict[str, Tool] = field(default_factory=dict)
    steps: List[Step] = field(default_factory=list)
    conditions: Dict[str, Condition] = field(default_factory=dict)
    error_handlers: List[ErrorHandler] = field(default_factory=list)
    hooks: Dict[str, List[Hook]] = field(default_factory=dict)
    parameters: Dict[str, Parameter] = field(default_factory=dict) 