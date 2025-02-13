"""
Tests for command executor.
"""
import os
import pytest
from pathlib import Path
from datetime import datetime

from bioflow.parser.models import Step, StepType, Container
from bioflow.engine.models import ExecutionContext, ExecutionStatus, Workflow
from bioflow.engine.executors.command import CommandExecutor


@pytest.fixture
def context(tmp_path):
    """Create test execution context."""
    workflow = Workflow(name="test", version="1.0")
    return ExecutionContext(
        workflow=workflow,
        working_dir=tmp_path / "work",
        temp_dir=tmp_path / "temp",
        env={"TEST_VAR": "test_value"}
    )


@pytest.fixture
def executor(context):
    """Create test executor."""
    return CommandExecutor(context)


def test_can_execute_command_step(executor):
    """Test can_execute with command step."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo hello"
    )
    assert executor.can_execute(step)


def test_cannot_execute_container_step(executor):
    """Test can_execute with container step."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo hello",
        container=Container(
            type="docker",
            image="test:latest"
        )
    )
    assert not executor.can_execute(step)


def test_cannot_execute_without_command(executor):
    """Test can_execute without command."""
    step = Step(
        name="test",
        type=StepType.SINGLE
    )
    assert not executor.can_execute(step)


@pytest.mark.asyncio
async def test_execute_successful_command(executor):
    """Test executing a successful command."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo hello"
    )
    
    state = await executor.execute(step)
    
    assert state.status == ExecutionStatus.COMPLETED
    assert state.exit_code == 0
    assert state.error_message is None
    assert state.start_time is not None
    assert state.end_time is not None


@pytest.mark.asyncio
async def test_execute_failing_command(executor):
    """Test executing a failing command."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="false"
    )
    
    state = await executor.execute(step)
    
    assert state.status == ExecutionStatus.FAILED
    assert state.exit_code == 1
    assert state.error_message is not None
    assert state.start_time is not None
    assert state.end_time is not None


@pytest.mark.asyncio
async def test_execute_invalid_command(executor):
    """Test executing an invalid command."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="nonexistent_command"
    )
    
    state = await executor.execute(step)
    
    assert state.status == ExecutionStatus.FAILED
    assert state.error_message is not None
    assert state.start_time is not None
    assert state.end_time is not None


@pytest.mark.asyncio
async def test_execute_with_working_directory(executor, tmp_path):
    """Test executing command in working directory."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="pwd"
    )
    
    state = await executor.execute(step)
    
    assert state.status == ExecutionStatus.COMPLETED
    assert state.exit_code == 0
    assert os.path.exists(executor.context.working_dir / step.name)


def test_prepare_env(executor):
    """Test preparing environment variables."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo hello"
    )
    
    env = executor._prepare_env(step)
    
    assert "TEST_VAR" in env
    assert env["TEST_VAR"] == "test_value"
    assert "PATH" in env  # Should include system environment 