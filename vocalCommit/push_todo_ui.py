#!/usr/bin/env python3
"""
Script to push initial TODO-UI content to GitHub repository.
"""

import os
import sys
import json
import shutil
from pathlib import Path

# Add the orchestrator to the path and set up the environment
orchestrator_path = Path(__file__).parent / "orchestrator"
sys.path.insert(0, str(orchestrator_path))

# Change to orchestrator directory for proper imports
original_cwd = os.getcwd()
os.chdir(orchestrator_path)

try:
    from tools.github_ops import github_ops
finally:
    # Change back to original directory
    os.chdir(original_cwd)

def copy_todo_ui_content():
    """Copy todo-ui content from orchestrator to the GitHub repo location."""
    source_path = Path("vocalCommit/orchestrator/todo-ui")
    target_path = Path("todo-ui")
    
    print(f"📁 Copying todo-ui content from {source_path} to {target_path}")
    
    if target_path.exists():
        print(f"⚠️  Target directory {target_path} already exists")
        # Don't remove, just update
    else:
        target_path.mkdir(parents=True, exist_ok=True)
    
    # Copy all files and directories
    for item in source_path.iterdir():
        if item.name in ['.vite', 'node_modules', 'dist']:
            print(f"⏭️  Skipping {item.name}")
            continue
            
        target_item = target_path / item.name
        
        if item.is_file():
            shutil.copy2(item, target_item)
            print(f"📄 Copied {item.name}")
        elif item.is_dir():
            if target_item.exists():
                shutil.rmtree(target_item)
            shutil.copytree(item, target_item)
            print(f"📁 Copied directory {item.name}")
    
    print("✅ Todo-UI content copied successfully")
    return True

def push_initial_content():
    """Push the initial todo-ui content to GitHub."""
    print("🚀 Starting TODO-UI GitHub push process...")
    
    # Step 1: Setup the repository
    print("\n📦 Setting up GitHub repository...")
    setup_result = github_ops.clone_or_pull_repo()
    print(f"Repository setup: {setup_result['status']}")
    
    if setup_result["status"] != "success":
        print(f"❌ Failed to setup repository: {setup_result.get('error', 'Unknown error')}")
        return False
    
    print(f"✅ Repository {setup_result['action']}: {setup_result['message']}")
    
    # Step 2: Copy todo-ui content to the repo
    print("\n📁 Copying todo-ui content...")
    if not copy_todo_ui_content():
        print("❌ Failed to copy todo-ui content")
        return False
    
    # Step 3: Get list of files to commit
    todo_ui_path = Path("todo-ui")
    if not todo_ui_path.exists():
        print("❌ Todo-ui directory not found after copy")
        return False
    
    # Get all files in the todo-ui directory
    modified_files = []
    for root, dirs, files in os.walk(todo_ui_path):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'dist', '.vite']]
        
        for file in files:
            file_path = Path(root) / file
            relative_path = file_path.relative_to(todo_ui_path)
            modified_files.append(str(relative_path))
    
    print(f"📄 Found {len(modified_files)} files to commit")
    
    # Step 4: Get AI suggestions (mock for initial push)
    gemini_suggestions = {
        "suggestions": {
            "summary": "Initial TODO-UI setup with React components and configuration",
            "recommendations": [
                "Initial project structure established",
                "React components and TypeScript configuration added",
                "Vite build system configured",
                "Theme system and UI components ready"
            ],
            "risk_assessment": "low",
            "confidence": 0.95,
            "estimated_impact": "major"
        }
    }
    
    # Step 5: Commit and push changes
    print("\n🔄 Committing and pushing changes to GitHub...")
    push_result = github_ops.commit_and_push_changes(
        task_description="Initial TODO-UI setup with React components and configuration",
        modified_files=modified_files,
        gemini_suggestions=gemini_suggestions
    )
    
    if push_result["status"] == "success":
        print(f"🎉 Successfully pushed to GitHub!")
        print(f"📝 Commit hash: {push_result['commit_hash']}")
        print(f"📁 Files pushed: {len(push_result['modified_files'])}")
        print(f"🔗 Repository: {github_ops.repo_url}")
        return True
    elif push_result["status"] == "no_changes":
        print("ℹ️  No changes to commit - repository is already up to date")
        return True
    else:
        print(f"❌ Failed to push changes: {push_result.get('error', 'Unknown error')}")
        if push_result.get('committed') and not push_result.get('pushed'):
            print("⚠️  Changes were committed locally but not pushed to GitHub")
        return False

def main():
    """Main function."""
    print("🎤 VocalCommit TODO-UI GitHub Push")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("vocalCommit").exists():
        print("❌ Please run this script from the VocalCommit root directory")
        sys.exit(1)
    
    # Check if GitHub token is configured
    if not github_ops.token:
        print("❌ GitHub token not configured. Please set GITHUB_TOKEN in your .env file")
        sys.exit(1)
    
    print(f"🔗 Target repository: {github_ops.repo_url}")
    print(f"📁 Local path: {github_ops.local_path}")
    
    # Push the content
    if push_initial_content():
        print("\n" + "=" * 50)
        print("🎉 TODO-UI successfully pushed to GitHub!")
        print(f"🌐 Repository URL: {github_ops.repo_url}")
        print("✅ Your TODO-UI is now ready for deployment on Render or other platforms")
    else:
        print("\n" + "=" * 50)
        print("❌ Failed to push TODO-UI to GitHub")
        print("Please check the error messages above and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()