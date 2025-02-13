"""
Tests for container executor.
"""
import os
import pytest
from pathlib import Path
from datetime import datetime

from bioflow.parser.models import Step, StepType, Container, Mount
from bioflow.engine.models import ExecutionContext, ExecutionStatus, Workflow
from bioflow.engine.executors.container import ContainerExecutor
from bioflow.engine.exceptions import ContainerError


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
    return ContainerExecutor(context)


def test_can_execute_docker_step(executor):
    """Test can_execute with Docker step."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo hello",
        container=Container(
            type="docker",
            image="alpine"
        )
    )
    assert executor.can_execute(step)


def test_cannot_execute_non_container_step(executor):
    """Test can_execute with non-container step."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo hello"
    )
    assert not executor.can_execute(step)


def test_cannot_execute_non_docker_container(executor):
    """Test can_execute with non-Docker container."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo hello",
        container=Container(
            type="singularity",
            image="test.sif"
        )
    )
    assert not executor.can_execute(step)


@pytest.mark.asyncio
async def test_execute_successful_container(executor):
    """Test executing a successful container."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo hello",
        container=Container(
            type="docker",
            image="alpine",
            version="latest"
        )
    )
    
    state = await executor.execute(step)
    
    assert state.status == ExecutionStatus.COMPLETED
    assert state.exit_code == 0
    assert state.error_message is None
    assert state.start_time is not None
    assert state.end_time is not None


@pytest.mark.asyncio
async def test_execute_failing_container(executor):
    """Test executing a failing container."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="exit 1",
        container=Container(
            type="docker",
            image="alpine",
            version="latest"
        )
    )
    
    state = await executor.execute(step)
    
    assert state.status == ExecutionStatus.FAILED
    assert state.exit_code == 1
    assert state.error_message is not None
    assert state.start_time is not None
    assert state.end_time is not None


@pytest.mark.asyncio
async def test_execute_with_environment(executor):
    """Test executing container with environment variables."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo $TEST_VAR",
        container=Container(
            type="docker",
            image="alpine",
            environment={"TEST_VAR": "hello"}
        )
    )
    
    state = await executor.execute(step)
    
    assert state.status == ExecutionStatus.COMPLETED
    assert state.exit_code == 0


@pytest.mark.asyncio
async def test_execute_with_mounts(executor, tmp_path):
    """Test executing container with volume mounts."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="cat /data/test.txt",
        container=Container(
            type="docker",
            image="alpine",
            mounts=[
                Mount(
                    host=str(tmp_path),
                    container="/data"
                )
            ]
        )
    )
    
    state = await executor.execute(step)
    
    assert state.status == ExecutionStatus.COMPLETED
    assert state.exit_code == 0


@pytest.mark.asyncio
async def test_execute_nonexistent_image(executor):
    """Test executing container with nonexistent image."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        command="echo hello",
        container=Container(
            type="docker",
            image="nonexistent_image_xyz"
        )
    )
    
    state = await executor.execute(step)
    
    assert state.status == ExecutionStatus.FAILED
    assert state.error_message is not None


def test_prepare_env(executor):
    """Test preparing environment variables."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        container=Container(
            type="docker",
            image="alpine",
            environment={"CONTAINER_VAR": "value"}
        )
    )
    
    env = executor._prepare_env(step)
    
    assert "TEST_VAR" in env  # From context
    assert env["TEST_VAR"] == "test_value"
    assert "CONTAINER_VAR" in env  # From container
    assert env["CONTAINER_VAR"] == "value"


def test_prepare_mounts(executor):
    """Test preparing volume mounts."""
    step = Step(
        name="test",
        type=StepType.SINGLE,
        container=Container(
            type="docker",
            image="alpine",
            mounts=[
                Mount(
                    host="/host/path",
                    container="/container/path"
                )
            ]
        )
    )
    
    mounts = executor._prepare_mounts(step, Path("/work/dir"))
    
    assert len(mounts) == 2  # Working dir mount + custom mount
    assert any(m.container == "/workspace" for m in mounts)  # Working dir mount
    assert any(m.container == "/container/path" for m in mounts)  # Custom mount 