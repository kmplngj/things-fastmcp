#!/usr/bin/env python3
"""
Template Storage for Things FastMCP

Provides persistent storage for project templates using py-key-value-aio.
Templates are stored with encrypted disk storage in ~/.things-fastmcp/templates/

Uses FastMCP's recommended storage backend: py-key-value-aio
https://github.com/strawgate/py-key-value
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.stores.disk import DiskStore

logger = logging.getLogger(__name__)

# Template storage directory
TEMPLATE_DIR = Path.home() / ".things-fastmcp" / "templates"
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

# Initialize encrypted disk storage for templates
# DiskStore provides persistent, file-based storage
template_store: AsyncKeyValue = DiskStore(directory=str(TEMPLATE_DIR))


def validate_template_name(name: str) -> bool:
    """
    Validate template name (alphanumeric, hyphens, underscores only).
    
    Args:
        name: Template name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    
    # Allow alphanumeric, hyphens, underscores (safe for keys)
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))


async def save_template(template_name: str, template_data: Dict[str, Any]) -> None:
    """
    Save a project template using py-key-value-aio disk storage.
    
    Args:
        template_name: Unique identifier for the template (alphanumeric, hyphens, underscores)
        template_data: Dictionary containing template structure
            Expected keys: title, notes, tags, area_id, todos, created, version
    
    Raises:
        ValueError: If template name is invalid or data is malformed
        OSError: If storage operations fail
    """
    if not validate_template_name(template_name):
        raise ValueError(
            "Template name must contain only alphanumeric characters, hyphens, and underscores"
        )
    
    if not isinstance(template_data, dict):
        raise ValueError("Template data must be a dictionary")
    
    # Add metadata if not present
    if "created" not in template_data:
        template_data["created"] = datetime.now(timezone.utc).isoformat()
    if "version" not in template_data:
        template_data["version"] = "1.0"
    
    logger.info(f"Saving template '{template_name}' via py-key-value-aio DiskStore")
    
    try:
        await template_store.put(
            key=template_name,
            value=template_data,
            collection="templates"
        )
    except Exception as e:
        logger.error(f"Failed to save template '{template_name}': {e}")
        raise OSError(f"Failed to save template: {e}") from e


async def get_template(template_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a project template from storage.
    
    Args:
        template_name: Name of the template to retrieve
        
    Returns:
        Template data dictionary, or None if template doesn't exist
        
    Raises:
        ValueError: If template name is invalid
        OSError: If storage operations fail
    """
    if not validate_template_name(template_name):
        raise ValueError(
            "Template name must contain only alphanumeric characters, hyphens, and underscores"
        )
    
    try:
        return await template_store.get(key=template_name, collection="templates")
    except Exception as e:
        logger.error(f"Failed to read template '{template_name}': {e}")
        raise OSError(f"Failed to read template: {e}") from e


async def list_templates() -> List[Dict[str, Any]]:
    """
    List all available project templates.
    
    Returns:
        List of template info dictionaries with keys: name, title, created, todo_count
        
    Raises:
        OSError: If storage operations fail
    """
    templates = []
    
    try:
        # Check if store supports enumeration
        if not hasattr(template_store, 'enumerate_keys'):
            # Fallback: scan directory for .json files (DiskStore uses JSON files)
            for template_file in TEMPLATE_DIR.glob("*.json"):
                template_name = template_file.stem
                
                try:
                    template_data = await get_template(template_name)
                    if template_data:
                        templates.append({
                            "name": template_name,
                            "title": template_data.get("title", "Untitled"),
                            "created": template_data.get("created", "Unknown"),
                            "todo_count": len(template_data.get("todos", []))
                        })
                except Exception as e:
                    logger.warning(f"Skipping corrupted template '{template_name}': {e}")
                    continue
        else:
            # Use enumerate_keys if available
            keys = await template_store.enumerate_keys(collection="templates")
            for template_name in keys:
                try:
                    template_data = await get_template(template_name)
                    if template_data:
                        templates.append({
                            "name": template_name,
                            "title": template_data.get("title", "Untitled"),
                            "created": template_data.get("created", "Unknown"),
                            "todo_count": len(template_data.get("todos", []))
                        })
                except Exception as e:
                    logger.warning(f"Skipping corrupted template '{template_name}': {e}")
                    continue
        
        return sorted(templates, key=lambda x: x["name"])
    
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise OSError(f"Failed to list templates: {e}") from e


async def delete_template(template_name: str) -> bool:
    """
    Delete a project template from storage.
    
    Args:
        template_name: Name of the template to delete
        
    Returns:
        True if template was deleted, False if it didn't exist
        
    Raises:
        ValueError: If template name is invalid
        OSError: If storage operations fail
    """
    if not validate_template_name(template_name):
        raise ValueError(
            "Template name must contain only alphanumeric characters, hyphens, and underscores"
        )
    
    try:
        deleted = await template_store.delete(key=template_name, collection="templates")
        if deleted:
            logger.info(f"Deleted template '{template_name}'")
        return deleted
    except Exception as e:
        logger.error(f"Failed to delete template '{template_name}': {e}")
        raise OSError(f"Failed to delete template: {e}") from e


async def template_exists(template_name: str) -> bool:
    """
    Check if a template exists.
    
    Args:
        template_name: Name of the template to check
        
    Returns:
        True if template exists, False otherwise
    """
    try:
        template = await get_template(template_name)
        return template is not None
    except Exception:
        return False


# Synchronous wrappers for backward compatibility with non-async tools
def save_template_sync(template_name: str, template_data: Dict[str, Any]) -> None:
    """Synchronous wrapper for save_template."""
    asyncio.run(save_template(template_name, template_data))


def get_template_sync(template_name: str) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for get_template."""
    return asyncio.run(get_template(template_name))


def list_templates_sync() -> List[Dict[str, Any]]:
    """Synchronous wrapper for list_templates."""
    return asyncio.run(list_templates())


def delete_template_sync(template_name: str) -> bool:
    """Synchronous wrapper for delete_template."""
    return asyncio.run(delete_template(template_name))


def template_exists_sync(template_name: str) -> bool:
    """Synchronous wrapper for template_exists."""
    return asyncio.run(template_exists(template_name))
