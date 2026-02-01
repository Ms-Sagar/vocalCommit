# VocalCommit - Voice Orchestrated SDLC

VocalCommit is an AI-powered voice-controlled software development lifecycle orchestrator that allows you to manage development tasks through voice commands and agent coordination.

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

## 📋 Usage Guide

### 1. Voice Commands

1. Open the **Voice Interface** at http://localhost:5173
2. Click "Start Listening" or type commands
3. Try example commands:
   - "Create a login form component"
   - "Add validation to the todo form"
   - "Generate a user profile page"

### 2. Production Workflow Process

1. **Voice Input** → PM Agent creates task plan
2. **Automatic Development** → Dev Agent generates code or modifies UI
3. **GitHub Sync** → System pulls latest changes from production repository
4. **AI Analysis** → Gemini AI analyzes changes and provides recommendations
5. **Local Commit** → Changes are committed locally
6. **Approval Required** → Manual approval needed for production push
7. **Production Push** → Changes are pushed to GitHub repository
8. **Revert Available** → Option to revert last production push

### 3. Production Management

#### GitHub Operations
- **Sync Repository**: Automatically pulls latest changes from production
- **AI Risk Assessment**: Gemini AI analyzes changes for potential issues
- **Production Push**: Requires manual approval before going live
- **Revert Changes**: Easy rollback of the last production push

#### Approval Workflow
1. Complete task locally
2. Review AI analysis and recommendations
3. Approve push to production repository
4. Monitor production deployment
5. Revert if issues are detected

### 4. Todo UI Management

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

**1. Push to Production Fails**
- Check GitHub token permissions
- Verify repository write access
- Review commit message format
- Check for merge conflicts

**2. Revert Not Working**
- Ensure last commit is a VocalCommit commit
- Check repository state
- Verify GitHub connectivity

### Service Status Check

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

### Production Endpoints

- **`GET /github-status`**: Get GitHub repository status and sync state
- **`POST /sync-todo-ui`**: Sync the todo-ui repository (clone or pull)
- **`POST /approve-github-push/{task_id}`**: Approve pushing changes to production
- **`POST /revert-last-push`**: Revert the last commit in production repository

### WebSocket Events

- **`task_completed`**: Task completed with GitHub status
- **`github_pushed`**: Changes successfully pushed to production
- **`commit_reverted`**: Production commit reverted

### Workflow Endpoints

- **`GET /admin-workflows`**: Get workflows with GitHub push status
- **`GET /pending-approvals`**: List pending task approvals
- **`POST /approve-commit/{task_id}`**: Approve local commit
- **`POST /rollback-commit/{task_id}`**: Rollback local commit

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

**Happy Voice Coding with Production Deployment! 🎤🚀**

*Production-ready workflow with GitHub integration, AI analysis, and safe deployment practices.*