"""
Data models for workflow execution.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..parser.models import Step, Workflow


class ExecutionStatus(Enum):
    """Execution status of a step or workflow."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()
    CANCELLED = auto()


@dataclass
class StepExecutionState:
    """Execution state of a workflow step."""
    step: Step
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    outputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Context for workflow execution."""
    workflow: Workflow
    working_dir: Path
    temp_dir: Path
    env: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    step_states: Dict[str, StepExecutionState] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of workflow execution."""
    workflow: Workflow
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    step_states: Dict[str, StepExecutionState] = field(default_factory=dict)
    error_message: Optional[str] = None 