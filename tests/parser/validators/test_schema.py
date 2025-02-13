"""
Tests for workflow schema validation.
"""
import pytest
from pathlib import Path
import yaml
import jsonschema
from bioflow.parser.validators.schema import SchemaValidator


@pytest.fixture
def valid_config():
    """Valid workflow configuration fixture."""
    return {
        "name": "test-workflow",
        "version": "1.0.0",
        "workflow": {
            "steps": [
                {
                    "name": "test",
                    "type": "single",
                    "command": "echo 'test'"
                }
            ]
        }
    }


@pytest.fixture
def validator():
    """SchemaValidator fixture."""
    return SchemaValidator()


def test_validate_valid_config(validator, valid_config):
    """Test validation of valid configuration."""
    validator.validate(valid_config)


def test_validate_missing_required_field(validator):
    """Test validation fails with missing required field."""
    config = {
        "name": "test-workflow",
        # missing version
        "workflow": {
            "steps": []
        }
    }
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validator.validate(config)


def test_validate_invalid_step_type(validator, valid_config):
    """Test validation fails with invalid step type."""
    config = valid_config.copy()
    config["workflow"]["steps"][0]["type"] = "invalid"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validator.validate(config)


def test_validate_invalid_input_type(validator, valid_config):
    """Test validation fails with invalid input type."""
    config = valid_config.copy()
    config["workflow"]["steps"][0]["inputs"] = [
        {
            "name": "test",
            "type": "invalid",
            "value": "test"
        }
    ]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validator.validate(config)


def test_validate_missing_step_name(validator, valid_config):
    """Test validation fails with missing step name."""
    config = valid_config.copy()
    del config["workflow"]["steps"][0]["name"]
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validator.validate(config)


def test_validate_file_not_found(validator):
    """Test validation fails with non-existent file."""
    with pytest.raises(FileNotFoundError):
        validator.validate_file(Path("/nonexistent/file.yaml"))


def test_validate_invalid_yaml(tmp_path, validator):
    """Test validation fails with invalid YAML."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content")
    with pytest.raises(yaml.YAMLError):
        validator.validate_file(config_file)


def test_validate_complex_config(validator):
    """Test validation of complex configuration."""
    config = {
        "name": "complex-workflow",
        "version": "1.0.0",
        "description": "Complex workflow",
        "global": {
            "working_dir": "/path/to/work",
            "temp_dir": "/path/to/temp",
            "max_retries": 3,
            "notification": {
                "email": "test@example.com",
                "slack_webhook": "https://hooks.slack.com/xxx"
            }
        },
        "env": {
            "REFERENCE": "/path/to/reference.fa"
        },
        "resources": {
            "default": {
                "cpu_units": 4,
                "memory": "8G",
                "time": "1h"
            },
            "gpu_support": True
        },
        "tools": {
            "bwa": {
                "container": "bwa:latest",
                "version": "0.7.17"
            }
        },
        "workflow": {
            "steps": [
                {
                    "name": "alignment",
                    "type": "single",
                    "tool": "bwa",
                    "depends_on": ["qc"],
                    "resources": {
                        "cpu": 4,
                        "memory": "8G"
                    },
                    "inputs": [
                        {
                            "name": "fastq",
                            "type": "file",
                            "value": "/path/to/input.fastq"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "bam",
                            "path": "/path/to/output.bam"
                        }
                    ],
                    "command": "bwa mem -t 4 ${inputs.fastq} > ${outputs.bam}"
                }
            ]
        },
        "conditions": {
            "skip_qc": {
                "when": "${params.skip_qc}",
                "skip": ["qc"]
            }
        },
        "error_handlers": [
            {
                "on_error": "alignment",
                "action": "retry",
                "max_retries": 3,
                "wait_time": "10m"
            }
        ],
        "hooks": {
            "before_step": [
                {
                    "name": "check",
                    "script": "scripts/check.py"
                }
            ]
        },
        "parameters": [
            {
                "name": "threads",
                "type": "integer",
                "required": True,
                "default": 4,
                "description": "Number of threads"
            }
        ]
    }
    validator.validate(config) 