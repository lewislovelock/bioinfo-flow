"""
Tests for dependency resolution.
"""
import pytest
from src.bioflow.parser.models import Step, StepType
from src.bioflow.parser.resolvers.dependency import DependencyResolver


@pytest.fixture
def resolver():
    """DependencyResolver fixture."""
    return DependencyResolver()


def test_add_step(resolver):
    """Test adding a step."""
    step = Step(name="test", type=StepType.SINGLE)
    resolver.add_step(step)
    assert "test" in resolver.nodes


def test_add_dependency(resolver):
    """Test adding a dependency."""
    step1 = Step(name="step1", type=StepType.SINGLE)
    step2 = Step(name="step2", type=StepType.SINGLE, depends_on=["step1"])
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    
    assert "step1" in resolver.nodes["step2"].dependencies
    assert "step2" in resolver.nodes["step1"].dependents


def test_implicit_dependency_from_command(resolver):
    """Test implicit dependency from command."""
    step1 = Step(name="step1", type=StepType.SINGLE)
    step2 = Step(
        name="step2",
        type=StepType.SINGLE,
        command="process ${steps.step1.outputs.out}"
    )
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    
    assert "step1" in resolver.nodes["step2"].dependencies


def test_implicit_dependency_from_input(resolver):
    """Test implicit dependency from input."""
    from src.bioflow.parser.models import Input, InputType
    
    step1 = Step(name="step1", type=StepType.SINGLE)
    step2 = Step(
        name="step2",
        type=StepType.SINGLE,
        inputs=[
            Input(
                name="test",
                type=InputType.FILE,
                value="${steps.step1.outputs.out}"
            )
        ]
    )
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    
    assert "step1" in resolver.nodes["step2"].dependencies


def test_nested_steps(resolver):
    """Test nested steps."""
    parent = Step(
        name="parent",
        type=StepType.PARALLEL_GROUP,
        steps=[
            Step(name="child1", type=StepType.SINGLE),
            Step(name="child2", type=StepType.SINGLE)
        ]
    )
    
    resolver.add_step(parent)
    
    assert "parent" in resolver.nodes
    assert "child1" in resolver.nodes
    assert "child2" in resolver.nodes
    assert "parent" in resolver.nodes["child1"].dependencies
    assert "parent" in resolver.nodes["child2"].dependencies


def test_circular_dependency_detection(resolver):
    """Test circular dependency detection."""
    step1 = Step(name="step1", type=StepType.SINGLE, depends_on=["step2"])
    step2 = Step(name="step2", type=StepType.SINGLE, depends_on=["step1"])
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    
    with pytest.raises(ValueError) as exc_info:
        resolver.validate()
    assert "Circular dependency detected" in str(exc_info.value)


def test_topological_sort(resolver):
    """Test topological sort."""
    step1 = Step(name="step1", type=StepType.SINGLE)
    step2 = Step(name="step2", type=StepType.SINGLE, depends_on=["step1"])
    step3 = Step(name="step3", type=StepType.SINGLE, depends_on=["step1"])
    step4 = Step(name="step4", type=StepType.SINGLE, depends_on=["step2", "step3"])
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    resolver.add_step(step3)
    resolver.add_step(step4)
    
    levels = resolver.sort()
    
    # First level should contain only step1
    assert levels[0] == ["step1"]
    # Second level should contain step2 and step3 (can run in parallel)
    assert set(levels[1]) == {"step2", "step3"}
    # Third level should contain step4
    assert levels[2] == ["step4"]


def test_get_execution_graph(resolver):
    """Test getting execution graph."""
    step1 = Step(name="step1", type=StepType.SINGLE)
    step2 = Step(name="step2", type=StepType.SINGLE, depends_on=["step1"])
    
    resolver.add_step(step1)
    resolver.add_step(step2)
    
    graph = resolver.get_execution_graph()
    
    assert graph["step1"] == set()
    assert graph["step2"] == {"step1"}


def test_complex_dependency_chain(resolver):
    """Test complex dependency chain."""
    # Create a more complex dependency chain
    steps = [
        Step(name="init", type=StepType.SINGLE),
        Step(name="preprocess", type=StepType.SINGLE, depends_on=["init"]),
        Step(name="align", type=StepType.SINGLE, depends_on=["preprocess"]),
        Step(name="qc", type=StepType.SINGLE, depends_on=["preprocess"]),
        Step(name="variant_call", type=StepType.SINGLE, depends_on=["align"]),
        Step(name="annotate", type=StepType.SINGLE, depends_on=["variant_call", "qc"])
    ]
    
    for step in steps:
        resolver.add_step(step)
    
    levels = resolver.sort()
    
    # Verify the execution order
    assert levels[0] == ["init"]
    assert levels[1] == ["preprocess"]
    assert set(levels[2]) == {"align", "qc"}
    assert levels[3] == ["variant_call"]
    assert levels[4] == ["annotate"]


def test_self_dependency_prevention(resolver):
    """Test prevention of self-dependencies."""
    step = Step(
        name="step",
        type=StepType.SINGLE,
        command="${steps.step.outputs.out}"  # Self-reference
    )
    
    resolver.add_step(step)
    # Verify no self-dependency was added
    assert "step" not in resolver.nodes["step"].dependencies 