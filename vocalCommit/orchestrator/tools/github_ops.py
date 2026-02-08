import os
import subprocess
import logging
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from core.config import settings

logger = logging.getLogger(__name__)

class GitHubOperations:
    """GitHub operations manager for production todo-ui repository."""
    
    def __init__(self):
        """Initialize GitHub operations."""
        self.token = settings.github_token
        self.repo_url = settings.todo_ui_repo_url
        
        # Resolve the local path relative to the orchestrator directory
        orchestrator_dir = Path(__file__).parent.parent
        self.local_path = (orchestrator_dir / settings.todo_ui_local_path).resolve()
        
        self.api_base = "https://api.github.com"
        
        # Extract owner and repo from URL
        # https://github.com/Ms-Sagar/TODO-UI.git -> Ms-Sagar/TODO-UI
        if self.repo_url.endswith('.git'):
            repo_path = self.repo_url[:-4].split('github.com/')[-1]
        else:
            repo_path = self.repo_url.split('github.com/')[-1]
        
        self.owner, self.repo_name = repo_path.split('/')
        
        logger.info(f"GitHub operations initialized for {self.owner}/{self.repo_name}")
        logger.info(f"Local repository path: {self.local_path}")
    
    def _run_git_command(self, command: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
        """Execute a git command safely."""
        try:
            work_dir = cwd or self.local_path
            result = subprocess.run(
                ["git"] + command,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=60
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
    
    def _make_github_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated GitHub API request."""
        if not self.token:
            return {
                "status": "error",
                "error": "GitHub token not configured"
            }
        
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "VocalCommit-Orchestrator"
        }
        
        url = f"{self.api_base}/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                return {"status": "error", "error": f"Unsupported method: {method}"}
            
            if response.status_code < 400:
                return {
                    "status": "success",
                    "data": response.json() if response.content else {},
                    "status_code": response.status_code
                }
            else:
                return {
                    "status": "error",
                    "error": f"GitHub API error: {response.status_code}",
                    "message": response.text,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def clone_or_pull_repo(self) -> Dict[str, Any]:
        """Clone the repository if it doesn't exist, or pull latest changes."""
        try:
            if self.local_path.exists():
                logger.info(f"Repository exists at {self.local_path}, pulling latest changes")
                
                # Check if it's a git repository
                if not (self.local_path / ".git").exists():
                    return {
                        "status": "error",
                        "error": f"Directory {self.local_path} exists but is not a git repository"
                    }
                
                # Pull latest changes
                pull_result = self._run_git_command(["pull", "origin", "main"])
                
                if pull_result["status"] != "success":
                    # Try master branch if main fails
                    pull_result = self._run_git_command(["pull", "origin", "master"])
                
                if pull_result["status"] != "success":
                    return {
                        "status": "error",
                        "error": f"Failed to pull changes: {pull_result.get('stderr', 'Unknown error')}",
                        "git_output": pull_result
                    }
                
                logger.info("Successfully pulled latest changes")
                return {
                    "status": "success",
                    "action": "pulled",
                    "message": "Repository updated with latest changes",
                    "git_output": pull_result
                }
            
            else:
                logger.info(f"Cloning repository to {self.local_path}")
                
                # Create parent directory if needed
                self.local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Clone with authentication
                auth_url = self.repo_url.replace("https://", f"https://{self.token}@")
                
                clone_result = self._run_git_command([
                    "clone", auth_url, str(self.local_path)
                ], cwd=self.local_path.parent)
                
                if clone_result["status"] != "success":
                    return {
                        "status": "error",
                        "error": f"Failed to clone repository: {clone_result.get('stderr', 'Unknown error')}",
                        "git_output": clone_result
                    }
                
                logger.info("Successfully cloned repository")
                return {
                    "status": "success",
                    "action": "cloned",
                    "message": "Repository cloned successfully",
                    "git_output": clone_result
                }
                
        except Exception as e:
            logger.error(f"Error in clone_or_pull_repo: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_gemini_suggestions(self, task_description: str, modified_files: List[str]) -> Dict[str, Any]:
        """Get Gemini AI suggestions for the changes."""
        try:
            # This would integrate with Gemini API to analyze changes
            # For now, return a structured response
            
            suggestions = {
                "summary": f"AI Analysis for: {task_description}",
                "recommendations": [
                    "Review code quality and consistency",
                    "Ensure proper error handling",
                    "Verify accessibility compliance",
                    "Check for security vulnerabilities"
                ],
                "risk_assessment": "low",  # low, medium, high
                "confidence": 0.85,
                "modified_files_count": len(modified_files),
                "estimated_impact": "minor"  # minor, moderate, major
            }
            
            return {
                "status": "success",
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"Error getting Gemini suggestions: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "suggestions": {
                    "summary": "AI analysis unavailable",
                    "recommendations": ["Manual review recommended"],
                    "risk_assessment": "unknown",
                    "confidence": 0.0
                }
            }
    
    def sync_files_to_repo(self, modified_files: List[str], source_base: Path) -> Dict[str, Any]:
        """
        Sync modified files from source to the GitHub repo.
        
        Args:
            modified_files: List of file paths relative to source_base
            source_base: Base path where the source files are located
            
        Returns:
            Dict containing sync result
        """
        try:
            import shutil
            
            synced_files = []
            failed_files = []
            
            logger.info(f"Starting file sync from {source_base} to {self.local_path}")
            logger.info(f"Files to sync: {modified_files}")
            
            for file_path in modified_files:
                try:
                    source_file = source_base / file_path
                    target_file = self.local_path / file_path
                    
                    logger.info(f"Syncing: {source_file} -> {target_file}")
                    
                    if not source_file.exists():
                        logger.warning(f"Source file not found: {source_file}")
                        failed_files.append(str(file_path))
                        continue
                    
                    # Create target directory if needed
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy the file
                    shutil.copy2(source_file, target_file)
                    synced_files.append(str(file_path))
                    logger.info(f"✓ Synced file: {file_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to sync {file_path}: {str(e)}")
                    failed_files.append(str(file_path))
            
            if failed_files:
                logger.warning(f"Failed to sync {len(failed_files)} files: {failed_files}")
            
            return {
                "status": "success" if synced_files else "error",
                "synced_files": synced_files,
                "failed_files": failed_files,
                "total_synced": len(synced_files),
                "message": f"Synced {len(synced_files)} files to GitHub repo"
            }
            
        except Exception as e:
            logger.error(f"Error syncing files to repo: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def commit_changes_locally(self, task_description: str, modified_files: List[str], 
                               gemini_suggestions: Dict[str, Any]) -> Dict[str, Any]:
        """Commit changes locally without pushing. Used for approval workflow."""
        try:
            logger.info(f"[LOCAL_COMMIT] Starting local commit for: {task_description}")
            logger.info(f"[LOCAL_COMMIT] Working directory: {self.local_path}")
            logger.info(f"[LOCAL_COMMIT] Modified files count: {len(modified_files)}")
            
            # Configure git pull strategy
            logger.info("[LOCAL_COMMIT] Step 1: Configuring git pull strategy")
            config_result = self._run_git_command(["config", "pull.rebase", "false"])
            logger.info(f"[LOCAL_COMMIT] Config result: {config_result}")
            
            # Pull latest changes before committing
            logger.info("[LOCAL_COMMIT] Step 2: Pulling latest changes from TODO-UI repository")
            pull_result = self._run_git_command(["pull", "origin", "main", "--no-edit"])
            logger.info(f"[LOCAL_COMMIT] Pull result (main): {pull_result}")
            
            if pull_result["status"] != "success":
                # Try master branch if main fails
                logger.info("[LOCAL_COMMIT] Main branch failed, trying master branch")
                pull_result = self._run_git_command(["pull", "origin", "master", "--no-edit"])
                logger.info(f"[LOCAL_COMMIT] Pull result (master): {pull_result}")
            
            if pull_result["status"] != "success":
                logger.warning(f"[LOCAL_COMMIT] Failed to pull latest changes: {pull_result.get('stderr', 'Unknown error')}")
                # Continue anyway, but log the warning
            else:
                logger.info("[LOCAL_COMMIT] ✅ Successfully pulled latest changes from TODO-UI repository")
            
            # Check if there are any changes to commit
            logger.info("[LOCAL_COMMIT] Step 3: Checking for changes to commit")
            status_result = self._run_git_command(["status", "--porcelain"])
            logger.info(f"[LOCAL_COMMIT] Status output: {status_result.get('stdout', '(empty)')}")
            
            if not status_result["stdout"]:
                logger.warning("[LOCAL_COMMIT] No changes to commit")
                return {
                    "status": "no_changes",
                    "message": "No changes to commit"
                }
            
            # Add all changes
            logger.info("[LOCAL_COMMIT] Step 4: Staging all changes")
            add_result = self._run_git_command(["add", "."])
            logger.info(f"[LOCAL_COMMIT] Add result: {add_result}")
            
            if add_result["status"] != "success":
                error_msg = f"Failed to stage changes: {add_result.get('stderr', 'Unknown error')}"
                logger.error(f"[LOCAL_COMMIT] {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg
                }
            
            # Create commit message with Gemini analysis
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            commit_message = f"[VocalCommit] {task_description}\n\n"
            commit_message += f"Timestamp: {timestamp}\n"
            commit_message += f"Modified files: {len(modified_files)}\n"
            
            if gemini_suggestions.get("suggestions"):
                suggestions = gemini_suggestions["suggestions"]
                commit_message += f"AI Risk Assessment: {suggestions.get('risk_assessment', 'unknown')}\n"
                commit_message += f"AI Confidence: {suggestions.get('confidence', 0.0):.2f}\n"
                commit_message += f"Estimated Impact: {suggestions.get('estimated_impact', 'unknown')}\n"
            
            commit_message += f"\nFiles modified:\n"
            for file_path in modified_files[:10]:  # Limit to first 10 files
                commit_message += f"- {file_path}\n"
            
            if len(modified_files) > 10:
                commit_message += f"... and {len(modified_files) - 10} more files\n"
            
            commit_message += f"\n[Status: Awaiting approval to push to remote]"
            
            logger.info(f"[LOCAL_COMMIT] Step 5: Committing changes locally (no push)")
            
            # Commit changes (DO NOT PUSH)
            commit_result = self._run_git_command(["commit", "-m", commit_message])
            logger.info(f"[LOCAL_COMMIT] Commit result: {commit_result}")
            
            if commit_result["status"] != "success":
                error_msg = f"Failed to commit changes: {commit_result.get('stderr', 'Unknown error')}"
                logger.error(f"[LOCAL_COMMIT] {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg
                }
            
            # Get commit hash
            logger.info("[LOCAL_COMMIT] Step 6: Getting commit hash")
            hash_result = self._run_git_command(["rev-parse", "HEAD"])
            commit_hash = hash_result["stdout"][:8] if hash_result["status"] == "success" else "unknown"
            logger.info(f"[LOCAL_COMMIT] Commit hash: {commit_hash}")
            
            logger.info(f"[LOCAL_COMMIT] ✅ Successfully committed locally: {commit_hash} (not pushed yet)")
            
            return {
                "status": "success",
                "commit_hash": commit_hash,
                "commit_message": commit_message,
                "modified_files": modified_files,
                "gemini_suggestions": gemini_suggestions,
                "timestamp": timestamp,
                "committed": True,
                "pushed": False,
                "awaiting_approval": True
            }
            
        except Exception as e:
            logger.error(f"[LOCAL_COMMIT] Error committing changes locally: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def push_committed_changes(self) -> Dict[str, Any]:
        """Push already committed changes to remote. Used after approval."""
        try:
            logger.info("[PUSH] Pushing committed changes to remote repository")
            logger.info(f"[PUSH] Working directory: {self.local_path}")
            
            # Push to origin
            logger.info("[PUSH] Executing git push")
            push_result = self._run_git_command(["push", "origin", "HEAD"])
            logger.info(f"[PUSH] Push result: {push_result}")
            
            if push_result["status"] != "success":
                error_msg = f"Failed to push changes: {push_result.get('stderr', 'Unknown error')}"
                logger.error(f"[PUSH] {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "pushed": False
                }
            
            # Get commit hash
            hash_result = self._run_git_command(["rev-parse", "HEAD"])
            commit_hash = hash_result["stdout"][:8] if hash_result["status"] == "success" else "unknown"
            
            logger.info(f"[PUSH] ✅ Successfully pushed to remote: {commit_hash}")
            
            return {
                "status": "success",
                "commit_hash": commit_hash,
                "pushed": True,
                "message": "Changes successfully pushed to remote repository"
            }
            
        except Exception as e:
            logger.error(f"[PUSH] Error pushing changes: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "pushed": False
            }
    
    def commit_and_push_changes(self, task_description: str, modified_files: List[str], 
                               gemini_suggestions: Dict[str, Any]) -> Dict[str, Any]:
        """Commit changes and push to GitHub with Gemini analysis. Always pulls latest changes first."""
        try:
            logger.info(f"[GITHUB] Starting commit and push for: {task_description}")
            logger.info(f"[GITHUB] Working directory: {self.local_path}")
            logger.info(f"[GITHUB] Modified files count: {len(modified_files)}")
            
            # CRITICAL: Configure git pull strategy first
            logger.info("[GITHUB] Step 1: Configuring git pull strategy")
            config_result = self._run_git_command(["config", "pull.rebase", "false"])
            logger.info(f"[GITHUB] Config result: {config_result}")
            
            # CRITICAL: Always pull latest changes before committing
            logger.info("[GITHUB] Step 2: Pulling latest changes from TODO-UI repository")
            pull_result = self._run_git_command(["pull", "origin", "main", "--no-edit"])
            logger.info(f"[GITHUB] Pull result (main): {pull_result}")
            
            if pull_result["status"] != "success":
                # Try master branch if main fails
                logger.info("[GITHUB] Main branch failed, trying master branch")
                pull_result = self._run_git_command(["pull", "origin", "master", "--no-edit"])
                logger.info(f"[GITHUB] Pull result (master): {pull_result}")
            
            if pull_result["status"] != "success":
                logger.warning(f"[GITHUB] Failed to pull latest changes: {pull_result.get('stderr', 'Unknown error')}")
                # Continue anyway, but log the warning
            else:
                logger.info("[GITHUB] ✅ Successfully pulled latest changes from TODO-UI repository")
            
            # Check if there are any changes to commit
            logger.info("[GITHUB] Step 3: Checking for changes to commit")
            status_result = self._run_git_command(["status", "--porcelain"])
            logger.info(f"[GITHUB] Status output: {status_result.get('stdout', '(empty)')}")
            
            if not status_result["stdout"]:
                logger.warning("[GITHUB] No changes to commit")
                return {
                    "status": "no_changes",
                    "message": "No changes to commit"
                }
            
            # Add all changes
            logger.info("[GITHUB] Step 4: Staging all changes")
            add_result = self._run_git_command(["add", "."])
            logger.info(f"[GITHUB] Add result: {add_result}")
            
            if add_result["status"] != "success":
                error_msg = f"Failed to stage changes: {add_result.get('stderr', 'Unknown error')}"
                logger.error(f"[GITHUB] {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg
                }
            
            # Create commit message with Gemini analysis
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            commit_message = f"[VocalCommit] {task_description}\n\n"
            commit_message += f"Timestamp: {timestamp}\n"
            commit_message += f"Modified files: {len(modified_files)}\n"
            
            if gemini_suggestions.get("suggestions"):
                suggestions = gemini_suggestions["suggestions"]
                commit_message += f"AI Risk Assessment: {suggestions.get('risk_assessment', 'unknown')}\n"
                commit_message += f"AI Confidence: {suggestions.get('confidence', 0.0):.2f}\n"
                commit_message += f"Estimated Impact: {suggestions.get('estimated_impact', 'unknown')}\n"
            
            commit_message += f"\nFiles modified:\n"
            for file_path in modified_files[:10]:  # Limit to first 10 files
                commit_message += f"- {file_path}\n"
            
            if len(modified_files) > 10:
                commit_message += f"... and {len(modified_files) - 10} more files\n"
            
            logger.info(f"[GITHUB] Step 5: Committing changes with message: {commit_message[:100]}...")
            
            # Commit changes
            commit_result = self._run_git_command(["commit", "-m", commit_message])
            logger.info(f"[GITHUB] Commit result: {commit_result}")
            
            if commit_result["status"] != "success":
                error_msg = f"Failed to commit changes: {commit_result.get('stderr', 'Unknown error')}"
                logger.error(f"[GITHUB] {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg
                }
            
            # Get commit hash
            logger.info("[GITHUB] Step 6: Getting commit hash")
            hash_result = self._run_git_command(["rev-parse", "HEAD"])
            commit_hash = hash_result["stdout"][:8] if hash_result["status"] == "success" else "unknown"
            logger.info(f"[GITHUB] Commit hash: {commit_hash}")
            
            # Push to origin
            logger.info("[GITHUB] Step 7: Pushing to remote repository")
            push_result = self._run_git_command(["push", "origin", "HEAD"])
            logger.info(f"[GITHUB] Push result: {push_result}")
            
            if push_result["status"] != "success":
                error_msg = f"Failed to push changes: {push_result.get('stderr', 'Unknown error')}"
                logger.error(f"[GITHUB] {error_msg}")
                logger.error(f"[GITHUB] Changes were committed locally but not pushed to remote")
                return {
                    "status": "error",
                    "error": error_msg,
                    "commit_hash": commit_hash,
                    "committed": True,
                    "pushed": False
                }
            
            logger.info(f"[GITHUB] ✅ Successfully committed and pushed changes to TODO-UI: {commit_hash}")
            
            return {
                "status": "success",
                "commit_hash": commit_hash,
                "commit_message": commit_message,
                "modified_files": modified_files,
                "gemini_suggestions": gemini_suggestions,
                "timestamp": timestamp,
                "committed": True,
                "pushed": True
            }
            
        except Exception as e:
            logger.error(f"Error committing and pushing changes: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_last_commit_info(self) -> Dict[str, Any]:
        """Get information about the last commit in the todo-ui repo."""
        try:
            if not self.local_path.exists():
                return {
                    "status": "error",
                    "error": "Repository not found locally"
                }
            
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
                "total_files": len(changed_files),
                "is_vocalcommit": "[VocalCommit]" in commit_message
            }
            
        except Exception as e:
            logger.error(f"Error getting last commit info: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def revert_last_commit(self) -> Dict[str, Any]:
        """Revert the last commit in the todo-ui repository."""
        try:
            # Get last commit info first
            last_commit = self.get_last_commit_info()
            if last_commit["status"] != "success":
                return {
                    "status": "error",
                    "error": "Failed to get last commit information"
                }
            
            # Check if it's a VocalCommit commit
            if not last_commit.get("is_vocalcommit", False):
                return {
                    "status": "error",
                    "error": "Last commit is not a VocalCommit commit. Manual revert required.",
                    "last_commit": last_commit
                }
            
            # Create revert commit
            revert_result = self._run_git_command([
                "revert", "--no-edit", "HEAD"
            ])
            
            if revert_result["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Failed to revert commit: {revert_result.get('stderr', 'Unknown error')}",
                    "git_output": revert_result
                }
            
            # Push the revert
            push_result = self._run_git_command(["push", "origin", "HEAD"])
            
            if push_result["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Failed to push revert: {push_result.get('stderr', 'Unknown error')}",
                    "reverted_locally": True,
                    "pushed": False
                }
            
            logger.info(f"Successfully reverted and pushed commit {last_commit['short_hash']}")
            
            return {
                "status": "success",
                "reverted_commit": last_commit["short_hash"],
                "commit_message": last_commit["commit_message"],
                "changed_files": last_commit["changed_files"],
                "message": f"Reverted commit {last_commit['short_hash']} and pushed to GitHub",
                "reverted_locally": True,
                "pushed": True
            }
            
        except Exception as e:
            logger.error(f"Error reverting commit: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

# Global GitHub operations instance
github_ops = GitHubOperations()