# BioFlow

[English](#english) | [中文](#中文)

<div id="english">

## Overview

BioFlow is a lightweight, container-based workflow engine designed specifically for bioinformatics pipelines. It provides a simple yet powerful YAML-based workflow definition language with support for Docker containers, dependency management, and parallel execution.

### Key Features

- **Simple YAML Configuration**
  - Human-readable workflow definitions
  - Environment variable support
  - Container configuration
  - Step dependencies

- **Docker Container Support**
  - Automatic image pulling
  - Volume mounting
  - Environment variable passing
  - Container resource management

- **Dependency Management**
  - Explicit dependency declaration
  - Automatic dependency resolution
  - Parallel execution of independent steps
  - Cycle detection

- **Robust Execution**
  - Asynchronous execution
  - Error handling
  - Status tracking
  - Detailed logging

## Installation

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from source
git clone https://github.com/yourusername/bioflow.git
cd bioflow
pip install -e ".[dev]"
```

## Quick Start

1. Create a workflow configuration file `workflow.yaml`:

```yaml
name: example-workflow
version: "1.0"
description: "Example workflow"

global:
  working_dir: "./work"
  temp_dir: "./temp"

env:
  INPUT_DIR: "./input"
  OUTPUT_DIR: "./output"
  SAMPLE_NAME: "test_sample"

workflow:
  steps:
    - name: quality_control
      type: single
      command: |
        echo "Running QC on ${env.SAMPLE_NAME}..."
        echo "Quality metrics:"
        echo "Read count: 1000000"
      container:
        type: docker
        image: alpine
        version: "latest"
        mounts:
          - host: ${env.OUTPUT_DIR}/qc
            container: /data/qc

    - name: analysis
      type: single
      command: |
        echo "Analyzing ${env.SAMPLE_NAME}..."
        echo "Analysis complete"
      container:
        type: docker
        image: alpine
        version: "latest"
        mounts:
          - host: ${env.OUTPUT_DIR}/results
            container: /data/results
      depends_on:
        - quality_control
```

2. Run the workflow:

```python
from pathlib import Path
from bioflow.parser import WorkflowParser
from bioflow.engine import WorkflowExecutor

# Parse workflow
parser = WorkflowParser()
workflow = parser.parse("workflow.yaml")

# Create executor
executor = WorkflowExecutor(
    workflow=workflow,
    working_dir=Path("work"),
    temp_dir=Path("temp")
)

# Execute workflow
result = await executor.execute()
```

## Documentation

For more detailed documentation and examples, please see:
- [Development Guide](DEVELOPMENT.md)
- [Example Workflows](examples/)

## Contributing

Contributions are welcome! Please read our [Contributing Guide](DEVELOPMENT.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

</div>

<div id="中文">

## 概述

BioFlow 是一个专为生物信息学设计的轻量级、基于容器的工作流引擎。它提供了简单但强大的基于 YAML 的工作流定义语言，支持 Docker 容器、依赖管理和并行执行。

### 主要特性

- **简单的 YAML 配置**
  - 人类可读的工作流定义
  - 环境变量支持
  - 容器配置
  - 步骤依赖

- **Docker 容器支持**
  - 自动镜像拉取
  - 卷挂载
  - 环境变量传递
  - 容器资源管理

- **依赖管理**
  - 显式依赖声明
  - 自动依赖解析
  - 独立步骤并行执行
  - 循环检测

- **健壮的执行**
  - 异步执行
  - 错误处理
  - 状态跟踪
  - 详细日志

## 安装

```bash
# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 从源码安装
git clone https://github.com/yourusername/bioflow.git
cd bioflow
pip install -e ".[dev]"
```

## 快速开始

1. 创建工作流配置文件 `workflow.yaml`：

```yaml
name: example-workflow
version: "1.0"
description: "示例工作流"

global:
  working_dir: "./work"
  temp_dir: "./temp"

env:
  INPUT_DIR: "./input"
  OUTPUT_DIR: "./output"
  SAMPLE_NAME: "test_sample"

workflow:
  steps:
    - name: quality_control
      type: single
      command: |
        echo "对 ${env.SAMPLE_NAME} 进行质控..."
        echo "质控指标："
        echo "读数：1000000"
      container:
        type: docker
        image: alpine
        version: "latest"
        mounts:
          - host: ${env.OUTPUT_DIR}/qc
            container: /data/qc

    - name: analysis
      type: single
      command: |
        echo "分析 ${env.SAMPLE_NAME}..."
        echo "分析完成"
      container:
        type: docker
        image: alpine
        version: "latest"
        mounts:
          - host: ${env.OUTPUT_DIR}/results
            container: /data/results
      depends_on:
        - quality_control
```

2. 运行工作流：

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

## 文档

更详细的文档和示例，请参见：
- [开发指南](DEVELOPMENT.md)
- [示例工作流](examples/)

## 贡献

欢迎贡献！请阅读我们的[开发指南](DEVELOPMENT.md)了解行为准则和提交拉取请求的流程。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

</div> 