# BioFlow

BioFlow 是一个专门为生物信息学设计的工作流引擎，提供强大而灵活的工作流定义和执行功能。

## 特性

- **强大的工作流定义语言**
  - YAML 格式配置
  - 支持参数化
  - 支持环境变量
  - 支持条件执行

- **容器化执行**
  - 支持 Docker 容器
  - 自动镜像管理
  - 卷挂载支持
  - 环境变量传递

- **依赖管理**
  - 显式依赖声明
  - 自动依赖解析
  - 支持复杂依赖关系
  - 循环依赖检测

- **并行执行**
  - 自动并行化
  - 基于依赖的调度
  - 支持并行和顺序执行组

- **错误处理**
  - 详细的错误报告
  - 步骤重试机制
  - 错误恢复策略

## 安装

```bash
pip install bioflow
```

## 快速开始

1. 创建工作流配置文件 `workflow.yaml`：

```yaml
name: example-workflow
version: "1.0"
description: "Example bioinformatics workflow"

env:
  THREADS: "4"
  MEMORY: "8G"

steps:
  - name: fastqc
    type: single
    command: "fastqc input.fastq -o output/"
    container:
      type: docker
      image: biocontainers/fastqc
      version: "0.11.9"
    
  - name: bwa_mem
    type: single
    command: "bwa mem -t $THREADS ref.fa input.fastq > output.sam"
    container:
      type: docker
      image: biocontainers/bwa
      version: "0.7.17"
    depends_on:
      - fastqc

  - name: samtools_sort
    type: single
    command: "samtools sort -@ $THREADS output.sam -o output.bam"
    container:
      type: docker
      image: biocontainers/samtools
      version: "1.9"
    depends_on:
      - bwa_mem
```

2. 执行工作流：

```python
from pathlib import Path
from bioflow.parser import WorkflowParser
from bioflow.engine import WorkflowExecutor

# 解析工作流
parser = WorkflowParser()
workflow = parser.parse("workflow.yaml")

# 创建执行器
executor = WorkflowExecutor(
    workflow=workflow,
    working_dir=Path("work"),
    temp_dir=Path("temp")
)

# 执行工作流
result = await executor.execute()
```

## 工作流配置

### 基本结构

```yaml
name: workflow-name
version: "1.0"
description: "Workflow description"

env:
  KEY: "value"

steps:
  - name: step-name
    type: single
    command: "command to run"
    container:
      type: docker
      image: image-name
      version: tag
    depends_on:
      - other-step
```

### 步骤类型

- `single`: 单个命令步骤
- `parallel_group`: 并行执行组
- `sequential_group`: 顺序执行组

### 容器配置

```yaml
container:
  type: docker
  image: image-name
  version: tag
  environment:
    KEY: "value"
  mounts:
    - host: /host/path
      container: /container/path
```

## API 文档

### Parser 模块

```python
from bioflow.parser import WorkflowParser

parser = WorkflowParser()
workflow = parser.parse("workflow.yaml")
```

### Engine 模块

```python
from bioflow.engine import WorkflowExecutor

executor = WorkflowExecutor(workflow, working_dir, temp_dir)
result = await executor.execute()
```

## 开发

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/bioflow.git
cd bioflow
```

2. 安装开发依赖：
```bash
pip install -e ".[dev]"
```

3. 运行测试：
```bash
pytest
```

## 许可证

MIT License 