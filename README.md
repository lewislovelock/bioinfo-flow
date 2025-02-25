# BioinfoFlow Specification v0.1 🧬

## Table of Contents
- [Overview](#overview) 📋
- [Core Concepts](#core-concepts) 💡
- [Configuration Reference](#configuration-reference) ⚙️
- [Examples](#examples) 🌟
- [Key Features](#key-features) ⭐
- [Best Practices](#best-practices) 🎯
- [Style Guide](#style-guide) 📝
- [Version Control](#version-control) 🔄

## Overview 📋

BioinfoFlow is a powerful workflow engine specifically designed for bioinformatics applications, enabling reproducible, scalable, and container-native data analysis pipelines. This specification defines a human-readable workflow language that emphasizes simplicity and maintainability.

### Target Audience
- Bioinformaticians and computational biologists
- Research laboratories and institutions
- Bioinformatics pipeline developers
- Data scientists working with biological data

### Use Cases
- High-throughput sequencing data analysis
- Genomics and transcriptomics workflows
- Population genetics studies
- Clinical genomics pipelines
- Custom bioinformatics tool integration

## Core Concepts 💡

BioinfoFlow is built around four fundamental concepts that work together to create robust bioinformatics pipelines:

### Workflows
A workflow is a collection of steps that process biological data. Each workflow:
- Has a unique name and version
- Contains one or more steps
- Defines its input requirements
- Specifies resource requirements
- Maintains reproducibility through containerization

### Steps
Steps are the basic building blocks of a workflow. They can be:
- Single steps (e.g., quality control, alignment)
- Parallel steps (e.g., sample-level processing)
- Sequential steps (e.g., variant calling pipeline)

Each step is:
- Containerized for reproducibility
- Resource-aware for efficient execution
- Input/output tracked for dependency management
- Automatically logged for monitoring

### Dependencies
Steps can depend on other steps, forming a directed acyclic graph (DAG):
- Explicit dependencies via 'after' field
- Implicit dependencies through input/output relationships
- Parallel execution of independent steps
- Automatic dependency resolution

### Containers
Each step runs in its own container environment, ensuring:
- Software version control
- Environment isolation
- Reproducibility across systems
- Portable execution

## Configuration Reference ⚙️

BioinfoFlow uses YAML format for workflow definitions. This section details the configuration structure and options available.

### Path Configuration

BioinfoFlow uses a flexible path resolution system:

1. **Base Directory**: Set with `BIOFLOW_BASE=/path/to/base` (default: current directory)
2. **Directory Structure**: All other directories derive from `BIOFLOW_BASE`:
   ```
   ${BIOFLOW_BASE}/
   ├── refs/          # Reference data (BIOFLOW_REFS)
   ├── workflows/     # Workflow definitions (BIOFLOW_WORKFLOWS)
   ├── runs/          # Workflow runs (BIOFLOW_RUNS)
   └── tmp/           # Temporary files (BIOFLOW_TMP)
   ```

3. **Path Resolution Rules**:
   - Absolute paths (starting with `/`) are used as-is
   - Paths starting with `~/` are expanded to the user's home directory
   - Paths starting with `./` are relative to the current directory
   - Paths without a leading `/`, `~/`, or `./` are relative to the workflow directory
   - Special variables like `${workflow.dir}` can be used for workflow-relative paths

### Root Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Workflow name |
| version | string | Yes | Workflow version |
| description | string | No | Workflow description |
| config | object | No | Global configuration |
| inputs | object | No | Global inputs |
| steps | object | Yes | Workflow steps |

### Configuration

The `config` section defines configuration settings like database paths, ref path, etc.

```yaml
config:
  base_dir: "/mnt/nas/bioflow"       # Override BIOFLOW_BASE
  ref_dir: "${config.base_dir}/refs" # Override BIOFLOW_REFS
  tmp_dir: "/scratch/tmp"            # Custom tmp directory
  
  # Reference data paths (relative to ref_dir)
  ref_genome: "hg38/genome.fa"       # Resolves to /mnt/nas/bioflow/refs/hg38/genome.fa
  dbsnp: "hg38/dbsnp.vcf.gz"
  known_indels: "hg38/known_indels.vcf.gz"
```

### Directory Structure

BioinfoFlow creates this directory structure for each workflow run:
```
${BIOFLOW_RUNS}/
└── workflow_name/              # Workflow name
    └── version/                # Workflow version
        └── run_id/             # Run ID (timestamp + random string)
            ├── workflow.yaml   # Copy of workflow definition
            ├── inputs/         # Input files/links
            ├── outputs/        # Output files
            ├── logs/           # Log files
            └── tmp/            # Temporary files (deleted after run)
```

Each step's outputs are organized within this structure.

### Input Configuration

The `inputs` section supports both single files and sample groups:

```yaml
inputs:
  # Single file input with absolute path
  reference:
    type: file
    path: "/absolute/path/to/reference.fa"  # Absolute path
  
  # Single file input with relative path (relative to workflow input directory)
  reads:
    type: file
    path: "*.fastq.gz"  # Relative to ${workflow.dir}/inputs/
  
  # Single file input with custom base directory
  annotations:
    type: file
    base_dir: "/data/shared/annotations"  # Custom base directory
    path: "gencode.v38.gtf"              # Relative to base_dir
  
  # Sample group input
  samples:
    type: sample_group
    path: "samples.csv"    # Sample information file, relative to ${workflow.dir}/inputs/
    format: csv            # Format can be csv, tsv, xlsx, etc.
    columns:
      - name: sample_id
        type: string
        unique: true
      - name: read1
        type: file
        path: "*.fastq.gz"
      - name: read2
        type: file
        path: "*.fastq.gz"
```

### Step Configuration

Each step follows a consistent structure:

```yaml
steps:
  step_name:
    container: "image:tag"                   # Container image
    foreach: samples                         # Optional: iterate over samples
    inputs:
      input1: ${steps.prev.outputs.out}      # Reference to previous step output
      input2: ${config.some_setting}         # Reference to configuration
    outputs:
      output1: "path/to/output"              # Output definition
    command: "command ${inputs.input1}"      # Command template
    after: [dependency1, dependency2]        # Step dependencies
    resources:                               # Resource requirements
      cpu: 2
      memory: 4G
```

**Key Fields**:
- `container`: Container image reference
- `volumes`: Container volume configuration, default to BIOFLOW_BASE
- `foreach`: Optional field for sample iteration
- `inputs`: Input definitions with references
- `outputs`: Output path definitions (using task directory)
- `command`: Command template with variable substitution
- `after`: Step dependencies
- `resources`: Resource requirements

### Variable References

Variables can be referenced using `${...}` syntax:
- `${config.VAR}`: Global configuration values
- `${inputs.NAME}`: Input references
- `${steps.STEP.outputs.NAME}`: Output from previous steps
- `${sample.FIELD}`: Sample field reference (in foreach context)
- `${workflow.name}`: Current workflow name
- `${workflow.version}`: Current workflow version
- `${workflow.dir}`: Current workflow directory
- `${run.id}`: Current run ID
- `${step.name}`: Current step name

**Default Values**:
Use the `:-` syntax to specify default values when a variable might be undefined:
```
${config.threads:-4}  # Use 4 if config.threads is not defined
```

**Environment Variables**:
Access system environment variables with the `env.` prefix:
```
${env.HOME}          # User's home directory
${env.PATH}          # System PATH
${env.BIOFLOW_BASE}  # BIOFLOW_BASE environment variable
```

**Examples**:
```yaml
# Reference a configuration value
command: "samtools view -@ ${config.threads}"

# Reference a step output
inputs:
  bam: ${steps.alignment.outputs.aligned_bam}

# Use a sample field in a foreach context
outputs:
  vcf: "variants/${sample.sample_id}.vcf"

# Combine with default value
memory: "${config.mem_gb:-4}G"
```

### Multi-sample Processing

For workflows processing multiple samples:
1. Define sample structure in `inputs.samples`
2. Use `foreach: samples` in steps
3. Reference sample fields with `${sample.field_name}`
4. Collect outputs using step references

## Examples 🌟

BioinfoFlow examples demonstrate common bioinformatics workflows and best practices for configuration.

### Variant Calling Pipeline Example

This example shows a complete germline variant calling workflow using BWA and GATK4:

```yaml
name: variant_calling_pipeline
version: "1.0.0"
description: "Germline variant calling workflow using BWA and GATK4"

config:
  ref_genome: "reference/hg38.fa"
  dbsnp: "reference/dbsnp.vcf.gz"
  known_indels: "reference/known_indels.vcf.gz"

inputs:
  samples:
    type: sample_group
    path: "samples.csv"
    format: csv
    columns:
      - name: sample_id
        type: string
        unique: true
      - name: read1
        type: file
        path: "*.fastq.gz"
      - name: read2
        type: file
        path: "*.fastq.gz"

steps:
  fastqc:
    container: "biocontainers/fastqc:v0.11.9"
    foreach: samples
    inputs:
      read1: ${sample.read1}
      read2: ${sample.read2}
    outputs:
      qc_report: "qc/${sample.sample_id}/fastqc_report.html"
    command: |
      fastqc ${inputs.read1} ${inputs.read2} -o $(dirname ${outputs.qc_report})
    resources:
      cpu: 2
      memory: 4G

  bwa_mem:
    container: "biocontainers/bwa:v0.7.17"
    foreach: samples
    inputs:
      read1: ${sample.read1}
      read2: ${sample.read2}
      ref: ${config.ref_genome}
    outputs:
      bam: "aligned/${sample.sample_id}.bam"
    command: |
      bwa mem -t ${resources.cpu} \
      -R "@RG\tID:${sample.sample_id}\tSM:${sample.sample_id}" \
      ${inputs.ref} ${inputs.read1} ${inputs.read2} \
      | samtools sort -@ ${resources.cpu} -o ${outputs.bam}
    after: [fastqc]
    resources:
      cpu: 8
      memory: 16G

  variant_call:
    container: "broadinstitute/gatk:4.2.6.1"
    foreach: samples
    inputs:
      bam: ${steps.bwa_mem.outputs.bam}
      ref: ${config.ref_genome}
    outputs:
      vcf: "variants/${sample.sample_id}.vcf.gz"
    command: |
      gatk HaplotypeCaller \
      -I ${inputs.bam} \
      -R ${inputs.ref} \
      -O ${outputs.vcf}
    after: [bwa_mem]
    resources:
      cpu: 4
      memory: 16G
```

## Experimental Features 🧪

### Metadata
```yaml
metadata:
  author: name
  tags: [DNA-seq, RNA-seq]
  license: MIT
  documentation: "https://docs.example.com"
```

### Conditions
```yaml
conditions:
  file_exists:
    when: "exists:/path/to/file"
    skip: false
```

### Hooks
```yaml
hooks:
  before_step:            # Before step execution
    - name: string
      script: string
  after_step:             # After step execution
    - name: string
      script: string
  on_success:             # On workflow success
    - name: string
      script: string
  on_failure:             # On workflow failure
    - name: string
      script: string
```

### Notifications
```yaml
notifications:
  email:
    recipients: ["user@example.com"]
    subject: "Workflow completed"
    body: "Workflow completed successfully"
  slack:
    webhook_url: "https://hooks.slack.com/services/.../..."
  discord:
    webhook_url: "https://discord.com/api/webhooks/.../..."
  feishu:
    webhook_url: "https://open.larkoffice.com/open-apis/bot/v2/hook/.../..."
```

## Key Features ⭐

- 🐳 Container-native execution with automatic version management
- 📊 Flexible resource management
- 💾 Built-in checkpoint and resume capability
- 🔍 Dynamic input pattern matching
- ⚡ Parallel and sequential execution support
- 🔗 Clear dependency management
- 🛡️ Environment isolation

## Best Practices 🎯

Follow these guidelines to create efficient and maintainable workflows:

### Container Management 🐳
- Use specific version tags for reproducibility
- Choose official or verified container images
- Keep container images minimal and focused

### Resource Management 📊
- Set appropriate CPU and memory limits
- Use resource profiles for different environments
- Monitor resource usage patterns

### Workflow Design 📐
- Keep steps modular and focused
- Use meaningful step and variable names
- Document inputs, outputs, and dependencies
- Follow the principle of least privilege

### Error Handling ⚠️
- Implement appropriate error checking
- Use retry strategies for transient failures
- Log errors with sufficient context
- Clean up temporary resources

## Style Guide 📝

Follow these conventions for consistent workflow definitions:

### Naming Conventions
- Use lowercase for workflow names
- Use snake_case for step names
- Use descriptive names for inputs and outputs

### YAML Formatting
- Use 2 spaces for indentation
- Break long commands with line continuations
- Group related configuration items

### Value Formatting
Use quotes for:
- File paths: `"path/to/file"`
- Version numbers: `"1.0.0"`
- Commands with variables
- Container references

Don't quote:
- Numbers
- Resource units
- Boolean values
- Simple identifiers

## Version Control 🔄

This is version 0.1 of the BioinfoFlow specification. Future versions will focus on:
- Enhanced container orchestration
- Advanced dependency management
- Extended security features
- Improved monitoring capabilities 