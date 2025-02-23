#!/usr/bin/env python3
"""
Example script demonstrating how to use BioinfoFlow to run the variant calling pipeline.

This script shows:
1. How to parse and validate a workflow
2. How to set up logging
3. How to execute the workflow
4. How to handle execution results
"""

import sys
from pathlib import Path
import logging
from typing import Optional

from bioinfoflow import (
    # Core functionality
    debug, info, warning, error,
    set_workflow_context, clear_context,
    
    # Exceptions
    BioinfoFlowError,
    ValidationError,
    ExecutionError,
)
from bioinfoflow.parser import parse_workflow
from bioinfoflow.executor import execute_workflow

def setup_logging(log_dir: Optional[Path] = None) -> None:
    """Set up logging configuration."""
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "pipeline.log"
    else:
        log_file = Path("pipeline.log")
    
    # Configure logging format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_prerequisites() -> None:
    """Check if all prerequisites are met."""
    # Check if docker is available
    import subprocess
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        error("Docker is not available")
        sys.exit(1)
    except FileNotFoundError:
        error("Docker is not installed")
        sys.exit(1)
    
    info("Prerequisites check passed")

def main() -> None:
    """Main entry point."""
    try:
        # Set up logging
        setup_logging()
        info("Starting variant calling pipeline")
        
        # Check prerequisites
        check_prerequisites()
        
        # Get workflow file path
        workflow_file = Path(__file__).parent / "workflows" / "variant_calling.yaml"
        if not workflow_file.exists():
            error("Workflow file not found: {}", workflow_file)
            sys.exit(1)
        
        # Parse and validate workflow
        info("Parsing workflow: {}", workflow_file)
        try:
            workflow = parse_workflow(workflow_file)
        except (ValidationError, BioinfoFlowError) as e:
            error("Failed to parse workflow: {}", str(e))
            sys.exit(1)
        
        info("Successfully parsed workflow: {} (v{})", 
             workflow.name, workflow.version)
        
        # Execute workflow
        info("Executing workflow")
        success = execute_workflow(workflow)
        
        if success:
            info("Workflow completed successfully")
        else:
            error("Workflow execution failed")
            sys.exit(1)
        
    except KeyboardInterrupt:
        error("Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        error("Unexpected error: {}", str(e))
        sys.exit(1)
    finally:
        clear_context()

if __name__ == "__main__":
    main() 