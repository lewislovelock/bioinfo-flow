"""
Container validator for BioinfoFlow workflows.

This module provides validation functionality for container configurations.
"""

import re
from typing import Dict

from ..core.models import ContainerConfig
from ..core.exceptions import ValidationError
from ..utils.logging import debug, error

def validate_containers(container: ContainerConfig) -> None:
    """
    Validate container configuration.
    
    Args:
        container: Container configuration to validate
        
    Raises:
        ValidationError: If validation fails
    """
    debug("Validating container configuration")
    
    # Validate image name
    if not container.image:
        error("Container image is required")
        raise ValidationError("Container image is required")
    
    # Docker image name validation best practice
    if not re.match(r'^[a-z0-9]+([._-][a-z0-9]+)*(/[a-z0-9]+([._-][a-z0-9]+)*)*$', container.image):
        error("Invalid image name format: {}", container.image)
        raise ValidationError(
            "Invalid image name format. Use lowercase letters, numbers, and separators (., _, -)"
        )
    
    # Validate tag
    if ":" in container.image:
        error("Invalid image format: tag should be specified in tag field")
        raise ValidationError("Tag should be specified in tag field, not in image string")
    
    if not container.tag:
        error("Container tag is required")
        raise ValidationError("Container tag is required")
    
    # Basic tag validation
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', container.tag):
        error("Invalid tag format: {}", container.tag)
        raise ValidationError(
            "Invalid tag format. Use letters, numbers, and separators (., _, -)"
        )
    
    # Validate volume mounts
    for volume in container.volumes:
        if ":" not in volume:
            error("Invalid volume format: {}", volume)
            raise ValidationError(f"Invalid volume format: {volume}. Use 'source:target'")
        
        source, target = volume.split(":", 1)
        if not source or not target:
            error("Invalid volume format: {}", volume)
            raise ValidationError(f"Invalid volume format: {volume}. Both source and target are required")
        
        # Basic path validation
        if not all(part.strip() for part in source.split("/")):
            error("Invalid volume source path: {}", source)
            raise ValidationError(f"Invalid volume source path: {source}")
        if not all(part.strip() for part in target.split("/")):
            error("Invalid volume target path: {}", target)
            raise ValidationError(f"Invalid volume target path: {target}")
    
    # Validate environment variables
    for key, value in container.env.items():
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
            error("Invalid environment variable name: {}", key)
            raise ValidationError(
                f"Invalid environment variable name: {key}. "
                "Use letters, numbers, and underscore, starting with letter or underscore"
            )
    
    debug("Container configuration validation passed") 