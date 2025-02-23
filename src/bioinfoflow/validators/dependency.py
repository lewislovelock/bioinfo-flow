"""
Dependency validator for BioinfoFlow workflows.

This module provides validation functionality for workflow dependencies.
"""

from typing import Dict, Set, List

from ..core.models import Step
from ..core.exceptions import ValidationError
from ..utils.logging import debug, error

def validate_dependencies(step: Step, available_steps: Set[str]) -> None:
    """
    Validate step dependencies.
    
    Args:
        step: Step configuration to validate
        available_steps: Set of available step names
        
    Raises:
        ValidationError: If validation fails
    """
    debug("Validating step dependencies")
    
    # Validate dependencies exist
    for dep in step.after:
        if dep not in available_steps:
            error("Unknown dependency: {}", dep)
            raise ValidationError(f"Unknown dependency: {dep}")
        if dep == step.name:
            error("Step cannot depend on itself: {}", step.name)
            raise ValidationError(f"Step cannot depend on itself: {step.name}")
    
    debug("Step dependencies validation passed")

def check_circular_dependencies(steps: Dict[str, Step]) -> None:
    """
    Check for circular dependencies in the workflow graph.
    
    Args:
        steps: Dictionary of step name to step configuration
        
    Raises:
        ValidationError: If circular dependencies are found
    """
    debug("Checking for circular dependencies")
    
    visited = set()
    path = set()
    
    def visit(step_name: str) -> None:
        """DFS visit helper function."""
        if step_name in path:
            error("Circular dependency detected at step: {}", step_name)
            raise ValidationError(f"Circular dependency involving step {step_name}")
        if step_name in visited:
            return
        
        path.add(step_name)
        visited.add(step_name)
        
        step = steps[step_name]
        for dep in step.after:
            visit(dep)
        
        path.remove(step_name)
    
    # Visit each unvisited node
    for step_name in steps:
        if step_name not in visited:
            visit(step_name)
    
    debug("No circular dependencies found")

def get_execution_order(steps: Dict[str, Step]) -> List[str]:
    """
    Get the execution order of steps based on dependencies.
    
    Args:
        steps: Dictionary of step name to step configuration
        
    Returns:
        List of step names in execution order
    """
    debug("Calculating execution order")
    
    # Calculate in-degree for each step
    in_degree = {name: 0 for name in steps}
    for step in steps.values():
        for dep in step.after:
            in_degree[step.name] += 1
    
    # Find steps with no dependencies
    queue = [name for name, degree in in_degree.items() if degree == 0]
    if not queue:
        error("No steps without dependencies found")
        raise ValidationError("Workflow must have at least one step without dependencies")
    
    # Topological sort
    execution_order = []
    while queue:
        step_name = queue.pop(0)
        execution_order.append(step_name)
        
        # Update in-degree for dependent steps
        step = steps[step_name]
        for dep_step in steps.values():
            if step_name in dep_step.after:
                in_degree[dep_step.name] -= 1
                if in_degree[dep_step.name] == 0:
                    queue.append(dep_step.name)
    
    if len(execution_order) != len(steps):
        error("Not all steps can be executed")
        raise ValidationError("Not all steps can be executed due to dependency configuration")
    
    debug("Execution order calculated: {}", ", ".join(execution_order))
    return execution_order 