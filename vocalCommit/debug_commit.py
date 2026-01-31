#!/usr/bin/env python3
"""
Debug script to test commit functionality with actual file paths
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'orchestrator'))

from tools.git_ops import git_ops

def debug_commit_workflow():
    """Debug the commit workflow with current repository state."""
    print("🔍 Debugging VocalCommit Commit Workflow")
    print("=" * 50)
    
    # Check current git status
    print("\n1. Current Git Status:")
    status = git_ops.check_git_status()
    print(f"   Repository Path: {git_ops.repo_path}")
    print(f"   Status: {status['status']}")
    
    if status['status'] == 'success':
        print(f"   Has Changes: {status['has_changes']}")
        print(f"   Modified Files: {status.get('modified_files', [])}")
        print(f"   Untracked Files: {status.get('untracked_files', [])}")
        print(f"   Staged Files: {status.get('staged_files', [])}")
    
    # Test with actual modified files
    if status['status'] == 'success' and status['has_changes']:
        modified_files = status.get('modified_files', []) + status.get('untracked_files', [])
        
        if modified_files:
            print(f"\n2. Testing Commit with {len(modified_files)} files:")
            for i, file_path in enumerate(modified_files[:3], 1):
                print(f"   {i}. {file_path}")
            
            # Test staging first
            print("\n3. Testing File Staging:")
            stage_result = git_ops.stage_files(modified_files[:1])  # Test with first file only
            print(f"   Stage Result: {stage_result['status']}")
            if stage_result['status'] != 'success':
                print(f"   Stage Error: {stage_result.get('error', 'Unknown error')}")
                if 'errors' in stage_result:
                    for error in stage_result['errors']:
                        print(f"   - {error}")
            else:
                print(f"   Staged Files: {stage_result['staged_files']}")
                
                # Test commit
                print("\n4. Testing Commit:")
                commit_result = git_ops.commit_changes(
                    message="Debug test commit",
                    task_id="debug_test",
                    modified_files=stage_result['staged_files']
                )
                print(f"   Commit Result: {commit_result['status']}")
                if commit_result['status'] == 'success':
                    print(f"   Commit Hash: {commit_result['commit_hash']}")
                else:
                    print(f"   Commit Error: {commit_result.get('error', 'Unknown error')}")
                    if 'git_output' in commit_result:
                        print(f"   Git Output: {commit_result['git_output']}")
        else:
            print("\n2. No modified files to test with")
    else:
        print("\n2. No changes to test commit workflow")
    
    # Test path resolution
    print(f"\n5. Path Resolution Test:")
    test_paths = [
        "vocalCommit/orchestrator/todo-ui/src/App.css",
        "orchestrator/todo-ui/src/App.css", 
        "todo-ui/src/App.css",
        "src/App.css"
    ]
    
    for test_path in test_paths:
        full_path = git_ops.repo_path / test_path
        exists = full_path.exists()
        print(f"   {test_path} -> {'✅ Exists' if exists else '❌ Not Found'}")

if __name__ == "__main__":
    debug_commit_workflow()