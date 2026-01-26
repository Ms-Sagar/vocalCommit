# VocalCommit - Voice Orchestrated SDLC

VocalCommit is an AI-powered voice-controlled software development lifecycle orchestrator that allows you to manage development tasks through voice commands and agent coordination.

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
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

### 3. Start Services Individually

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

#### Terminal 3 - Todo UI (now inside orchestrator)
```bash
cd vocalCommit/orchestrator/todo-ui
npm run dev
```

**💡 Why Individual Startup?**
- Better log visibility per service
- Independent restart capability
- Easier debugging and development
- Individual process control

### 4. Access the Application

- **Voice Interface**: http://localhost:5173
- **Todo Management UI**: http://localhost:5174
- **API Health Check**: http://localhost:8000/health

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

### Workflow Management
- **Approval System**: Manual review and approval of agent plans
- **Real-time Updates**: Live WebSocket connections
- **File Generation**: Export generated code to frontend
- **UI File Watching**: Automatic detection of todo-ui changes

## 🛠️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Voice Interface│    │   Orchestrator   │    │    Todo UI      │
│   (React/Vite)  │◄──►│  (FastAPI/WS)    │◄──►│  (React/Vite)   │
│   Port: 5173    │    │   Port: 8000     │    │ Port: 5174      │
└─────────────────┘    └──────────────────┘    │ (inside orch.)  │
                              │                 └─────────────────┘
                              ▼
                    ┌──────────────────┐
                    │   Agent System   │
                    │  PM │ Dev │ Sec  │
                    └──────────────────┘
```

## 📋 Usage Guide

### 1. Voice Commands

1. Open the **Voice Interface** at http://localhost:5173
2. Click "Start Listening" or type commands
3. Try example commands:
   - "Create a login form component"
   - "Add validation to the todo form"
   - "Generate a user profile page"

### 2. Workflow Process

1. **Voice Input** → PM Agent creates task plan
2. **Manual Approval** → Review and approve/reject plans
3. **Development** → Dev Agent generates code or modifies UI
4. **File Generation** → Export code to frontend (optional)

### 3. Todo UI Management

- View generated tasks and workflows
- Real-time updates from voice commands
- Theme toggle (light/dark mode)
- CRUD operations with optimistic updates

## 🔧 Configuration

### Environment Variables

Create `vocalCommit/orchestrator/.env`:
```env
# Google AI API (optional - for enhanced AI features)
GOOGLE_API_KEY=your_api_key_here

# Development settings
DEBUG=true
LOG_LEVEL=INFO
```

### File Watching

The system automatically watches `vocalCommit/orchestrator/todo-ui/src` for changes. Configure paths in:
```python
# vocalCommit/orchestrator/tools/ui_file_watcher.py
```

## 🚨 Troubleshooting

### Common Issues

**1. Backend Connection Failed**
```bash
# Check if port 8000 is available
lsof -i :8000
# Restart orchestrator
cd vocalCommit/orchestrator
python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
```

**2. Frontend Build Errors**
```bash
# Clear node_modules and reinstall
cd vocalCommit/frontend
rm -rf node_modules package-lock.json
npm install
```

**3. Missing Dependencies**
```bash
# Todo UI missing uuid (now inside orchestrator)
cd vocalCommit/orchestrator/todo-ui
npm install uuid @types/uuid
```

**4. CSS Not Loading**
- Ensure `import './App.css'` is in App.tsx
- Check browser console for import errors
- Restart dev server with `npm run dev`

### Service Status Check

```bash
# Check individual services
curl http://localhost:8000/health  # Backend
curl -I http://localhost:5173      # Voice Interface
curl -I http://localhost:5174      # Todo UI

# Check running processes
ps aux | grep -E "(uvicorn|vite|npm)"
```

### Individual Service Management

**Restart Backend Only:**
```bash
# Stop: Ctrl+C in backend terminal
cd vocalCommit/orchestrator
python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
```

**Restart Frontend Only:**
```bash
# Stop: Ctrl+C in frontend terminal
cd vocalCommit/frontend
npm run dev
```

**Restart Todo UI Only:**
```bash
# Stop: Ctrl+C in todo-ui terminal
cd vocalCommit/orchestrator/todo-ui
npm run dev
```

## 📁 Project Structure

```
vocalCommit/
├── README.md                    # This file
├── setup_vocalCommit.py         # Automated setup script
├── orchestrator/               # Backend API & Agent System
│   ├── core/
│   │   ├── main.py            # FastAPI application
│   │   └── config.py          # Configuration
│   ├── agents/                # AI Agent implementations
│   │   ├── pm_agent/          # Project Manager Agent
│   │   ├── dev_agent/         # Development Agent
│   │   ├── security_agent/    # Security Agent (disabled)
│   │   └── devops_agent/      # DevOps Agent (disabled)
│   ├── tools/                 # Utility tools
│   │   ├── file_ops.py        # File operations
│   │   └── ui_file_watcher.py # UI file monitoring
│   ├── utils/                 # Helper utilities
│   ├── requirements.txt       # Python dependencies
│   ├── start_server.sh        # Backend startup script
│   └── todo-ui/               # Todo Management Interface (moved here)
│       ├── src/
│       │   ├── App.tsx        # Main todo application
│       │   ├── App.css        # Styling
│       │   └── main.tsx
│       └── package.json
├── frontend/                  # Voice Interface
│   ├── src/
│   │   ├── components/
│   │   │   └── VoiceInterface.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
```

## 🔄 Development Workflow

### Adding New Features

1. **Voice Commands**: Modify `VoiceInterface.tsx`
2. **Agent Logic**: Update agent files in `orchestrator/agents/`
3. **API Endpoints**: Add routes in `orchestrator/core/main.py`
4. **UI Components**: Enhance `todo-ui/src/App.tsx`

### Testing Individual Services

**Backend API:**
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test WebSocket (requires wscat: npm install -g wscat)
wscat -c ws://localhost:8000/ws

# Test pending approvals
curl http://localhost:8000/pending-approvals
```

**Frontend Services:**
```bash
# Check if services are responding
curl -I http://localhost:5173  # Voice Interface
curl -I http://localhost:5174  # Todo UI
```

## 📝 API Reference

### WebSocket Endpoints

- **`/ws`**: Main WebSocket connection for voice commands

### REST Endpoints

- **`GET /health`**: Service health check
- **`GET /pending-approvals`**: List pending task approvals
- **`GET /tasks`**: Get manual todos
- **`GET /admin-workflows`**: Get admin workflows
- **`POST /todos`**: Create manual todo
- **`PUT /todos/{id}`**: Update todo
- **`DELETE /todos/{id}`**: Delete todo

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review browser console for errors
3. Check individual service logs in terminal windows
4. Ensure all dependencies are installed correctly

---

**Happy Voice Coding! 🎤✨**

*Individual service control gives you the power to debug, restart, and monitor each component independently.*