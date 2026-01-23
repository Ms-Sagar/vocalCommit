#!/usr/bin/env python3
"""
VocalCommit Setup Script
Creates the complete folder structure and boilerplate code for the Voice-Orchestrated SDLC system.
"""

import os
from pathlib import Path


def create_directory(path):
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {path}")


def write_file(path, content):
    """Write content to file."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created file: {path}")


def setup_vocalcommit():
    """Set up the complete VocalCommit project structure."""
    
    # Root directory
    root_dir = "./vocalCommit"
    create_directory(root_dir)
    
    # Root README.md
    readme_content = """# VocalCommit - Voice Orchestrated SDLC

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
"""
    write_file(f"{root_dir}/README.md", readme_content)
    
    # .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# Environment Variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
"""
    write_file(f"{root_dir}/.gitignore", gitignore_content)
    
    # Backend/Orchestrator structure
    orchestrator_dir = f"{root_dir}/orchestrator"
    create_directory(orchestrator_dir)
    
    # Requirements.txt
    requirements_content = """fastapi==0.104.1
uvicorn==0.24.0
google-generativeai==0.3.2
websockets==12.0
python-dotenv==1.0.0
pydantic==2.5.0
"""
    write_file(f"{orchestrator_dir}/requirements.txt", requirements_content)
    
    # .env template
    env_content = """# VocalCommit Environment Configuration
GEMINI_API_KEY=
"""
    write_file(f"{orchestrator_dir}/.env", env_content)
    
    # Core directory
    core_dir = f"{orchestrator_dir}/core"
    create_directory(core_dir)
    
    # Core __init__.py
    write_file(f"{core_dir}/__init__.py", "")
    
    # main.py (FastAPI entry point)
    main_content = """from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="VocalCommit Orchestrator", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "VocalCommit Orchestrator is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "vocalcommit-orchestrator"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive voice command/transcript
            data = await websocket.receive_text()
            logger.info(f"Received: {data}")
            
            try:
                message = json.loads(data)
                command_type = message.get("type", "unknown")
                transcript = message.get("transcript", "")
                
                # Process command through agent orchestration
                response = await process_voice_command(command_type, transcript)
                
                await manager.send_personal_message(
                    json.dumps(response), 
                    websocket
                )
                
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"error": "Invalid JSON format"}),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def process_voice_command(command_type: str, transcript: str) -> dict:
    \"\"\"Process voice commands through the agent system.\"\"\"
    # TODO: Implement agent orchestration logic
    return {
        "status": "processed",
        "command_type": command_type,
        "transcript": transcript,
        "response": "Command received and queued for processing"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
    write_file(f"{core_dir}/main.py", main_content)
    
    # config.py
    config_content = """from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    gemini_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()
"""
    write_file(f"{core_dir}/config.py", config_content)
    
    # Agents directory
    agents_dir = f"{orchestrator_dir}/agents"
    create_directory(agents_dir)
    write_file(f"{agents_dir}/__init__.py", "")
    
    # PM Agent
    pm_agent_dir = f"{agents_dir}/pm_agent"
    create_directory(pm_agent_dir)
    write_file(f"{pm_agent_dir}/__init__.py", "")
    
    pm_logic_content = """from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class PMAgent:
    \"\"\"Project Management Agent - Handles task planning and project coordination.\"\"\"
    
    def __init__(self):
        self.name = "PM Agent"
        self.role = "Project Manager"
    
    async def plan_task(self, transcript: str) -> Dict[str, Any]:
        \"\"\"
        Analyze voice transcript and create a structured task plan.
        
        Args:
            transcript: Voice command transcript
            
        Returns:
            Dict containing task breakdown, priorities, and dependencies
        \"\"\"
        logger.info(f"PM Agent processing transcript: {transcript}")
        
        # TODO: Implement AI-powered task planning logic
        # This should integrate with Gemini API for intelligent planning
        
        plan = {
            "task_id": f"task_{hash(transcript) % 10000}",
            "description": transcript,
            "breakdown": [
                "Analyze requirements",
                "Design solution architecture", 
                "Implement core functionality",
                "Add security measures",
                "Deploy and test"
            ],
            "priority": "medium",
            "estimated_effort": "2-4 hours",
            "dependencies": [],
            "assigned_agents": ["dev_agent", "security_agent", "devops_agent"]
        }
        
        return {
            "status": "success",
            "agent": self.name,
            "plan": plan
        }
    
    async def update_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        \"\"\"Update task status and notify stakeholders.\"\"\"
        logger.info(f"Updating task {task_id} status to {status}")
        
        return {
            "task_id": task_id,
            "status": status,
            "updated_by": self.name
        }
