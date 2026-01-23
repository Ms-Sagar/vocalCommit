# VocalCommit - Voice Orchestrated SDLC

A multi-agent system that orchestrates software development lifecycle through voice commands.

## Architecture

- **Orchestrator**: Central FastAPI backend that coordinates all agents
- **PM Agent**: Project management and task planning
- **Dev Agent**: Code generation and development
- **Security Agent**: Code security scanning and validation
- **DevOps Agent**: Deployment and operations management

## Quick Start

1. Install backend dependencies:
   ```bash
   cd orchestrator
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY
   ```

3. Run the orchestrator:
   ```bash
   cd orchestrator
   python -m uvicorn core.main:app --reload
   ```

4. Set up frontend:
   ```bash
   cd frontend
   npm create vite@latest .
   ```

## WebSocket Endpoint

Connect to `ws://localhost:8000/ws` for voice command processing.
