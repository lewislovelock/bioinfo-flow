"""
Tests for workflow executor.
"""
import os
import pytest
from pathlib import Path
from datetime import datetime

from bioflow.parser.models import (
    Step,
    StepType,
    Container,
    Mount,
    Workflow
)
from bioflow.engine.models import ExecutionStatus
from bioflow.engine.workflow import WorkflowEngine
from bioflow.engine.exceptions import ExecutionError


@pytest.fixture
def workflow():
    """Create test workflow."""
    return Workflow(
        name="test_workflow",
        version="1.0",
        env={"GLOBAL_VAR": "value"}
    )


@pytest.fixture
def executor(workflow, tmp_path):
    """Create test executor."""
    return WorkflowEngine(
        workflow=workflow,
        working_dir=tmp_path / "work",
        temp_dir=tmp_path / "temp"
    )


def test_init(executor, tmp_path):
    """Test executor initialization."""
    assert executor.workflow.name == "test_workflow"
    assert executor.working_dir == tmp_path / "work"
    assert executor.temp_dir == tmp_path / "temp"
    assert len(executor.executors) == 2  # CommandExecutor and ContainerExecutor
    assert executor.context.env == {"GLOBAL_VAR": "value"}


@pytest.mark.asyncio
async def test_execute_empty_workflow(executor):
    """Test executing an empty workflow."""
    result = await executor.execute()
    
    assert result.status == ExecutionStatus.COMPLETED
    assert result.start_time is not None
    assert result.end_time is not None
    assert not result.step_states
    assert not result.error_message


@pytest.mark.asyncio
async def test_execute_single_step(executor):
    """Test executing a workflow with a single step."""
    # Add a simple command step
    step = Step(
        name="test_step",
        type=StepType.SINGLE,
        command="echo hello"
    )
    executor.workflow.steps.append(step)
    
    result = await executor.execute()
    
    assert result.status == ExecutionStatus.COMPLETED
    assert step.name in result.step_states
    assert result.step_states[step.name].status == ExecutionStatus.COMPLETED
    assert not result.error_message


@pytest.mark.asyncio
async def test_execute_container_step(executor):
    """Test executing a workflow with a container step."""
    # Add a container step
    step = Step(
        name="test_step",
        type=StepType.SINGLE,
        command="echo hello",
        container=Container(
            type="docker",
            image="alpine",
            version="latest"
        )
    )
    executor.workflow.steps.append(step)
    
    result = await executor.execute()
    
    assert result.status == ExecutionStatus.COMPLETED
    assert step.name in result.step_states
    assert result.step_states[step.name].status == ExecutionStatus.COMPLETED
    assert not result.error_message


@pytest.mark.asyncio
async def test_execute_dependent_steps(executor):
    """Test executing a workflow with dependent steps."""
    # Create two steps with dependency
    step1 = Step(
        name="step1",
        type=StepType.SINGLE,
        command="echo first"
    )
    step2 = Step(
        name="step2",
        type=StepType.SINGLE,
        command="echo second",
        depends_on=["step1"]
    )
    executor.workflow.steps.extend([step1, step2])
    
    result = await executor.execute()
    
    assert result.status == ExecutionStatus.COMPLETED
    assert step1.name in result.step_states
    assert step2.name in result.step_states
    assert result.step_states[step1.name].status == ExecutionStatus.COMPLETED
    assert result.step_states[step2.name].status == ExecutionStatus.COMPLETED
    assert not result.error_message


@pytest.mark.asyncio
async def test_execute_parallel_steps(executor):
    """Test executing parallel steps."""
    # Create two independent steps
    step1 = Step(
        name="step1",
        type=StepType.SINGLE,
        command="echo first"
    )
    step2 = Step(
        name="step2",
        type=StepType.SINGLE,
        command="echo second"
    )
    executor.workflow.steps.extend([step1, step2])
    
    result = await executor.execute()
    
    assert result.status == ExecutionStatus.COMPLETED
    assert step1.name in result.step_states
    assert step2.name in result.step_states
    assert result.step_states[step1.name].status == ExecutionStatus.COMPLETED
    assert result.step_states[step2.name].status == ExecutionStatus.COMPLETED
    assert not result.error_message


@pytest.mark.asyncio
async def test_execute_failing_step(executor):
    """Test executing a workflow with a failing step."""
    # Add a failing step
    step = Step(
        name="failing_step",
        type=StepType.SINGLE,
        command="exit 1"
    )
    executor.workflow.steps.append(step)
    
    result = await executor.execute()
    
    assert result.status == ExecutionStatus.FAILED
    assert step.name in result.step_states
    assert result.step_states[step.name].status == ExecutionStatus.FAILED
    assert result.error_message is not None


@pytest.mark.asyncio
async def test_execute_invalid_step(executor):
    """Test executing a workflow with an invalid step."""
    # Add a step without executor
    step = Step(
        name="invalid_step",
        type=StepType.SINGLE
    )
    executor.workflow.steps.append(step)
    
    result = await executor.execute()
    
    assert result.status == ExecutionStatus.FAILED
    assert result.error_message is not None


def test_find_executor(executor):
    """Test finding suitable executor for steps."""
    # Command step
    command_step = Step(
        name="command_step",
        type=StepType.SINGLE,
        command="echo hello"
    )
    assert executor._find_executor(command_step) is not None
    
    # Container step
    container_step = Step(
        name="container_step",
        type=StepType.SINGLE,
        command="echo hello",
        container=Container(
            type="docker",
            image="alpine"
        )
    )
    assert executor._find_executor(container_step) is not None
    
    # Invalid step
    invalid_step = Step(
        name="invalid_step",
        type=StepType.SINGLE
    )
    assert executor._find_executor(invalid_step) is None 