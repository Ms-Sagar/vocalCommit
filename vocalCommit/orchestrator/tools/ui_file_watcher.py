"""
UI File Watcher - Monitor changes to todo-ui files
"""

import os
import time
import logging
from typing import Dict, List, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class UIFileHandler(FileSystemEventHandler):
    """Handle file system events for UI files."""
    
    def __init__(self, callback: Callable[[str, str], None]):
        self.callback = callback
        self.ui_extensions = {'.tsx', '.ts', '.css', '.scss', '.js', '.jsx'}
    
    def on_modified(self, event):
        if not event.is_directory:
            file_path = event.src_path
            _, ext = os.path.splitext(file_path)
            
            if ext in self.ui_extensions:
                logger.info(f"UI file modified: {file_path}")
                self.callback("modified", file_path)
    
    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            _, ext = os.path.splitext(file_path)
            
            if ext in self.ui_extensions:
                logger.info(f"UI file created: {file_path}")
                self.callback("created", file_path)

class UIFileWatcher:
    """Watch UI files for changes and trigger callbacks."""
    
    def __init__(self, watch_paths: List[str]):
        self.watch_paths = watch_paths
        self.observer = Observer()
        self.callbacks = []
        self.is_watching = False
    
    def add_callback(self, callback: Callable[[str, str], None]):
        """Add a callback to be called when files change."""
        self.callbacks.append(callback)
    
    def _handle_file_change(self, event_type: str, file_path: str):
        """Handle file change events."""
        for callback in self.callbacks:
            try:
                callback(event_type, file_path)
            except Exception as e:
                logger.error(f"Error in file change callback: {e}")
    
    def start_watching(self):
        """Start watching for file changes."""
        if self.is_watching:
            return
        
        handler = UIFileHandler(self._handle_file_change)
        
        for path in self.watch_paths:
            if os.path.exists(path):
                self.observer.schedule(handler, path, recursive=True)
                logger.info(f"Watching UI files in: {path}")
            else:
                logger.warning(f"Watch path does not exist: {path}")
        
        self.observer.start()
        self.is_watching = True
        logger.info("UI file watcher started")
    
    def stop_watching(self):
        """Stop watching for file changes."""
        if not self.is_watching:
            return
        
        self.observer.stop()
        self.observer.join()
        self.is_watching = False
        logger.info("UI file watcher stopped")
    
    def get_file_info(self, file_path: str) -> Dict[str, any]:
        """Get information about a file."""
        if not os.path.exists(file_path):
            return {"exists": False}
        
        stat = os.stat(file_path)
        return {
            "exists": True,
            "size": stat.st_size,
            "modified_time": stat.st_mtime,
            "modified_time_str": time.ctime(stat.st_mtime)
        }

def create_ui_watcher(todo_ui_path: str = "todo-ui/src") -> UIFileWatcher:
    """Create a UI file watcher for the todo-ui directory (now inside orchestrator)."""
    # Get the orchestrator directory (where this script is running from)
    orchestrator_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Build absolute paths - todo-ui is now inside orchestrator
    base_todo_path = os.path.join(orchestrator_dir, "todo-ui", "src")
    watch_paths = []
    
    # Only add paths that actually exist
    if os.path.exists(base_todo_path):
        watch_paths.append(base_todo_path)
    
    # Add additional paths if they exist
    additional_paths = [
        os.path.join(orchestrator_dir, "todo-ui", "src", "components"),
        os.path.join(orchestrator_dir, "todo-ui", "src", "styles"),
        os.path.join(orchestrator_dir, "todo-ui", "public")
    ]
    
    for path in additional_paths:
        if os.path.exists(path):
            watch_paths.append(path)
    
    return UIFileWatcher(watch_paths)

# Example usage and callback functions
def log_file_changes(event_type: str, file_path: str):
    """Log file changes to console."""
    print(f"🔄 UI File {event_type}: {file_path}")

def notify_ui_reload(event_type: str, file_path: str):
    """Notify that UI should reload (placeholder for WebSocket notification)."""
    print(f"🌐 UI Reload triggered by {event_type}: {os.path.basename(file_path)}")

if __name__ == "__main__":
    # Test the file watcher
    print("🔍 Testing UI File Watcher")
    
    watcher = create_ui_watcher()
    watcher.add_callback(log_file_changes)
    watcher.add_callback(notify_ui_reload)
    
    try:
        watcher.start_watching()
        print("Watching for UI file changes... Press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping file watcher...")
        watcher.stop_watching()
        print("File watcher stopped")