"""
Core logging functionality for BioFlow.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import logging.handlers


class WorkflowLogFormatter(logging.Formatter):
    """Custom formatter for workflow logs."""
    
    def __init__(self):
        """Initialize the formatter."""
        super().__init__()
        self.default_msec_format = '%s.%03d'

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record into a structured format.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log message
        """
        # Create base log entry
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add workflow context if available
        if hasattr(record, "extra_fields"):
            if "workflow_name" in record.extra_fields:
                log_entry["workflow"] = record.extra_fields["workflow_name"]
            if "step_name" in record.extra_fields:
                log_entry["step"] = record.extra_fields["step_name"]
            if "execution_id" in record.extra_fields:
                log_entry["execution_id"] = record.extra_fields["execution_id"]
            if "status" in record.extra_fields:
                log_entry["status"] = record.extra_fields["status"]
            
            # Add remaining extra fields
            for key, value in record.extra_fields.items():
                if key not in ["workflow_name", "step_name", "execution_id", "status"]:
                    log_entry[key] = value
            
        # Add error information if available
        if record.exc_info:
            log_entry["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }
            
        return json.dumps(log_entry)


class WorkflowLogger:
    """Logger for workflow execution."""
    
    def __init__(
        self,
        name: str,
        log_dir: Path,
        level: int = logging.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        Initialize the logger.
        
        Args:
            name: Logger name
            log_dir: Directory for log files
            level: Logging level
            max_bytes: Maximum size of each log file
            backup_count: Number of backup files to keep
        """
        self.name = name
        self.log_dir = log_dir
        self.level = level
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove any existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        json_formatter = WorkflowLogFormatter()
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)8s] %(message)s (%(name)s:%(lineno)s)'
        )
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(level)
        self.logger.addHandler(console_handler)
        
        # Setup file handlers
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main log file with rotation
        main_log = log_dir / f"{name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(level)
        self.logger.addHandler(file_handler)
        
        # Error log file with rotation
        error_log = log_dir / f"{name}.error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        self.logger.addHandler(error_handler)
        
    def _log(
        self,
        level: int,
        msg: str,
        workflow_name: Optional[str] = None,
        step_name: Optional[str] = None,
        execution_id: Optional[str] = None,
        status: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ) -> None:
        """
        Log a message with context.
        
        Args:
            level: Log level
            msg: Log message
            workflow_name: Name of the workflow
            step_name: Name of the step
            execution_id: Execution ID
            status: Execution status
            extra: Additional fields to log
            exc_info: Exception information
        """
        extra_fields = {}
        
        # Add workflow context
        if workflow_name:
            extra_fields["workflow_name"] = workflow_name
        if step_name:
            extra_fields["step_name"] = step_name
        if execution_id:
            extra_fields["execution_id"] = execution_id
        if status:
            extra_fields["status"] = status
            
        # Add extra fields
        if extra:
            extra_fields.update(extra)
            
        self.logger.log(
            level,
            msg,
            extra={"extra_fields": extra_fields},
            exc_info=exc_info
        )
    
    def info(self, msg: str, **kwargs) -> None:
        """Log an info message."""
        self._log(logging.INFO, msg, **kwargs)
    
    def error(self, msg: str, **kwargs) -> None:
        """Log an error message."""
        self._log(logging.ERROR, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs) -> None:
        """Log a warning message."""
        self._log(logging.WARNING, msg, **kwargs)
    
    def debug(self, msg: str, **kwargs) -> None:
        """Log a debug message."""
        self._log(logging.DEBUG, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs) -> None:
        """Log a critical message."""
        self._log(logging.CRITICAL, msg, **kwargs)


_loggers: Dict[str, WorkflowLogger] = {}


def setup_logging(
    name: str,
    log_dir: Path,
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> WorkflowLogger:
    """
    Setup logging for a workflow.
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        level: Logging level
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger
    """
    if name not in _loggers:
        _loggers[name] = WorkflowLogger(
            name=name,
            log_dir=log_dir,
            level=level,
            max_bytes=max_bytes,
            backup_count=backup_count
        )
    return _loggers[name]


def get_logger(name: str) -> WorkflowLogger:
    """
    Get a configured logger.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger
        
    Raises:
        KeyError: If logger is not configured
    """
    if name not in _loggers:
        raise KeyError(f"Logger '{name}' not configured. Call setup_logging first.")
    return _loggers[name] 