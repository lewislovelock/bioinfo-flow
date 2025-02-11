"""
YAML schema validation for workflow configuration.
"""
from typing import Any, Dict
import jsonschema
from pathlib import Path


# Schema definition for workflow configuration
WORKFLOW_SCHEMA = {
    "type": "object",
    "required": ["name", "version", "workflow"],
    "properties": {
        "name": {"type": "string"},
        "version": {"type": "string"},
        "description": {"type": "string"},
        "global": {
            "type": "object",
            "properties": {
                "working_dir": {"type": "string"},
                "temp_dir": {"type": "string"},
                "max_retries": {"type": "integer"},
                "notification": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "slack_webhook": {"type": "string"}
                    }
                }
            },
            "required": ["working_dir", "temp_dir"]
        },
        "env": {
            "type": "object",
            "additionalProperties": {"type": "string"}
        },
        "resources": {
            "type": "object",
            "properties": {
                "default": {
                    "type": "object",
                    "properties": {
                        "cpu_units": {"type": "integer"},
                        "memory": {"type": "string"},
                        "time": {"type": "string"}
                    }
                },
                "gpu_support": {"type": "boolean"}
            }
        },
        "tools": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["container", "version"],
                "properties": {
                    "container": {"type": "string"},
                    "version": {"type": "string"}
                }
            }
        },
        "workflow": {
            "type": "object",
            "required": ["steps"],
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/step"}
                }
            }
        },
        "conditions": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["when", "skip"],
                "properties": {
                    "when": {"type": "string"},
                    "skip": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "error_handlers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["on_error", "action"],
                "properties": {
                    "on_error": {"type": "string"},
                    "action": {"type": "string"},
                    "max_retries": {"type": "integer"},
                    "wait_time": {"type": "string"}
                }
            }
        },
        "hooks": {
            "type": "object",
            "properties": {
                "before_step": {"$ref": "#/definitions/hook_list"},
                "after_step": {"$ref": "#/definitions/hook_list"},
                "on_success": {"$ref": "#/definitions/hook_list"},
                "on_failure": {"$ref": "#/definitions/hook_list"}
            }
        },
        "parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type"],
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "required": {"type": "boolean"},
                    "default": {},
                    "description": {"type": "string"}
                }
            }
        }
    },
    "definitions": {
        "step": {
            "type": "object",
            "required": ["name", "type"],
            "properties": {
                "name": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["parallel_group", "sequential_group", "single"]
                },
                "tool": {"type": "string"},
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "resources": {
                    "type": "object",
                    "properties": {
                        "cpu": {"type": "integer"},
                        "memory": {"type": "string"},
                        "time": {"type": "string"}
                    }
                },
                "inputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "type", "value"],
                        "properties": {
                            "name": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": ["file", "directory", "string", "integer", "float", "boolean"]
                            },
                            "value": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                },
                "outputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "path"],
                        "properties": {
                            "name": {"type": "string"},
                            "path": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                },
                "command": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/step"}
                }
            }
        },
        "hook_list": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "script"],
                "properties": {
                    "name": {"type": "string"},
                    "script": {"type": "string"}
                }
            }
        }
    }
}


class SchemaValidator:
    """Validator for workflow configuration schema."""
    
    def __init__(self):
        """Initialize the validator with the workflow schema."""
        self.validator = jsonschema.Draft7Validator(WORKFLOW_SCHEMA)
    
    def validate(self, config: Dict[str, Any]) -> None:
        """
        Validate workflow configuration against the schema.
        
        Args:
            config: Workflow configuration dictionary
            
        Raises:
            jsonschema.exceptions.ValidationError: If validation fails
        """
        self.validator.validate(config)
    
    def validate_file(self, config_path: Path) -> None:
        """
        Validate workflow configuration file against the schema.
        
        Args:
            config_path: Path to the workflow configuration file
            
        Raises:
            jsonschema.exceptions.ValidationError: If validation fails
            FileNotFoundError: If the configuration file doesn't exist
        """
        import yaml
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        self.validate(config) 