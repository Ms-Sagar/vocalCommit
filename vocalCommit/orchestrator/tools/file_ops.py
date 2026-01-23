import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def write_to_frontend(file_path: str, content: str, frontend_base: str = "../frontend") -> Dict[str, Any]:
    """
    Safely write files to the frontend folder.
    
    Args:
        file_path: Relative path within frontend folder
        content: File content to write
        frontend_base: Base path to frontend folder
        
    Returns:
        Dict containing operation status and details
    """
    try:
        # Resolve and validate the target path
        frontend_path = Path(frontend_base).resolve()
        target_path = (frontend_path / file_path).resolve()
        
        # Security check: ensure target is within frontend directory
        if not str(target_path).startswith(str(frontend_path)):
            raise ValueError("Invalid file path: outside frontend directory")
        
        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Successfully wrote file: {target_path}")
        
        return {
            "status": "success",
            "file_path": str(target_path),
            "size_bytes": len(content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        }

def read_from_frontend(file_path: str, frontend_base: str = "../frontend") -> Dict[str, Any]:
    """
    Safely read files from the frontend folder.
    
    Args:
        file_path: Relative path within frontend folder
        frontend_base: Base path to frontend folder
        
    Returns:
        Dict containing file content and metadata
    """
    try:
        frontend_path = Path(frontend_base).resolve()
        target_path = (frontend_path / file_path).resolve()
        
        # Security check
        if not str(target_path).startswith(str(frontend_path)):
            raise ValueError("Invalid file path: outside frontend directory")
        
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "status": "success",
            "content": content,
            "file_path": str(target_path),
            "size_bytes": len(content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        }

def create_project_structure(base_path: str, structure: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a project structure based on a nested dictionary.
    
    Args:
        base_path: Base directory path
        structure: Nested dict representing folder/file structure
        
    Returns:
        Dict containing creation results
    """
    created_items = []
    errors = []
    
    try:
        base = Path(base_path)
        base.mkdir(parents=True, exist_ok=True)
        
        def create_recursive(current_path: Path, items: Dict[str, Any]):
            for name, content in items.items():
                item_path = current_path / name
                
                if isinstance(content, dict):
                    # It's a directory
                    item_path.mkdir(exist_ok=True)
                    created_items.append(f"DIR: {item_path}")
                    create_recursive(item_path, content)
                else:
                    # It's a file
                    with open(item_path, 'w', encoding='utf-8') as f:
                        f.write(str(content))
                    created_items.append(f"FILE: {item_path}")
        
        create_recursive(base, structure)
        
        return {
            "status": "success",
            "created_items": created_items,
            "total_items": len(created_items)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "created_items": created_items,
            "errors": errors
        }
