"""
Core data models for BioinfoFlow.

This module contains the core data models that represent the components
of a BioinfoFlow workflow.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from pathlib import Path
import enum

class StepStatus(enum.Enum):
    """Represents the current status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class InputType(enum.Enum):
    """Type of workflow input."""
    FILE = "file"  # Single file input
    SAMPLE_GROUP = "sample_group"  # Group of related files/data (e.g., paired-end reads)

@dataclass
class ResourceRequirements:
    """Resource requirements for a workflow step."""
    cpu: int = 1
    memory: str = "1GB"  # Memory string like "4GB", "512MB"
    disk: Optional[str] = None
    gpu: Optional[int] = None

@dataclass
class ContainerConfig:
    """Container configuration for a workflow step."""
    image: str  # Docker/Singularity image reference
    tag: str = "latest"
    volumes: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)

@dataclass
class InputConfig:
    """Configuration for workflow inputs."""
    type: InputType  # Type of input (file or sample_group)
    pattern: str  # Glob pattern or file path
    format: Optional[str] = None  # For sample_group inputs: csv, tsv, etc.
    columns: Optional[List[Dict[str, str]]] = None  # For sample_group inputs
    description: Optional[str] = None  # Optional description of the input

@dataclass
class OutputConfig:
    """Configuration for workflow outputs."""
    path: str
    type: str = "file"
    description: Optional[str] = None

@dataclass
class Step:
    """Represents a single step in a workflow."""
    name: str
    container: ContainerConfig
    command: str
    inputs: Dict[str, str]  # Input name -> reference
    outputs: Dict[str, OutputConfig]
    resources: ResourceRequirements = field(default_factory=ResourceRequirements)
    after: List[str] = field(default_factory=list)  # Dependencies
    foreach: Optional[str] = None  # For sample iteration
    status: StepStatus = StepStatus.PENDING

@dataclass
class WorkflowConfig:
    """Global workflow configuration."""
    max_retries: int = 3
    work_dir: Path = Path("work_dir")
    ref_paths: Dict[str, Path] = field(default_factory=dict)

@dataclass
class Workflow:
    """Root workflow definition."""
    name: str
    version: str
    description: Optional[str] = None
    config: WorkflowConfig = field(default_factory=WorkflowConfig)
    inputs: Dict[str, InputConfig] = field(default_factory=dict)
    steps: Dict[str, Step] = field(default_factory=dict) 