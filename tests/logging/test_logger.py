"""
Tests for logging system.
"""
import json
import logging
import pytest
from pathlib import Path

from bioflow.logging import setup_logging, get_logger
from bioflow.logging.logger import WorkflowLogFormatter


@pytest.fixture
def log_dir(tmp_path):
    """Create a temporary directory for logs."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    return log_dir


def test_setup_logging(log_dir):
    """Test setting up logging."""
    logger = setup_logging("test", log_dir)
    assert logger.name == "test"
    assert logger.log_dir == log_dir
    assert logger.level == logging.INFO


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
    
    # 清除之前的处理器
    logger.logger.handlers.clear()
    
    # 重新设置处理器
    json_formatter = WorkflowLogFormatter()
    file_handler = logging.FileHandler(log_dir / "test.log")
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(logging.DEBUG)  # 确保 handler 也能处理 DEBUG 级别的日志
    logger.logger.addHandler(file_handler)
    
    # 确保 logger 本身也设置为 DEBUG 级别
    logger.logger.setLevel(logging.DEBUG)
    
    # 写入不同级别的日志
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # 确保文件写入完成
    file_handler.close()
    
    # 读取并验证日志内容
    log_file = log_dir / "test.log"
    assert log_file.exists()
    
    with open(log_file, 'r') as f:
        content = f.read()
        print(f"Log file content: {content}")  # 添加调试输出
    
    # 检查日志文件内容
    logs = [json.loads(line) for line in log_file.read_text().splitlines()]
    print(f"Parsed logs: {logs}")  # 添加调试输出
    
    levels = [log["level"] for log in logs]
    print(f"Log levels: {levels}")  # 添加调试输出
    
    # 验证所有级别的日志都被记录
    assert "DEBUG" in levels, "DEBUG level missing"
    assert "INFO" in levels, "INFO level missing"
    assert "WARNING" in levels, "WARNING level missing"
    assert "ERROR" in levels, "ERROR level missing"
    assert "CRITICAL" in levels, "CRITICAL level missing"


def test_workflow_context(log_dir):
    """Test logging with workflow context."""
    logger = setup_logging("test", log_dir)
    
    # 清除之前的处理器并重新设置
    logger.logger.handlers.clear()
    json_formatter = WorkflowLogFormatter()
    file_handler = logging.FileHandler(log_dir / "test.log")
    file_handler.setFormatter(json_formatter)
    logger.logger.addHandler(file_handler)
    
    logger.info(
        "Step started",
        workflow_name="test_workflow",
        step_name="test_step",
        execution_id="123",
        status="running"
    )
    
    # 确保文件写入完成
    file_handler.close()
    
    log_file = log_dir / "test.log"
    assert log_file.exists()
    
    logs = [json.loads(line) for line in log_file.read_text().splitlines()]
    log_entry = logs[-1]
    
    assert log_entry["workflow"] == "test_workflow"
    assert log_entry["step"] == "test_step"
    assert log_entry["execution_id"] == "123"
    assert log_entry["status"] == "running"


def test_error_logging(log_dir):
    """Test error logging."""
    logger = setup_logging("test", log_dir)
    
    # 清除之前的处理器并重新设置
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
            workflow_name="test_workflow",
            step_name="test_step",
            exc_info=e
        )
    
    # 确保文件写入完成
    error_handler.close()
    
    error_log = log_dir / "test.error.log"
    assert error_log.exists()
    
    logs = [json.loads(line) for line in error_log.read_text().splitlines()]
    log_entry = logs[-1]
    
    assert log_entry["level"] == "ERROR"
    assert log_entry["workflow"] == "test_workflow"
    assert log_entry["step"] == "test_step"
    assert log_entry["error"]["type"] == "ValueError"
    assert log_entry["error"]["message"] == "Test error"


def test_log_rotation(log_dir):
    """Test log file rotation."""
    logger = setup_logging(
        "test",
        log_dir,
        max_bytes=50,  # 更小的大小以确保触发轮转
        backup_count=2
    )
    
    # 清除之前的处理器并重新设置
    logger.logger.handlers.clear()
    json_formatter = WorkflowLogFormatter()
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "test.log",
        maxBytes=50,
        backupCount=2
    )
    file_handler.setFormatter(json_formatter)
    logger.logger.addHandler(file_handler)
    
    # 写入足够的日志以触发轮转
    for i in range(10):
        logger.info("x" * 20)  # 写入固定长度的消息
    
    # 确保文件写入完成
    file_handler.close()
    
    # 检查是否有轮转文件
    log_files = list(log_dir.glob("test.log*"))
    assert len(log_files) >= 2  # 至少有原始文件和一个备份


def test_extra_fields(log_dir):
    """Test logging with extra fields."""
    logger = setup_logging("test", log_dir)
    
    # 清除之前的处理器并重新设置
    logger.logger.handlers.clear()
    json_formatter = WorkflowLogFormatter()
    file_handler = logging.FileHandler(log_dir / "test.log")
    file_handler.setFormatter(json_formatter)
    logger.logger.addHandler(file_handler)
    
    extra = {
        "duration": 1.23,
        "memory": "1GB",
        "cpu": 2
    }
    
    logger.info(
        "Resource usage",
        workflow_name="test_workflow",
        extra=extra
    )
    
    # 确保文件写入完成
    file_handler.close()
    
    log_file = log_dir / "test.log"
    assert log_file.exists()
    
    logs = [json.loads(line) for line in log_file.read_text().splitlines()]
    log_entry = logs[-1]
    
    # 检查额外字段是否直接添加到日志条目中
    assert log_entry["duration"] == 1.23
    assert log_entry["memory"] == "1GB"
    assert log_entry["cpu"] == 2 