"""
Dependency resolution for workflow steps.
"""
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
from ..models import Step, StepType


@dataclass
class DependencyNode:
    """Node in the dependency graph."""
    step: Step
    dependencies: Set[str]
    dependents: Set[str]


class DependencyResolver:
    """Resolver for step dependencies in workflow configuration."""
    
    def __init__(self):
        """Initialize the resolver."""
        self.nodes: Dict[str, DependencyNode] = {}
        self.sorted_steps: List[List[str]] = []
    
    def add_step(self, step: Step) -> None:
        """
        Add a step to the dependency graph.
        
        Args:
            step: The step to add
        """
        if step.name not in self.nodes:
            node = DependencyNode(
                step=step,
                dependencies=set(step.depends_on),
                dependents=set()
            )
            self.nodes[step.name] = node
            
            # Add this step as a dependent to all its dependencies
            for dep in step.depends_on:
                if dep in self.nodes:
                    self.nodes[dep].dependents.add(step.name)
            
        # Add implicit dependencies from variable references
        self._add_implicit_dependencies(step)
        
        # Process nested steps if this is a group
        if step.steps:
            for nested_step in step.steps:
                self.add_step(nested_step)
                # Add implicit dependency on the parent step
                self.add_dependency(nested_step.name, step.name)
    
    def add_dependency(self, from_step: str, to_step: str) -> None:
        """
        Add a dependency between steps.
        
        Args:
            from_step: Name of the dependent step
            to_step: Name of the dependency step
        """
        if from_step not in self.nodes or to_step not in self.nodes:
            return
            
        self.nodes[from_step].dependencies.add(to_step)
        self.nodes[to_step].dependents.add(from_step)
    
    def _add_implicit_dependencies(self, step: Step) -> None:
        """
        Add implicit dependencies from variable references.
        
        Args:
            step: Step to analyze for implicit dependencies
        """
        # Check command for step output references
        if step.command:
            self._add_dependencies_from_string(step.name, step.command)
            
        # Check input values for step output references
        for input_def in step.inputs:
            self._add_dependencies_from_string(step.name, input_def.value)
    
    def _add_dependencies_from_string(self, step_name: str, value: str) -> None:
        """
        Add dependencies from variable references in a string.
        
        Args:
            step_name: Name of the current step
            value: String to analyze for variable references
        """
        import re
        
        # Match step output references: ${steps.STEP_NAME.outputs.OUTPUT_NAME}
        pattern = r'\${steps\.([^.]+)\.outputs\.[^}]+}'
        matches = re.finditer(pattern, value)
        
        for match in matches:
            dependency_step = match.group(1)
            if dependency_step != step_name:  # Avoid self-dependencies
                self.add_dependency(step_name, dependency_step)
    
    def validate(self) -> None:
        """
        Validate the dependency graph.
        
        Raises:
            ValueError: If circular dependencies are detected
        """
        visited = set()
        temp_visited = set()
        
        def visit(node_name: str) -> None:
            """DFS visit with cycle detection."""
            if node_name in temp_visited:
                cycle = self._find_cycle(node_name)
                raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")
                
            if node_name in visited:
                return
                
            temp_visited.add(node_name)
            
            for dep in self.nodes[node_name].dependencies:
                visit(dep)
                
            temp_visited.remove(node_name)
            visited.add(node_name)
        
        # Visit all nodes
        for node_name in self.nodes:
            if node_name not in visited:
                visit(node_name)
    
    def _find_cycle(self, start: str) -> List[str]:
        """
        Find a cycle in the graph starting from the given node.
        
        Args:
            start: Starting node name
            
        Returns:
            List of node names forming a cycle
        """
        cycle = [start]
        current = start
        
        while True:
            # Find the first dependency that leads back to start
            for dep in self.nodes[current].dependencies:
                if dep == start:
                    cycle.append(start)
                    return cycle
                if dep in cycle:
                    continue
                current = dep
                cycle.append(current)
                break
    
    def sort(self) -> List[List[str]]:
        """
        Topologically sort steps into execution levels.
        
        Returns:
            List of lists of step names, where each inner list
            contains steps that can be executed in parallel
        """
        if not self.sorted_steps:
            self.validate()  # Ensure no cycles
            
            # Initialize in-degree count
            in_degree = {
                name: len(node.dependencies)
                for name, node in self.nodes.items()
            }
            
            # Group steps by level
            levels: List[List[str]] = []
            while in_degree:
                # Find all nodes with in-degree 0
                level = [
                    name
                    for name, degree in in_degree.items()
                    if degree == 0
                ]
                
                if not level:
                    break  # No more nodes with in-degree 0
                
                levels.append(level)
                
                # Remove processed nodes and update in-degrees
                for name in level:
                    del in_degree[name]
                    for dependent in self.nodes[name].dependents:
                        if dependent in in_degree:
                            in_degree[dependent] -= 1
            
            self.sorted_steps = levels
            
        return self.sorted_steps
    
    def get_execution_graph(self) -> Dict[str, Set[str]]:
        """
        Get the execution graph representation.
        
        Returns:
            Dictionary mapping step names to sets of dependency step names
        """
        return {
            name: node.dependencies
            for name, node in self.nodes.items()
        } 