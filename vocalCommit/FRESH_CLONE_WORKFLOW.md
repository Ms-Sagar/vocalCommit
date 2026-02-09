# Fresh Clone Workflow

## Overview

This document describes the improved workflow that ensures clean, tested commits to the origin repository.

## Key Features

### 1. **Fresh Clone for Every Request**
- The local repository directory is **removed completely** before each new request
- A **fresh clone** is performed from the origin repository
- This ensures no stale files or uncommitted changes interfere with the workflow

### 2. **Comprehensive Testing Before Commit**
- All modified files are tested using the Testing Agent
- Tests include:
  - Syntax validation
  - Code quality checks
  - Accessibility compliance
  - Security vulnerability scanning
- **Commits only happen after successful testing**

### 3. **Two-Stage Commit Process**
- **Stage 1: Local Commit** (after testing passes)
  - Changes are committed to the local repository
  - Commit includes AI analysis and risk assessment
  - **NOT pushed to origin yet**
  
- **Stage 2: Push After Approval** (manual approval required)
  - User reviews the commit and changes
  - User approves the push to origin
  - Changes are pushed to the production repository

## Workflow Steps

```
┌─────────────────────────────────────────────────────────────┐
│ 1. NEW REQUEST RECEIVED                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. REMOVE EXISTING DIRECTORY                                │
│    - Delete orchestrator/todo-ui directory if exists        │
│    - Ensures clean slate for every request                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. CLONE FRESH REPOSITORY                                   │
│    - Clone from origin (GitHub)                             │
│    - Get latest production code                             │
│    - No merge conflicts or stale files                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. PROCESS REQUEST (Dev Agent)                              │
│    - Modify files according to user request                 │
│    - Generate code changes                                  │
│    - Apply modifications                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. SYNC FILES TO FRESH CLONE                                │
│    - Copy modified files to cloned repository               │
│    - Prepare for testing and commit                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. RUN COMPREHENSIVE TESTS                                  │
│    - Testing Agent validates all changes                    │
│    - Syntax, quality, security, accessibility checks        │
│    - MUST PASS before proceeding                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
                    ┌─────────┐
                    │ PASS?   │
                    └─────────┘
                    ↙         ↘
              YES ↙             ↘ NO
                ↙                 ↘
┌──────────────────────┐    ┌──────────────────────┐
│ 7. GET AI ANALYSIS   │    │ REPORT FAILURE       │
│    - Gemini AI       │    │ - Show test errors   │
│    - Risk assessment │    │ - No commit made     │
│    - Confidence      │    │ - User notified      │
└──────────────────────┘    └──────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. COMMIT LOCALLY (NO PUSH)                                 │
│    - Commit to local repository                             │
│    - Include AI analysis in commit message                  │
│    - Status: "Awaiting approval to push"                    │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. NOTIFY USER - AWAITING APPROVAL                          │
│    - Show commit details                                    │
│    - Display AI risk assessment                             │
│    - Provide approval/rollback options                      │
└─────────────────────────────────────────────────────────────┘
         ↓
    ┌─────────┐
    │ APPROVE?│
    └─────────┘
    ↙         ↘
YES ↙           ↘ NO
  ↙               ↘
┌──────────────┐  ┌──────────────┐
│ 10. PUSH TO  │  │ ROLLBACK     │
│     ORIGIN   │  │ - Soft reset │
│              │  │ - Hard reset │
│ ✅ DONE!     │  │ - Discard    │
└──────────────┘  └──────────────┘
```

## Implementation Details

### GitHub Operations (`github_ops.py`)

#### `remove_and_clone_fresh()`
```python
def remove_and_clone_fresh(self) -> Dict[str, Any]:
    """
    Remove existing directory and clone fresh repository.
    Used for every new request.
    
    Returns:
        Dict with status, action, message, and git_output
    """
```

**Steps:**
1. Check if local directory exists
2. Remove directory completely using `shutil.rmtree()`
3. Create parent directory if needed
4. Clone repository with authentication
5. Verify clone was successful

#### `commit_changes_locally()`
```python
def commit_changes_locally(
    self, 
    task_description: str, 
    modified_files: List[str],
    gemini_suggestions: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Commit changes locally without pushing.
    Always removes directory and clones fresh.
    Used for approval workflow.
    """
```

**Steps:**
1. Remove existing directory and clone fresh
2. Sync modified files to fresh clone
3. Check for changes to commit
4. Stage all changes
5. Create commit message with AI analysis
6. Commit locally (DO NOT PUSH)
7. Return commit hash and details

#### `push_committed_changes()`
```python
def push_committed_changes(self) -> Dict[str, Any]:
    """
    Push already committed changes to remote.
    Used after approval.
    """
```

