"""
Dependency resolver for workflow execution.
"""
from collections import defaultdict
from typing import Dict, List, Set

from ..parser.models import Step
from ..parser.resolvers.dependency import DependencyResolver


class ExecutionDependencyResolver:
    """Resolver for execution dependencies."""
    
    def __init__(self):
        """Initialize the resolver."""
        self.dependency_resolver = DependencyResolver()
        self.steps: Dict[str, Step] = {}
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_dependencies: Dict[str, Set[str]] = defaultdict(set)
    
    def add_step(self, step: Step) -> None:
        """
        Add a step to the resolver.
        
        Args:
            step: Step to add
        """
        # Add step to dependency resolver for validation
        self.dependency_resolver.add_step(step)
        
        # Store step
        self.steps[step.name] = step
        
        # Store dependencies
        for dep in step.depends_on:
            self.dependencies[step.name].add(dep)
            self.reverse_dependencies[dep].add(step.name)
    
    def get_execution_layers(self) -> List[List[Step]]:
        """
        Get execution layers for parallel execution.
        Each layer contains steps that can be executed in parallel.
        Steps in later layers depend on steps in earlier layers.
        
        Returns:
            List of layers, where each layer is a list of steps
        """
        # Initialize remaining steps and completed steps
        remaining = set(self.steps.keys())
        completed: Set[str] = set()
        layers: List[List[Step]] = []
        
        while remaining:
            # Find steps that can be executed (all dependencies satisfied)
            ready = {
                name for name in remaining
                if all(dep in completed for dep in self.dependencies[name])
            }
            
            if not ready:
                # If no steps are ready but there are remaining steps,
                # there must be a cycle
                raise ValueError("Cycle detected in step dependencies")
            
            # Create layer with ready steps
            layer = [self.steps[name] for name in ready]
            layers.append(layer)
            
            # Update remaining and completed steps
            remaining -= ready
            completed |= ready
        
        return layers 