"""
    write_file(f"{pm_agent_dir}/pm_logic.py", pm_logic_content)
    
    # Dev Agent
    dev_agent_dir = f"{agents_dir}/dev_agent"
    create_directory(dev_agent_dir)
    write_file(f"{dev_agent_dir}/__init__.py", "")
    
    dev_logic_content = """from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DevAgent:
    \"\"\"Development Agent - Handles code generation and implementation.\"\"\"
    
    def __init__(self):
        self.name = "Dev Agent"
        self.role = "Software Developer"
    
    async def write_code(self, plan: Dict[str, Any], thought_signature: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"
        Generate code based on task plan and context from other agents.
        
        Args:
            plan: Task plan from PM Agent
            thought_signature: Context and insights from previous agent interactions
            
        Returns:
            Dict containing generated code, file structure, and implementation notes
        \"\"\"
        logger.info(f"Dev Agent generating code for plan: {plan.get('task_id', 'unknown')}")
        
        # TODO: Implement AI-powered code generation
        # This should integrate with Gemini API for intelligent code creation
        
        code_output = {
            "files": {
                "main.py": "# Generated code placeholder\\nprint('Hello VocalCommit')",
                "utils.py": "# Utility functions\\ndef helper_function():\\n    pass"
            },
            "structure": {
                "directories": ["src", "tests", "docs"],
                "entry_point": "main.py"
            },
            "dependencies": ["requests", "pydantic"],
            "implementation_notes": [
                "Used modular architecture for maintainability",
                "Added error handling for robustness",
                "Included type hints for better code quality"
            ]
        }
        
        return {
            "status": "success",
            "agent": self.name,
            "task_id": plan.get("task_id"),
            "code_output": code_output,
            "thought_signature": thought_signature
        }
    
    async def refactor_code(self, existing_code: str, requirements: str) -> Dict[str, Any]:
        \"\"\"Refactor existing code based on new requirements.\"\"\"
        logger.info("Dev Agent refactoring code")
        
        return {
            "status": "success",
            "agent": self.name,
            "refactored_code": existing_code,  # TODO: Implement actual refactoring
            "changes_made": ["Improved error handling", "Added documentation"]
        }
"""
    write_file(f"{dev_agent_dir}/dev_logic.py", dev_logic_content)
    
    # Security Agent
    security_agent_dir = f"{agents_dir}/security_agent"
    create_directory(security_agent_dir)
    write_file(f"{security_agent_dir}/__init__.py", "")
    
    sec_logic_content = """from typing import Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)

