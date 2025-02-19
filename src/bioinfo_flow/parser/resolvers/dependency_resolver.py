"""
Dependency resolver for workflow definitions.
Handles step dependencies and generates execution order.
"""

from typing import Dict, List, Set
from collections import defaultdict
from loguru import logger
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich import box

from bioinfo_flow.parser.model import BioinfoFlow, Step
from bioinfo_flow.parser.errors import (
    DependencyResolutionError,
    CircularDependencyError,
    setup_logger
)

# Initialize logger
logger = setup_logger()


class DependencyResolver:
    """Resolver for workflow step dependencies."""

    def __init__(self, workflow: BioinfoFlow):
        """Initialize resolver with workflow definition."""
        self.workflow = workflow
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        logger.debug(f"Initializing dependency resolver for '{workflow.name}'")
        self._build_dependency_graph()

    def _build_dependency_graph(self) -> None:
        """Build dependency graph from workflow steps."""
        # Add explicit dependencies from depends_on
        for step in self.workflow.workflow.steps:
            for dep in step.depends_on:
                self.graph[step.name].add(dep)
                logger.debug(f"Added explicit dependency: {step.name} → {dep}")

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
            logger.debug(f"Added implicit dependency: {step_name} → {ref}")

    def validate_dependencies(self) -> None:
        """
        Validate workflow dependencies.

        Raises:
            DependencyResolutionError: If missing steps are found
            CircularDependencyError: If circular dependencies are found
        """
        logger.debug("Validating workflow dependencies")
        
        # Check for missing steps
        all_steps = {step.name for step in self.workflow.workflow.steps}
        for step, deps in self.graph.items():
            missing = deps - all_steps
            if missing:
                logger.error(f"Missing dependencies for step '{step}': {missing}")
                raise DependencyResolutionError(
                    f"Step '{step}' depends on non-existent steps: {missing}",
                    step,
                    {"missing_steps": list(missing)}
                )

        # Check for cycles
        try:
            self.get_execution_order()
            logger.debug("Dependency validation successful")
        except CircularDependencyError as e:
            logger.error(f"Circular dependency detected: {e}")
            raise

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
            CircularDependencyError: If circular dependencies are found
        """
        logger.debug("Calculating execution order")
        
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
            logger.debug(f"Added to execution order: {current}")

            # Remove edges from the graph
            for dependent in self.graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(execution_order) != len(self.workflow.workflow.steps):
            # Find the cycle
            remaining = set(step_map.keys()) - {step.name for step in execution_order}
            cycle = self._find_cycle(remaining)
            logger.error(f"Circular dependency detected: {' → '.join(cycle)}")
            raise CircularDependencyError(cycle)

        ordered_steps = list(reversed(execution_order))
        # logger.info(f"Execution order: {' → '.join(s.name for s in ordered_steps)}")
        return ordered_steps

    def get_parallel_groups(self) -> List[List[Step]]:
        """
        Get groups of steps that can be executed in parallel.
        
        Each group contains steps that:
        1. Have all their dependencies satisfied by previous groups
        2. Can be executed in parallel with other steps in the same group
        
        For example, given the following dependency graph:
        ```
        step1 <-- step2 <-- step4
          ^
          |
        step3 <-- step5
        ```
        
        The parallel groups would be:
        [
            [step1],           # Group 1 (no dependencies)
            [step2, step3],    # Group 2 (depend on step1)
            [step4, step5]     # Group 3 (depend on step2/step3)
        ]
        
        Returns:
            List of step groups, where each group is a list of steps
            that can be executed in parallel
        """
        try:
            # Get execution order first to validate no cycles
            ordered_steps = self.get_execution_order()
        except CircularDependencyError as e:
            logger.error(f"Cannot get parallel groups: {e}")
            raise

        # Create a map of steps to their dependencies
        step_map = {step.name: step for step in ordered_steps}
        
        # Group steps by their maximum dependency depth
        groups: Dict[int, List[Step]] = {}
        
        for step in ordered_steps:
            # Calculate the longest path to this step (its depth)
            depth = self._get_max_dependency_depth(step.name, step_map)
            if depth not in groups:
                groups[depth] = []
            groups[depth].append(step)
            logger.debug(f"Step '{step.name}' assigned to depth {depth}")
        
        # Convert to list of groups, sorted by depth
        parallel_groups = [groups[depth] for depth in sorted(groups.keys())]
        
        # Log the groups
        for i, group in enumerate(parallel_groups, 1):
            step_names = [step.name for step in group]
            # logger.info(f"Parallel group {i}: {', '.join(step_names)}")
        
        return parallel_groups

    def _get_max_dependency_depth(self, step_name: str, step_map: Dict[str, Step]) -> int:
        """
        Calculate the maximum dependency depth for a step.
        
        Args:
            step_name: Name of the step to check
            step_map: Map of step names to Step objects
            
        Returns:
            Maximum depth of dependencies (0 for root steps)
        """
        if not self.graph[step_name]:
            return 0
            
        # Get depths of all dependencies
        dep_depths = [
            self._get_max_dependency_depth(dep, step_map)
            for dep in self.graph[step_name]
        ]
        
        # Return maximum depth + 1
        return max(dep_depths) + 1

    def visualize_graph(self) -> None:
        """
        Create a rich visualization of the dependency graph using the rich package.
        
        Example output for a linear dependency chain (step1 -> step2 -> step3):
        ```
        Dependency Graph
        ╭────────── Step ───────────╮
        │ step1                     │
        │ Type: single              │
        │ Mode: local               │
        ╰───────────────────────────╯
            ├── ╭────────── Step ───────────╮
            │   │ step2                     │
            │   │ Type: single              │
            │   │ Mode: local               │
            │   ╰───────────────────────────╯
            │       └── ╭────────── Step ───────────╮
            │           │ step3                     │
            │           │ Type: single              │
            │           │ Mode: local               │
            │           ╰───────────────────────────╯
            └── ╭────────── Step ───────────╮
                │ step4                     │
                │ Type: single              │
                │ Mode: local               │
                ╰───────────────────────────╯
        ```
        """
        console = Console()
        
        try:
            ordered_steps = self.get_execution_order()
        except CircularDependencyError:
            console.print("[red]Error: Cannot visualize graph with cycles[/red]")
            return

        main_tree = Tree("[bold blue]Dependency Graph[/bold blue]")

        # Get all step information
        step_map = {step.name: step for step in self.workflow.workflow.steps}
        
        # Fix: Treat steps with empty dependency sets as root nodes
        root_nodes = {
            step.name for step in self.workflow.workflow.steps
            if not self.graph[step.name]
        }

        def add_step_tree(parent_tree: Tree, step_name: str, visited: Set[str]) -> None:
            """Recursively add steps and their dependent sub-nodes to the tree."""
            if step_name in visited:
                return
            visited.add(step_name)
            
            step = step_map[step_name]
            step_node = Panel.fit(
                f"[bold cyan]{step_name}[/bold cyan]\n"
                f"[dim]Type: {step.type}[/dim]\n"
                f"[dim]Mode: {step.execution.mode}[/dim]",
                box=box.ROUNDED,
                padding=(0, 1),
                title="[blue]Step[/blue]"
            )
            current_tree = parent_tree.add(step_node)
            
            # Find all steps that depend on the current step
            dependents = sorted([
                name for name, deps in self.graph.items()
                if step_name in deps
            ])
            
            for dependent in dependents:
                add_step_tree(current_tree, dependent, visited)

        visited = set()
        for root in sorted(root_nodes):
            add_step_tree(main_tree, root, visited)

        console.print(main_tree)

        # # Print parallel execution groups
        # parallel_groups = self.get_parallel_groups()
        # if len(parallel_groups) > 1:
        #     console.print("\n[bold yellow]Parallel Execution Groups:[/bold yellow]")
        #     for i, group in enumerate(parallel_groups, 1):
        #         step_names = [step.name for step in group]
        #         if len(step_names) > 1:
        #             console.print(f"[green]Group {i}:[/green] {', '.join(sorted(step_names))}")

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
    from rich.console import Console
    from rich import print as rprint

    console = Console()

    example_workflow = """
    name: test-workflow
    version: "0.1.0"
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

            - name: step4
              type: single
              depends_on: ["step1"]
              execution:
                mode: local
                command: "echo 'parallel with step2'"
                
            - name: step5
              type: single
              depends_on: ["step2"]
              execution:
                mode: local
                command: "echo 'parallel with step3'"
    """

    try:
        workflow = WorkflowParser.load_workflow_from_string(example_workflow)
        resolver = DependencyResolver(workflow)
        
        resolver.validate_dependencies()
        resolver.visualize_graph()
        
        console.print("\n[bold green]Parallel Groups:[/bold green]")
        for i, group in enumerate(resolver.get_parallel_groups(), 1):
            step_names = [step.name for step in group]
            console.print(
                f"{i}. [cyan]{', '.join(step_names)}[/cyan]"
            )
            
    except Exception as e:
        console.print(f"[red]Error resolving dependencies: {e}[/red]")


if __name__ == "__main__":
    main() 