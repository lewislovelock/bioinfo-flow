"""
Variable resolver for workflow definitions.
Handles variable substitution in workflow commands and values.
"""

import re
from typing import Any, Dict, Optional

from bioinfo_flow.parser.model import BioinfoFlow, Step


class VariableResolver:
    """Resolver for variable substitution in workflow definitions."""

    VAR_PATTERN = re.compile(r'\${([^}]+)}')

    def __init__(self, workflow: BioinfoFlow):
        """Initialize resolver with workflow definition."""
        self.workflow = workflow
        # Initialize context with all global variables
        self.context: Dict[str, Dict[str, Any]] = {
            'env': workflow.env,
            'params': {p.name: p.default for p in workflow.parameters},
            'resources': workflow.resources.default,
            'global': {
                'working_dir': workflow.global_config.working_dir,
                'temp_dir': workflow.global_config.temp_dir
            }
        }

    def resolve_string(self, value: str, step: Optional[Step] = None) -> str:
        """
        Resolve variables in a string value.

        Args:
            value: String containing variables to resolve (e.g., "${env.PATH}")
            step: Optional step context for step-specific variables

        Returns:
            Resolved string value

        Raises:
            ValueError: If variable cannot be resolved
        """
        if not isinstance(value, str):
            return value

        def replace(match: re.Match) -> str:
            var_path = match.group(1)
            parts = var_path.split('.')

            # Handle different variable types
            try:
                if parts[0] == 'steps':
                    # ${steps.step_name.outputs.output_name}
                    return self._resolve_step_reference(parts[1:])
                elif parts[0] in self.context:
                    # ${env.VAR}, ${params.NAME}, ${resources.cpu}, ${global.working_dir}
                    return str(self._get_nested_value(self.context[parts[0]], parts[1:]))
                elif step and parts[0] in ['inputs', 'outputs']:
                    # ${inputs.name}, ${outputs.name}
                    return self._resolve_step_io(step, parts)
                else:
                    raise ValueError(f"Unknown variable type: {parts[0]}")
            except (KeyError, ValueError) as e:
                raise ValueError(f"Failed to resolve variable '${{{var_path}}}': {str(e)}")

        # Keep resolving until no more variables are found
        prev_value = None
        current_value = value
        max_iterations = 10  # Prevent infinite loops

        for _ in range(max_iterations):
            if prev_value == current_value:
                break
            prev_value = current_value
            current_value = self.VAR_PATTERN.sub(replace, current_value)

        if self.VAR_PATTERN.search(current_value):
            raise ValueError(f"Could not fully resolve variables after {max_iterations} iterations: {current_value}")

        return current_value

    def _resolve_step_reference(self, parts: list) -> str:
        """Resolve references to other steps (e.g., steps.step1.outputs.file)."""
        if len(parts) < 3:
            raise ValueError("Invalid step reference format")

        step_name, ref_type, ref_name = parts[0], parts[1], parts[2]
        step = next((s for s in self.workflow.workflow.steps if s.name == step_name), None)
        if not step:
            raise ValueError(f"Step not found: {step_name}")

        if ref_type != 'outputs':
            raise ValueError(f"Only step outputs can be referenced, got: {ref_type}")

        output = next((o for o in step.outputs if o.name == ref_name), None)
        if not output:
            raise ValueError(f"Output '{ref_name}' not found in step '{step_name}'")

        return output.value or ''

    def _resolve_step_io(self, step: Step, parts: list) -> str:
        """Resolve step input/output references (e.g., inputs.file, outputs.result)."""
        if len(parts) != 2:
            raise ValueError("Invalid input/output reference format")

        io_type, io_name = parts[0], parts[1]
        io_list = step.inputs if io_type == 'inputs' else step.outputs
        io_item = next((io for io in io_list if io.name == io_name), None)
        if not io_item:
            raise ValueError(f"{io_type.capitalize()} '{io_name}' not found in step '{step.name}'")

        return io_item.value or ''

    def _get_nested_value(self, data: Dict[str, Any], parts: list) -> Any:
        """Get nested value from dictionary using dot notation."""
        value = data
        for part in parts:
            if not isinstance(value, dict):
                raise ValueError(f"Cannot access '{part}' in non-dictionary value")
            if part not in value:
                raise KeyError(f"Key not found: {part}")
            value = value[part]
        return value

    def resolve_step(self, step: Step) -> Step:
        """
        Resolve all variables in a step definition.

        Args:
            step: Step to resolve

        Returns:
            Resolved step with all variables substituted
        """
        resolved_step = step.model_copy(deep=True)

        # First resolve input/output values
        for io in resolved_step.inputs + resolved_step.outputs:
            if io.value:
                io.value = self.resolve_string(io.value, resolved_step)

        # Then resolve command (which might reference the resolved I/O values)
        resolved_step.execution.command = self.resolve_string(
            resolved_step.execution.command,
            resolved_step
        )

        # Finally resolve container volumes if present
        if resolved_step.execution.container:
            for volume in resolved_step.execution.container.volumes:
                volume.host = self.resolve_string(volume.host, resolved_step)
                volume.container = self.resolve_string(volume.container, resolved_step)

        return resolved_step


def main():
    """Run example workflow resolution."""
    from bioinfo_flow.parser.workflow_parser import WorkflowParser

    example_workflow = """
    name: test-workflow
    version: "1.0.0"
    global:
        working_dir: "/tmp/test"
        temp_dir: "/tmp/test/temp"
    env:
        INPUT_DIR: "/data/input"
    workflow:
        steps:
            - name: step1
              type: single
              inputs:
                - name: input_file
                  type: file
                  value: "${env.INPUT_DIR}/data.txt"
              outputs:
                - name: output_file
                  type: file
                  value: "output.txt"
              execution:
                mode: local
                command: "cat ${inputs.input_file} > ${outputs.output_file}"
    """

    try:
        workflow = WorkflowParser.load_workflow_from_string(example_workflow)
        resolver = VariableResolver(workflow)
        
        # Resolve first step
        resolved_step = resolver.resolve_step(workflow.workflow.steps[0])
        print("Original command:", workflow.workflow.steps[0].execution.command)
        print("Resolved command:", resolved_step.execution.command)
        print("Original input:", workflow.workflow.steps[0].inputs[0].value)
        print("Resolved input:", resolved_step.inputs[0].value)
        print("Original output:", workflow.workflow.steps[0].outputs[0].value)
        print("Resolved output:", resolved_step.outputs[0].value)
    except Exception as e:
        print(f"Error resolving variables: {e}")


if __name__ == "__main__":
    main() 