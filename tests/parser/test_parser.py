"""
Tests for workflow parser.
"""
import pytest
from pathlib import Path
from src.bioflow.parser import WorkflowParser
from src.bioflow.parser.models import Workflow


@pytest.fixture
def valid_config_file(tmp_path):
    """Create a valid configuration file."""
    config = """
name: test-workflow
version: 1.0.0
description: Test workflow

global:
  working_dir: /path/to/work
  temp_dir: /path/to/temp
  max_retries: 3
  notification:
    email: test@example.com

env:
  REFERENCE: /path/to/reference.fa

workflow:
  steps:
    - name: test
      type: single
      command: echo 'test'
"""
    config_file = tmp_path / "workflow.yaml"
    config_file.write_text(config)
    return config_file


@pytest.fixture
def parser():
    """WorkflowParser fixture."""
    return WorkflowParser()


def test_parse_valid_config(parser, valid_config_file):
    """Test parsing valid configuration."""
    workflow = parser.parse(valid_config_file)
    assert isinstance(workflow, Workflow)
    assert workflow.name == "test-workflow"
    assert workflow.version == "1.0.0"
    assert len(workflow.steps) == 1


def test_parse_with_parameters(parser, valid_config_file):
    """Test parsing with parameters."""
    parameters = {
        "sample_id": "test_sample"
    }
    workflow = parser.parse(valid_config_file, parameters)
    assert isinstance(workflow, Workflow)


def test_parse_file_not_found(parser):
    """Test parsing non-existent file."""
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("/nonexistent/workflow.yaml"))


def test_parse_invalid_yaml(tmp_path, parser):
    """Test parsing invalid YAML."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content")
    with pytest.raises(Exception):
        parser.parse(config_file)


def test_parse_complex_workflow(tmp_path, parser):
    """Test parsing complex workflow."""
    config = """
name: complex-workflow
version: 1.0.0
description: Complex workflow

global:
  working_dir: /path/to/work
  temp_dir: /path/to/temp
  max_retries: 3
  notification:
    email: test@example.com
    slack_webhook: https://hooks.slack.com/xxx

env:
  REFERENCE: /path/to/reference.fa
  THREADS: "4"

resources:
  default:
    cpu_units: 4
    memory: 16G
    time: 4h
  gpu_support: true

tools:
  bwa:
    container: bwa:latest
    version: 0.7.17

workflow:
  steps:
    - name: preprocessing
      type: parallel_group
      steps:
        - name: fastqc
          type: single
          tool: fastqc
          resources:
            cpu: 2
            memory: 4G
          inputs:
            - name: fastq
              type: file
              value: ${params.input_fastq}
          outputs:
            - name: report
              path: ${working_dir}/qc/report.html
          command: fastqc ${inputs.fastq}

    - name: alignment
      type: sequential_group
      steps:
        - name: bwa_mem
          type: single
          tool: bwa
          depends_on: ["preprocessing"]
          resources:
            cpu: 16
            memory: 32G
          inputs:
            - name: reference
              type: file
              value: ${env.REFERENCE}
            - name: fastq
              type: file
              value: ${params.input_fastq}
          outputs:
            - name: bam
              path: ${working_dir}/align/output.bam
          command: bwa mem -t ${resources.cpu} ${inputs.reference} ${inputs.fastq}

conditions:
  skip_qc:
    when: ${params.skip_qc}
    skip: ["fastqc"]

error_handlers:
  - on_error: bwa_mem
    action: retry
    max_retries: 3
    wait_time: 10m

hooks:
  before_step:
    - name: check_inputs
      script: scripts/check_inputs.py
  after_step:
    - name: backup_outputs
      script: scripts/backup_outputs.py

parameters:
  - name: input_fastq
    type: string
    required: true
    description: Input FASTQ file
  - name: skip_qc
    type: boolean
    default: false
    description: Skip QC steps
"""
    config_file = tmp_path / "complex.yaml"
    config_file.write_text(config)
    
    parameters = {
        "input_fastq": "/path/to/input.fastq",
        "skip_qc": False
    }
    
    workflow = parser.parse(config_file, parameters)
    
    assert workflow.name == "complex-workflow"
    assert workflow.version == "1.0.0"
    assert len(workflow.steps) == 2
    assert workflow.steps[0].type.value == "parallel_group"
    assert workflow.steps[1].type.value == "sequential_group"
    assert len(workflow.conditions) == 1
    assert len(workflow.error_handlers) == 1
    assert workflow.hooks is not None 