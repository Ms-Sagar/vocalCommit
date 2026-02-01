#!/usr/bin/env python3
"""
VocalCommit Production Setup Script

This script sets up VocalCommit for production use with GitHub integration.
It handles:
1. Cloning the separate TODO-UI repository
2. Installing dependencies
3. Configuring environment variables
4. Verifying GitHub access
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(command, cwd=None, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {command}")
        print(f"Error: {e.stderr}")
        return e

def check_prerequisites():
    """Check if required tools are installed."""
    print("🔍 Checking prerequisites...")
    
    # Check Python
    try:
        result = run_command("python3 --version")
        print(f"✅ Python: {result.stdout.strip()}")
    except:
        print("❌ Python 3 not found. Please install Python 3.8+")
        return False
    
    # Check Node.js
    try:
        result = run_command("node --version")
        print(f"✅ Node.js: {result.stdout.strip()}")
    except:
        print("❌ Node.js not found. Please install Node.js 16+")
        return False
    
    # Check npm
    try:
        result = run_command("npm --version")
        print(f"✅ npm: {result.stdout.strip()}")
    except:
        print("❌ npm not found. Please install npm")
        return False
    
    # Check Git
    try:
        result = run_command("git --version")
        print(f"✅ Git: {result.stdout.strip()}")
    except:
        print("❌ Git not found. Please install Git")
        return False
    
    return True

def setup_environment():
    """Set up environment variables."""
    print("\n🔧 Setting up environment configuration...")
    
    env_file = Path("vocalCommit/orchestrator/.env")
    
    if env_file.exists():
        print(f"✅ Environment file exists: {env_file}")
        with open(env_file, 'r') as f:
            content = f.read()
            
        # Check for required variables
        required_vars = ['GITHUB_TOKEN', 'TODO_UI_REPO_URL']
        missing_vars = []
        
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
            print("Please update your .env file with the required GitHub configuration.")
            return False
        else:
            print("✅ All required environment variables are configured")
            return True
    else:
        print(f"❌ Environment file not found: {env_file}")
        print("Please create the .env file with GitHub configuration.")
        return False

def verify_github_access():
    """Verify GitHub token and repository access."""
    print("\n🔐 Verifying GitHub access...")
    
    # Read environment variables
    env_file = Path("vocalCommit/orchestrator/.env")
    if not env_file.exists():
        print("❌ Environment file not found")
        return False
    
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                env_vars[key] = value
    
    github_token = env_vars.get('GITHUB_TOKEN')
    repo_url = env_vars.get('TODO_UI_REPO_URL', 'https://github.com/Ms-Sagar/TODO-UI.git')
    
    if not github_token:
        print("❌ GITHUB_TOKEN not found in environment")
        return False
    
    # Extract owner/repo from URL
    if repo_url.endswith('.git'):
        repo_path = repo_url[:-4].split('github.com/')[-1]
    else:
        repo_path = repo_url.split('github.com/')[-1]
    
    # Test GitHub API access
    try:
        import requests
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Test user access
        response = requests.get("https://api.github.com/user", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ GitHub authentication successful for user: {user_data.get('login')}")
        else:
            print(f"❌ GitHub authentication failed: {response.status_code}")
            return False
        
        # Test repository access
        response = requests.get(f"https://api.github.com/repos/{repo_path}", headers=headers)
        if response.status_code == 200:
            repo_data = response.json()
            print(f"✅ Repository access verified: {repo_data.get('full_name')}")
        else:
            print(f"❌ Repository access failed: {response.status_code}")
            print(f"Please check repository URL and token permissions")
            return False
        
        return True
        
    except ImportError:
        print("⚠️  requests library not installed, skipping GitHub verification")
        return True
    except Exception as e:
        print(f"❌ GitHub verification failed: {str(e)}")
        return False

def clone_todo_ui_repo():
    """Clone the TODO-UI repository."""
    print("\n📦 Setting up TODO-UI repository...")
    
    # Read environment variables
    env_file = Path("vocalCommit/orchestrator/.env")
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                env_vars[key] = value
    
    github_token = env_vars.get('GITHUB_TOKEN')
    repo_url = env_vars.get('TODO_UI_REPO_URL', 'https://github.com/Ms-Sagar/TODO-UI.git')
    local_path = env_vars.get('TODO_UI_LOCAL_PATH', 'todo-ui')
    
    # Check if repository already exists
    if Path(local_path).exists():
        if (Path(local_path) / ".git").exists():
            print(f"✅ TODO-UI repository already exists at: {local_path}")
            
            # Pull latest changes
            print("🔄 Pulling latest changes...")
            result = run_command("git pull origin main", cwd=local_path, check=False)
            if result.returncode != 0:
                # Try master branch
                result = run_command("git pull origin master", cwd=local_path, check=False)
            
            if result.returncode == 0:
                print("✅ Repository updated successfully")
            else:
                print("⚠️  Failed to pull latest changes, but repository exists")
            
            return True
        else:
            print(f"❌ Directory {local_path} exists but is not a git repository")
            return False
    
    # Clone the repository
    print(f"📥 Cloning TODO-UI repository to: {local_path}")
    
    # Create authenticated URL
    auth_url = repo_url.replace("https://", f"https://{github_token}@")
    
    result = run_command(f"git clone {auth_url} {local_path}", check=False)
    
    if result.returncode == 0:
        print("✅ TODO-UI repository cloned successfully")
        
        # Install dependencies
        print("📦 Installing TODO-UI dependencies...")
        package_json = Path(local_path) / "package.json"
        
        if package_json.exists():
            result = run_command("npm install", cwd=local_path)
            if result.returncode == 0:
                print("✅ TODO-UI dependencies installed")
            else:
                print("⚠️  Failed to install TODO-UI dependencies")
        else:
            print("⚠️  package.json not found in TODO-UI repository")
        
        return True
    else:
        print(f"❌ Failed to clone repository: {result.stderr}")
        return False

def install_dependencies():
    """Install Python and Node.js dependencies."""
    print("\n📦 Installing dependencies...")
    
    # Install Python dependencies
    print("🐍 Installing Python dependencies...")
    result = run_command("pip3 install -r requirements.txt", cwd="vocalCommit/orchestrator")
    if result.returncode == 0:
        print("✅ Python dependencies installed")
    else:
        print("❌ Failed to install Python dependencies")
        return False
    
    # Install frontend dependencies
    print("🌐 Installing frontend dependencies...")
    result = run_command("npm install", cwd="vocalCommit/frontend")
    if result.returncode == 0:
        print("✅ Frontend dependencies installed")
    else:
        print("❌ Failed to install frontend dependencies")
        return False
    
    # Install local todo-ui dependencies (fallback)
    todo_ui_local = Path("vocalCommit/orchestrator/todo-ui")
    if todo_ui_local.exists():
        print("📱 Installing local todo-ui dependencies...")
        result = run_command("npm install", cwd=str(todo_ui_local))
        if result.returncode == 0:
            print("✅ Local todo-ui dependencies installed")
        else:
            print("⚠️  Failed to install local todo-ui dependencies")
    
    return True

def create_startup_script():
    """Create a startup script for production."""
    print("\n📝 Creating startup script...")
    
    startup_script = """#!/bin/bash
