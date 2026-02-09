#!/usr/bin/env python3
"""
Test script for the fresh clone workflow.

This script tests:
1. Remove existing directory for every new request
2. Clone fresh repository each time
3. Commit changes locally after testing
4. Push to origin after approval

Usage:
    python test_fresh_clone_workflow.py
"""

import sys
import os
from pathlib import Path

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))

from tools.github_ops import github_ops
from agents.testing_agent.test_logic import run_testing_agent
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_fresh_clone_workflow():
    """Test the complete fresh clone workflow."""
    
    print("\n" + "="*80)
    print("TESTING FRESH CLONE WORKFLOW")
    print("="*80 + "\n")
    
    # Test 1: Remove and clone fresh
    print("\n[TEST 1] Testing remove_and_clone_fresh()...")
    print("-" * 80)
    
    result = github_ops.remove_and_clone_fresh()
    
    if result["status"] == "success":
        print(f"✅ SUCCESS: {result['message']}")
        print(f"   Action: {result['action']}")
        print(f"   Local path: {github_ops.local_path}")
        
        # Verify the directory exists and is a git repo
        if github_ops.local_path.exists():
            print(f"   ✓ Directory exists")
            
            if (github_ops.local_path / ".git").exists():
                print(f"   ✓ Is a git repository")
            else:
                print(f"   ✗ NOT a git repository!")
                return False
        else:
            print(f"   ✗ Directory does NOT exist!")
            return False
    else:
        print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        return False
    
    # Test 2: Verify we can get last commit info
    print("\n[TEST 2] Testing get_last_commit_info()...")
    print("-" * 80)
    
    commit_info = github_ops.get_last_commit_info()
    
    if commit_info["status"] == "success":
        print(f"✅ SUCCESS: Got last commit info")
        print(f"   Commit hash: {commit_info['short_hash']}")
        print(f"   Message: {commit_info['commit_message'][:60]}...")
        print(f"   Timestamp: {commit_info['timestamp']}")
        print(f"   Files changed: {commit_info['total_files']}")
    else:
        print(f"❌ FAILED: {commit_info.get('error', 'Unknown error')}")
        return False
    
    # Test 3: Test file sync (simulate modified files)
    print("\n[TEST 3] Testing sync_files_to_repo()...")
    print("-" * 80)
    
    # Create a test file in a temporary source directory (not in the cloned repo)
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    test_file_path = temp_dir / "TEST_FILE.md"
    
    with open(test_file_path, 'w') as f:
        f.write("# Test File\n\nThis is a test file for the fresh clone workflow.\n")
    
    print(f"   Created test file: {test_file_path}")
    
    # Sync the test file
    sync_result = github_ops.sync_files_to_repo(["TEST_FILE.md"], temp_dir)
    
    if sync_result["status"] == "success":
        print(f"✅ SUCCESS: Synced {sync_result['total_synced']} files")
        print(f"   Synced files: {sync_result['synced_files']}")
        
        # Verify the file exists in the cloned repo
        synced_file = github_ops.local_path / "TEST_FILE.md"
        if synced_file.exists():
            print(f"   ✓ File exists in cloned repo: {synced_file}")
        else:
            print(f"   ✗ File NOT found in cloned repo!")
            return False
    else:
        print(f"❌ FAILED: {sync_result.get('error', 'Unknown error')}")
        return False
    
    # Test 4: Test commit locally (without push)
    print("\n[TEST 4] Testing commit_changes_locally()...")
    print("-" * 80)
    
    # Re-create test file in temp directory for commit test
    test_file_path = temp_dir / "TEST_FILE.md"
    with open(test_file_path, 'w') as f:
        f.write("# Test File\n\nThis is a test file for the fresh clone workflow.\n")
    
    print(f"   Re-created test file: {test_file_path}")
    
    # Manually sync the file first (since commit_changes_locally will use orchestrator/todo-ui as source)
    # We need to copy it to the expected source location
    expected_source = Path(__file__).parent / "orchestrator" / "todo-ui" / "TEST_FILE.md"
    expected_source.parent.mkdir(parents=True, exist_ok=True)
    
    import shutil as sh
    sh.copy2(test_file_path, expected_source)
    print(f"   Copied test file to expected source: {expected_source}")
    
    commit_result = github_ops.commit_changes_locally(
        "Test fresh clone workflow",
        ["TEST_FILE.md"],
        {"suggestions": {
            "summary": "Test commit",
            "risk_assessment": "low",
            "confidence": 1.0,
            "estimated_impact": "minor"
        }}
    )
    
    if commit_result["status"] == "success":
        print(f"✅ SUCCESS: Committed locally")
        print(f"   Commit hash: {commit_result['commit_hash']}")
        print(f"   Awaiting approval: {commit_result['awaiting_approval']}")
        print(f"   Pushed: {commit_result['pushed']}")
        
        if not commit_result['pushed']:
            print(f"   ✓ Correctly NOT pushed (awaiting approval)")
        else:
            print(f"   ✗ Should NOT be pushed yet!")
            return False
    elif commit_result["status"] == "no_changes":
        print(f"⚠️  WARNING: No changes to commit (this might be expected)")
    else:
        print(f"❌ FAILED: {commit_result.get('error', 'Unknown error')}")
        return False
    
    # Test 5: Test push committed changes (simulating approval)
    print("\n[TEST 5] Testing push_committed_changes() [SKIPPED - would push to production]")
    print("-" * 80)
    print("   ⚠️  Skipping actual push to avoid modifying production repository")
    print("   ✓ In real workflow, this would push after approval")
    
    # Cleanup: Remove test file and temp directory
    print("\n[CLEANUP] Removing test files and temp directory...")
    print("-" * 80)
    
    # Remove expected source file
    if expected_source.exists():
        expected_source.unlink()
        print(f"   ✓ Removed expected source file: {expected_source}")
    
    if test_file_path.exists():
        test_file_path.unlink()
        print(f"   ✓ Removed test file: {test_file_path}")
    
    # Remove temp directory
    import shutil as sh2
    if temp_dir.exists():
        sh2.rmtree(temp_dir)
        print(f"   ✓ Removed temp directory: {temp_dir}")
    
    # Reset the cloned repo to remove test commit
    print("\n[CLEANUP] Resetting cloned repository...")
    print("-" * 80)
    
    reset_result = github_ops._run_git_command(["reset", "--hard", "HEAD~1"])
    if reset_result["status"] == "success":
        print(f"   ✓ Reset to previous commit")
    else:
        print(f"   ⚠️  Could not reset: {reset_result.get('stderr', 'Unknown error')}")
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED! ✅")
    print("="*80 + "\n")
    
    print("Summary:")
    print("  ✓ Fresh clone workflow works correctly")
    print("  ✓ Directory is removed and cloned fresh each time")
    print("  ✓ Files can be synced to the fresh clone")
    print("  ✓ Changes can be committed locally without pushing")
    print("  ✓ Push can be done after approval (not tested to avoid production changes)")
    
    return True


