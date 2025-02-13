"""
Tests for execution dependency resolver.
"""
import pytest

from bioflow.parser.models import Step, StepType
from bioflow.engine.dependency import ExecutionDependencyResolver


@pytest.fixture
def resolver():
    """Create test resolver."""
    return ExecutionDependencyResolver()


def test_add_step(resolver):
    """Test adding a step."""
    step = Step(name="test", type=StepType.SINGLE)
    resolver.add_step(step)
    
    assert "test" in resolver.steps
    assert not resolver.dependencies["test"]
    assert not resolver.reverse_dependencies["test"]


def test_add_dependent_step(resolver):
    """Test adding a step with dependencies."""
    step1 = Step(name="step1", type=StepType.SINGLE)
    step2 = Step(name="step2", type=StepType.SINGLE, depends_on=["step1"])
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    
    assert "step1" in resolver.steps
    assert "step2" in resolver.steps
    assert "step1" in resolver.dependencies["step2"]
    assert "step2" in resolver.reverse_dependencies["step1"]


def test_get_execution_layers_empty(resolver):
    """Test getting execution layers for empty workflow."""
    layers = resolver.get_execution_layers()
    assert not layers


def test_get_execution_layers_single_step(resolver):
    """Test getting execution layers for single step."""
    step = Step(name="test", type=StepType.SINGLE)
    resolver.add_step(step)
    
    layers = resolver.get_execution_layers()
    assert len(layers) == 1
    assert layers[0] == [step]


def test_get_execution_layers_independent_steps(resolver):
    """Test getting execution layers for independent steps."""
    step1 = Step(name="step1", type=StepType.SINGLE)
    step2 = Step(name="step2", type=StepType.SINGLE)
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    
    layers = resolver.get_execution_layers()
    assert len(layers) == 1
    assert len(layers[0]) == 2
    assert step1 in layers[0]
    assert step2 in layers[0]


def test_get_execution_layers_dependent_steps(resolver):
    """Test getting execution layers for dependent steps."""
    step1 = Step(name="step1", type=StepType.SINGLE)
    step2 = Step(name="step2", type=StepType.SINGLE, depends_on=["step1"])
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    
    layers = resolver.get_execution_layers()
    assert len(layers) == 2
    assert layers[0] == [step1]
    assert layers[1] == [step2]


def test_get_execution_layers_complex_dependencies(resolver):
    """Test getting execution layers for complex dependencies."""
    # Create a diamond dependency pattern:
    #   A
    #  / \
    # B   C
    #  \ /
    #   D
    step_a = Step(name="A", type=StepType.SINGLE)
    step_b = Step(name="B", type=StepType.SINGLE, depends_on=["A"])
    step_c = Step(name="C", type=StepType.SINGLE, depends_on=["A"])
    step_d = Step(name="D", type=StepType.SINGLE, depends_on=["B", "C"])
    
    resolver.add_step(step_a)
    resolver.add_step(step_b)
    resolver.add_step(step_c)
    resolver.add_step(step_d)
    
    layers = resolver.get_execution_layers()
    assert len(layers) == 3
    assert layers[0] == [step_a]
    assert len(layers[1]) == 2
    assert step_b in layers[1]
    assert step_c in layers[1]
    assert layers[2] == [step_d]


def test_get_execution_layers_cyclic_dependencies(resolver):
    """Test getting execution layers with cyclic dependencies."""
    step1 = Step(name="step1", type=StepType.SINGLE, depends_on=["step2"])
    step2 = Step(name="step2", type=StepType.SINGLE, depends_on=["step1"])
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    
    with pytest.raises(ValueError, match="Cycle detected in step dependencies"):
        resolver.get_execution_layers() 