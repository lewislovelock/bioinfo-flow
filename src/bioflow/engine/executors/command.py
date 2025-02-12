"""
Command executor implementation.
"""
import asyncio
import os
import shlex
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from ...parser.models import Step, StepType
from ..models import ExecutionContext, StepExecutionState, ExecutionStatus


class CommandExecutor:
    """Executor for command-line steps."""
    
    def __init__(self, context: ExecutionContext):
        """
        Initialize the executor.
        
        Args:
            context: Execution context
        """
        self.context = context
    
    def can_execute(self, step: Step) -> bool:
        """
        Check if this executor can execute the given step.
        
        Args:
            step: Step to check
            
        Returns:
            True if this executor can execute the step
        """
        return (
            step.type == StepType.SINGLE and
            step.command is not None and
            not step.container  # Not containerized
        )
    
    async def execute(self, step: Step) -> StepExecutionState:
        """
        Execute a command-line step.
        
        Args:
            step: Step to execute
            
        Returns:
            Execution state of the step
            
        Raises:
            ExecutionError: If the step execution fails
        """
        # Create working directory
        step_dir = self.context.working_dir / step.name
        os.makedirs(step_dir, exist_ok=True)
        
        # Prepare environment
        env = self._prepare_env(step)
        
        # Create initial state
        state = StepExecutionState(
            step=step,
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            # Execute command
            exit_code, stdout, stderr = await self._run_command(
                step.command,
                cwd=step_dir,
                env=env
            )
            
            # Update state based on result
            status = (
                ExecutionStatus.COMPLETED
                if exit_code == 0
                else ExecutionStatus.FAILED
            )
            
            # Prepare error message if command failed
            error_message = None
            if status == ExecutionStatus.FAILED:
                error_message = stderr or stdout or f"Command failed with exit code {exit_code}"
            
            self._update_state(
                state,
                status=status,
                end_time=datetime.now(),
                exit_code=exit_code,
                error_message=error_message
            )
            
        except Exception as e:
            self._update_state(
                state,
                status=ExecutionStatus.FAILED,
                end_time=datetime.now(),
                error_message=str(e)
            )
        
        return state
    
    async def _run_command(
        self,
        command: str,
        cwd: Path,
        env: Dict[str, str]
    ) -> Tuple[int, Optional[str], Optional[str]]:
        """
        Run a shell command.
        
        Args:
            command: Command to run
            cwd: Working directory
            env: Environment variables
            
        Returns:
            Tuple of (exit code, stdout output if any, stderr output if any)
        """
        # 使用shell执行命令以支持内置命令
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash"  # 明确指定shell路径
        )
        
        # 等待完成
        stdout, stderr = await process.communicate()
        
        # 确保获取正确的退出码
        returncode = process.returncode if process.returncode is not None else -1
        
        return (
            returncode,
            stdout.decode() if stdout else None,
            stderr.decode() if stderr else None
        )
    
    def _prepare_env(self, step: Step) -> Dict[str, str]:
        """
        Prepare environment variables.
        
        Args:
            step: Step to prepare environment for
            
        Returns:
            Dictionary of environment variables
        """
        # Start with current environment
        env = dict(os.environ)
        
        # Add workflow-level environment
        env.update(self.context.env)
        
        # Convert all values to strings
        return {k: str(v) for k, v in env.items()}
    
    def _update_state(self, state: StepExecutionState, **kwargs) -> None:
        """
        Update an execution state.
        
        Args:
            state: State to update
            **kwargs: Attributes to update
        """
        for key, value in kwargs.items():
            setattr(state, key, value) 