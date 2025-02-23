"""
Logging configuration for BioinfoFlow.

This module provides a centralized logging configuration using loguru.
It implements structured logging with consistent formatting and multiple outputs.
"""

import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any

from loguru import logger

# Remove default logger
logger.remove()

class BioflowLogger:
    """
    Centralized logging configuration for BioinfoFlow.
    
    Features:
    - Structured logging with consistent formatting
    - Console and file outputs with different levels
    - Log rotation with size and time-based policies
    - Contextual information for workflow and step tracking
    """
    
    # Log format with timestamp, level, module, and message
    CONSOLE_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    FILE_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "workflow={extra[workflow_name]} step={extra[step_name]} | "
        "{message}"
    )
    
    def __init__(self, log_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the logger with console and file handlers.
        
        Args:
            log_dir: Directory for log files. Defaults to ./logs
        """
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Add console handler (INFO and above)
        logger.add(
            sys.stderr,
            format=self.CONSOLE_FORMAT,
            level="INFO",
            colorize=True,
        )
        
        # Add file handler for all logs (DEBUG and above)
        logger.add(
            self.log_dir / "bioflow.log",
            format=self.FILE_FORMAT,
            level="DEBUG",
            rotation="100 MB",  # Rotate at 100MB
            retention="1 week",  # Keep logs for 1 week
            compression="gz",    # Compress rotated logs
        )
        
        # Add file handler for errors (ERROR and above)
        logger.add(
            self.log_dir / "error.log",
            format=self.FILE_FORMAT,
            level="ERROR",
            rotation="100 MB",
            retention="1 month",  # Keep error logs longer
            compression="gz",
        )
        
        # Initialize context
        self.workflow_context: Dict[str, Any] = {
            "workflow_name": "unknown",
            "step_name": "unknown",
        }
    
    def set_workflow_context(self, workflow_name: str) -> None:
        """Set the current workflow context."""
        self.workflow_context["workflow_name"] = workflow_name
        logger.configure(extra=self.workflow_context)
    
    def set_step_context(self, step_name: str) -> None:
        """Set the current step context."""
        self.workflow_context["step_name"] = step_name
        logger.configure(extra=self.workflow_context)
    
    def clear_context(self) -> None:
        """Clear the current context."""
        self.workflow_context = {
            "workflow_name": "unknown",
            "step_name": "unknown",
        }
        logger.configure(extra=self.workflow_context)

# Create global logger instance
bioflow_logger = BioflowLogger()

# Convenience methods
def set_workflow_context(workflow_name: str) -> None:
    """Set the current workflow context."""
    bioflow_logger.set_workflow_context(workflow_name)

def set_step_context(step_name: str) -> None:
    """Set the current step context."""
    bioflow_logger.set_step_context(step_name)

def clear_context() -> None:
    """Clear the current context."""
    bioflow_logger.clear_context()

# Export logger for use in other modules
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical

__all__ = [
    "bioflow_logger",
    "set_workflow_context",
    "set_step_context",
    "clear_context",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
] 