"""
Tests for workflow configuration models.
"""
from pathlib import Path
import pytest
from src.bioflow.parser.models import (
    StepType,
    InputType,
    Notification,
    Global,
    Resources,
    Tool,
    Input,
    Output,
    Step,
    Condition,
    ErrorHandler,
    Hook,
    Hooks,
    Parameter,
    Workflow,
)


def test_step_type_enum():
    """Test StepType enumeration."""
    assert StepType.PARALLEL_GROUP.value == "parallel_group"
    assert StepType.SEQUENTIAL_GROUP.value == "sequential_group"
    assert StepType.SINGLE.value == "single"


def test_input_type_enum():
    """Test InputType enumeration."""
    assert InputType.FILE.value == "file"
    assert InputType.DIRECTORY.value == "directory"
    assert InputType.STRING.value == "string"
    assert InputType.INTEGER.value == "integer"
    assert InputType.FLOAT.value == "float"
    assert InputType.BOOLEAN.value == "boolean"


def test_notification():
    """Test Notification dataclass."""
    notif = Notification(email="test@example.com", slack_webhook="https://hooks.slack.com/xxx")
    assert notif.email == "test@example.com"
    assert notif.slack_webhook == "https://hooks.slack.com/xxx"


def test_global_config():
    """Test Global configuration dataclass."""
    global_config = Global(
        working_dir=Path("/path/to/work"),
        temp_dir=Path("/path/to/temp"),
        max_retries=5,
        notification=Notification(email="test@example.com")
    )
    assert global_config.working_dir == Path("/path/to/work")
    assert global_config.temp_dir == Path("/path/to/temp")
    assert global_config.max_retries == 5
    assert global_config.notification.email == "test@example.com"


def test_resources():
    """Test Resources dataclass."""
    resources = Resources(cpu=4, memory="8G", time="1h")
    assert resources.cpu == 4
    assert resources.memory == "8G"
    assert resources.time == "1h"


def test_tool():
    """Test Tool dataclass."""
    tool = Tool(container="ubuntu:20.04", version="1.0.0")
    assert tool.container == "ubuntu:20.04"
    assert tool.version == "1.0.0"


def test_input():
    """Test Input dataclass."""
    input_def = Input(
        name="reference",
        type=InputType.FILE,
        value="/path/to/reference.fa",
        description="Reference genome"
    )
    assert input_def.name == "reference"
    assert input_def.type == InputType.FILE
    assert input_def.value == "/path/to/reference.fa"
    assert input_def.description == "Reference genome"


def test_output():
    """Test Output dataclass."""
    output = Output(
        name="aligned_bam",
        path=Path("/path/to/output.bam"),
        description="Aligned BAM file"
    )
    assert output.name == "aligned_bam"
    assert output.path == Path("/path/to/output.bam")
    assert output.description == "Aligned BAM file"


def test_step():
    """Test Step dataclass."""
    step = Step(
        name="alignment",
        type=StepType.SINGLE,
        tool="bwa",
        depends_on=["qc"],
        resources=Resources(cpu=4, memory="8G"),
        inputs=[
            Input(name="fastq", type=InputType.FILE, value="/path/to/input.fastq")
        ],
        outputs=[
            Output(name="bam", path=Path("/path/to/output.bam"))
        ],
        command="bwa mem -t 4 ${inputs.fastq} > ${outputs.bam}"
    )
    assert step.name == "alignment"
    assert step.type == StepType.SINGLE
    assert step.tool == "bwa"
    assert step.depends_on == ["qc"]
    assert step.resources.cpu == 4
    assert len(step.inputs) == 1
    assert len(step.outputs) == 1
    assert "fastq" in step.command


def test_condition():
    """Test Condition dataclass."""
    condition = Condition(when="${params.skip_qc}", skip=["qc"])
    assert condition.when == "${params.skip_qc}"
    assert condition.skip == ["qc"]


def test_error_handler():
    """Test ErrorHandler dataclass."""
    handler = ErrorHandler(
        on_error="alignment",
        action="retry",
        max_retries=3,
        wait_time="10m"
    )
    assert handler.on_error == "alignment"
    assert handler.action == "retry"
    assert handler.max_retries == 3
    assert handler.wait_time == "10m"


def test_hook():
    """Test Hook dataclass."""
    hook = Hook(name="backup", script=Path("scripts/backup.py"))
    assert hook.name == "backup"
    assert hook.script == Path("scripts/backup.py")


def test_hooks():
    """Test Hooks dataclass."""
    hooks = Hooks(
        before_step=[Hook(name="check", script=Path("scripts/check.py"))],
        after_step=[Hook(name="backup", script=Path("scripts/backup.py"))],
        on_success=[Hook(name="notify", script=Path("scripts/notify.py"))],
        on_failure=[Hook(name="cleanup", script=Path("scripts/cleanup.py"))]
    )
    assert len(hooks.before_step) == 1
    assert len(hooks.after_step) == 1
    assert len(hooks.on_success) == 1
    assert len(hooks.on_failure) == 1


def test_parameter():
    """Test Parameter dataclass."""
    param = Parameter(
        name="threads",
        type="integer",
        required=True,
        default=4,
        description="Number of threads"
    )
    assert param.name == "threads"
    assert param.type == "integer"
    assert param.required is True
    assert param.default == 4
    assert param.description == "Number of threads"


def test_workflow():
    """Test Workflow dataclass."""
    workflow = Workflow(
        name="test-workflow",
        version="1.0.0",
        description="Test workflow",
        global_config=Global(
            working_dir=Path("/path/to/work"),
            temp_dir=Path("/path/to/temp")
        ),
        env={"REFERENCE": "/path/to/reference.fa"},
        resources={"default": Resources(cpu=4, memory="8G")},
        tools={"bwa": Tool(container="bwa:latest", version="0.7.17")},
        steps=[
            Step(name="test", type=StepType.SINGLE)
        ],
        conditions={"skip_qc": Condition(when="${params.skip_qc}", skip=["qc"])},
        error_handlers=[
            ErrorHandler(on_error="test", action="retry", max_retries=3, wait_time="10m")
        ],
        hooks=Hooks(),
        parameters=[
            Parameter(name="threads", type="integer", required=True, default=4)
        ]
    )
    assert workflow.name == "test-workflow"
    assert workflow.version == "1.0.0"
    assert len(workflow.steps) == 1
    assert len(workflow.conditions) == 1
    assert len(workflow.error_handlers) == 1
    assert len(workflow.parameters) == 1 