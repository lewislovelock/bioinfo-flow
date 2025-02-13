"""
Tests for variable resolution.
"""
import pytest
from bioflow.parser.resolvers.variable import VariableResolver


@pytest.fixture
def config():
    """Sample workflow configuration fixture."""
    return {
        "name": "test-workflow",
        "version": "1.0.0",
        "env": {
            "REFERENCE": "/path/to/reference.fa",
            "THREADS": "4"
        },
        "workflow": {
            "steps": [
                {
                    "name": "step1",
                    "outputs": [
                        {
                            "name": "out1",
                            "path": "/path/to/output1.txt"
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def parameters():
    """Sample parameters fixture."""
    return {
        "sample_id": "test_sample",
        "threads": 8
    }


def test_resolve_env_variable(config, parameters):
    """Test resolving environment variables."""
    resolver = VariableResolver(config, parameters)
    result = resolver.resolve_string("Reference: ${env.REFERENCE}")
    assert result == "Reference: /path/to/reference.fa"


def test_resolve_parameter(config, parameters):
    """Test resolving parameters."""
    resolver = VariableResolver(config, parameters)
    result = resolver.resolve_string("Sample: ${params.sample_id}")
    assert result == "Sample: test_sample"


def test_resolve_step_output(config, parameters):
    """Test resolving step outputs."""
    resolver = VariableResolver(config, parameters)
    result = resolver.resolve_string("Output: ${steps.step1.outputs.out1}")
    assert result == "Output: /path/to/output1.txt"


def test_resolve_missing_variable(config, parameters):
    """Test resolving missing variable raises error."""
    resolver = VariableResolver(config, parameters)
    with pytest.raises(KeyError):
        resolver.resolve_string("${env.MISSING}")


def test_resolve_invalid_path(config, parameters):
    """Test resolving invalid path raises error."""
    resolver = VariableResolver(config, parameters)
    with pytest.raises(KeyError):
        resolver.resolve_string("${invalid.path}")


def test_resolve_nested_dict(config, parameters):
    """Test resolving nested dictionary."""
    data = {
        "path": "${env.REFERENCE}",
        "nested": {
            "value": "${params.sample_id}"
        }
    }
    resolver = VariableResolver(config, parameters)
    result = resolver.resolve_dict(data)
    assert result["path"] == "/path/to/reference.fa"
    assert result["nested"]["value"] == "test_sample"


def test_resolve_list(config, parameters):
    """Test resolving list."""
    data = [
        "${env.REFERENCE}",
        {
            "value": "${params.sample_id}"
        }
    ]
    resolver = VariableResolver(config, parameters)
    result = resolver.resolve_list(data)
    assert result[0] == "/path/to/reference.fa"
    assert result[1]["value"] == "test_sample"


def test_resolve_multiple_variables(config, parameters):
    """Test resolving multiple variables in one string."""
    resolver = VariableResolver(config, parameters)
    result = resolver.resolve_string(
        "Ref: ${env.REFERENCE}, Sample: ${params.sample_id}"
    )
    assert result == "Ref: /path/to/reference.fa, Sample: test_sample"


def test_resolve_no_variables(config, parameters):
    """Test resolving string without variables."""
    resolver = VariableResolver(config, parameters)
    result = resolver.resolve_string("No variables here")
    assert result == "No variables here"


def test_resolve_empty_string(config, parameters):
    """Test resolving empty string."""
    resolver = VariableResolver(config, parameters)
    result = resolver.resolve_string("")
    assert result == ""


def test_resolve_invalid_step_output(config, parameters):
    """Test resolving invalid step output reference."""
    resolver = VariableResolver(config, parameters)
    with pytest.raises(KeyError):
        resolver.resolve_string("${steps.missing_step.outputs.out}")


def test_resolve_complex_nested_structure(config, parameters):
    """Test resolving complex nested structure."""
    data = {
        "simple": "${env.REFERENCE}",
        "nested": {
            "value": "${params.sample_id}",
            "list": [
                "${env.THREADS}",
                {
                    "deep": "${steps.step1.outputs.out1}"
                }
            ]
        }
    }
    resolver = VariableResolver(config, parameters)
    result = resolver.resolve_dict(data)
    
    assert result["simple"] == "/path/to/reference.fa"
    assert result["nested"]["value"] == "test_sample"
    assert result["nested"]["list"][0] == "4"
    assert result["nested"]["list"][1]["deep"] == "/path/to/output1.txt" 