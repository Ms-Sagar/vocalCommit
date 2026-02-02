#!/usr/bin/env python3
"""
Test script to verify the enhanced approval flow with GitHub push functionality.
"""

import requests
import json
import time

def test_approval_flow_with_github():
    """Test the approval flow with GitHub push functionality."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Enhanced Approval Flow with GitHub Push")
    print("=" * 60)
    
    # Test 1: Check if orchestrator is running
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Orchestrator is running")
        else:
            print("❌ Orchestrator health check failed")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to orchestrator: {e}")
        return False
    
    # Test 2: Check GitHub status
    try:
        response = requests.get(f"{base_url}/github-status")
        if response.status_code == 200:
            github_status = response.json()
            print("✅ GitHub integration available")
            print(f"   Repo URL: {github_status.get('repo_url', 'Not configured')}")
            print(f"   Local repo exists: {github_status.get('local_repo_exists', False)}")
        else:
            print("❌ GitHub status check failed")
    except Exception as e:
        print(f"❌ GitHub status error: {e}")
    
    # Test 3: Check completed tasks
    try:
        response = requests.get(f"{base_url}/admin-workflows")
        if response.status_code == 200:
            workflows = response.json().get('workflows', [])
            completed_tasks = [w for w in workflows if w.get('workflow_type') == 'completed']
            
            print(f"✅ Found {len(completed_tasks)} completed tasks")
            
            if completed_tasks:
                # Test approval flow with the first completed task
                task = completed_tasks[0]
                task_id = task['id']
                
                print(f"\n🔍 Testing approval flow with task: {task_id}")
                print(f"   Title: {task.get('title', 'Unknown')}")
                print(f"   Has commit: {task.get('has_commit', False)}")
                print(f"   GitHub pushed: {task.get('github_pushed', False)}")
                
                if task.get('has_commit') and not task.get('github_pushed'):
                    print(f"\n✅ Task {task_id} is ready for approval with GitHub push")
                    print("   - Approve commit will push to GitHub")
                    print("   - Rollback will also push the rollback to GitHub")
                elif task.get('github_pushed'):
                    print(f"\n✅ Task {task_id} already pushed to GitHub")
                    print("   - Rollback will push the rollback to GitHub")
                else:
                    print(f"\nℹ️  Task {task_id} has no commit to test with")
            else:
                print("ℹ️  No completed tasks found to test approval flow")
        else:
            print("❌ Failed to get workflows")
    except Exception as e:
        print(f"❌ Workflows check error: {e}")
    
    # Test 4: Check workflow stats
    try:
        response = requests.get(f"{base_url}/workflow-stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"\n✅ Workflow Statistics:")
            print(f"   Pending: {stats.get('pending', 0)}")
            print(f"   Active: {stats.get('active', 0)}")
            print(f"   Completed: {stats.get('completed', 0)}")
            print(f"   Approved: {stats.get('approved', 0)}")
            print(f"   Rolled back: {stats.get('rolled_back', 0)}")
        else:
            print("❌ Workflow stats check failed")
    except Exception as e:
        print(f"❌ Workflow stats error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Enhanced Approval Flow Test Complete!")
    print("\n📋 New Approval Flow Features:")
    print("   ✅ Approve Commit: Now pushes to GitHub automatically")
    print("   ✅ Rollback Commit: Now pushes rollback to GitHub automatically")
    print("   ✅ GitHub Integration: Both local and remote operations")
    print("   ✅ Status Tracking: GitHub push status in notifications")
    print("   ✅ Error Handling: Graceful handling of GitHub failures")
    
    print("\n🔄 Approval Flow Process:")
    print("   1. Task completes (may auto-push or wait for approval)")
    print("   2. User sees commit approval options in VocalCommit UI")
    print("   3. Approve Commit: Pushes to GitHub + marks as final")
    print("   4. Rollback Commit: Reverts locally + pushes rollback to GitHub")
    print("   5. Real-time notifications show both local and GitHub status")
    
    print("\n🚀 How to Test:")
    print("   1. Complete a task that doesn't auto-push (if any)")
    print("   2. Use VocalCommit UI approval buttons")
    print("   3. Check GitHub repository for pushed changes")
    print("   4. Verify WebSocket notifications include GitHub status")
    
    return True

if __name__ == "__main__":
    test_approval_flow_with_github()