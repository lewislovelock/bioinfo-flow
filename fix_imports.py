import os
import re
from pathlib import Path

def fix_imports(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace 'from src.bioflow' with 'from bioflow'
    content = re.sub(r'from src\.bioflow', 'from bioflow', content)
    # Replace 'import src.bioflow' with 'import bioflow'
    content = re.sub(r'import src\.bioflow', 'import bioflow', content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def main():
    # Get all Python test files
    test_dir = Path('tests')
    test_files = test_dir.glob('**/*.py')
    
    for file_path in test_files:
        print(f"Fixing imports in {file_path}")
        fix_imports(file_path)

if __name__ == '__main__':
    main() 