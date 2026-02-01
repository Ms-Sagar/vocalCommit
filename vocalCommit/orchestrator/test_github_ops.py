#!/usr/bin/env python3
"""
Test script to verify GitHub operations work with the todo-ui repository.
"""

import json
from tools.github_ops import github_ops

def test_github_operations():
    """Test the GitHub operations."""
    print("🧪 Testing GitHub Operations")
    print("=" * 40)
    
    print(f"🔗 Repository URL: {github_ops.repo_url}")
    print(f"📁 Local Path: {github_ops.local_path}")
    print(f"👤 Owner: {github_ops.owner}")
    print(f"📦 Repo Name: {github_ops.repo_name}")
    
    # Test repository status
    print("\n📊 Getting last commit info...")
    commit_info = github_ops.get_last_commit_info()
    print(f"Status: {commit_info['status']}")
    
    if commit_info["status"] == "success":
        print(f"✅ Last commit: {commit_info['short_hash']}")
        print(f"📝 Message: {commit_info['commit_message']}")
        print(f"📁 Files changed: {commit_info['total_files']}")
        print(f"🎤 VocalCommit commit: {commit_info['is_vocalcommit']}")
    else:
        print(f"❌ Error: {commit_info.get('error', 'Unknown error')}")
    
    print("\n✅ GitHub operations test complete!")

if __name__ == "__main__":
    test_github_operations()