class SecurityAgent:
    \"\"\"Security Agent - Handles code security scanning and validation.\"\"\"
    
    def __init__(self):
        self.name = "Security Agent"
        self.role = "Security Specialist"
        self.vulnerability_patterns = [
            r"eval\\(",
            r"exec\\(",
            r"__import__",
            r"input\\(",
            r"raw_input\\(",
        ]
    
    async def scan_code(self, code_content: str) -> Dict[str, Any]:
        \"\"\"
        Scan code for security vulnerabilities and best practices.
        
        Args:
            code_content: Source code to analyze
            
        Returns:
            Dict containing security findings, risk levels, and recommendations
        \"\"\"
        logger.info("Security Agent scanning code for vulnerabilities")
        
        findings = []
        risk_level = "low"
        
        # Basic pattern matching for common vulnerabilities
        for pattern in self.vulnerability_patterns:
            matches = re.findall(pattern, code_content, re.IGNORECASE)
            if matches:
                findings.append({
                    "type": "potential_vulnerability",
                    "pattern": pattern,
                    "matches": len(matches),
                    "severity": "high",
                    "description": f"Potentially dangerous function usage: {pattern}"
                })
                risk_level = "high"
        
        # Check for hardcoded secrets (basic patterns)
        secret_patterns = [
            r"password\\s*=\\s*['\"][^'\"]+['\"]",
            r"api_key\\s*=\\s*['\"][^'\"]+['\"]",
            r"secret\\s*=\\s*['\"][^'\"]+['\"]"
        ]
        
        for pattern in secret_patterns:
            matches = re.findall(pattern, code_content, re.IGNORECASE)
            if matches:
                findings.append({
                    "type": "hardcoded_secret",
                    "severity": "medium",
                    "description": "Potential hardcoded secret detected"
                })
                if risk_level == "low":
                    risk_level = "medium"
        
        recommendations = [
            "Use environment variables for sensitive data",
            "Implement input validation and sanitization",
            "Add proper error handling",
            "Use parameterized queries for database operations",
            "Implement proper authentication and authorization"
        ]
        
        return {
            "status": "success",
            "agent": self.name,
            "scan_results": {
                "risk_level": risk_level,
                "findings": findings,
                "recommendations": recommendations,
                "scanned_lines": len(code_content.split('\\n')),
                "timestamp": "2024-01-01T00:00:00Z"  # TODO: Use actual timestamp
            }
        }
    
    async def validate_dependencies(self, dependencies: List[str]) -> Dict[str, Any]:
        \"\"\"Validate project dependencies for known vulnerabilities.\"\"\"
        logger.info(f"Security Agent validating {len(dependencies)} dependencies")
        
        # TODO: Implement actual dependency vulnerability checking
        return {
            "status": "success",
            "agent": self.name,
            "dependency_report": {
                "total_dependencies": len(dependencies),
                "vulnerable_packages": [],
                "recommendations": ["Keep dependencies updated", "Use dependency scanning tools"]
            }
        }
