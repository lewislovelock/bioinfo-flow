"""
Tests for base executor.
"""
import pytest
from pathlib import Path
from datetime import datetime

from bioflow.parser.models import Step, StepType, Container, Input, InputType
from bioflow.engine.models import ExecutionContext, StepExecutionState, ExecutionStatus, Workflow
from bioflow.engine.executors.base import BaseExecutor


class TestExecutor(BaseExecutor):
    """Test executor implementation."""
    
    def can_execute(self, step: Step) -> bool:
        return True
    
    async def execute(self, step: Step) -> StepExecutionState:
        state = self._create_state(step)
        state.status = ExecutionStatus.COMPLETED
        return state


@pytest.fixture
def context():
    """Create test execution context."""
    workflow = Workflow(name="test", version="1.0")
    return ExecutionContext(
        workflow=workflow,
        working_dir=Path("/tmp/work"),
        temp_dir=Path("/tmp/temp"),
        env={"GLOBAL": "value"}
    )


@pytest.fixture
def executor(context):
    """Create test executor."""
    return TestExecutor(context)


def test_create_state(executor):
    """Test creating execution state."""
    step = Step(name="test", type=StepType.SINGLE)
    state = executor._create_state(
        step,
        status=ExecutionStatus.RUNNING,
        start_time=datetime.now()
    )
    
    assert state.step == step
    assert state.status == ExecutionStatus.RUNNING
    assert state.start_time is not None


def test_update_state(executor):
    """Test updating execution state."""
    step = Step(name="test", type=StepType.SINGLE)
    state = StepExecutionState(step=step)
    
    executor._update_state(
        state,
        status=ExecutionStatus.RUNNING,
        start_time=datetime.now()
    )
    
    assert state.status == ExecutionStatus.RUNNING
    assert state.start_time is not None


def test_prepare_env(executor):
    """Test preparing environment variables."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        container=Container(
            type="docker",
            image="test:latest",
            environment={"STEP": "value"}
        )
    )
    
    env = executor._prepare_env(step)
    
    assert env["GLOBAL"] == "value"  # From context
    assert env["STEP"] == "value"    # From step


def test_resolve_inputs(executor):
    """Test resolving input values."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        inputs=[
            Input(
                name="input1",
                type=InputType.STRING,
                value="test_value"
            )
        ]
    )
    
    inputs = executor._resolve_inputs(step)
    
    assert inputs["input1"] == "test_value"


def test_validate_outputs(executor):
    """Test validating outputs."""
    step = Step(name="test", type=StepType.SINGLE)
    outputs = {"output1": "value1"}
    
    assert executor._validate_outputs(step, outputs)


@pytest.mark.asyncio
async def test_execute(executor):
    """Test executing a step."""
    step = Step(name="test", type=StepType.SINGLE)
    
    state = await executor.execute(step)
    
    assert state.step == step
    assert state.status == ExecutionStatus.COMPLETED 