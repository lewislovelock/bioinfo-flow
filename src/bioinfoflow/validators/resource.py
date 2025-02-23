"""
Resource validator for BioinfoFlow workflows.

This module provides validation functionality for resource requirements.
"""

import re
from typing import Optional, Dict

from ..core.models import ResourceRequirements
from ..core.exceptions import ValidationError
from ..utils.logging import debug, error

def _parse_size(size: str) -> Optional[int]:
    """Parse size string to bytes."""
    if not size:
        return None
    
    match = re.match(r'^(\d+)([MGT]B)$', size)
    if not match:
        return None
    
    value, unit = match.groups()
    value = int(value)
    
    multipliers = {
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024,
    }
    
    return value * multipliers[unit]

def validate_resources(resources: ResourceRequirements) -> None:
    """
    Validate resource requirements.
    
    Args:
        resources: Resource requirements to validate
        
    Raises:
        ValidationError: If validation fails
    """
    debug("Validating resource requirements")
    
    # Validate CPU
    if resources.cpu < 1:
        error("Invalid CPU count: {}", resources.cpu)
        raise ValidationError("CPU count must be at least 1")
    
    # Validate memory format and value
    if not re.match(r'^\d+[MGT]B$', resources.memory):
        error("Invalid memory format: {}", resources.memory)
        raise ValidationError("Invalid memory format. Use format like '4GB', '512MB'")
    
    memory_bytes = _parse_size(resources.memory)
    if memory_bytes and memory_bytes < 1024 * 1024:  # Less than 1MB
        error("Memory value too small: {}", resources.memory)
        raise ValidationError("Memory value must be at least 1MB")
    
    # Validate disk format if specified
    if resources.disk:
        if not re.match(r'^\d+[MGT]B$', resources.disk):
            error("Invalid disk format: {}", resources.disk)
            raise ValidationError("Invalid disk format. Use format like '10GB', '1TB'")
        
        disk_bytes = _parse_size(resources.disk)
        if disk_bytes and disk_bytes < 1024 * 1024:  # Less than 1MB
            error("Disk value too small: {}", resources.disk)
            raise ValidationError("Disk value must be at least 1MB")
    
    # Validate GPU count if specified
    if resources.gpu is not None:
        if resources.gpu < 0:
            error("Invalid GPU count: {}", resources.gpu)
            raise ValidationError("GPU count cannot be negative")
        if resources.gpu > 8:  # Reasonable maximum for MVP
            error("GPU count too high: {}", resources.gpu)
            raise ValidationError("GPU count cannot exceed 8 for MVP")
    
    debug("Resource requirements validation passed") 