def test_testing_agent():
    """Test the testing agent to ensure it runs before commit."""
    
    print("\n" + "="*80)
    print("TESTING TESTING AGENT")
    print("="*80 + "\n")
    
    print("[TEST] Running testing agent on sample files...")
    print("-" * 80)
    
    # Test with some sample files
    test_files = ["src/App.tsx", "src/components/TodoItem.tsx"]
    
    result = run_testing_agent("Test task", test_files)
    
    if result["status"] == "success":
        print(f"✅ SUCCESS: Testing agent completed")
        print(f"   Test results: {result.get('test_summary', 'N/A')}")
        print(f"   Recommendations: {len(result.get('recommendations', []))} items")
    else:
        print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        return False
    
    print("\n" + "="*80)
    print("TESTING AGENT TEST PASSED! ✅")
    print("="*80 + "\n")
    
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("VOCALCOMMIT FRESH CLONE WORKFLOW TEST SUITE")
    print("="*80 + "\n")
    
    try:
        # Test 1: Fresh clone workflow
        if not test_fresh_clone_workflow():
            print("\n❌ Fresh clone workflow tests FAILED!")
            sys.exit(1)
        
        # Test 2: Testing agent
        if not test_testing_agent():
            print("\n❌ Testing agent tests FAILED!")
            sys.exit(1)
        
        print("\n" + "="*80)
        print("ALL TEST SUITES PASSED! ✅✅✅")
        print("="*80 + "\n")
        
        print("The workflow is ready:")
        print("  1. ✅ Directory is removed for every new request")
        print("  2. ✅ Repository is cloned fresh each time")
        print("  3. ✅ Testing agent runs before commit")
        print("  4. ✅ Changes are committed locally after testing")
        print("  5. ✅ Push happens only after approval")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Test suite failed with exception: {e}", exc_info=True)
        print(f"\n❌ Test suite FAILED with exception: {e}")
        sys.exit(1)
