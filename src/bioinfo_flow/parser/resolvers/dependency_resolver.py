"""
Dependency resolver for workflow definitions.
Handles step dependencies and generates execution order.
"""

from typing import Dict, List, Set
from collections import defaultdict

from bioinfo_flow.parser.model import BioinfoFlow, Step, Workflow


class DependencyError(Exception):
    """Error raised for dependency resolution issues."""
    pass


class DependencyResolver:
    """Resolver for workflow step dependencies."""

    def __init__(self, workflow: BioinfoFlow):
        """Initialize resolver with workflow definition."""
        self.workflow = workflow
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        self._build_dependency_graph()

    def _build_dependency_graph(self) -> None:
        """Build dependency graph from workflow steps."""
        # Add explicit dependencies from depends_on
        for step in self.workflow.workflow.steps:
            for dep in step.depends_on:
                self.graph[step.name].add(dep)

        # Add implicit dependencies from step references
        for step in self.workflow.workflow.steps:
            self._add_implicit_dependencies(step)

    def _add_implicit_dependencies(self, step: Step) -> None:
        """Add implicit dependencies from variable references in step."""
        # Check command for step references
        self._add_deps_from_string(step.execution.command, step.name)

        # Check input values for step references
        for input_def in step.inputs:
            if input_def.value:
                self._add_deps_from_string(input_def.value, step.name)

        # Check container volumes if present
        if step.execution.container:
            for volume in step.execution.container.volumes:
                self._add_deps_from_string(volume.host, step.name)
                self._add_deps_from_string(volume.container, step.name)

    def _add_deps_from_string(self, value: str, step_name: str) -> None:
        """Add dependencies from variable references in a string."""
        if not isinstance(value, str):
            return

        # Match ${steps.step_name.outputs.output_name} pattern
        import re
        step_refs = re.findall(r'\${steps\.([^.]+)\.outputs\.[^}]+}', value)
        for ref in step_refs:
            self.graph[step_name].add(ref)

    def validate_dependencies(self) -> None:
        """
        Validate workflow dependencies.

        Raises:
            DependencyError: If circular dependencies or missing steps are found
        """
        # Check for missing steps
        all_steps = {step.name for step in self.workflow.workflow.steps}
        for step, deps in self.graph.items():
            missing = deps - all_steps
            if missing:
                raise DependencyError(
                    f"Step '{step}' depends on non-existent steps: {missing}"
                )

        # Check for cycles
        try:
            self.get_execution_order()
        except DependencyError as e:
            raise DependencyError(f"Circular dependency detected: {e}")

    def get_execution_order(self) -> List[Step]:
        """
        Get steps in dependency-resolved order.

        The method uses Kahn's algorithm for topological sort to determine
        the execution order. For example, given the following dependency graph:

        ```
        step1 <-- step2 <-- step3
          ^
          |
        step4
        ```

        The execution order would be: [step1, step4, step2, step3]
        where:
        - step1 and step4 can run in parallel (no dependencies)
        - step2 must wait for step1
        - step3 must wait for step2

        Returns:
            List of steps in execution order (dependencies first)

        Raises:
            DependencyError: If circular dependencies are found
        """
        # Kahn's algorithm for topological sort
        in_degree = defaultdict(int)
        for deps in self.graph.values():
            for dep in deps:
                in_degree[dep] += 1

        # Initialize queue with steps that have no dependencies
        queue = [
            step.name for step in self.workflow.workflow.steps
            if step.name not in in_degree
        ]
        
        execution_order = []
        step_map = {step.name: step for step in self.workflow.workflow.steps}

        while queue:
            current = queue.pop(0)
            execution_order.append(step_map[current])

            # Remove edges from the graph
            for dependent in self.graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(execution_order) != len(self.workflow.workflow.steps):
            # Find the cycle
            remaining = set(step_map.keys()) - {step.name for step in execution_order}
            cycle = self._find_cycle(remaining)
            raise DependencyError(f"Circular dependency found: {' -> '.join(cycle)}")

        # Reverse the order to get dependencies first
        return list(reversed(execution_order))

    def _find_cycle(self, nodes: Set[str]) -> List[str]:
        """Find a cycle in the dependency graph starting from given nodes."""
        def dfs(node: str, path: List[str], visited: Set[str]) -> List[str]:
            if node in path:
                idx = path.index(node)
                return path[idx:]
            if node in visited:
                return []

            path.append(node)
            visited.add(node)

            for neighbor in self.graph[node]:
                cycle = dfs(neighbor, path, visited)
                if cycle:
                    return cycle

            path.pop()
            return []

        for node in nodes:
            cycle = dfs(node, [], set())
            if cycle:
                return cycle + [cycle[0]]  # Complete the cycle

        return []  # Should not reach here if called after topological sort failure


def main():
    """Run example dependency resolution."""
    from bioinfo_flow.parser.workflow_parser import WorkflowParser

    example_workflow = """
    name: test-workflow
    version: "1.0.0"
    global:
        working_dir: "/tmp/test"
        temp_dir: "/tmp/test/temp"
    workflow:
        steps:
            - name: step1
              type: single
              outputs:
                - name: file
                  type: file
                  value: "step1.txt"
              execution:
                mode: local
                command: "echo 'step1' > ${outputs.file}"

            - name: step2
              type: single
              depends_on: ["step1"]
              execution:
                mode: local
                command: "echo 'step2' && cat ${steps.step1.outputs.file}"
              
            - name: step3
              type: single
              depends_on: ["step2"]
              execution:
                mode: local
                command: "echo 'step3'"
    """

    try:
        workflow = WorkflowParser.load_workflow_from_string(example_workflow)
        resolver = DependencyResolver(workflow)
        
        print("Validating dependencies...")
        resolver.validate_dependencies()
        
        print("\nDependency Graph:")
        for step_name, deps in resolver.graph.items():
            if deps:
                print(f"{step_name} depends on: {list(deps)}")
            else:
                print(f"{step_name}: no dependencies")
        
        print("\nExecution Order:")
        for i, step in enumerate(resolver.get_execution_order(), 1):
            deps = resolver.graph[step.name]
            print(f"{i}. {step.name} (depends on: {list(deps) if deps else 'none'})")
            
    except Exception as e:
        print(f"Error resolving dependencies: {e}")


if __name__ == "__main__":
    main() 