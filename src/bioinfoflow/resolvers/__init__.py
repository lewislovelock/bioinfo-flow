"""
Resolvers module for BioinfoFlow.

This module provides functionality for resolving variables and paths
in workflow configurations.
"""

from .variable import resolve_variables
from .path import resolve_paths, normalize_path

__all__ = [
    "resolve_variables",  # Variable reference resolution
    "resolve_paths",     # Path resolution and validation
    "normalize_path",    # Path normalization helper
] 