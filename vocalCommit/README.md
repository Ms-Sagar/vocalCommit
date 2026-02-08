# VocalCommit - Voice Orchestrated SDLC

VocalCommit is an AI-powered voice-controlled software development lifecycle orchestrator that allows you to manage development tasks through voice commands and agent coordination.

## 📑 Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features)
- [Architecture](#-architecture)
- [Usage Guide & Major Workflows](#-usage-guide--major-workflows)
  - [Workflow 1: Complete Development Lifecycle](#workflow-1-complete-development-lifecycle-voice-to-production)
  - [Workflow 2: Commit Approval Process](#workflow-2-commit-approval-process)
  - [Workflow 3: Drop Latest Production Commit](#workflow-3-drop-latest-production-commit)
  - [Workflow 4: Real-Time Status Updates](#workflow-4-real-time-status-updates)
  - [Workflow 5: Manual GitHub Operations](#workflow-5-manual-github-operations)
  - [Workflow 6: Error Recovery](#workflow-6-error-recovery)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)
- [Development Workflow](#-development-workflow)
- [API Reference](#-api-reference)
- [Quick Reference](#-quick-reference)
- [Contributing](#-contributing)
- [License](#-license)
- [Support](#-support)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Git** with GitHub access
- **macOS/Linux** (tested on macOS)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd vocalCommit
```

### 2. Automated Setup (Recommended)

```bash
# Run the setup script to install all dependencies
python3 setup_vocalCommit.py
```

### 3. Production Configuration

#### Environment Setup
Create or update `vocalCommit/orchestrator/.env`:
```env
# Google AI API (required for AI features)
GEMINI_API_KEY=your_gemini_api_key_here

# GitHub Configuration for Production TODO-UI (required)
GITHUB_TOKEN=your_github_fine_grained_token
TODO_UI_REPO_URL=https://github.com/Ms-Sagar/TODO-UI.git
TODO_UI_LOCAL_PATH=todo-ui
```

#### GitHub Token Setup
1. Go to GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens
2. Create a new token with repository access to your TODO-UI repo
3. Grant permissions: Contents (read/write), Metadata (read), Pull requests (read)
4. Copy the token to your `.env` file

### 4. Start Services

Start each service in a separate terminal for better control and monitoring:

#### Terminal 1 - Backend Orchestrator
```bash
cd vocalCommit/orchestrator
python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2 - Voice Interface
```bash
cd vocalCommit/frontend
npm run dev
```

#### Terminal 3 - Todo UI (Production or Local)
```bash
# If production todo-ui repo is cloned (recommended)
cd todo-ui
npm run dev

# OR if using local development version
cd vocalCommit/orchestrator/todo-ui
npm run dev
```

### 5. Access the Application

- **Voice Interface**: http://localhost:5173
- **Todo Management UI**: http://localhost:5174 (or production port)
- **API Health Check**: http://localhost:8000/health
- **GitHub Status**: http://localhost:8000/github-status

## 🎯 Features

### Voice Commands
- **Task Creation**: "Create a user authentication system"
- **UI Modifications**: "Add a dark mode toggle to the todo UI"
- **Code Generation**: "Build a REST API for user management"

### Agent System
- **PM Agent**: Task planning and project coordination
- **Dev Agent**: AI-powered code generation and UI editing
- **Security Agent**: Code vulnerability scanning (disabled)
- **DevOps Agent**: Deployment automation (disabled)

### Production Workflow Management
- **GitHub Integration**: Automatic sync with production TODO-UI repository
- **AI Analysis**: Gemini AI provides change recommendations and risk assessment
- **Approval System**: Manual review and approval before pushing to production
- **Real-time Updates**: Live WebSocket connections for workflow status
- **Revert Capability**: Easy rollback of production changes

### Git Integration & Production Workflow
1. **Local Development**: Changes are made to local todo-ui files
2. **GitHub Sync**: System pulls latest changes from production repository
3. **AI Analysis**: Gemini AI analyzes changes and provides recommendations
4. **Approval Required**: Manual approval needed before pushing to production
5. **Production Push**: Changes are committed and pushed to GitHub repository
6. **Revert Option**: Easy revert of last production push if needed

## 🛠️ Architecture

### System Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Voice Interface│    │   Orchestrator   │    │ Production      │
│   (React/Vite)  │◄──►│  (FastAPI/WS)    │◄──►│ TODO-UI Repo    │
│   Port: 5173    │    │   Port: 8000     │    │ (GitHub)        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          │
                              ▼                          ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │   Agent System   │    │   Local Todo-UI │
                    │  PM │ Dev │ AI   │    │   (Development) │
                    └──────────────────┘    └─────────────────┘
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER INPUT                               │
│                    (Voice or Text Command)                       │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ PM Agent   │→ │ Dev Agent  │→ │  Testing   │                │
│  │ (Planning) │  │ (Coding)   │  │ (Validate) │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    LOCAL GIT COMMIT                              │
│              (orchestrator/todo-ui changes)                      │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   APPROVAL REQUIRED                              │
│         User Reviews Changes in UI Modal                         │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
                    ┌────────┴────────┐
                    ▼                 ▼
            ┌──────────────┐   ┌──────────────┐
            │   APPROVE    │   │   ROLLBACK   │
            └──────┬───────┘   └──────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                  GITHUB SYNC & PUSH                              │
│  1. Pull latest from GitHub                                      │
│  2. Copy files: orchestrator/todo-ui → todo-ui/                 │
│  3. Commit in GitHub repo                                        │
│  4. Push to remote                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYED                           │
│              (Changes live on GitHub)                            │
└──────────────────────────────────────────────────────────────────┘
```

### Repository Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR REPOSITORY                      │
│  (Main VocalCommit codebase - where you run the system)        │
│                                                                 │
│  vocalCommit/                                                   │
│  ├── orchestrator/          ← Backend & Agents                  │
│  │   ├── core/             ← FastAPI app                       │
│  │   ├── agents/           ← PM, Dev, Testing agents           │
│  │   ├── tools/            ← Git, GitHub, File operations      │
│  │   └── todo-ui/          ← LOCAL development copy            │
│  │       └── src/          ← Changes made HERE first           │
│  ├── frontend/              ← Voice Interface UI                │
│  └── README.md                                                  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ On Approval
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TODO-UI REPOSITORY                           │
│  (Separate GitHub repo - production deployment target)         │
│                                                                 │
│  todo-ui/                   ← GitHub repo clone                 │
│  ├── .git/                  ← Git repository                    │
│  ├── src/                   ← Files synced HERE on approval     │
│  │   ├── App.tsx                                                │
│  │   ├── components/                                            │
│  │   └── ...                                                    │
│  └── package.json                                               │
│                                                                 │
│  Pushed to: https://github.com/USERNAME/TODO-UI                │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                      VOICE INTERFACE                            │
│  • Voice/Text Input                                             │
│  • Active Workflows Display                                     │
│  • Commit Approval Modal                                        │
│  • Latest Push Status                                           │
│  • Agent Response Feed                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │ WebSocket (ws://localhost:8000/ws)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR BACKEND                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ WebSocket Manager                                        │  │
│  │  • Real-time bidirectional communication                 │  │
│  │  • Task status updates                                   │  │
│  │  • Approval notifications                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Agent Orchestration                                      │  │
│  │  • PM Agent: Task planning                               │  │
│  │  • Dev Agent: Code generation                            │  │
│  │  • Testing Agent: Validation                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Git Operations                                           │  │
│  │  • Local commits (git_ops.py)                            │  │
│  │  • GitHub sync (github_ops.py)                           │  │
│  │  • File synchronization                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ Git Commands
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GIT REPOSITORIES                           │
│  ┌─────────────────────┐      ┌─────────────────────┐          │
│  │ Orchestrator Repo   │      │ TODO-UI Repo        │          │
│  │ (Local commits)     │      │ (Production pushes) │          │
│  └─────────────────────┘      └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Usage Guide & Major Workflows

### 1. Voice Commands

1. Open the **Voice Interface** at http://localhost:5173
2. Click "Start Listening" or type commands
3. Try example commands:
   - "Create a login form component"
   - "Add validation to the todo form"
   - "Generate a user profile page"
   - "Add a dark mode toggle"
   - "Create a user profile component with avatar"

---

## 🔄 Major Workflows

### Workflow 1: Complete Development Lifecycle (Voice to Production)

This is the primary workflow from voice command to production deployment:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. VOICE INPUT                                                  │
│    User speaks or types command                                 │
│    Example: "Add a priority field to todo items"               │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. PM AGENT ANALYSIS                                            │
│    • Analyzes requirements                                      │
│    • Creates task breakdown                                     │
│    • Identifies files to modify                                 │
│    • Estimates complexity                                       │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. DEV AGENT IMPLEMENTATION                                     │
│    • Generates/modifies code                                    │
│    • Updates UI components                                      │
│    • Writes to orchestrator/todo-ui/                           │
│    • Maintains code quality                                     │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. TESTING & VALIDATION                                         │
│    • Syntax validation                                          │
│    • Build test (if applicable)                                 │
│    • Functional validation                                      │
│    • Test results displayed in UI                               │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. LOCAL GIT COMMIT                                             │
│    • Changes staged automatically                               │
│    • Commit created with task details                           │
│    • Commit hash generated                                      │
│    • Files tracked in orchestrator repo                         │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. COMMIT APPROVAL REQUIRED ⚠️                                  │
│    • Approval modal appears in UI                               │
│    • Shows commit details and modified files                    │
│    • Three options available:                                   │
│      ✅ Approve: Push to production                             │
│      🔄 Soft Rollback: Undo commit, keep changes unstaged       │
│      🗑️ Hard Rollback: Discard changes completely              │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. PRODUCTION PUSH (After Approval)                             │
│    • Sync TODO-UI repo from GitHub                              │
│    • Copy files from orchestrator/todo-ui to GitHub repo        │
│    • Create commit in GitHub repo                               │
│    • Push to remote GitHub repository                           │
│    • Update UI with push status                                 │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. PRODUCTION MONITORING                                        │
│    • Latest push displayed in UI                                │
│    • Commit hash and timestamp shown                            │
│    • Option to drop latest commit if needed                     │
│    • Real-time status updates via WebSocket                     │
└─────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- Changes are made in `orchestrator/todo-ui/` (local development)
- Local commit happens automatically after testing
- Manual approval required before production push
- Files are synced to GitHub repo clone before pushing
- Production push creates a new commit in the TODO-UI repository

---

### Workflow 2: Commit Approval Process

When a task completes, you'll see an approval modal with three options:

#### Option A: Approve Commit ✅
```
User clicks "Approve Commit"
    ↓
Backend receives approval request
    ↓
Pull latest changes from GitHub TODO-UI repo
    ↓
Sync modified files from orchestrator/todo-ui to GitHub repo
    ↓
Create commit in GitHub repo with task details
    ↓
Push commit to remote GitHub repository
    ↓
Send WebSocket notification to frontend
    ↓
UI closes modal and shows GitHub push status
    ↓
Latest push section displays commit info
```

**What happens:**
- Changes are pushed to production GitHub repository
- Commit is permanent in GitHub history
- UI updates to show successful push
- Latest push section shows commit details

#### Option B: Soft Rollback 🔄
```
User clicks "Soft Rollback"
    ↓
Backend performs git reset --soft HEAD~1
    ↓
Commit is undone in local orchestrator repo
    ↓
Changes remain as unstaged files
    ↓
UI closes modal and removes from approval list
```

**What happens:**
- Local commit is undone
- Files keep their modifications (unstaged)
- Can be re-committed later if needed
- No changes to GitHub repository

#### Option C: Hard Rollback 🗑️
```
User clicks "Hard Rollback"
    ↓
Backend performs git reset --soft HEAD~1
    ↓
Backend runs git checkout HEAD -- <files>
    ↓
Only modified files are discarded
    ↓
UI closes modal and removes from approval list
```

**What happens:**
- Local commit is undone
- Modified files are discarded completely
- Changes are permanently lost
- Safer than full hard reset (only affects commit files)
- No changes to GitHub repository

---

### Workflow 3: Drop Latest Production Commit

If you need to revert the last push to production:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. IDENTIFY ISSUE                                               │
│    • Bug discovered in production                               │
│    • Need to revert latest changes                              │
│    • Latest push section shows commit details                   │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. CLICK "DROP LATEST COMMIT"                                   │
│    • Button available in Latest Push section                    │
│    • Confirms the commit hash to drop                           │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. BACKEND REVERT PROCESS                                       │
│    • Verifies commit is a VocalCommit commit                    │
│    • Creates revert commit in GitHub repo                       │
│    • Pushes revert to remote repository                         │
│    • Sends WebSocket notification                               │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. UI UPDATE                                                    │
│    • Latest push section cleared                                │
│    • Success message displayed                                  │
│    • Production is now at previous state                        │
└─────────────────────────────────────────────────────────────────┘
```

**Important Notes:**
- Only VocalCommit commits can be dropped
- Creates a revert commit (doesn't delete history)
- Pushes revert to GitHub automatically
- Cannot be undone (permanent revert)

---

### Workflow 4: Real-Time Status Updates

The UI provides real-time updates through WebSocket connections:

```
┌─────────────────────────────────────────────────────────────────┐
│ WEBSOCKET CONNECTION                                            │
│    Frontend ←→ Backend (ws://localhost:8000/ws)                 │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ EVENT TYPES                                                     │
│                                                                 │
│ • task_created          → New task started                      │
│ • processing            → Agent working on task                 │
│ • completed             → Task finished, approval needed        │
│ • commit_approved       → Commit approved, pushed to GitHub     │
│ • github_pushed         → Successful push notification          │
│ • commit_dropped        → Production commit reverted            │
│ • rolled_back           → Local commit rolled back              │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ UI UPDATES                                                      │
│                                                                 │
│ • Active Workflows section shows progress                       │
│ • Commit Approvals section shows pending approvals              │
│ • Latest Push section shows production status                   │
│ • Agent Responses section shows communication                   │
└─────────────────────────────────────────────────────────────────┘
```

---

### Workflow 5: Manual GitHub Operations

You can manually manage the GitHub repository:

#### Sync Repository
```bash
# Via API
curl -X POST http://localhost:8000/sync-todo-ui

# What it does:
# - Clones repo if not present
# - Pulls latest changes if exists
# - Updates local GitHub repo clone
```

#### Check GitHub Status
```bash
# Via API
curl http://localhost:8000/github-status

# Returns:
# - Repository URL and local path
# - Last commit information
# - Sync status
# - Token validation status
```

#### Manual File Sync (Development)
```bash
# Use the push script
cd vocalCommit/orchestrator
python3 push_todo_ui.py

# What it does:
# - Copies files from orchestrator/todo-ui to GitHub repo
# - Creates commit with all changes
# - Pushes to GitHub
```

---

### Workflow 6: Error Recovery

If something goes wrong, here's how to recover:

#### Scenario A: Approval Push Failed
```
Problem: Clicked approve but push failed
    ↓
Check GitHub token permissions
    ↓
Verify repository write access
    ↓
Check backend logs for specific error
    ↓
Fix the issue (token, network, etc.)
    ↓
Task remains in approval list
    ↓
Click approve again to retry
```

#### Scenario B: Modal Won't Close
```
Problem: Approval modal stuck open
    ↓
Check browser console for errors
    ↓
Verify WebSocket connection status
    ↓
Refresh the page (WebSocket reconnects)
    ↓
Check backend logs for approval response
    ↓
If needed, restart backend service
```

#### Scenario C: Files Not Syncing
```
Problem: Changes not appearing in GitHub
    ↓
Verify files exist in orchestrator/todo-ui/
    ↓
Check modified_files list in task data
    ↓
Manually sync: python3 push_todo_ui.py
    ↓
Check GitHub repo for changes
    ↓
Review backend logs for sync errors
```

---

### 2. Production Management

#### GitHub Operations
- **Sync Repository**: Automatically pulls latest changes from production
- **AI Risk Assessment**: Gemini AI analyzes changes for potential issues
- **Production Push**: Requires manual approval before going live
- **Revert Changes**: Easy rollback of the last production push

#### Approval Workflow Summary
1. Task completes with local commit
2. Approval modal appears with commit details
3. Review changes and modified files
4. Choose: Approve (push to GitHub), Soft Rollback (keep changes), or Hard Rollback (discard)
5. If approved: Files sync to GitHub repo and push to remote
6. Monitor production status in Latest Push section
7. Drop commit if issues detected

### 3. Todo UI Management

- View generated tasks and workflows
- Real-time updates from voice commands
- Production status indicators
- Theme toggle (light/dark mode)
- CRUD operations with optimistic updates

## 🔧 Configuration

### Environment Variables

Required configuration in `vocalCommit/orchestrator/.env`:
```env
# Google AI API (required for AI features)
GEMINI_API_KEY=your_gemini_api_key_here

# GitHub Configuration (required for production)
GITHUB_TOKEN=your_github_fine_grained_token
TODO_UI_REPO_URL=https://github.com/Ms-Sagar/TODO-UI.git
TODO_UI_LOCAL_PATH=todo-ui

# Development settings (optional)
DEBUG=true
LOG_LEVEL=INFO
```

### GitHub Repository Setup

1. **Create TODO-UI Repository**: Separate repository for production todo-ui
2. **Fine-grained Token**: Create GitHub token with repository access
3. **Local Clone**: System will automatically clone/sync the repository
4. **Production Deployment**: Set up your preferred deployment pipeline

### File Watching

The system automatically watches both local and production todo-ui directories:
- Local: `vocalCommit/orchestrator/todo-ui/src` (development)
- Production: `todo-ui/src` (production repository)

## 🚨 Troubleshooting

### Common Issues

**1. GitHub Authentication Failed**
```bash
# Check token permissions
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# Verify repository access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/Ms-Sagar/TODO-UI
```

**2. Production Repository Sync Issues**
```bash
# Check GitHub status
curl http://localhost:8000/github-status

# Manual sync
curl -X POST http://localhost:8000/sync-todo-ui
```

**3. AI Analysis Failures**
- Verify `GEMINI_API_KEY` is set correctly
- Check API quota and rate limits
- Review logs for specific error messages

**4. Backend Connection Failed**
```bash
# Check if port 8000 is available
lsof -i :8000
# Restart orchestrator
cd vocalCommit/orchestrator
python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Workflow Issues

**1. Approval Modal Won't Close After Clicking Approve**

**Symptoms:**
- Clicked "Approve Commit" button
- Button shows "⏳ Approving..." but never completes
- Modal remains visible
- Changes not pushed to GitHub

**Causes & Solutions:**

a) **WebSocket Connection Issue**
```bash
# Check browser console for WebSocket errors
# Look for: "WebSocket connection closed" or "Failed to send"

# Solution: Refresh the page
# The WebSocket will reconnect automatically
```

b) **Backend Not Sending Approval Notification**
```bash
# Check backend logs for:
# "Task {task_id} commit approved and finalized"
# "Successfully pushed approved commit to GitHub"

# If missing, check:
cd vocalCommit/orchestrator
tail -f orchestrator.log

# Restart backend if needed
python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
```

c) **File Sync Failed**
```bash
# Check logs for:
# "Failed to sync files to GitHub repo"

# Verify files exist:
ls -la vocalCommit/orchestrator/todo-ui/src/

# Manual sync:
cd vocalCommit/orchestrator
python3 push_todo_ui.py
```

**2. Push to Production Fails**

**Symptoms:**
- Approval succeeds but GitHub push fails
- Error message in UI: "Failed to push changes"

**Solutions:**

a) **Check GitHub Token Permissions**
```bash
# Test token
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# Verify repository access
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/YOUR_USERNAME/TODO-UI

# Required permissions:
# - Contents: Read and Write
# - Metadata: Read
```

b) **Check Repository Write Access**
```bash
# Verify you can push to the repo
cd todo-ui
git push origin main

# If fails, check:
# - Token has write permissions
# - Repository exists
# - Branch name is correct (main vs master)
```

c) **Check for Merge Conflicts**
```bash
# Pull latest changes
cd todo-ui
git pull origin main

# If conflicts, resolve manually
git status
# Fix conflicts, then:
git add .
git commit -m "Resolve conflicts"
git push origin main
```

**3. Changes Not Appearing in GitHub Repository**

**Symptoms:**
- Approval succeeds
- No errors shown
- But changes not in GitHub repo

**Solutions:**

a) **Verify File Sync**
```bash
# Check if files were synced to GitHub repo clone
cd todo-ui
git status

# Should show modified files
# If not, files weren't synced from orchestrator/todo-ui
```

b) **Check Modified Files List**
```bash
# In backend logs, look for:
# "Synced X files to GitHub repo"

# Verify the file paths are correct
# Should be relative paths like: "src/App.tsx"
```

c) **Manual File Sync**
```bash
# Copy files manually
cd vocalCommit/orchestrator
python3 push_todo_ui.py

# This will:
# - Copy all files from orchestrator/todo-ui to todo-ui
# - Create commit
# - Push to GitHub
```

**4. Revert Not Working**

**Symptoms:**
- Clicked "Drop Latest Commit"
- Error: "Last commit is not a VocalCommit commit"

**Solutions:**

a) **Check Last Commit**
```bash
cd todo-ui
git log -1

# Look for "[VocalCommit]" in commit message
# Only VocalCommit commits can be auto-reverted
```

b) **Manual Revert**
```bash
cd todo-ui
git revert HEAD
git push origin main
```

**5. Approval Button Disabled**

**Symptoms:**
- Approve button is grayed out
- Can't click to approve

**Causes:**
- Another approval in progress for same task
- Task already approved
- Backend processing previous request

**Solutions:**
```bash
# Refresh the page
# Check backend logs for stuck requests
# Restart backend if needed
```

**6. Multiple Approval Modals**

**Symptoms:**
- Multiple tasks showing approval modals
- Confusing which to approve

**Solutions:**
- Each modal shows task ID and description
- Approve or rollback each one individually
- They're independent operations
- Can approve in any order

---

### 2. Backend Connection Failed

```bash
# Check individual services
curl http://localhost:8000/health          # Backend
curl http://localhost:8000/github-status   # GitHub integration
curl -I http://localhost:5173              # Voice Interface
curl -I http://localhost:5174              # Todo UI
```

## 📁 Project Structure

```
vocalCommit/
├── README.md                    # This file
├── setup_vocalCommit.py         # Automated setup script
├── orchestrator/               # Backend API & Agent System
│   ├── core/
│   │   ├── main.py            # FastAPI application
│   │   └── config.py          # Configuration with GitHub settings
│   ├── agents/                # AI Agent implementations
│   ├── tools/                 # Utility tools
│   │   ├── github_ops.py      # GitHub operations (NEW)
│   │   ├── git_ops.py         # Local git operations
│   │   ├── file_ops.py        # File operations (updated)
│   │   └── ui_file_watcher.py # UI file monitoring (updated)
│   ├── utils/                 # Helper utilities
│   ├── requirements.txt       # Python dependencies (updated)
│   ├── .env                   # Environment configuration (updated)
│   └── todo-ui/               # Local Development UI (fallback)
├── frontend/                  # Voice Interface
│   ├── src/
│   │   ├── components/
│   │   │   └── VoiceInterface.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
└── todo-ui/                   # Production TODO-UI Repository (separate)
    ├── .git/                  # Git repository
    ├── src/
    │   ├── App.tsx            # Main todo application
    │   ├── App.css            # Styling
    │   └── main.tsx
    └── package.json
```

## 🔄 Development Workflow

### Production Development Process

1. **Voice Command**: Issue voice command for new feature
2. **Local Development**: Changes made to local todo-ui files
3. **AI Analysis**: Gemini AI analyzes changes and provides recommendations
4. **Review & Approve**: Manual review of changes and AI recommendations
5. **Production Push**: Approved changes pushed to GitHub repository
6. **Monitor & Revert**: Monitor production and revert if needed

### Adding New Features

1. **Voice Commands**: Modify `VoiceInterface.tsx`
2. **Agent Logic**: Update agent files in `orchestrator/agents/`
3. **API Endpoints**: Add routes in `orchestrator/core/main.py`
4. **Production Integration**: Use GitHub operations for production deployment

### Testing Production Workflow

**GitHub Integration:**
```bash
# Test GitHub status
curl http://localhost:8000/github-status

# Test repository sync
curl -X POST http://localhost:8000/sync-todo-ui

# Test revert functionality
curl -X POST http://localhost:8000/revert-last-push
```

## 📝 API Reference

### Core Endpoints

- **`GET /health`**: Health check endpoint
- **`GET /`**: Root endpoint with API information
- **`WS /ws`**: WebSocket connection for real-time updates

### Task & Workflow Endpoints

- **`GET /admin-workflows`**: Get all workflows with status and GitHub push info
- **`GET /pending-approvals`**: List tasks pending approval (deprecated - use workflows)
- **`POST /voice-command`**: Submit a voice command (alternative to WebSocket)

### Commit Management Endpoints

- **`POST /approve-commit/{task_id}`**: Approve a local commit and push to GitHub
  - Syncs files from orchestrator/todo-ui to GitHub repo
  - Creates commit in GitHub repository
  - Pushes to remote GitHub
  - Returns: commit hash, push status, GitHub commit info

- **`POST /rollback-commit/{task_id}?hard_rollback={bool}`**: Rollback a local commit
  - `hard_rollback=false`: Soft rollback (keeps changes unstaged)
  - `hard_rollback=true`: Hard rollback (discards changes for commit files only)
  - Returns: rolled back commit hash, affected files

- **`POST /drop-latest-commit`**: Drop the latest commit from production TODO-UI repo
  - Creates revert commit in GitHub repository
  - Pushes revert to remote
  - Only works on VocalCommit commits
  - Returns: reverted commit hash, changed files

### GitHub Integration Endpoints

- **`GET /github-status`**: Get GitHub repository status and sync state
  - Returns: repo URL, local path, last commit info, sync status

- **`POST /sync-todo-ui`**: Sync the todo-ui repository (clone or pull)
  - Clones if not present, pulls if exists
  - Returns: sync status, action taken (cloned/pulled)

### WebSocket Events

#### Outgoing (Backend → Frontend)

- **`task_created`**: New task started
  ```json
  {
    "type": "task_created",
    "task_id": "string",
    "transcript": "string",
    "status": "processing"
  }
  ```

- **`processing`**: Agent working on task
  ```json
  {
    "status": "processing",
    "agent": "string",
    "response": "string",
    "task_id": "string"
  }
  ```

- **`completed`**: Task finished, approval needed
  ```json
  {
    "status": "completed",
    "task_id": "string",
    "commit_info": {
      "commit_hash": "string",
      "commit_message": "string",
      "timestamp": "string"
    },
    "modified_files": ["string"],
    "github_pushed": false
  }
  ```

- **`commit_approved`**: Commit approved and pushed to GitHub
  ```json
  {
    "type": "commit_approved",
    "task_id": "string",
    "status": "approved",
    "commit_hash": "string",
    "github_pushed": true,
    "github_commit_info": {
      "commit_hash": "string",
      "pushed_at": "string"
    }
  }
  ```

- **`github_pushed`**: Successful push notification
  ```json
  {
    "type": "github_pushed",
    "task_id": "string",
    "commit_hash": "string"
  }
  ```

- **`commit_dropped`**: Production commit reverted
  ```json
  {
    "type": "commit_dropped",
    "reverted_commit": "string",
    "changed_files": ["string"]
  }
  ```

- **`rolled_back`**: Local commit rolled back
  ```json
  {
    "status": "rolled_back",
    "task_id": "string",
    "rolled_back_commit": "string",
    "changed_files": ["string"]
  }
  ```

#### Incoming (Frontend → Backend)

- **`voice_command`**: Voice input from user
  ```json
  {
    "type": "voice_command",
    "transcript": "string",
    "timestamp": "string"
  }
  ```

- **`text_command`**: Text input from user
  ```json
  {
    "type": "text_command",
    "transcript": "string",
    "timestamp": "string"
  }
  ```

### Response Formats

#### Success Response
```json
{
  "status": "success",
  "message": "string",
  "data": {}
}
```

#### Error Response
```json
{
  "status": "error",
  "error": "string",
  "details": {}
}
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8000/health

# GitHub status
curl http://localhost:8000/github-status

# Sync repository
curl -X POST http://localhost:8000/sync-todo-ui

# Get workflows
curl http://localhost:8000/admin-workflows

# Approve commit
curl -X POST http://localhost:8000/approve-commit/task_123

# Soft rollback
curl -X POST "http://localhost:8000/rollback-commit/task_123?hard_rollback=false"

# Hard rollback
curl -X POST "http://localhost:8000/rollback-commit/task_123?hard_rollback=true"

# Drop latest commit
curl -X POST http://localhost:8000/drop-latest-commit
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Test with production workflow
4. Commit changes: `git commit -am 'Add new feature'`
5. Push to branch: `git push origin feature/new-feature`
6. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Verify GitHub token and repository access
3. Review browser console for errors
4. Check individual service logs in terminal windows
5. Test GitHub integration endpoints

---

## 🎯 Quick Reference

### Common Commands

```bash
# Start Backend
cd vocalCommit/orchestrator
python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload

# Start Frontend
cd vocalCommit/frontend
npm run dev

# Start Todo UI (Production)
cd todo-ui
npm run dev

# Check Services
curl http://localhost:8000/health          # Backend
curl http://localhost:8000/github-status   # GitHub
curl -I http://localhost:5173              # Frontend
curl -I http://localhost:5174              # Todo UI

# GitHub Operations
curl -X POST http://localhost:8000/sync-todo-ui
curl -X POST http://localhost:8000/drop-latest-commit

# Manual File Sync
cd vocalCommit/orchestrator
python3 push_todo_ui.py
```

### Approval Workflow Quick Guide

1. **Task Completes** → Approval modal appears
2. **Review Changes** → Check commit details and files
3. **Choose Action:**
   - ✅ **Approve**: Push to GitHub production
   - 🔄 **Soft Rollback**: Undo commit, keep changes
   - 🗑️ **Hard Rollback**: Discard changes completely
4. **Monitor** → Check Latest Push section
5. **Revert if Needed** → Click "Drop Latest Commit"

### File Locations

```
orchestrator/todo-ui/          # Local development (changes made here)
todo-ui/                       # GitHub repo clone (pushed from here)
orchestrator/.env              # Configuration
orchestrator/orchestrator.log  # Backend logs
```

### Port Reference

- **8000**: Backend API & WebSocket
- **5173**: Voice Interface (Frontend)
- **5174**: Todo UI (Production/Development)

### Environment Variables

```env
# Required
GEMINI_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here
TODO_UI_REPO_URL=https://github.com/USERNAME/TODO-UI.git

# Optional
TODO_UI_LOCAL_PATH=todo-ui
DEBUG=true
LOG_LEVEL=INFO
```

### Workflow States

- **pending**: Task created, waiting for PM agent
- **processing**: Agent working on task
- **completed**: Task done, awaiting approval
- **approved**: Commit approved, pushed to GitHub
- **rolled_back**: Commit undone locally

### WebSocket Connection

```javascript
// Frontend connects to:
ws://localhost:8000/ws

// Or in production:
wss://your-domain.com/ws
```

---

**Happy Voice Coding with Production Deployment! 🎤🚀**

*Production-ready workflow with GitHub integration, AI analysis, and safe deployment practices.*

---

## 📚 Additional Resources

### Architecture Overview

```
Voice Input → PM Agent → Dev Agent → Testing → Local Commit
                                                    ↓
                                            Approval Required
                                                    ↓
                                    ┌───────────────┼───────────────┐
                                    ↓               ↓               ↓
                                Approve      Soft Rollback    Hard Rollback
                                    ↓
                            Sync Files to GitHub Repo
                                    ↓
                            Commit in GitHub Repo
                                    ↓
                            Push to Remote GitHub
                                    ↓
                            Production Deployed
                                    ↓
                            Monitor & Drop if Needed
```

### Key Concepts

**Two Repository System:**
- **Orchestrator Repo**: Where VocalCommit runs and makes changes
- **TODO-UI Repo**: Separate GitHub repository for production deployment

**Approval System:**
- Local commits happen automatically after testing
- Manual approval required before production push
- Three rollback options for safety

**File Synchronization:**
- Changes made in `orchestrator/todo-ui/`
- On approval, files copied to `todo-ui/` (GitHub repo clone)
- Then committed and pushed to remote GitHub

**WebSocket Communication:**
- Real-time updates between backend and frontend
- Task status, approval notifications, push confirmations
- Automatic reconnection on disconnect

---

## 🔐 Security Best Practices

1. **GitHub Token**: Use fine-grained tokens with minimal permissions
2. **Environment Variables**: Never commit `.env` files
3. **Code Review**: Always review changes before approving
4. **Testing**: Test locally before pushing to production
5. **Rollback Plan**: Know how to revert changes quickly
6. **Monitoring**: Watch production after deployments
7. **Access Control**: Limit who can approve production pushes

---

## 🚀 Deployment Considerations

### Local Development
- Use `orchestrator/todo-ui` for development
- Test changes before committing
- Use soft rollback to iterate

### Production Deployment
- Approve only tested changes
- Monitor after each push
- Keep GitHub token secure
- Set up CI/CD for automated testing
- Configure deployment platform (Render, Vercel, etc.)

### Scaling
- Consider rate limiting for voice commands
- Add authentication for production use
- Implement proper logging and monitoring
- Set up error tracking (Sentry, etc.)
- Add database for persistent task storage

---

**Happy Voice Coding with Production Deployment! 🎤🚀**

*Production-ready workflow with GitHub integration, AI analysis, and safe deployment practices.*