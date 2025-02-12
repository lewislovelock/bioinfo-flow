# Development Guide

## Setting up the development environment

1. Clone the repository:
```bash
git clone https://github.com/yourusername/biofo-flow.git
cd biofo-flow
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package in development mode with development dependencies:
```bash
pip install -e ".[dev]"
```

## Running Tests

Run all tests:
```bash
pytest
```

Run tests with coverage report:
```bash
pytest --cov=bioflow --cov-report=html
```

## Code Style

This project uses `black` for code formatting and `isort` for import sorting:

```bash
# Format code
black .

# Sort imports
isort .
```

## Type Checking

Run type checking with mypy:
```bash
mypy src/bioflow
```

## Project Structure

```
biofo-flow/
├── src/
│   └── bioflow/           # Main package
│       ├── engine/        # Workflow execution engine
│       └── parser/        # Workflow configuration parser
├── tests/                 # Test files
├── examples/              # Example workflows and scripts
├── docs/                  # Documentation
├── setup.py              # Package setup
├── pyproject.toml        # Build system requirements
├── README.md             # Project documentation
└── DEVELOPMENT.md        # Development guide
```

## Making Changes

1. Create a new branch for your changes:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and ensure all tests pass:
```bash
pytest
```

3. Format your code:
```bash
black .
isort .
```

4. Commit your changes:
```bash
git add .
git commit -m "Description of your changes"
```

5. Push your changes and create a pull request:
```bash
git push origin feature/your-feature-name
``` 