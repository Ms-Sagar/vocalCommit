#!/usr/bin/env python3
"""
Simple test to verify the fresh clone workflow works correctly.
"""

import sys
import os
from pathlib import Path

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))

from tools.github_ops import github_ops
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    print("\n" + "="*80)
    print("FRESH CLONE WORKFLOW - SIMPLE TEST")
    print("="*80 + "\n")
    
    # Test 1: Remove and clone fresh
    print("[TEST 1] Remove existing directory and clone fresh...")
    result = github_ops.remove_and_clone_fresh()
    
    if result["status"] == "success":
        print(f"✅ SUCCESS: {result['message']}")
        print(f"   Local path: {github_ops.local_path}")
        
        # Verify it's a git repo
        if (github_ops.local_path / ".git").exists():
            print(f"   ✓ Is a valid git repository")
        else:
            print(f"   ✗ NOT a git repository!")
            return False
    else:
        print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        return False
    
    # Test 2: Get last commit info
    print("\n[TEST 2] Get last commit info...")
    commit_info = github_ops.get_last_commit_info()
    
    if commit_info["status"] == "success":
        print(f"✅ SUCCESS: Got commit info")
        print(f"   Commit: {commit_info['short_hash']}")
        print(f"   Message: {commit_info['commit_message'][:60]}...")
    else:
        print(f"❌ FAILED: {commit_info.get('error', 'Unknown error')}")
        return False
    
    # Test 3: Verify fresh clone removes old directory
    print("\n[TEST 3] Verify fresh clone removes old directory...")
    
    # Create a marker file
    marker_file = github_ops.local_path / "MARKER_FILE.txt"
    with open(marker_file, 'w') as f:
        f.write("This file should be removed on fresh clone")
    
    print(f"   Created marker file: {marker_file}")
    
    # Clone fresh again
    result = github_ops.remove_and_clone_fresh()
    
    if result["status"] == "success":
        # Check if marker file is gone
        if not marker_file.exists():
            print(f"✅ SUCCESS: Marker file was removed (directory was cleaned)")
        else:
            print(f"❌ FAILED: Marker file still exists (directory was NOT cleaned)")
            return False
    else:
        print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        return False
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED! ✅")
    print("="*80 + "\n")
    
    print("Summary:")
    print("  ✓ Fresh clone workflow works correctly")
    print("  ✓ Directory is removed and cloned fresh each time")
    print("  ✓ No stale files remain between clones")
    print("  ✓ Repository is always in clean state")
    
    return True


if __name__ == "__main__":
    try:
        if main():
            print("\n✅ Test suite PASSED!\n")
            sys.exit(0)
        else:
            print("\n❌ Test suite FAILED!\n")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        print(f"\n❌ Test FAILED with exception: {e}\n")
        sys.exit(1)