"""
    write_file(f"{security_agent_dir}/sec_logic.py", sec_logic_content)
    
    # DevOps Agent
    devops_agent_dir = f"{agents_dir}/devops_agent"
    create_directory(devops_agent_dir)
    write_file(f"{devops_agent_dir}/__init__.py", "")
    
    ops_logic_content = """from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DevOpsAgent:
    \"\"\"DevOps Agent - Handles deployment, infrastructure, and operations.\"\"\"
    
    def __init__(self):
        self.name = "DevOps Agent"
        self.role = "DevOps Engineer"
    
    async def create_deployment_config(self, code_structure: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"
        Create deployment configuration based on code structure.
        
        Args:
            code_structure: Code structure from Dev Agent
            
        Returns:
            Dict containing deployment configs, infrastructure setup, and CI/CD pipeline
        \"\"\"
        logger.info("DevOps Agent creating deployment configuration")
        
        # TODO: Implement intelligent deployment config generation
        
        deployment_config = {
            "docker": {
                "dockerfile": self._generate_dockerfile(code_structure),
                "docker_compose": self._generate_docker_compose()
            },
            "kubernetes": {
                "deployment.yaml": self._generate_k8s_deployment(),
                "service.yaml": self._generate_k8s_service()
            },
            "ci_cd": {
                "github_actions": self._generate_github_actions(),
                "pipeline_stages": ["build", "test", "security-scan", "deploy"]
            },
            "infrastructure": {
                "cloud_provider": "aws",
                "services": ["ec2", "rds", "s3", "cloudfront"],
                "estimated_cost": "$50-100/month"
            }
        }
        
        return {
            "status": "success",
            "agent": self.name,
            "deployment_config": deployment_config
        }
    
    def _generate_dockerfile(self, code_structure: Dict[str, Any]) -> str:
        \"\"\"Generate Dockerfile based on code structure.\"\"\"
        return '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
    
    def _generate_docker_compose(self) -> str:
        \"\"\"Generate docker-compose.yml.\"\"\"
        return '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: vocalcommit
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
'''
    
    def _generate_k8s_deployment(self) -> str:
        \"\"\"Generate Kubernetes deployment.\"\"\"
        return '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: vocalcommit-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vocalcommit
  template:
    metadata:
      labels:
        app: vocalcommit
    spec:
      containers:
      - name: app
        image: vocalcommit:latest
        ports:
        - containerPort: 8000
'''
    
    def _generate_k8s_service(self) -> str:
        \"\"\"Generate Kubernetes service.\"\"\"
        return '''apiVersion: v1
kind: Service
metadata:
  name: vocalcommit-service
spec:
  selector:
    app: vocalcommit
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
'''
    
    def _generate_github_actions(self) -> str:
        \"\"\"Generate GitHub Actions workflow.\"\"\"
        return '''name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Run tests
      run: |
        pytest
    - name: Security scan
      run: |
        bandit -r .
'''

    async def monitor_deployment(self, deployment_id: str) -> Dict[str, Any]:
        \"\"\"Monitor deployment health and performance.\"\"\"
        logger.info(f"DevOps Agent monitoring deployment: {deployment_id}")
        
        return {
            "status": "success",
            "agent": self.name,
            "monitoring_data": {
                "deployment_id": deployment_id,
                "health_status": "healthy",
                "uptime": "99.9%",
                "response_time": "150ms",
                "error_rate": "0.1%"
            }
        }
"""
    write_file(f"{devops_agent_dir}/ops_logic.py", ops_logic_content)
    
    # Tools directory
    tools_dir = f"{orchestrator_dir}/tools"
    create_directory(tools_dir)
    write_file(f"{tools_dir}/__init__.py", "")
    
    # file_ops.py
    file_ops_content = """import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def write_to_frontend(file_path: str, content: str, frontend_base: str = "../frontend") -> Dict[str, Any]:
    \"\"\"
    Safely write files to the frontend folder.
    
    Args:
        file_path: Relative path within frontend folder
        content: File content to write
        frontend_base: Base path to frontend folder
        
    Returns:
        Dict containing operation status and details
    \"\"\"
    try:
        # Resolve and validate the target path
        frontend_path = Path(frontend_base).resolve()
        target_path = (frontend_path / file_path).resolve()
        
        # Security check: ensure target is within frontend directory
        if not str(target_path).startswith(str(frontend_path)):
            raise ValueError("Invalid file path: outside frontend directory")
        
        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Successfully wrote file: {target_path}")
        
        return {
            "status": "success",
            "file_path": str(target_path),
            "size_bytes": len(content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        }

def read_from_frontend(file_path: str, frontend_base: str = "../frontend") -> Dict[str, Any]:
    \"\"\"
    Safely read files from the frontend folder.
    
    Args:
        file_path: Relative path within frontend folder
        frontend_base: Base path to frontend folder
        
    Returns:
        Dict containing file content and metadata
    \"\"\"
    try:
        frontend_path = Path(frontend_base).resolve()
        target_path = (frontend_path / file_path).resolve()
        
        # Security check
        if not str(target_path).startswith(str(frontend_path)):
            raise ValueError("Invalid file path: outside frontend directory")
        
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "status": "success",
            "content": content,
            "file_path": str(target_path),
            "size_bytes": len(content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        }

def create_project_structure(base_path: str, structure: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"
    Create a project structure based on a nested dictionary.
    
    Args:
        base_path: Base directory path
        structure: Nested dict representing folder/file structure
        
    Returns:
        Dict containing creation results
    \"\"\"
    created_items = []
    errors = []
    
    try:
        base = Path(base_path)
        base.mkdir(parents=True, exist_ok=True)
        
        def create_recursive(current_path: Path, items: Dict[str, Any]):
            for name, content in items.items():
                item_path = current_path / name
                
                if isinstance(content, dict):
                    # It's a directory
                    item_path.mkdir(exist_ok=True)
                    created_items.append(f"DIR: {item_path}")
                    create_recursive(item_path, content)
                else:
                    # It's a file
                    with open(item_path, 'w', encoding='utf-8') as f:
                        f.write(str(content))
                    created_items.append(f"FILE: {item_path}")
        
        create_recursive(base, structure)
        
        return {
            "status": "success",
            "created_items": created_items,
            "total_items": len(created_items)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "created_items": created_items,
            "errors": errors
        }
"""
    write_file(f"{tools_dir}/file_ops.py", file_ops_content)
    
    # Utils directory
    utils_dir = f"{orchestrator_dir}/utils"
    create_directory(utils_dir)
    write_file(f"{utils_dir}/__init__.py", "")
    
    # thought_signatures.py
    thought_signatures_content = """from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class ThoughtSignature:
    \"\"\"Represents context and insights passed between agents.\"\"\"
    
    def __init__(self, agent_name: str, task_id: str, content: Dict[str, Any]):
        self.agent_name = agent_name
        self.task_id = task_id
        self.content = content
        self.timestamp = datetime.utcnow().isoformat()
        self.signature_id = f"{agent_name}_{task_id}_{hash(str(content)) % 10000}"
    
    def to_dict(self) -> Dict[str, Any]:
        \"\"\"Convert thought signature to dictionary.\"\"\"
        return {
            "signature_id": self.signature_id,
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        \"\"\"Convert thought signature to JSON string.\"\"\"
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThoughtSignature':
        \"\"\"Create ThoughtSignature from dictionary.\"\"\"
        signature = cls(
            agent_name=data["agent_name"],
            task_id=data["task_id"],
            content=data["content"]
        )
        signature.timestamp = data.get("timestamp", signature.timestamp)
        signature.signature_id = data.get("signature_id", signature.signature_id)
        return signature

class ThoughtChain:
    \"\"\"Manages a chain of thought signatures for a task.\"\"\"
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.signatures: List[ThoughtSignature] = []
        self.created_at = datetime.utcnow().isoformat()
    
    def add_signature(self, signature: ThoughtSignature):
        \"\"\"Add a thought signature to the chain.\"\"\"
        if signature.task_id != self.task_id:
            raise ValueError(f"Signature task_id {signature.task_id} doesn't match chain task_id {self.task_id}")
        
        self.signatures.append(signature)
        logger.info(f"Added signature from {signature.agent_name} to chain {self.task_id}")
    
    def get_context_for_agent(self, agent_name: str) -> Dict[str, Any]:
        \"\"\"Get relevant context for a specific agent.\"\"\"
        context = {
            "task_id": self.task_id,
            "requesting_agent": agent_name,
            "previous_work": [],
            "key_insights": [],
            "dependencies": []
        }
        
        for signature in self.signatures:
            if signature.agent_name != agent_name:
                context["previous_work"].append({
                    "agent": signature.agent_name,
                    "timestamp": signature.timestamp,
                    "summary": signature.content.get("summary", "No summary available"),
                    "outputs": signature.content.get("outputs", {}),
                    "recommendations": signature.content.get("recommendations", [])
                })
        
        return context
    
    def get_latest_signature(self) -> Optional[ThoughtSignature]:
        \"\"\"Get the most recent thought signature.\"\"\"
        return self.signatures[-1] if self.signatures else None
    
    def get_signature_by_agent(self, agent_name: str) -> Optional[ThoughtSignature]:
        \"\"\"Get the most recent signature from a specific agent.\"\"\"
        for signature in reversed(self.signatures):
            if signature.agent_name == agent_name:
                return signature
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        \"\"\"Convert thought chain to dictionary.\"\"\"
        return {
            "task_id": self.task_id,
            "created_at": self.created_at,
            "signatures": [sig.to_dict() for sig in self.signatures],
            "signature_count": len(self.signatures)
        }

class ThoughtManager:
    \"\"\"Global manager for thought signatures and chains.\"\"\"
    
    def __init__(self):
        self.chains: Dict[str, ThoughtChain] = {}
    
    def create_chain(self, task_id: str) -> ThoughtChain:
        \"\"\"Create a new thought chain for a task.\"\"\"
        if task_id in self.chains:
            logger.warning(f"Chain {task_id} already exists, returning existing chain")
            return self.chains[task_id]
        
        chain = ThoughtChain(task_id)
        self.chains[task_id] = chain
        logger.info(f"Created new thought chain for task {task_id}")
        return chain
    
    def get_chain(self, task_id: str) -> Optional[ThoughtChain]:
        \"\"\"Get an existing thought chain.\"\"\"
        return self.chains.get(task_id)
    
    def add_thought(self, task_id: str, agent_name: str, content: Dict[str, Any]) -> ThoughtSignature:
        \"\"\"Add a thought signature to a task chain.\"\"\"
        chain = self.get_chain(task_id)
        if not chain:
            chain = self.create_chain(task_id)
        
        signature = ThoughtSignature(agent_name, task_id, content)
        chain.add_signature(signature)
        
        return signature
    
    def get_context_for_agent(self, task_id: str, agent_name: str) -> Dict[str, Any]:
        \"\"\"Get context for an agent working on a specific task.\"\"\"
        chain = self.get_chain(task_id)
        if not chain:
            return {
                "task_id": task_id,
                "requesting_agent": agent_name,
                "previous_work": [],
                "message": "No previous context available"
            }
        
        return chain.get_context_for_agent(agent_name)

# Global thought manager instance
thought_manager = ThoughtManager()

def create_thought_signature(agent_name: str, task_id: str, content: Dict[str, Any]) -> str:
    \"\"\"Convenience function to create and store a thought signature.\"\"\"
    signature = thought_manager.add_thought(task_id, agent_name, content)
    return signature.to_json()

def get_agent_context(task_id: str, agent_name: str) -> Dict[str, Any]:
    \"\"\"Convenience function to get context for an agent.\"\"\"
    return thought_manager.get_context_for_agent(task_id, agent_name)
"""
    write_file(f"{utils_dir}/thought_signatures.py", thought_signatures_content)
    
    # Frontend directory
    frontend_dir = f"{root_dir}/frontend"
    create_directory(frontend_dir)
    
    # Frontend README
    frontend_readme_content = """# VocalCommit Frontend

Run 'npm create vite@latest .' in this folder to initialize React.

## Setup Instructions

1. Initialize Vite React project:
   ```bash
   npm create vite@latest .
   ```

2. Select React and TypeScript when prompted

3. Install dependencies:
   ```bash
   npm install
   ```

4. Install additional dependencies for voice integration:
   ```bash
   npm install @types/web-speech-api socket.io-client
   ```

5. Start development server:
   ```bash
   npm run dev
   ```

## Integration with Backend

The frontend will connect to the VocalCommit orchestrator via WebSocket at `ws://localhost:8000/ws`.

Voice commands will be captured using the Web Speech API and sent to the backend for processing by the AI agents.
"""
    write_file(f"{frontend_dir}/README.md", frontend_readme_content)
    
    print("\\n" + "="*60)
    print("🎉 VocalCommit project structure created successfully!")
    print("="*60)
    print(f"\\nProject root: {root_dir}")
    print("\\nNext steps:")
    print("1. cd vocalCommit/orchestrator")
    print("2. pip install -r requirements.txt")
    print("3. Add your GEMINI_API_KEY to .env file")
    print("4. python -m uvicorn core.main:app --reload")
    print("5. cd ../frontend && npm create vite@latest .")
    print("\\nWebSocket endpoint: ws://localhost:8000/ws")
    print("="*60)

if __name__ == "__main__":
    setup_vocalcommit()