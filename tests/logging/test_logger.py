"""
Tests for logging system.
"""
import json
import logging
import pytest
from pathlib import Path

from bioflow.logging import setup_logging, get_logger
from bioflow.logging.logger import WorkflowContext, WorkflowLogFormatter


@pytest.fixture
def log_dir(tmp_path):
    """Create a temporary directory for logs."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


@pytest.fixture
def workflow_context():
    """Create a test workflow context."""
    return WorkflowContext(
        workflow_id="wf-123",
        workflow_name="test_workflow",
        execution_id="exec-456",
        step_id="step-1",
        step_name="quality_control",
        status="running"
    )


def test_workflow_context():
    """Test WorkflowContext functionality."""
    context = WorkflowContext(
        workflow_id="wf-123",
        workflow_name="test_workflow"
    )
    
    # Test required fields
    assert context.workflow_id == "wf-123"
    assert context.workflow_name == "test_workflow"
    
    # Test optional fields are None by default
    assert context.execution_id is None
    assert context.step_id is None
    assert context.step_name is None
    assert context.status is None
    
    # Test as_dict method excludes None values
    context_dict = context.as_dict()
    assert "workflow_id" in context_dict
    assert "workflow_name" in context_dict
    assert "execution_id" not in context_dict


def test_setup_logging(log_dir):
    """Test setting up logging."""
    logger = setup_logging("test", log_dir)
    assert logger.name == "test"
    assert logger.log_dir == log_dir
    assert logger.level == logging.INFO
    
    # Test file creation
    assert (log_dir / "test.log").exists()
    assert (log_dir / "test.error.log").exists()


def test_get_logger(log_dir):
    """Test getting a configured logger."""
    setup_logging("test", log_dir)
    logger = get_logger("test")
    assert logger.name == "test"
    
    with pytest.raises(KeyError):
        get_logger("nonexistent")


def test_log_levels(log_dir):
    """Test different log levels."""
    logger = setup_logging("test", log_dir, level=logging.DEBUG)
    
    # Clear previous handlers
    logger.logger.handlers.clear()
    
    # Reset handlers
    json_formatter = WorkflowLogFormatter()
    file_handler = logging.FileHandler(log_dir / "test.log")
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.logger.addHandler(file_handler)
    logger.logger.setLevel(logging.DEBUG)
    
    # Log messages at different levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # Ensure file write is complete
    file_handler.close()
    
    # Read and verify log content
    log_file = log_dir / "test.log"
    assert log_file.exists()
    
    logs = [json.loads(line) for line in log_file.read_text().splitlines()]
    levels = [log["level"] for log in logs]
    
    assert "DEBUG" in levels
    assert "INFO" in levels
    assert "WARNING" in levels
    assert "ERROR" in levels
    assert "CRITICAL" in levels


def test_context_logging(log_dir, workflow_context):
    """Test logging with workflow context."""
    logger = setup_logging("test", log_dir, context=workflow_context)
    
    # Clear and reset handlers
    logger.logger.handlers.clear()
    json_formatter = WorkflowLogFormatter()
    file_handler = logging.FileHandler(log_dir / "test.log")
    file_handler.setFormatter(json_formatter)
    logger.logger.addHandler(file_handler)
    
    # Keep the original context
    logger.context = workflow_context
    
    logger.info("Step started")
    
    # Ensure file write is complete
    file_handler.close()
    
    # Verify log content
    log_file = log_dir / "test.log"
    logs = [json.loads(line) for line in log_file.read_text().splitlines()]
    log_entry = logs[-1]
    
    assert log_entry["workflow_id"] == "wf-123"
    assert log_entry["workflow_name"] == "test_workflow"
    assert log_entry["execution_id"] == "exec-456"
    assert log_entry["step_id"] == "step-1"
    assert log_entry["step_name"] == "quality_control"
    assert log_entry["status"] == "running"


def test_context_switching(log_dir, workflow_context):
    """Test switching contexts using with_context and with_step."""
    logger = setup_logging("test", log_dir, context=workflow_context)
    
    # Keep the original context when clearing handlers
    original_context = logger.context
    logger.logger.handlers.clear()
    logger.context = original_context
    
    # Switch to new step
    step_logger = logger.with_step("step-2", "data_analysis")
    assert step_logger.context.step_id == "step-2"
    assert step_logger.context.step_name == "data_analysis"
    assert step_logger.context.workflow_id == workflow_context.workflow_id
    
    # Create new context
    new_context = WorkflowContext(
        workflow_id="wf-789",
        workflow_name="another_workflow"
    )
    new_logger = logger.with_context(new_context)
    assert new_logger.context.workflow_id == "wf-789"
    assert new_logger.context.workflow_name == "another_workflow"


def test_metadata_logging(log_dir):
    """Test logging with metadata."""
    logger = setup_logging("test", log_dir)
    
    # Clear and reset handlers
    logger.logger.handlers.clear()
    json_formatter = WorkflowLogFormatter()
    file_handler = logging.FileHandler(log_dir / "test.log")
    file_handler.setFormatter(json_formatter)
    logger.logger.addHandler(file_handler)
    
    metadata = {
        "duration": 1.23,
        "memory": "1GB",
        "cpu": 2
    }
    
    logger.info("Resource usage", metadata=metadata)
    
    # Ensure file write is complete
    file_handler.close()
    
    # Verify log content
    log_file = log_dir / "test.log"
    logs = [json.loads(line) for line in log_file.read_text().splitlines()]
    log_entry = logs[-1]
    
    assert log_entry["metadata"]["duration"] == 1.23
    assert log_entry["metadata"]["memory"] == "1GB"
    assert log_entry["metadata"]["cpu"] == 2


def test_error_logging(log_dir):
    """Test error logging with exception information."""
    logger = setup_logging("test", log_dir)
    
    # Clear and reset handlers
    logger.logger.handlers.clear()
    json_formatter = WorkflowLogFormatter()
    error_handler = logging.FileHandler(log_dir / "test.error.log")
    error_handler.setFormatter(json_formatter)
    error_handler.setLevel(logging.ERROR)
    logger.logger.addHandler(error_handler)
    
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.error(
            "Step failed",
            metadata={"step": "test_step"},
            exc_info=e
        )
    
    # Ensure file write is complete
    error_handler.close()
    
    # Verify error log content
    error_log = log_dir / "test.error.log"
    logs = [json.loads(line) for line in error_log.read_text().splitlines()]
    log_entry = logs[-1]
    
    assert log_entry["level"] == "ERROR"
    assert log_entry["message"] == "Step failed"
    assert log_entry["metadata"]["step"] == "test_step"
    assert log_entry["error"]["type"] == "ValueError"
    assert log_entry["error"]["message"] == "Test error"
    assert "traceback" in log_entry["error"]


def test_log_rotation(log_dir):
    """Test log file rotation."""
    logger = setup_logging(
        "test",
        log_dir,
        max_bytes=50,  # Small size to trigger rotation
        backup_count=2
    )
    
    # Clear and reset handlers
    logger.logger.handlers.clear()
    json_formatter = WorkflowLogFormatter()
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "test.log",
        maxBytes=50,
        backupCount=2
    )
    file_handler.setFormatter(json_formatter)
    logger.logger.addHandler(file_handler)
    
    # Write enough logs to trigger rotation
    for i in range(10):
        logger.info("x" * 20)
    
    # Ensure file write is complete
    file_handler.close()
    
    # Check rotated files
    log_files = list(log_dir.glob("test.log*"))
    assert len(log_files) >= 2  # Original file plus at least one backup 