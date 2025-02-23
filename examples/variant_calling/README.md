# Variant Calling Pipeline Example

This example demonstrates a basic germline variant calling workflow using BWA and GATK4.

## Directory Structure
```
variant_calling/
├── workflows/
│   └── variant_calling.yaml    # Workflow definition
├── inputs/
│   ├── samples.csv            # Sample information
│   ├── sample1_R1.fastq.gz    # Sample 1 forward reads
│   ├── sample1_R2.fastq.gz    # Sample 1 reverse reads
│   ├── sample2_R1.fastq.gz    # Sample 2 forward reads
│   └── sample2_R2.fastq.gz    # Sample 2 reverse reads
├── reference/
│   ├── hg38.fa               # Reference genome
│   ├── dbsnp.vcf.gz         # dbSNP database
│   └── known_indels.vcf.gz  # Known indels
└── run_pipeline.py           # Example script to run the workflow
```

## Prerequisites

1. Python 3.8 or later
2. Docker installed and running
3. Reference files:
   - Download hg38 reference genome and index files
   - Download dbSNP and known indels VCF files

4. Input data:
   - Prepare paired-end FASTQ files
   - Update `samples.csv` with your sample information

## Installation

1. Install BioinfoFlow:
   ```bash
   pip install bioinfoflow
   ```

2. Clone the example repository:
   ```bash
   git clone https://github.com/yourusername/bioinfo-flow.git
   cd bioinfo-flow/examples/variant_calling
   ```

## Running the Workflow

1. Place your input FASTQ files in the `inputs` directory
2. Update `samples.csv` with the correct file paths
3. Run the workflow:
   ```bash
   python run_pipeline.py
   ```

The script will:
1. Check prerequisites (Python version, Docker availability)
2. Parse and validate the workflow definition
3. Execute the workflow with proper resource management
4. Monitor progress and handle any errors
5. Clean up resources on completion

## Expected Outputs

The workflow will generate:
1. FastQC quality reports in `qc/<sample_id>/`
2. Aligned BAM files in `aligned/`
3. Variant calls (VCF) in `variants/`

## Logging

Logs are written to:
- Console output for progress monitoring
- `pipeline.log` for detailed execution logs

## Troubleshooting

Common issues:
1. Docker not running:
   ```
   Error: Docker is not available
   ```
   Solution: Start Docker daemon

2. Missing input files:
   ```
   Error: Input file not found: inputs/sample1_R1.fastq.gz
   ```
   Solution: Check file paths in samples.csv

3. Resource limits:
   ```
   Error: Insufficient memory available
   ```
   Solution: Adjust resource requirements in workflow.yaml

## Support

For issues and questions:
- Open an issue on GitHub
- Check the BioinfoFlow documentation
- Contact the development team 