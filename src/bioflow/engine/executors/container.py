"""
Container executor implementation.
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...parser.models import Step, StepType, Mount
from ..models import ExecutionContext, StepExecutionState, ExecutionStatus
from ..exceptions import ContainerError


class ContainerExecutor:
    """Executor for containerized steps."""
    
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
            step.container is not None and
            step.container.type.lower() == "docker"
        )
    
    async def execute(self, step: Step) -> StepExecutionState:
        """
        Execute a containerized step.
        
        Args:
            step: Step to execute
            
        Returns:
            Execution state of the step
            
        Raises:
            ContainerError: If container execution fails
        """
        if not step.container:
            raise ContainerError("No container configuration provided", step.name)
            
        # Create working directory
        step_dir = self.context.working_dir / step.name
        os.makedirs(step_dir, exist_ok=True)
        
        # Create initial state
        state = StepExecutionState(
            step=step,
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            # Pull container image if needed
            await self._ensure_image(step)
            
            # Execute container
            exit_code, stdout, stderr = await self._run_container(
                step=step,
                cwd=step_dir
            )
            
            # Update state based on result
            status = (
                ExecutionStatus.COMPLETED
                if exit_code == 0
                else ExecutionStatus.FAILED
            )
            
            # Prepare error message if container failed
            error_message = None
            if status == ExecutionStatus.FAILED:
                error_message = stderr or stdout or f"Container failed with exit code {exit_code}"
            
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
    
    async def _ensure_image(self, step: Step) -> None:
        """
        Ensure container image is available.
        
        Args:
            step: Step to ensure image for
            
        Raises:
            ContainerError: If image pull fails
        """
        image = f"{step.container.image}:{step.container.version or 'latest'}"
        
        try:
            # Check if image exists locally
            proc = await asyncio.create_subprocess_exec(
                "docker", "image", "inspect", image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            
            # Pull image if not found locally
            if proc.returncode != 0:
                pull_proc = await asyncio.create_subprocess_exec(
                    "docker", "pull", image,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await pull_proc.communicate()
                
                if pull_proc.returncode != 0:
                    raise ContainerError(
                        f"Failed to pull image {image}: {stderr.decode()}",
                        step.name
                    )
                    
        except Exception as e:
            raise ContainerError(f"Error ensuring image {image}: {str(e)}", step.name)
    
    async def _run_container(
        self,
        step: Step,
        cwd: Path
    ) -> Tuple[int, Optional[str], Optional[str]]:
        """
        Run a container.
        
        Args:
            step: Step to run container for
            cwd: Working directory
            
        Returns:
            Tuple of (exit code, stdout output if any, stderr output if any)
            
        Raises:
            ContainerError: If container execution fails
        """
        if not step.container:
            raise ContainerError("No container configuration provided", step.name)
            
        # Prepare container command
        cmd = ["docker", "run", "--rm"]
        
        # Add environment variables
        env = self._prepare_env(step)
        for key, value in env.items():
            cmd.extend(["-e", f"{key}={value}"])
        
        # Add volume mounts
        mounts = self._prepare_mounts(step, cwd)
        for mount in mounts:
            cmd.extend(["-v", f"{mount.host}:{mount.container}"])
        
        # Add container image
        image = f"{step.container.image}:{step.container.version or 'latest'}"
        cmd.append(image)
        
        # Add command to run in container
        if step.command:
            cmd.extend(["/bin/sh", "-c", step.command])
        
        try:
            # Run container
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion
            stdout, stderr = await process.communicate()
            
            # Ensure we have a valid return code
            returncode = process.returncode if process.returncode is not None else -1
            
            return (
                returncode,
                stdout.decode() if stdout else None,
                stderr.decode() if stderr else None
            )
            
        except Exception as e:
            raise ContainerError(f"Container execution failed: {str(e)}", step.name)
    
    def _prepare_env(self, step: Step) -> Dict[str, str]:
        """
        Prepare environment variables for container.
        
        Args:
            step: Step to prepare environment for
            
        Returns:
            Dictionary of environment variables
        """
        # Start with workflow-level environment
        env = self.context.env.copy()
        
        # Add container-specific environment
        if step.container and step.container.environment:
            env.update(step.container.environment)
        
        # Convert all values to strings
        return {k: str(v) for k, v in env.items()}
    
    def _prepare_mounts(self, step: Step, cwd: Path) -> List[Mount]:
        """
        Prepare volume mounts for container.
        
        Args:
            step: Step to prepare mounts for
            cwd: Working directory
            
        Returns:
            List of mounts
        """
        mounts = []
        
        # Add working directory mount
        mounts.append(Mount(
            host=str(cwd),
            container="/workspace",
            options=[]
        ))
        
        # Add step-specific mounts
        if step.container and step.container.mounts:
            mounts.extend(step.container.mounts)
        
        return mounts
    
    def _update_state(self, state: StepExecutionState, **kwargs) -> None:
        """
        Update an execution state.
        
        Args:
            state: State to update
            **kwargs: Attributes to update
        """
        for key, value in kwargs.items():
            setattr(state, key, value) 