**Steps:**
1. Push to origin using `git push origin HEAD`
2. Get commit hash
3. Return success/failure status

#### `commit_and_push_changes()`
```python
def commit_and_push_changes(
    self,
    task_description: str,
    modified_files: List[str],
    gemini_suggestions: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Commit changes and push to GitHub with Gemini analysis.
    Always removes directory and clones fresh.
    """
```

**Steps:**
1. Remove existing directory and clone fresh
2. Sync modified files to fresh clone
3. Check for changes to commit
4. Stage all changes
5. Create commit message with AI analysis
6. Commit changes
7. Push to origin
8. Return commit hash and details

### Main Orchestrator (`main.py`)

#### Background Processing Workflow

```python
async def process_task_in_background(task_id: str, approval_data: dict):
    """Process the approved task in the background."""
    
    # 1. Execute Dev Agent (modify files)
    dev_result = process_ui_editing_plan(plan, transcript)
    
    # 2. Run comprehensive testing
    test_result = run_testing_agent(transcript, modified_files)
    
    # 3. Remove directory and clone fresh
    sync_result = github_ops.remove_and_clone_fresh()
    
    # 4. Sync modified files to fresh clone
    file_sync_result = github_ops.sync_files_to_repo(modified_files, source_base)
    
    # 5. Get AI analysis
    gemini_suggestions = github_ops.get_gemini_suggestions(transcript, modified_files)
    
    # 6. Commit locally (no push)
    commit_result = github_ops.commit_changes_locally(
        transcript,
        modified_files,
        {"suggestions": gemini_analysis}
    )
    
    # 7. Notify user - awaiting approval
    # User can approve or rollback
```

#### Approval Endpoint

```python
@app.post("/approve-github-push/{task_id}")
async def approve_github_push(task_id: str):
    """
    Approve pushing already committed changes to GitHub remote repository.
    """
    
    # 1. Verify task is awaiting approval
    # 2. Push committed changes
    push_result = github_ops.push_committed_changes()
    
    # 3. Update task status
    # 4. Notify user of success
```

## Benefits

### 1. **Clean State**
- No stale files or uncommitted changes
- Every request starts with latest production code
- No merge conflicts from previous operations

### 2. **Quality Assurance**
- All changes are tested before commit
- AI analysis provides risk assessment
- User has final approval before production push

### 3. **Safety**
- Two-stage commit process prevents accidental pushes
- Rollback options available before push
- Clear audit trail with detailed commit messages

### 4. **Transparency**
- User sees exactly what will be committed
- AI analysis shows risk level and confidence
- Full visibility into the workflow

## Testing

Run the test suite to verify the workflow:

```bash
cd vocalCommit
python test_fresh_clone_workflow.py
```

The test suite verifies:
- ✅ Directory removal and fresh clone
- ✅ File synchronization
- ✅ Local commit without push
- ✅ Testing agent execution
- ✅ Approval workflow

## Configuration

Required environment variables in `vocalCommit/orchestrator/.env`:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token
TODO_UI_REPO_URL=https://github.com/your-username/TODO-UI.git
TODO_UI_LOCAL_PATH=todo-ui

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key
```

## API Endpoints

### Get Pending Approvals
```http
GET /pending-approvals
```

Returns all tasks awaiting push approval.

### Approve GitHub Push
```http
POST /approve-github-push/{task_id}
```

Approves and pushes a committed task to origin.

### Rollback Commit
```http
POST /rollback-commit/{task_id}?hard_rollback=false
```

Rolls back a local commit (soft or hard reset).

### Get GitHub Status
```http
GET /github-status
```

Returns current GitHub repository status and sync state.

## Troubleshooting

### Issue: "Failed to remove directory"
**Solution:** Check directory permissions and ensure no processes are using the directory.

### Issue: "Failed to clone repository"
**Solution:** Verify GitHub token has correct permissions and repository URL is correct.

### Issue: "No changes to commit"
**Solution:** Ensure files were properly synced to the fresh clone.

### Issue: "Failed to push changes"
**Solution:** Check GitHub token permissions and network connectivity.

## Future Enhancements

1. **Parallel Testing**: Run multiple test suites concurrently
2. **Incremental Sync**: Only sync changed files for better performance
3. **Conflict Resolution**: Automatic handling of merge conflicts
4. **Rollback History**: Track and manage multiple rollback points
5. **Approval Workflow**: Multi-user approval process for production pushes

## Summary

The fresh clone workflow ensures:
- ✅ Clean state for every request
- ✅ Comprehensive testing before commit
- ✅ Two-stage commit process with approval
- ✅ Safe and transparent workflow
- ✅ Full audit trail and rollback capability

This workflow provides a robust, production-ready system for managing code changes with confidence.
