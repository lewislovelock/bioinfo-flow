"""
Parser module for BioinfoFlow.

This module provides functionality for parsing workflow definitions
and related configuration files.
"""

from .workflow import parse_workflow

__all__ = ["parse_workflow"] 