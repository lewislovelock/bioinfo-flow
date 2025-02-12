"""
Tests for workflow execution models.
"""
import pytest
from datetime import datetime
from pathlib import Path

from src.bioflow.parser.models import Step, Workflow, StepType
from src.bioflow.engine.models import (
    ExecutionStatus,
    StepExecutionState,
    ExecutionContext,
    ExecutionResult
)


def test_execution_status():
    """Test ExecutionStatus enum."""
    assert ExecutionStatus.PENDING.name == "PENDING"
    assert ExecutionStatus.RUNNING.name == "RUNNING"
    assert ExecutionStatus.COMPLETED.name == "COMPLETED"
    assert ExecutionStatus.FAILED.name == "FAILED"
    assert ExecutionStatus.SKIPPED.name == "SKIPPED"
    assert ExecutionStatus.CANCELLED.name == "CANCELLED"


def test_step_execution_state():
    """Test StepExecutionState class."""
    step = Step(name="test_step", type=StepType.SINGLE)
    state = StepExecutionState(step=step)
    
    assert state.step == step
    assert state.status == ExecutionStatus.PENDING
    assert state.start_time is None
    assert state.end_time is None
    assert state.exit_code is None
    assert state.error_message is None
    assert state.retry_count == 0
    assert state.outputs == {}


def test_execution_context():
    """Test ExecutionContext class."""
    workflow = Workflow(name="test_workflow", version="1.0")
    working_dir = Path("/tmp/working")
    temp_dir = Path("/tmp/temp")
    
    context = ExecutionContext(
        workflow=workflow,
        working_dir=working_dir,
        temp_dir=temp_dir,
        env={"PATH": "/usr/bin"},
        parameters={"input": "test.txt"}
    )
    
    assert context.workflow == workflow
    assert context.working_dir == working_dir
    assert context.temp_dir == temp_dir
    assert context.env == {"PATH": "/usr/bin"}
    assert context.parameters == {"input": "test.txt"}
    assert context.step_states == {}


def test_execution_result():
    """Test ExecutionResult class."""
    workflow = Workflow(name="test_workflow", version="1.0")
    start_time = datetime.now()
    
    result = ExecutionResult(
        workflow=workflow,
        status=ExecutionStatus.COMPLETED,
        start_time=start_time
    )
    
    assert result.workflow == workflow
    assert result.status == ExecutionStatus.COMPLETED
    assert result.start_time == start_time
    assert result.end_time is None
    assert result.step_states == {}
    assert result.error_message is None


def test_step_execution_state_with_data():
    """Test StepExecutionState class with data."""
    step = Step(name="test_step", type=StepType.SINGLE)
    start_time = datetime.now()
    
    state = StepExecutionState(
        step=step,
        status=ExecutionStatus.RUNNING,
        start_time=start_time,
        retry_count=1,
        outputs={"result": "output.txt"}
    )
    
    assert state.step == step
    assert state.status == ExecutionStatus.RUNNING
    assert state.start_time == start_time
    assert state.retry_count == 1
    assert state.outputs == {"result": "output.txt"} 