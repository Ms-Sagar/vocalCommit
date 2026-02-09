# Quick Start Guide: Fresh Clone Workflow

## What Changed?

The system now **removes the directory and clones fresh** for every new request, ensuring:
- ✅ Clean state (no stale files)
- ✅ Latest production code
- ✅ Comprehensive testing before commit
- ✅ Two-stage commit with approval

## How It Works

```
Request → Remove Dir → Clone Fresh → Modify → Test → Commit Local → Approve → Push
```

## Key Features

### 1. Fresh Clone Every Time
```python
# Before each request:
1. Remove orchestrator/todo-ui directory
2. Clone fresh from GitHub
3. Start with clean, latest code
```

### 2. Testing Before Commit
```python
# All changes are tested:
1. Syntax validation
2. Code quality checks
3. Security scanning
4. Accessibility compliance
```

### 3. Two-Stage Commit
```python
# Stage 1: Local Commit (automatic after tests pass)
- Commit to local repository
- Include AI analysis
- Status: "Awaiting approval"

# Stage 2: Push to Origin (requires user approval)
- User reviews commit
- User approves push
- Changes go to production
```

## Quick Test

Run this to verify everything works:

```bash
cd vocalCommit
python3 test_workflow_simple.py
```

Expected output:
```
================================================================================
ALL TESTS PASSED! ✅
================================================================================

Summary:
  ✓ Fresh clone workflow works correctly
  ✓ Directory is removed and cloned fresh each time
  ✓ No stale files remain between clones
  ✓ Repository is always in clean state
```

## Configuration

Make sure these are set in `vocalCommit/orchestrator/.env`:

```bash
GITHUB_TOKEN=your_github_token
TODO_UI_REPO_URL=https://github.com/your-username/TODO-UI.git
TODO_UI_LOCAL_PATH=todo-ui
GEMINI_API_KEY=your_gemini_api_key
```

## Usage Example

### 1. Start the Orchestrator
```bash
cd vocalCommit/orchestrator
python -m uvicorn core.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Make a Request
```javascript
// Via WebSocket
{
  "type": "command",
  "transcript": "Add a dark mode toggle button"
}
```

### 3. System Processing
```
1. ✅ PM Agent creates plan
2. ✅ Dev Agent modifies files
3. ✅ Testing Agent validates changes
4. ✅ Remove directory and clone fresh
5. ✅ Sync modified files to fresh clone
6. ✅ Commit locally (no push yet)
7. ⏳ Awaiting your approval...
```

### 4. Review and Approve
```javascript
// Check pending approvals
GET /pending-approvals

// Approve and push
POST /approve-github-push/{task_id}
```

### 5. Done!
```
✅ Changes committed and pushed to origin
✅ Production repository updated
✅ Clean state maintained
```

## API Endpoints

### Get Pending Approvals
```bash
curl http://localhost:8000/pending-approvals
```

### Approve and Push
```bash
curl -X POST http://localhost:8000/approve-github-push/{task_id}
```

### Rollback (before push)
```bash
curl -X POST http://localhost:8000/rollback-commit/{task_id}?hard_rollback=false
```

### Check GitHub Status
```bash
curl http://localhost:8000/github-status
```

## Troubleshooting

### "Failed to remove directory"
```bash
# Manual fix:
rm -rf vocalCommit/orchestrator/todo-ui

# Then retry the request
```

### "Failed to clone repository"
```bash
# Check token:
echo $GITHUB_TOKEN

# Test manually:
git clone https://github.com/your-username/TODO-UI.git
```

### "No changes to commit"
```bash
# This is normal if:
- Files were already up to date
- No modifications were made
- Changes were identical to existing code
```

## Benefits

### Before (Old Workflow)
- ❌ Stale files could interfere
- ❌ Merge conflicts possible
- ❌ Unclear state between requests
- ❌ Direct push without approval

### After (New Workflow)
- ✅ Always clean state
- ✅ No merge conflicts
- ✅ Clear state for each request
- ✅ Approval required before push

## Next Steps

1. **Run the test**: `python3 test_workflow_simple.py`
2. **Start the orchestrator**: `uvicorn core.main:app --reload`
3. **Make a test request**: Submit a simple change
4. **Review the commit**: Check pending approvals
5. **Approve and push**: Push to production

## Documentation

- **FRESH_CLONE_WORKFLOW.md** - Detailed workflow documentation
- **IMPLEMENTATION_SUMMARY.md** - Implementation details
- **test_workflow_simple.py** - Test suite

## Support

If you encounter issues:
1. Check the logs: `vocalCommit/orchestrator/orchestrator.log`
2. Run the test suite: `python3 test_workflow_simple.py`
3. Verify configuration: Check `.env` file
4. Review documentation: Read FRESH_CLONE_WORKFLOW.md

---

**Status: READY TO USE** ✅

The fresh clone workflow is fully implemented, tested, and ready for production use!
