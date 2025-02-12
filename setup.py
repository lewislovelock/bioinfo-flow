from setuptools import setup, find_packages

setup(
    name="bioflow",
    version="0.1.0",
    description="A workflow engine for bioinformatics",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.7",
    install_requires=[
        "pyyaml>=5.1",
        "docker>=5.0.0",
        "asyncio>=3.4.3",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.14.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "isort>=5.0",
            "mypy>=0.800",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 