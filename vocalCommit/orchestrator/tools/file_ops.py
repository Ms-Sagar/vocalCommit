import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

def get_todo_ui_path() -> Path:
    """Get the path to the todo-ui directory (production or local)."""
    # Check if production todo-ui exists (separate repo)
    production_path = Path(settings.todo_ui_local_path).resolve()
    if production_path.exists() and (production_path / ".git").exists():
        logger.info(f"Using production todo-ui at: {production_path}")
        return production_path
    
    # Fall back to local todo-ui inside orchestrator
    orchestrator_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_path = Path(orchestrator_dir) / "todo-ui"
    logger.info(f"Using local todo-ui at: {local_path}")
    return local_path

def write_to_todo_ui(file_path: str, content: str) -> Dict[str, Any]:
    """
    Safely write files to the todo-ui folder (now inside orchestrator).
    
    Args:
        file_path: Relative path within todo-ui folder
        content: File content to write
        
    Returns:
        Dict containing operation status and details
    """
    try:
        # Get the todo-ui directory (production or local)
        todo_ui_path = get_todo_ui_path()
        
        # Resolve and validate the target path
        target_path = (todo_ui_path / file_path).resolve()
        
        # Security check: ensure target is within todo-ui directory
        if not str(target_path).startswith(str(todo_ui_path)):
            raise ValueError("Invalid file path: outside todo-ui directory")
        
        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Successfully wrote file: {target_path}")
        
        return {
            "status": "success",
            "file_path": str(target_path),
            "size_bytes": len(content.encode('utf-8')),
            "is_production": str(todo_ui_path) == str(Path(settings.todo_ui_local_path).resolve())
        }
        
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        }

def read_from_todo_ui(file_path: str) -> Dict[str, Any]:
    """
    Safely read files from the todo-ui folder (now inside orchestrator).
    
    Args:
        file_path: Relative path within todo-ui folder
        
    Returns:
        Dict containing file content and metadata
    """
    try:
        # Get the todo-ui directory (production or local)
        todo_ui_path = get_todo_ui_path()
        
        target_path = (todo_ui_path / file_path).resolve()
        
        # Security check
        if not str(target_path).startswith(str(todo_ui_path)):
            raise ValueError("Invalid file path: outside todo-ui directory")
        
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "status": "success",
            "content": content,
            "file_path": str(target_path),
            "size_bytes": len(content.encode('utf-8')),
            "is_production": str(todo_ui_path) == str(Path(settings.todo_ui_local_path).resolve())
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

def update_todo_ui_component(component_updates: Dict[str, str]) -> Dict[str, Any]:
    """
    Update todo-ui components directly with new code.
    
    Args:
        component_updates: Dict mapping file paths to new content
        
    Returns:
        Dict containing update results
    """
    updated_files = []
    errors = []
    
    try:
        for file_path, new_content in component_updates.items():
            # Create backup first
            backup_result = create_backup_file(file_path)
            if backup_result["status"] != "success":
                errors.append(f"Failed to backup {file_path}: {backup_result['error']}")
                continue
            
            # Write new content
            result = write_to_todo_ui(file_path, new_content)
            if result["status"] == "success":
                updated_files.append({
                    "file_path": file_path,
                    "size_bytes": result["size_bytes"],
                    "backup_created": True
                })
                logger.info(f"Updated todo-ui component: {file_path}")
            else:
                errors.append(f"Failed to update {file_path}: {result['error']}")
        
        return {
            "status": "success" if not errors else "partial_success",
            "updated_files": updated_files,
            "errors": errors,
            "total_updated": len(updated_files)
        }
        
    except Exception as e:
        logger.error(f"Error updating todo-ui components: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "updated_files": updated_files,
            "errors": errors
        }

def create_backup_file(file_path: str) -> Dict[str, Any]:
    """
    Create a backup of a todo-ui file before modifying it.
    
    Args:
        file_path: Relative path within todo-ui folder
        
    Returns:
        Dict containing backup operation result
    """
    try:
        # Read original file
        read_result = read_from_todo_ui(file_path)
        if read_result["status"] != "success":
            return read_result
        
        # Create backup with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        
        # Write backup
        backup_result = write_to_todo_ui(backup_path, read_result["content"])
        if backup_result["status"] == "success":
            logger.info(f"Created backup: {backup_path}")
            return {
                "status": "success",
                "backup_path": backup_path,
                "original_size": read_result["size_bytes"]
            }
        else:
            return backup_result
            
    except Exception as e:
        logger.error(f"Failed to create backup for {file_path}: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

def generate_code_to_todo_ui(task_id: str, code_files: Dict[str, str]) -> Dict[str, Any]:
    """
    Generate code files directly into todo-ui src directory.
    
    Args:
        task_id: Task identifier for organizing generated files
        code_files: Dict mapping filenames to code content
        
    Returns:
        Dict containing generation results
    """
    generated_files = []
    errors = []
    
    try:
        # Create a generated folder inside todo-ui/src
        generated_dir = f"src/generated/{task_id}"
        
        for filename, content in code_files.items():
            file_path = f"{generated_dir}/{filename}"
            result = write_to_todo_ui(file_path, content)
            
            if result["status"] == "success":
                generated_files.append({
                    "filename": filename,
                    "path": result["file_path"],
                    "size": result["size_bytes"]
                })
                logger.info(f"Generated code file: {file_path}")
            else:
                errors.append(f"Failed to generate {filename}: {result['error']}")
        
        return {
            "status": "success" if not errors else "partial_success",
            "generated_files": generated_files,
            "errors": errors,
            "total_generated": len(generated_files),
            "generated_dir": generated_dir
        }
        
    except Exception as e:
        logger.error(f"Error generating code to todo-ui: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "generated_files": generated_files,
            "errors": errors
        }