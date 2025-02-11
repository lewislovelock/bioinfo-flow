"""
Variable resolution for workflow configuration.
"""
import re
from typing import Any, Dict, List, Optional


class VariableResolver:
    """Resolver for variable references in workflow configuration."""
    
    def __init__(self, config: Dict[str, Any], parameters: Dict[str, Any]):
        """
        Initialize the resolver.
        
        Args:
            config: Workflow configuration dictionary
            parameters: Runtime parameters
        """
        self.config = config
        self.parameters = parameters
        self.var_pattern = re.compile(r'\${([^}]+)}')
        
        # Initialize context variables
        self.context = {
            'working_dir': config.get('global', {}).get('working_dir', ''),
            'temp_dir': config.get('global', {}).get('temp_dir', '')
        }
        
        # Initialize step context stack
        self.step_stack: List[Dict[str, Any]] = []
    
    def resolve(self) -> Dict[str, Any]:
        """
        Resolve all variable references in the configuration.
        
        Returns:
            Configuration with resolved variables
        """
        return self.resolve_dict(self.config)
    
    def _get_value_from_path(self, path: str) -> Any:
        """
        Get a value from a dot-notation path.
        
        Args:
            path: Dot-notation path (e.g., "env.REFERENCE_GENOME")
            
        Returns:
            The value at the specified path
            
        Raises:
            KeyError: If the path doesn't exist
        """
        # Check context variables first
        if path in self.context:
            return self.context[path]
        
        current = self.config
        parts = path.split('.')
        
        # Special handling for parameters
        if parts[0] == 'params':
            if len(parts) != 2:
                raise KeyError(f"Invalid parameter reference: {path}")
            if parts[1] not in self.parameters:
                raise KeyError(f"Parameter not found: {parts[1]}")
            return self.parameters[parts[1]]
        
        # Special handling for step outputs
        if parts[0] == 'steps':
            if len(parts) != 4 or parts[2] != 'outputs':
                raise KeyError(f"Invalid step output reference: {path}")
            step_name = parts[1]
            output_name = parts[3]
            
            # Find the step
            for step in self.config['workflow']['steps']:
                if step['name'] == step_name:
                    for output in step.get('outputs', []):
                        if output['name'] == output_name:
                            return output['path']
            raise KeyError(f"Step output not found: {path}")
        
        # Special handling for inputs
        if parts[0] == 'inputs' and self.step_stack:
            if len(parts) != 2:
                raise KeyError(f"Invalid input reference: {path}")
            input_name = parts[1]
            current_step = self.step_stack[-1]
            for input_def in current_step.get('inputs', []):
                if input_def['name'] == input_name:
                    return input_def['value']
            raise KeyError(f"Input not found: {path}")
        
        # Special handling for resources
        if parts[0] == 'resources' and self.step_stack:
            if len(parts) != 2:
                raise KeyError(f"Invalid resource reference: {path}")
            resource_name = parts[1]
            current_step = self.step_stack[-1]
            if resource_name not in current_step.get('resources', {}):
                raise KeyError(f"Resource not found: {path}")
            return current_step['resources'][resource_name]
        
        # Navigate the path
        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    raise KeyError(f"Path not found: {path}")
                current = current[part]
            else:
                raise KeyError(f"Invalid path: {path}")
        
        return current
    
    def resolve_string(self, value: str) -> str:
        """
        Resolve variable references in a string.
        
        Args:
            value: String containing variable references
            
        Returns:
            String with resolved variables
            
        Raises:
            KeyError: If a referenced variable doesn't exist
        """
        def replace(match):
            path = match.group(1)
            try:
                resolved = self._get_value_from_path(path)
                return str(resolved)
            except KeyError as e:
                raise KeyError(f"Failed to resolve variable: ${{{path}}}") from e
        
        return self.var_pattern.sub(replace, value)
    
    def resolve_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve variable references in a dictionary.
        
        Args:
            data: Dictionary containing variable references
            
        Returns:
            Dictionary with resolved variables
        """
        result = {}
        
        # If this is a step, push it onto the stack
        if 'type' in data and isinstance(data.get('type'), str):
            self.step_stack.append(data)
            
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                result[key] = self.resolve_list(value)
            elif isinstance(value, str):
                result[key] = self.resolve_string(value)
            else:
                result[key] = value
                
        # Pop the step from the stack if we're done with it
        if 'type' in data and isinstance(data.get('type'), str):
            self.step_stack.pop()
            
        return result
    
    def resolve_list(self, data: List[Any]) -> List[Any]:
        """
        Resolve variable references in a list.
        
        Args:
            data: List containing variable references
            
        Returns:
            List with resolved variables
        """
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(self.resolve_dict(item))
            elif isinstance(item, list):
                result.append(self.resolve_list(item))
            elif isinstance(item, str):
                result.append(self.resolve_string(item))
            else:
                result.append(item)
        return result 