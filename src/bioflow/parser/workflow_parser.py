"""
Workflow configuration parser implementation.
"""
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

from .models import (
    StepType,
    InputType,
    Notification,
    Global,
    Resources,
    Tool,
    Input,
    Output,
    Step,
    Condition,
    ErrorHandler,
    Hook,
    Hooks,
    Parameter,
    Workflow
)
from .validators.schema import SchemaValidator
from .resolvers.variable import VariableResolver
from .resolvers.dependency import DependencyResolver


class WorkflowParser:
    """Parser for workflow configuration."""
    
    def __init__(self):
        """Initialize the parser."""
        self.validator = SchemaValidator()
    
    def parse(self, config_file: Path, parameters: Optional[Dict[str, Any]] = None) -> Workflow:
        """
        Parse a workflow configuration file.
        
        Args:
            config_file: Path to the configuration file
            parameters: Optional parameters to substitute
            
        Returns:
            Parsed workflow configuration
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            yaml.YAMLError: If the configuration file is invalid YAML
            jsonschema.exceptions.ValidationError: If the configuration is invalid
        """
        # Load configuration
        with open(config_file) as f:
            config = yaml.safe_load(f)
            
        # Validate configuration
        self.validator.validate(config)
        
        # Resolve variables
        resolver = VariableResolver(config, parameters or {})
        config = resolver.resolve()
        
        # Create workflow object
        workflow = self._create_workflow(config)
        
        # Analyze dependencies
        dependency_resolver = DependencyResolver()
        for step in workflow.steps:
            dependency_resolver.add_step(step)
        
        return workflow
    
    def _create_workflow(self, config: Dict[str, Any]) -> Workflow:
        """
        Create a workflow object from parsed configuration.
        
        Args:
            config: Parsed configuration dictionary
            
        Returns:
            Workflow object
        """
        # Create global configuration
        global_config = None
        if 'global' in config:
            global_config = Global(
                working_dir=Path(config['global'].get('working_dir', '')),
                temp_dir=Path(config['global'].get('temp_dir', '')),
                max_retries=config['global'].get('max_retries'),
                notification=Notification(**config['global']['notification'])
                if 'notification' in config['global']
                else None
            )
        
        # Create resources
        resources = {}
        if 'resources' in config:
            for name, resource in config['resources'].items():
                if isinstance(resource, dict):
                    resources[name] = Resources(
                        cpu=resource.get('cpu') or resource.get('cpu_units'),
                        memory=resource.get('memory'),
                        time=resource.get('time')
                    )
        
        # Create tools
        tools = {}
        if 'tools' in config:
            for name, tool in config['tools'].items():
                tools[name] = Tool(
                    container=tool.get('container'),
                    version=tool.get('version')
                )
        
        # Create steps
        steps = []
        if 'workflow' in config and 'steps' in config['workflow']:
            steps = [
                self._create_step(step_config)
                for step_config in config['workflow']['steps']
            ]
        
        # Create conditions
        conditions = {}
        if 'conditions' in config:
            for name, condition in config['conditions'].items():
                conditions[name] = Condition(
                    when=condition['when'],
                    skip=condition['skip']
                )
        
        # Create error handlers
        error_handlers = []
        if 'error_handlers' in config:
            for handler in config['error_handlers']:
                error_handlers.append(ErrorHandler(
                    on_error=handler['on_error'],
                    action=handler['action'],
                    max_retries=handler.get('max_retries'),
                    wait_time=handler.get('wait_time')
                ))
        
        # Create hooks
        hooks = None
        if 'hooks' in config:
            hooks_config = config['hooks']
            hooks = Hooks(
                before_step=[
                    Hook(name=h['name'], script=Path(h['script']))
                    for h in hooks_config.get('before_step', [])
                ],
                after_step=[
                    Hook(name=h['name'], script=Path(h['script']))
                    for h in hooks_config.get('after_step', [])
                ],
                on_success=[
                    Hook(name=h['name'], script=Path(h['script']))
                    for h in hooks_config.get('on_success', [])
                ],
                on_failure=[
                    Hook(name=h['name'], script=Path(h['script']))
                    for h in hooks_config.get('on_failure', [])
                ]
            )
        
        # Create parameters
        parameters = []
        if 'parameters' in config:
            for param in config['parameters']:
                parameters.append(Parameter(
                    name=param['name'],
                    type=param['type'],
                    required=param.get('required', False),
                    default=param.get('default'),
                    description=param.get('description')
                ))
        
        return Workflow(
            name=config['name'],
            version=config['version'],
            description=config.get('description'),
            global_config=global_config,
            env=config.get('env', {}),
            resources=resources,
            tools=tools,
            steps=steps,
            conditions=conditions,
            error_handlers=error_handlers,
            hooks=hooks,
            parameters=parameters
        )
    
    def _create_step(self, config: Dict[str, Any]) -> Step:
        """
        Create a step object from configuration.
        
        Args:
            config: Step configuration dictionary
            
        Returns:
            Step object
        """
        # Create resources if specified
        resources = None
        if 'resources' in config:
            resources = Resources(
                cpu=config['resources'].get('cpu'),
                memory=config['resources'].get('memory'),
                time=config['resources'].get('time')
            )
        
        # Create inputs
        inputs = []
        if 'inputs' in config:
            for input_config in config['inputs']:
                inputs.append(Input(
                    name=input_config['name'],
                    type=InputType(input_config['type']),
                    value=input_config['value'],
                    description=input_config.get('description')
                ))
        
        # Create outputs
        outputs = []
        if 'outputs' in config:
            for output_config in config['outputs']:
                outputs.append(Output(
                    name=output_config['name'],
                    path=Path(output_config['path']),
                    description=output_config.get('description')
                ))
        
        # Create nested steps for group types
        nested_steps = []
        if 'steps' in config:
            nested_steps = [
                self._create_step(step_config)
                for step_config in config['steps']
            ]
        
        return Step(
            name=config['name'],
            type=StepType(config['type']),
            tool=config.get('tool'),
            depends_on=config.get('depends_on', []),
            resources=resources,
            inputs=inputs,
            outputs=outputs,
            command=config.get('command'),
            steps=nested_steps
        ) 