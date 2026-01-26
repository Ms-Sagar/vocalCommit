#!/usr/bin/env python3
"""
VocalCommit Setup Script
Automated setup and dependency installation for VocalCommit
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
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
        sys.exit(1)
    
    # Check Node.js
    try:
        result = run_command("node --version")
        print(f"✅ Node.js: {result.stdout.strip()}")
    except:
        print("❌ Node.js not found. Please install Node.js 16+")
        sys.exit(1)
    
    # Check npm
    try:
        result = run_command("npm --version")
        print(f"✅ npm: {result.stdout.strip()}")
    except:
        print("❌ npm not found. Please install npm")
        sys.exit(1)
    
    print("✅ All prerequisites satisfied!\n")

def setup_backend():
    """Setup the backend orchestrator."""
    print("🐍 Setting up backend orchestrator...")
    
    orchestrator_path = Path("vocalCommit/orchestrator")
    if not orchestrator_path.exists():
        print("❌ Orchestrator directory not found")
        sys.exit(1)
    
    # Install Python dependencies
    print("Installing Python dependencies...")
    run_command("python3 -m pip install -r requirements.txt", cwd=orchestrator_path)
    
    # Make start script executable
    start_script = orchestrator_path / "start_server.sh"
    if start_script.exists():
        run_command(f"chmod +x {start_script}")
        print("✅ Made start_server.sh executable")
    
    print("✅ Backend setup complete!\n")

def setup_frontend():
    """Setup the frontend voice interface."""
    print("⚛️ Setting up frontend voice interface...")
    
    frontend_path = Path("vocalCommit/frontend")
    if not frontend_path.exists():
        print("❌ Frontend directory not found")
        sys.exit(1)
    
    # Install npm dependencies
    print("Installing frontend dependencies...")
    run_command("npm install", cwd=frontend_path)
    
    print("✅ Frontend setup complete!\n")

def setup_todo_ui():
    """Setup the todo UI."""
    print("📋 Setting up todo UI...")
    
    todo_ui_path = Path("vocalCommit/orchestrator/todo-ui")
    if not todo_ui_path.exists():
        print("❌ Todo UI directory not found")
        sys.exit(1)
    
    # Install npm dependencies
    print("Installing todo UI dependencies...")
    run_command("npm install", cwd=todo_ui_path)
    
    # Install uuid if not present
    print("Ensuring uuid dependency...")
    run_command("npm install uuid @types/uuid", cwd=todo_ui_path, check=False)
    
    print("✅ Todo UI setup complete!\n")

def create_env_file():
    """Create a sample .env file if it doesn't exist."""
    env_path = Path("vocalCommit/orchestrator/.env")
    
    if not env_path.exists():
        print("📝 Creating sample .env file...")
        env_content = """# VocalCommit Environment Configuration

# Google AI API Key (optional - for enhanced AI features)
# Get your API key from: https://makersuite.google.com/app/apikey
# GOOGLE_API_KEY=your_api_key_here

# Development Settings
DEBUG=true
LOG_LEVEL=INFO

# Server Configuration
HOST=0.0.0.0
PORT=8000
"""
        env_path.write_text(env_content)
        print("✅ Created sample .env file")
        print("💡 Edit vocalCommit/orchestrator/.env to add your API keys\n")

def print_startup_instructions():
    """Print instructions for starting the services individually."""
    print("🚀 Setup Complete! Here's how to start VocalCommit:\n")
    
    print("Individual Service Startup (Recommended):")
    print("=" * 50)
    print()
    print("Terminal 1 - Backend Orchestrator:")
    print("  cd vocalCommit/orchestrator")
    print("  python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload")
    print("  # OR use: ./start_server.sh")
    print()
    print("Terminal 2 - Voice Interface:")
    print("  cd vocalCommit/frontend")
    print("  npm run dev")
    print()
    print("Terminal 3 - Todo UI (now inside orchestrator):")
    print("  cd vocalCommit/orchestrator/todo-ui")
    print("  npm run dev")
    print()
    
    print("💡 Benefits of Individual Startup:")
    print("  ✅ Better log visibility per service")
    print("  ✅ Independent restart capability")
    print("  ✅ Easier debugging and development")
    print("  ✅ Individual process control")
    print()
    
    print("🌐 Access URLs:")
    print("  Voice Interface: http://localhost:5173")
    print("  Todo UI:         http://localhost:5174")
    print("  API Health:      http://localhost:8000/health")
    print()
    
    print("🔧 Service Management:")
    print("  Stop any service: Ctrl+C in its terminal")
    print("  Restart: Re-run the command in the same terminal")
    print("  Logs: Visible in each service's terminal")
    print()
    
    print("📖 For more details, see vocalCommit/README.md")
    print("🎤 Happy Voice Coding!")

def main():
    """Main setup function."""
    print("🎤 VocalCommit Setup Script")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("vocalCommit").exists():
        print("❌ vocalCommit directory not found.")
        print("Please run this script from the project root directory.")
        sys.exit(1)
    
    try:
        check_prerequisites()
        setup_backend()
        setup_frontend()
        setup_todo_ui()
        create_env_file()
        print_startup_instructions()
        
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()