# VocalCommit Production Startup Script

echo "🚀 Starting VocalCommit Production Services..."

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  Port $1 is already in use"
        return 1
    else
        return 0
    fi
}

# Check ports
echo "🔍 Checking ports..."
check_port 8000 || exit 1
check_port 5173 || exit 1
check_port 5174 || exit 1

echo "✅ All ports available"

# Start services in background
echo "🔧 Starting orchestrator..."
cd vocalCommit/orchestrator
python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 &
ORCHESTRATOR_PID=$!

echo "🎤 Starting voice interface..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "📱 Starting todo-ui..."
if [ -d "../../todo-ui" ]; then
    cd ../../todo-ui
    echo "Using production todo-ui repository"
else
    cd ../orchestrator/todo-ui
    echo "Using local todo-ui (fallback)"
fi
npm run dev &
TODOUI_PID=$!

echo "✅ All services started!"
echo "📊 Service URLs:"
echo "  - Voice Interface: http://localhost:5173"
echo "  - Todo UI: http://localhost:5174"
echo "  - API Health: http://localhost:8000/health"
echo "  - GitHub Status: http://localhost:8000/github-status"

echo ""
echo "🛑 To stop all services, press Ctrl+C"

# Wait for interrupt
trap 'echo "🛑 Stopping services..."; kill $ORCHESTRATOR_PID $FRONTEND_PID $TODOUI_PID; exit' INT
wait
"""
    
    with open("start_production.sh", "w") as f:
        f.write(startup_script)
    
    # Make executable
    os.chmod("start_production.sh", 0o755)
    
    print("✅ Startup script created: start_production.sh")

def main():
    """Main setup function."""
    print("🎤 VocalCommit Production Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("vocalCommit").exists():
        print("❌ Please run this script from the VocalCommit root directory")
        sys.exit(1)
    
    # Run setup steps
    steps = [
        ("Prerequisites", check_prerequisites),
        ("Environment", setup_environment),
        ("GitHub Access", verify_github_access),
        ("Dependencies", install_dependencies),
        ("TODO-UI Repository", clone_todo_ui_repo),
        ("Startup Script", create_startup_script)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        if not step_func():
            print(f"\n❌ Setup failed at step: {step_name}")
            sys.exit(1)
    
    print("\n" + "="*50)
    print("🎉 VocalCommit Production Setup Complete!")
    print("\n📋 Next Steps:")
    print("1. Review your .env file configuration")
    print("2. Start services: ./start_production.sh")
    print("3. Access Voice Interface: http://localhost:5173")
    print("4. Access Todo UI: http://localhost:5174")
    print("5. Check GitHub status: http://localhost:8000/github-status")
    print("\n🚀 Happy Voice Coding with Production Deployment!")

if __name__ == "__main__":
    main()