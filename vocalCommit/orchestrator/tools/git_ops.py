import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GitOperations:
    """Git operations manager for VocalCommit orchestrator."""
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize Git operations.
        
        Args:
            repo_path: Path to git repository. If None, uses current working directory.
        """
        if repo_path is None:
            # Default to the vocalCommit root directory
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.repo_path = current_dir
        else:
            self.repo_path = repo_path
        
        self.repo_path = Path(self.repo_path).resolve()
        logger.info(f"Git operations initialized for repository: {self.repo_path}")
    
    def _run_git_command(self, command: List[str]) -> Dict[str, Any]:
        """
        Execute a git command safely.
        
        Args:
            command: Git command as list of strings
            
        Returns:
            Dict containing command result
        """
        try:
            # Ensure we're in the repository directory
            result = subprocess.run(
                ["git"] + command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Git command timed out",
                "returncode": -1
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "returncode": -1
            }
    
    def check_git_status(self) -> Dict[str, Any]:
        """
        Check git repository status.
        
        Returns:
            Dict containing repository status information
        """
        try:
            # Check if we're in a git repository
            status_result = self._run_git_command(["status", "--porcelain"])
            
            if status_result["status"] != "success":
                return {
                    "status": "error",
                    "error": "Not a git repository or git not available",
                    "is_git_repo": False
                }
            
            # Get current branch
            branch_result = self._run_git_command(["branch", "--show-current"])
            current_branch = branch_result["stdout"] if branch_result["status"] == "success" else "unknown"
            
            # Parse status output
            status_lines = status_result["stdout"].split('\n') if status_result["stdout"] else []
            
            modified_files = []
            untracked_files = []
            staged_files = []
            
            for line in status_lines:
                if len(line) >= 3:
                    status_code = line[:2]
                    file_path = line[3:]
                    
                    if status_code[0] in ['M', 'A', 'D', 'R', 'C']:
                        staged_files.append(file_path)
                    if status_code[1] in ['M', 'D']:
                        modified_files.append(file_path)
                    if status_code == '??':
                        untracked_files.append(file_path)
            
            has_changes = bool(modified_files or untracked_files or staged_files)
            
            return {
                "status": "success",
                "is_git_repo": True,
                "current_branch": current_branch,
                "has_changes": has_changes,
                "modified_files": modified_files,
                "untracked_files": untracked_files,
                "staged_files": staged_files,
                "total_changes": len(modified_files) + len(untracked_files) + len(staged_files)
            }
            
        except Exception as e:
            logger.error(f"Error checking git status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "is_git_repo": False
            }
    
    def stage_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Stage specific files for commit.
        
        Args:
            file_paths: List of file paths to stage
            
        Returns:
            Dict containing staging result
        """
        try:
            if not file_paths:
                return {
                    "status": "error",
                    "error": "No files provided to stage"
                }
            
            # Stage each file
            staged_files = []
            errors = []
            
            for file_path in file_paths:
                result = self._run_git_command(["add", file_path])
                if result["status"] == "success":
                    staged_files.append(file_path)
                    logger.info(f"Staged file: {file_path}")
                else:
                    errors.append(f"Failed to stage {file_path}: {result.get('stderr', 'Unknown error')}")
            
            return {
                "status": "success" if not errors else "partial_success",
                "staged_files": staged_files,
                "errors": errors,
                "total_staged": len(staged_files)
            }
            
        except Exception as e:
            logger.error(f"Error staging files: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def commit_changes(self, message: str, task_id: str, modified_files: List[str]) -> Dict[str, Any]:
        """
        Commit staged changes with a descriptive message.
        
        Args:
            message: Commit message
            task_id: Task identifier for tracking
            modified_files: List of files that were modified
            
        Returns:
            Dict containing commit result
        """
        try:
            # First, stage the modified files
            if modified_files:
                stage_result = self.stage_files(modified_files)
                if stage_result["status"] == "error":
                    return {
                        "status": "error",
                        "error": f"Failed to stage files: {stage_result['error']}"
                    }
            
            # Create commit message with task context
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"[VocalCommit] {message}\n\nTask ID: {task_id}\nTimestamp: {timestamp}\nFiles modified: {len(modified_files)}"
            
            # Commit the changes
            result = self._run_git_command(["commit", "-m", commit_message])
            
            if result["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Commit failed: {result.get('stderr', 'Unknown error')}",
                    "git_output": result
                }
            
            # Get the commit hash
            hash_result = self._run_git_command(["rev-parse", "HEAD"])
            commit_hash = hash_result["stdout"][:8] if hash_result["status"] == "success" else "unknown"
            
            logger.info(f"Successfully committed changes for task {task_id}: {commit_hash}")
            
            return {
                "status": "success",
                "commit_hash": commit_hash,
                "commit_message": commit_message,
                "modified_files": modified_files,
                "task_id": task_id,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error committing changes: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_last_commit_info(self) -> Dict[str, Any]:
        """
        Get information about the last commit.
        
        Returns:
            Dict containing last commit information
        """
        try:
            # Get last commit hash
            hash_result = self._run_git_command(["rev-parse", "HEAD"])
            if hash_result["status"] != "success":
                return {
                    "status": "error",
                    "error": "Failed to get last commit hash"
                }
            
            commit_hash = hash_result["stdout"]
            
            # Get commit message
            message_result = self._run_git_command(["log", "-1", "--pretty=format:%s"])
            commit_message = message_result["stdout"] if message_result["status"] == "success" else "Unknown"
            
            # Get commit timestamp
            timestamp_result = self._run_git_command(["log", "-1", "--pretty=format:%ci"])
            commit_timestamp = timestamp_result["stdout"] if timestamp_result["status"] == "success" else "Unknown"
            
            # Get files changed in last commit
            files_result = self._run_git_command(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"])
            changed_files = files_result["stdout"].split('\n') if files_result["stdout"] else []
            
            return {
                "status": "success",
                "commit_hash": commit_hash,
                "short_hash": commit_hash[:8],
                "commit_message": commit_message,
                "timestamp": commit_timestamp,
                "changed_files": changed_files,
                "total_files": len(changed_files)
            }
            
        except Exception as e:
            logger.error(f"Error getting last commit info: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def rollback_last_commit(self, task_id: str) -> Dict[str, Any]:
        """
        Rollback the last commit (soft reset to keep working directory changes).
        
        Args:
            task_id: Task identifier for logging
            
        Returns:
            Dict containing rollback result
        """
        try:
            # Get last commit info before rollback
            last_commit = self.get_last_commit_info()
            if last_commit["status"] != "success":
                return {
                    "status": "error",
                    "error": "Failed to get last commit information"
                }
            
            # Check if the last commit is a VocalCommit commit
            if "[VocalCommit]" not in last_commit["commit_message"]:
                return {
                    "status": "error",
                    "error": "Last commit is not a VocalCommit commit. Manual rollback required.",
                    "last_commit": last_commit
                }
            
            # Perform soft reset to undo the commit but keep changes
            reset_result = self._run_git_command(["reset", "--soft", "HEAD~1"])
            
            if reset_result["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Failed to rollback commit: {reset_result.get('stderr', 'Unknown error')}",
                    "git_output": reset_result
                }
            
            logger.info(f"Successfully rolled back commit {last_commit['short_hash']} for task {task_id}")
            
            return {
                "status": "success",
                "rolled_back_commit": last_commit["short_hash"],
                "commit_message": last_commit["commit_message"],
                "changed_files": last_commit["changed_files"],
                "task_id": task_id,
                "message": f"Rolled back commit {last_commit['short_hash']}. Changes are now unstaged."
            }
            
        except Exception as e:
            logger.error(f"Error rolling back commit: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def hard_rollback_last_commit(self, task_id: str) -> Dict[str, Any]:
        """
        Hard rollback the last commit (completely undo changes).
        
        Args:
            task_id: Task identifier for logging
            
        Returns:
            Dict containing rollback result
        """
        try:
            # Get last commit info before rollback
            last_commit = self.get_last_commit_info()
            if last_commit["status"] != "success":
                return {
                    "status": "error",
                    "error": "Failed to get last commit information"
                }
            
            # Check if the last commit is a VocalCommit commit
            if "[VocalCommit]" not in last_commit["commit_message"]:
                return {
                    "status": "error",
                    "error": "Last commit is not a VocalCommit commit. Manual rollback required.",
                    "last_commit": last_commit
                }
            
            # Perform hard reset to completely undo the commit and changes
            reset_result = self._run_git_command(["reset", "--hard", "HEAD~1"])
            
            if reset_result["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Failed to hard rollback commit: {reset_result.get('stderr', 'Unknown error')}",
                    "git_output": reset_result
                }
            
            logger.info(f"Successfully hard rolled back commit {last_commit['short_hash']} for task {task_id}")
            
            return {
                "status": "success",
                "rolled_back_commit": last_commit["short_hash"],
                "commit_message": last_commit["commit_message"],
                "changed_files": last_commit["changed_files"],
                "task_id": task_id,
                "message": f"Hard rolled back commit {last_commit['short_hash']}. All changes have been discarded."
            }
            
        except Exception as e:
            logger.error(f"Error hard rolling back commit: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_commit_history(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent commit history.
        
        Args:
            limit: Number of commits to retrieve
            
        Returns:
            Dict containing commit history
        """
        try:
            # Get commit history with format: hash|message|timestamp|author
            result = self._run_git_command([
                "log", 
                f"-{limit}", 
                "--pretty=format:%H|%s|%ci|%an"
            ])
            
            if result["status"] != "success":
                return {
                    "status": "error",
                    "error": "Failed to get commit history"
                }
            
            commits = []
            if result["stdout"]:
                for line in result["stdout"].split('\n'):
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        commits.append({
                            "hash": parts[0],
                            "short_hash": parts[0][:8],
                            "message": parts[1],
                            "timestamp": parts[2],
                            "author": parts[3],
                            "is_vocalcommit": "[VocalCommit]" in parts[1]
                        })
            
            return {
                "status": "success",
                "commits": commits,
                "total_commits": len(commits)
            }
            
        except Exception as e:
            logger.error(f"Error getting commit history: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

# Global git operations instance
git_ops = GitOperations()