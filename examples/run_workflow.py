#!/usr/bin/env python3
"""
Example script to run a BioFlow workflow.
"""
import asyncio
import logging
from pathlib import Path

from bioflow.parser import WorkflowParser
from bioflow.engine import WorkflowEngine, ExecutionStatus


async def main():
    """Run the example workflow."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Setup paths
        workflow_file = Path(__file__).parent / "example_workflow.yaml"
        work_dir = Path("work")
        temp_dir = Path("temp")
        
        # Create directories
        work_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse workflow
        logger.info("Parsing workflow configuration")
        parser = WorkflowParser()
        workflow = parser.parse(workflow_file)
        
        # Create executor
        logger.info("Creating workflow engine")
        engine = WorkflowEngine(
            workflow=workflow,
            working_dir=work_dir,
            temp_dir=temp_dir
        )
        
        # Execute workflow
        logger.info("Starting workflow execution")
        result = await engine.execute()
        
        # Check result
        if result.status == ExecutionStatus.COMPLETED:
            logger.info("Workflow completed successfully")
        else:
            logger.error(
                "Workflow failed: %s",
                result.error_message or "Unknown error"
            )
            
    except Exception as e:
        logger.error("Error running workflow: %s", str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main()) 