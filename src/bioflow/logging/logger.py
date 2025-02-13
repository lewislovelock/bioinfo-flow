"""
Core logging functionality for BioFlow.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, NamedTuple
import json
import logging.handlers
from dataclasses import dataclass, asdict


@dataclass
class WorkflowContext:
    """Workflow execution context for logging."""
    workflow_id: str
    workflow_name: str
    execution_id: Optional[str] = None
    step_id: Optional[str] = None
    step_name: Optional[str] = None
    status: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class WorkflowLogFormatter(logging.Formatter):
    """Custom formatter for workflow logs."""
    
    def __init__(self, fmt: Optional[str] = None):
        """Initialize the formatter."""
        super().__init__(fmt)
        self.default_msec_format = '%s.%03d'

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record into a structured format."""
        # Create base log entry
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add context if available
        if hasattr(record, "workflow_context"):
            log_entry.update(record.workflow_context.as_dict())
        
        # Add metadata if available
        if hasattr(record, "metadata"):
            log_entry["metadata"] = record.metadata
        
        # Add error information if available
        if record.exc_info:
            log_entry["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
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
        backup_count: int = 5,
        context: Optional[WorkflowContext] = None
    ):
        """Initialize the logger."""
        self.name = name
        self.log_dir = log_dir
        self.level = level
        self.context = context
        
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

    def with_context(self, context: WorkflowContext) -> 'WorkflowLogger':
        """Create a new logger with the given context."""
        return WorkflowLogger(
            name=self.name,
            log_dir=self.log_dir,
            level=self.level,
            context=context
        )

    def with_step(self, step_id: str, step_name: str) -> 'WorkflowLogger':
        """Create a new logger with updated step information."""
        if self.context is None:
            raise ValueError("Logger has no workflow context")
        
        new_context = WorkflowContext(
            workflow_id=self.context.workflow_id,
            workflow_name=self.context.workflow_name,
            execution_id=self.context.execution_id,
            step_id=step_id,
            step_name=step_name,
            status=self.context.status
        )
        return self.with_context(new_context)
    
    def _log(
        self,
        level: int,
        msg: str,
        metadata: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ) -> None:
        """Log a message with context."""
        extra = {}
        if self.context:
            extra["workflow_context"] = self.context
        if metadata:
            extra["metadata"] = metadata
            
        self.logger.log(
            level,
            msg,
            extra=extra,
            exc_info=exc_info
        )
    
    def info(self, msg: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log an info message."""
        self._log(logging.INFO, msg, metadata)
    
    def error(self, msg: str, metadata: Optional[Dict[str, Any]] = None, exc_info: Optional[Exception] = None) -> None:
        """Log an error message."""
        self._log(logging.ERROR, msg, metadata, exc_info)
    
    def warning(self, msg: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning message."""
        self._log(logging.WARNING, msg, metadata)
    
    def debug(self, msg: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug message."""
        self._log(logging.DEBUG, msg, metadata)
    
    def critical(self, msg: str, metadata: Optional[Dict[str, Any]] = None, exc_info: Optional[Exception] = None) -> None:
        """Log a critical message."""
        self._log(logging.CRITICAL, msg, metadata, exc_info)


_loggers: Dict[str, WorkflowLogger] = {}


def setup_logging(
    name: str,
    log_dir: Path,
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    context: Optional[WorkflowContext] = None
) -> WorkflowLogger:
    """Setup logging for a workflow."""
    if name not in _loggers:
        _loggers[name] = WorkflowLogger(
            name=name,
            log_dir=log_dir,
            level=level,
            max_bytes=max_bytes,
            backup_count=backup_count,
            context=context
        )
    return _loggers[name]


def get_logger(name: str) -> WorkflowLogger:
    """Get a configured logger."""
    if name not in _loggers:
        raise KeyError(f"Logger '{name}' not configured. Call setup_logging first.")
    return _loggers[name] 