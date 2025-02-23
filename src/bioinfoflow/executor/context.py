"""
Execution context management for BioinfoFlow.

This module provides the execution context for workflow runs,
managing state, resources, and environment variables.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..core.models import Workflow, Step
from ..core.exceptions import ExecutionError
from ..utils.logging import debug, error

@dataclass
class StepContext:
    """Context for a single step execution."""
    step: Step
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    container_id: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    def mark_running(self) -> None:
        """Mark step as running."""
        self.status = "running"
        self.start_time = datetime.now()
    
    def mark_completed(self, exit_code: int = 0) -> None:
        """Mark step as completed."""
        self.status = "completed"
        self.end_time = datetime.now()
        self.exit_code = exit_code
    
    def mark_failed(self, error_msg: str, exit_code: int = 1) -> None:
        """Mark step as failed."""
        self.status = "failed"
        self.end_time = datetime.now()
        self.exit_code = exit_code
        self.error_message = error_msg

class ExecutionContext:
    """
    Execution context for workflow runs.
    
    This class manages:
    - Workflow state and metadata
    - Step execution states
    - Resource tracking
    - Environment variables
    - Working directories
    """
    
    def __init__(self, workflow: Workflow, run_id: Optional[str] = None):
        """
        Initialize execution context.
        
        Args:
            workflow: Workflow to execute
            run_id: Optional run identifier (defaults to timestamp)
        """
        self.workflow = workflow
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize working directories
        self.work_dir = workflow.config.work_dir / self.run_id
        self.logs_dir = self.work_dir / "logs"
        self.temp_dir = self.work_dir / "temp"
        
        # Initialize step contexts
        self.steps: Dict[str, StepContext] = {
            name: StepContext(step=step)
            for name, step in workflow.steps.items()
        }
        
        # Initialize resource tracking
        self.allocated_cpus = 0
        self.allocated_memory = 0  # in bytes
        self.allocated_gpus = 0
        
        # Initialize environment
        self.env_vars = {
            "BIOFLOW_RUN_ID": self.run_id,
            "BIOFLOW_WORK_DIR": str(self.work_dir),
            "BIOFLOW_LOGS_DIR": str(self.logs_dir),
            "BIOFLOW_TEMP_DIR": str(self.temp_dir),
        }
    
    def setup(self) -> None:
        """Set up execution environment."""
        try:
            # Create working directories
            self.work_dir.mkdir(parents=True, exist_ok=True)
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            debug("Created working directories under: {}", self.work_dir)
            
            # Set up environment variables
            os.environ.update(self.env_vars)
            
        except Exception as e:
            error("Failed to set up execution environment: {}", str(e))
            raise ExecutionError(f"Failed to set up execution environment: {str(e)}")
    
    def cleanup(self) -> None:
        """Clean up execution environment."""
        try:
            # Remove temporary directory
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
            
            debug("Cleaned up temporary directory: {}", self.temp_dir)
            
        except Exception as e:
            error("Failed to clean up execution environment: {}", str(e))
            # Don't raise here, just log the error
    
    def get_step_context(self, step_name: str) -> StepContext:
        """Get context for a specific step."""
        if step_name not in self.steps:
            raise ExecutionError(f"Unknown step: {step_name}")
        return self.steps[step_name]
    
    def can_run_step(self, step_name: str) -> bool:
        """Check if a step can be run based on resource availability."""
        step = self.steps[step_name].step
        resources = step.resources
        
        # Check CPU availability
        if self.allocated_cpus + resources.cpu > os.cpu_count():
            return False
        
        # Check memory availability (simple check, can be improved)
        import psutil
        available_memory = psutil.virtual_memory().available
        required_memory = self._parse_memory(resources.memory)
        if self.allocated_memory + required_memory > available_memory:
            return False
        
        # Check GPU availability if required
        if resources.gpu and self.allocated_gpus + resources.gpu > self._get_available_gpus():
            return False
        
        return True
    
    def allocate_resources(self, step_name: str) -> None:
        """Allocate resources for a step."""
        step = self.steps[step_name].step
        resources = step.resources
        
        self.allocated_cpus += resources.cpu
        self.allocated_memory += self._parse_memory(resources.memory)
        if resources.gpu:
            self.allocated_gpus += resources.gpu
    
    def release_resources(self, step_name: str) -> None:
        """Release resources allocated to a step."""
        step = self.steps[step_name].step
        resources = step.resources
        
        self.allocated_cpus -= resources.cpu
        self.allocated_memory -= self._parse_memory(resources.memory)
        if resources.gpu:
            self.allocated_gpus -= resources.gpu
    
    @staticmethod
    def _parse_memory(memory_str: str) -> int:
        """Parse memory string to bytes."""
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4
        }
        
        import re
        match = re.match(r'(\d+)\s*([KMGT]?B)', memory_str.upper())
        if not match:
            raise ExecutionError(f"Invalid memory format: {memory_str}")
        
        value, unit = match.groups()
        return int(value) * units[unit]
    
    @staticmethod
    def _get_available_gpus() -> int:
        """Get number of available GPUs."""
        try:
            import torch
            return torch.cuda.device_count()
        except ImportError:
            return 0  # No GPU support 