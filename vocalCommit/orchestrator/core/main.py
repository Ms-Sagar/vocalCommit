from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
from .config import settings

# Import agents
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.pm_agent.pm_logic import PMAgent
from agents.dev_agent.dev_logic import run_dev_agent, process_ui_editing_plan
from agents.security_agent.sec_logic import SecurityAgent
from agents.devops_agent.ops_logic import DevOpsAgent
from agents.testing_agent.test_logic import run_testing_agent
from utils.thought_signatures import thought_manager
from utils.theme_system_patterns import get_theme_system_knowledge
from tools.ui_file_watcher import create_ui_watcher
from tools.git_ops import git_ops
from tools.github_ops import github_ops

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

# Initialize agents (Security and DevOps disabled for now)
pm_agent = PMAgent()
# dev_agent = DevAgent()  # Now using run_dev_agent function directly
# security_agent = SecurityAgent()  # Disabled
# devops_agent = DevOpsAgent()      # Disabled

# Initialize UI file watcher
ui_watcher = None
try:
    ui_watcher = create_ui_watcher()
    if ui_watcher.watch_paths:  # Only start if we have paths to watch
        ui_watcher.add_callback(lambda event_type, file_path: 
            logger.info(f"UI file {event_type}: {os.path.basename(file_path)}"))
        ui_watcher.start_watching()
        logger.info(f"UI file watcher initialized and started, watching {len(ui_watcher.watch_paths)} paths")
    else:
        logger.warning("No valid paths found for UI file watcher")
except Exception as e:
    logger.warning(f"Could not initialize UI file watcher: {e}")
    logger.info("Continuing without file watcher - real-time UI editing will still work")

# Store pending approvals
pending_approvals = {}

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

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    if ui_watcher:
        ui_watcher.stop_watching()
        logger.info("UI file watcher stopped")

@app.get("/rate-limit-status")
async def get_rate_limit_status():
    """Get current Gemini API rate limiting status."""
    from tools.rate_limiter import get_gemini_api_status
    
    status = get_gemini_api_status()
    return {
        "rate_limit_status": status,
        "message": f"Remaining requests: {status['remaining_requests']}/5 per minute"
    }

@app.get("/api-key-status")
async def get_api_key_status():
    """Get Gemini API key status by testing it with the API."""
    from tools.rate_limiter import get_gemini_api_status
    import google.genai as genai
    
    logger.info("API key status requested")
    logger.info(f"Current settings.gemini_api_key: {settings.gemini_api_key[:8] if settings.gemini_api_key else 'None'}...")
    
    # Check if API key is configured
    if not settings.gemini_api_key:
        logger.info("No API key configured")
        return {
            "status": "missing",
            "configured": False,
            "message": "No Gemini API key configured. Please add your API key.",
            "quota_info": None
        }
    
    # Mask the API key for display (show first 8 and last 4 characters)
    key = settings.gemini_api_key
    if len(key) > 12:
        masked_key = f"{key[:8]}...{key[-4:]}"
    else:
        masked_key = f"{key[:4]}...{key[-2:]}"
    
    # Get rate limit status (local tracking)
    quota_info = get_gemini_api_status()
    
    # Test the API key by making a simple API call
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        
        # Try to list models - this will fail if key is invalid
        try:
            models = client.models.list()
            model_count = len(list(models)) if models else 0
            
            if model_count > 0:
                logger.info(f"API key is valid - found {model_count} models")
                logger.info(f"Returning masked key: {masked_key}")
                
                return {
                    "status": "active",
                    "configured": True,
                    "masked_key": masked_key,
                    "message": "API key is valid and working",
                    "quota_info": quota_info,
                    "models_available": model_count
                }
            else:
                logger.warning("API key validation returned no models")
                return {
                    "status": "invalid",
                    "configured": True,
                    "masked_key": masked_key,
                    "message": "API key is configured but returned no models",
                    "quota_info": quota_info
                }
        except Exception as list_error:
            # If listing models fails, try a simple generation to test the key
            logger.info(f"Model listing failed, trying simple generation: {list_error}")
            try:
                response = client.models.generate_content(
                    model='gemini-2.0-flash-exp',
                    contents='test'
                )
                if response:
                    logger.info("API key is valid - generation test passed")
                    return {
                        "status": "active",
                        "configured": True,
                        "masked_key": masked_key,
                        "message": "API key is valid and working",
                        "quota_info": quota_info
                    }
            except Exception as gen_error:
                logger.error(f"Generation test also failed: {gen_error}")
                raise list_error  # Raise the original error
            
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"API key validation failed: {e}")
        
        # Check for specific error types
        if "api key not valid" in error_msg or "invalid api key" in error_msg or "invalid_argument" in error_msg or "api_key_invalid" in error_msg:
            return {
                "status": "invalid",
                "configured": True,
                "masked_key": masked_key,
                "message": "API key is invalid. Please check your key.",
                "quota_info": quota_info,
                "error_details": str(e)
            }
        elif "quota" in error_msg or "resource_exhausted" in error_msg or "429" in error_msg:
            return {
                "status": "quota_exceeded",
                "configured": True,
                "masked_key": masked_key,
                "message": "API quota exceeded. Please wait or upgrade your plan.",
                "quota_info": quota_info,
                "error_details": str(e)
            }
        else:
            return {
                "status": "error",
                "configured": True,
                "masked_key": masked_key,
                "message": f"Error validating API key: {str(e)}",
                "quota_info": quota_info,
                "error_details": str(e)
            }

@app.post("/update-api-key")
async def update_api_key(request: dict):
    """
    Update the Gemini API key.
    
    Works in two modes:
    1. Local development: Updates .env file
    2. Production (Render): Updates in-memory only (requires restart with new env var)
    """
    import os
    from pathlib import Path
    
    new_key = request.get("api_key", "").strip()
    
    if not new_key:
        return {
            "status": "error",
            "message": "API key cannot be empty"
        }
    
    # Validate API key format (basic check)
    if len(new_key) < 20:
        return {
            "status": "error",
            "message": "Invalid API key format. Key seems too short."
        }
    
    # Mask the key for response
    if len(new_key) > 12:
        masked_key = f"{new_key[:8]}...{new_key[-4:]}"
    else:
        masked_key = f"{new_key[:4]}...{new_key[-2:]}"
    
    # Check if we're in production (Render) or local development
    is_production = os.getenv("ENVIRONMENT") == "production" or os.getenv("RENDER") == "true"
    
    if is_production:
        # Production mode: Update in-memory only
        # Note: This will be lost on restart - user must update env var in Render dashboard
        settings.gemini_api_key = new_key
        
        logger.info(f"API key updated in memory (production mode): {masked_key}")
        
        return {
            "status": "success",
            "message": "API key updated in memory. ⚠️ This change is temporary and will be lost on restart. Please update the GEMINI_API_KEY environment variable in your Render dashboard for permanent changes.",
            "masked_key": masked_key,
            "temporary": True,
            "production_mode": True
        }
    else:
        # Local development: Update .env file
        try:
            env_path = Path(__file__).parent.parent / ".env"
            logger.info(f"Updating .env file at: {env_path}")
            
            # Read existing .env content
            if env_path.exists():
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                logger.info(f"Read {len(lines)} lines from .env file")
            else:
                lines = []
                logger.info(".env file does not exist, will create new one")
            
            # Update or add GEMINI_API_KEY
            key_found = False
            for i, line in enumerate(lines):
                if line.strip().startswith("GEMINI_API_KEY="):
                    lines[i] = f"GEMINI_API_KEY={new_key}\n"
                    key_found = True
                    logger.info(f"Updated existing key at line {i+1}")
                    break
            
            if not key_found:
                lines.append(f"\nGEMINI_API_KEY={new_key}\n")
                logger.info("Added new GEMINI_API_KEY line")
            
            # Write back to .env
            with open(env_path, 'w') as f:
                f.writelines(lines)
            logger.info(f"Wrote {len(lines)} lines to .env file")
            
            # Update settings in memory
            old_key = settings.gemini_api_key
            settings.gemini_api_key = new_key
            logger.info(f"Updated settings.gemini_api_key in memory")
            logger.info(f"Old key (masked): {old_key[:8] if old_key else 'None'}...")
            logger.info(f"New key (masked): {masked_key}")
            
            # Verify the update
            if settings.gemini_api_key == new_key:
                logger.info("✅ Verification: settings.gemini_api_key matches new key")
            else:
                logger.error(f"❌ Verification failed: settings.gemini_api_key = {settings.gemini_api_key[:8] if settings.gemini_api_key else 'None'}...")
            
            return {
                "status": "success",
                "message": "API key updated successfully in .env file",
                "masked_key": masked_key,
                "temporary": False,
                "production_mode": False
            }
            
        except Exception as e:
            logger.error(f"Error updating API key in .env: {e}")
            logger.exception("Full traceback:")
            
            # Fallback: Update in memory only
            settings.gemini_api_key = new_key
            
            return {
                "status": "warning",
                "message": f"API key updated in memory only. Could not write to .env file: {str(e)}",
                "masked_key": masked_key,
                "temporary": True,
                "production_mode": False
            }

@app.get("/ui-status")
async def get_ui_status():
    """Get UI file watcher status and recent changes."""
    if not ui_watcher:
        return {"status": "disabled", "message": "UI file watcher not initialized"}
    
    return {
        "status": "active" if ui_watcher.is_watching else "inactive",
        "watching_paths": ui_watcher.watch_paths,
        "message": "UI file watcher is monitoring todo-ui files for real-time changes"
    }

@app.get("/pending-approvals")
async def get_pending_approvals():
    """Get all pending approvals."""
    return {
        "pending_approvals": [
            {
                "task_id": task_id,
                "step": data["step"],
                "transcript": data["transcript"],
                "next_step": data["next_step"]
            }
            for task_id, data in pending_approvals.items()
        ]
    }

# Store completed tasks (admin workflows)
completed_tasks = {}

# Store manual todos (separate from admin workflows)
manual_todos = {}

# Store suspended workflows (rejected workflows that should not reappear)
suspended_workflows = set()

# Store workflow states for better tracking
workflow_states = {
    "pending": {},      # Waiting for approval
    "active": {},       # Currently being processed
    "completed": {},    # Successfully completed
    "rejected": {},     # Rejected and suspended
    "failed": {}        # Failed during execution
}

@app.get("/tasks")
async def get_all_tasks():
    """Get manual todos only (not admin workflows)."""
    return {"tasks": list(manual_todos.values())}

@app.get("/admin-workflows")
async def get_admin_workflows():
    """Get active admin workflows only (pending and in-progress, not completed or rejected)."""
    workflows = []
    
    # Add pending workflows (waiting for Dev Agent approval)
    for task_id, data in pending_approvals.items():
        if task_id not in suspended_workflows:  # Don't show suspended workflows
            workflows.append({
                "id": task_id,
                "title": data["transcript"],
                "description": f"Ready to modify files - waiting for Dev Agent approval",
                "status": "pending_dev_approval",
                "priority": "medium",
                "createdAt": "2024-01-23T" + str(len(workflows)).zfill(2) + ":00:00Z",
                "updatedAt": "2024-01-23T" + str(len(workflows)).zfill(2) + ":00:00Z",
                "step": data["step"],
                "next_step": data["next_step"],
                "plan": data.get("plan", {}),
                "workflow_type": "active"
            })
    
    # Add active workflows (currently being processed)
    for task_id, data in workflow_states["active"].items():
        workflows.append({
            "id": task_id,
            "title": data["transcript"],
            "description": f"Currently processing: {data.get('current_step', 'Unknown step')}",
            "status": "in_progress",
            "priority": data.get("priority", "medium"),
            "createdAt": data.get("createdAt", "2024-01-23T10:00:00Z"),
            "updatedAt": data.get("updatedAt", "2024-01-23T10:00:00Z"),
            "step": data.get("step", "processing"),
            "workflow_type": "active"
        })
    
    # Add completed workflows (with commit info and approval options)
    for task_id, task in completed_tasks.items():
        if task.get("status") == "completed":
            commit_info = task.get("commit_info", {})
            has_commit = bool(commit_info.get("commit_hash"))
            
            # Determine available actions based on commit and push status
            actions = []
            if task.get("awaiting_push_approval") and has_commit:
                actions.append("approve_github_push")
            
            if has_commit and not task.get("github_pushed"):
                actions.extend(["rollback_soft", "rollback_hard"])
            elif task.get("github_pushed"):
                actions.append("revert_github_push")
            
            # Determine status based on commit/push workflow
            if task.get("github_pushed"):
                status = "pushed_to_production"
                description = f"Pushed to production - {len(task.get('modified_files', []))} files live"
            elif task.get("awaiting_push_approval"):
                status = "awaiting_push_approval"
                description = f"Committed locally - awaiting approval to push to remote"
            elif task.get("commit_failed"):
                status = "commit_failed"
                description = f"Commit failed - {task.get('commit_error', 'Unknown error')}"
            else:
                status = "completed"
                description = f"Completed - {len(task.get('modified_files', []))} files modified"
            
            workflows.append({
                "id": task_id,
                "title": task["title"],
                "description": description,
                "status": status,
                "priority": task.get("priority", "medium"),
                "createdAt": task.get("createdAt", "2024-01-23T10:00:00Z"),
                "updatedAt": task.get("updatedAt", "2024-01-23T10:00:00Z"),
                "workflow_type": "completed",
                "commit_info": commit_info,
                "has_commit": has_commit,
                "github_pushed": task.get("github_pushed", False),
                "awaiting_push_approval": task.get("awaiting_push_approval", False),
                "commit_failed": task.get("commit_failed", False),
                "gemini_analysis": task.get("gemini_analysis"),
                "can_rollback": has_commit and not task.get("github_pushed"),
                "can_revert_github": task.get("github_pushed", False),
                "modified_files": task.get("modified_files", []),
                "actions": actions
            })
    
    return {"workflows": workflows}

@app.post("/todos")
async def create_manual_todo(todo_data: dict):
    """Create a manual todo (not from admin workflow)."""
    import uuid
    
    todo_id = f"todo_{uuid.uuid4().hex[:8]}"
    todo = {
        "id": todo_id,
        "title": todo_data.get("title", "Untitled Todo"),
        "description": todo_data.get("description", ""),
        "status": todo_data.get("status", "pending"),
        "priority": todo_data.get("priority", "medium"),
        "createdAt": "2024-01-23T10:00:00Z",
        "updatedAt": "2024-01-23T10:00:00Z"
    }
    
    manual_todos[todo_id] = todo
    return {"status": "success", "todo": todo}

@app.put("/todos/{todo_id}")
async def update_manual_todo(todo_id: str, todo_data: dict):
    """Update a manual todo."""
    if todo_id not in manual_todos:
        return {"error": "Todo not found"}
    
    todo = manual_todos[todo_id]
    todo.update({
        "title": todo_data.get("title", todo["title"]),
        "description": todo_data.get("description", todo["description"]),
        "status": todo_data.get("status", todo["status"]),
        "priority": todo_data.get("priority", todo["priority"]),
        "updatedAt": "2024-01-23T" + str(len(manual_todos) + 10).zfill(2) + ":00:00Z"
    })
    
    return {"status": "success", "todo": todo}

@app.delete("/todos/{todo_id}")
async def delete_manual_todo(todo_id: str):
    """Delete a manual todo."""
    if todo_id not in manual_todos:
        return {"error": "Todo not found"}
    
    del manual_todos[todo_id]
    return {"status": "success", "message": "Todo deleted"}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task by ID."""
    # Check manual todos first
    if task_id in manual_todos:
        return manual_todos[task_id]
    
    # Check pending workflows
    if task_id in pending_approvals:
        data = pending_approvals[task_id]
        return {
            "id": task_id,
            "title": data["transcript"],
            "description": f"Task plan created, waiting for approval to proceed to {data['next_step'].replace('_', ' ')}",
            "status": "pending_approval",
            "priority": "medium",
            "createdAt": "2024-01-23T10:00:00Z",
            "updatedAt": "2024-01-23T10:00:00Z",
            "step": data["step"],
            "next_step": data["next_step"],
            "plan": data.get("plan", {})
        }
    
    # Check completed workflows
    if task_id in completed_tasks:
        return completed_tasks[task_id]
    
    return {"error": "Task not found"}
    
@app.put("/admin-workflows/{task_id}")
async def edit_workflow(task_id: str, workflow_data: dict):
    """Edit a pending workflow before approval."""
    if task_id not in pending_approvals:
        return {"error": "Workflow not found or already processed"}
    
    workflow = pending_approvals[task_id]
    
    # Update editable fields
    if "transcript" in workflow_data:
        workflow["transcript"] = workflow_data["transcript"]
    
    if "plan" in workflow_data and "plan" in workflow:
        plan = workflow["plan"]
        plan_updates = workflow_data["plan"]
        
        if "description" in plan_updates:
            plan["description"] = plan_updates["description"]
        if "priority" in plan_updates:
            plan["priority"] = plan_updates["priority"]
        if "estimated_effort" in plan_updates:
            plan["estimated_effort"] = plan_updates["estimated_effort"]
        if "breakdown" in plan_updates:
            plan["breakdown"] = plan_updates["breakdown"]
        if "dependencies" in plan_updates:
            plan["dependencies"] = plan_updates["dependencies"]
    
    return {
        "status": "success",
        "message": "Workflow updated successfully",
        "workflow": {
            "task_id": task_id,
            "transcript": workflow["transcript"],
            "plan": workflow.get("plan", {})
        }
    }

@app.post("/generate-files/{task_id}")
async def generate_files_to_frontend(task_id: str):
    """Generate files from a completed task to the frontend."""
    if task_id not in completed_tasks:
        return {"error": "Task not found or not completed"}
    
    task = completed_tasks[task_id]
    if "code_files" not in task:
        return {"error": "No code files available for this task"}
    
    try:
        from tools.file_ops import generate_code_to_todo_ui
        
        # Generate files directly into todo-ui
        result = generate_code_to_todo_ui(task_id, task["code_files"])
        
        if result["status"] in ["success", "partial_success"]:
            logger.info(f"Generated {result['total_generated']} files successfully")
            return {
                "status": "success",
                "task_id": task_id,
                "generated_files": result["generated_files"],
                "generated_dir": result["generated_dir"],
                "message": f"Generated {result['total_generated']} files for task: {task['title']} in todo-ui/{result['generated_dir']}"
            }
        else:
            logger.error(f"Failed to generate files: {result.get('error', 'Unknown error')}")
            return {"error": f"Failed to generate files: {result.get('error', 'Unknown error')}"}
        
    except Exception as e:
        return {"error": f"Failed to generate files: {str(e)}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info(f"WebSocket client connected from {websocket.client}")
    try:
        while True:
            # Receive voice command/transcript
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket data: {data}")
            
            try:
                message = json.loads(data)
                command_type = message.get("type", "unknown")
                transcript = message.get("transcript", "")
                
                logger.info(f"Processing command: {command_type} - {transcript}")
                
                # Process command through agent orchestration
                response = await process_voice_command(command_type, transcript)
                
                logger.info(f"Sending response: {response.get('status', 'unknown')}")
                await manager.send_personal_message(
                    json.dumps(response), 
                    websocket
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                await manager.send_personal_message(
                    json.dumps({"error": "Invalid JSON format"}),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")

async def process_voice_command(command_type: str, transcript: str) -> dict:
    """Process voice commands through the agent system with direct Dev Agent approval."""
    try:
        # Create a task ID for this command
        task_id = f"task_{hash(transcript) % 10000}"
        
        # Handle approval commands
        if command_type == "approval":
            return await handle_approval(transcript, task_id)
        
        # Check if this workflow was previously rejected/suspended
        if task_id in suspended_workflows:
            return {
                "status": "suspended",
                "agent": "System",
                "response": f"🚫 **Workflow Suspended**\n\nThis workflow was previously rejected and has been suspended.\n\n**Command**: {transcript}\n\n**Action**: No new workflow created\n\n💡 **Tip**: Modify your command to create a new workflow.",
                "transcript": transcript,
                "task_id": task_id
            }
        
        # Check if there's already a pending workflow for this command
        if task_id in pending_approvals:
            return {
                "status": "duplicate",
                "agent": "System", 
                "response": f"⚠️ **Duplicate Workflow**\n\nA workflow for this command is already pending approval.\n\n**Command**: {transcript}\n\n**Task ID**: {task_id}\n\n**Action**: Please approve or reject the existing workflow first.",
                "transcript": transcript,
                "task_id": task_id
            }
        
        # Show immediate processing status
        logger.info(f"Processing command: {transcript}")
        
        # Check rate limit status before calling PM Agent
        from tools.rate_limiter import get_gemini_api_status
        rate_status = get_gemini_api_status()
        
        processing_msg = "🤖 **Analyzing Your Request**\n\n"
        if rate_status['remaining_requests'] == 0:
            wait_time = rate_status.get('reset_in_seconds', 0)
            processing_msg += f"⏳ **Rate Limit**: Waiting {wait_time:.0f}s for AI analysis...\n"
        else:
            processing_msg += f"🧠 **AI Planning**: Creating implementation plan...\n"
        
        processing_msg += f"📝 **Command**: {transcript}\n\n⚡ **Status**: Analysis in progress..."
        
        # Step 1: PM Agent creates a plan automatically (no approval needed)
        logger.info(f"PM Agent automatically creating plan for: {transcript}")
        pm_result = await pm_agent.plan_task(transcript, is_ui_editing=True)
        
        if pm_result["status"] != "success":
            # Check if it's a rate limit error
            if pm_result.get("error") == "api_rate_limit":
                return {
                    "status": "error",
                    "agent": "PM Agent",
                    "error_type": "api_rate_limit",
                    "response": (
                        f"🚫 **API Rate Limit Exceeded**\n\n"
                        f"**Task**: {transcript}\n\n"
                        f"❌ **Error**: Gemini API has reached its rate limit (429 RESOURCE_EXHAUSTED)\n\n"
                        f"🔑 **Action Required**: Please update your Gemini API key\n\n"
                        f"**Steps to fix:**\n"
                        f"1. Get a new API key from [Google AI Studio](https://aistudio.google.com/apikey)\n"
                        f"2. Update `GEMINI_API_KEY` in `vocalCommit/orchestrator/.env`\n"
                        f"3. Restart the orchestrator\n"
                        f"4. Retry your task\n\n"
                        f"💡 **Tip**: Free tier has limited requests per minute. Consider upgrading for higher limits."
                    ),
                    "transcript": transcript
                }
            
            return {
                "status": "error",
                "agent": "PM Agent",
                "response": "❌ **Planning Failed**\n\nFailed to create implementation plan. Please try again.",
                "transcript": transcript
            }
        
        plan = pm_result["plan"]
        logger.info(f"PM Agent created plan with {len(plan.get('target_files', []))} target files")
        
        # Step 2: Execute Dev Agent directly (no approval needed)
        logger.info(f"Starting direct execution of Dev Agent for task: {task_id}")
        
        # Move directly to active state
        workflow_states["active"][task_id] = {
            "transcript": transcript,
            "plan": plan,
            "status": "in_progress",
            "started_at": "2024-01-23T10:00:00Z",
            "current_step": "dev_agent"
        }
        
        # Create thought signature for PM Agent
        thought_manager.add_thought(task_id, "PM Agent", {
            "summary": f"Created task plan for: {transcript}",
            "outputs": {"plan": plan},
            "recommendations": ["Proceed with development", "Consider UI/UX implications"]
        })
        
        # Show target files that will be modified
        target_files_display = ""
        if plan.get("target_files"):
            target_files_display = f"\n📁 **Files to Modify**: {', '.join(plan['target_files'])}"
        
        # Start background processing immediately
        import asyncio
        asyncio.create_task(process_task_in_background(task_id, {
            "plan": plan,
            "transcript": transcript
        }))
        
        return {
            "status": "processing",
            "task_id": task_id,
            "agent": "Dev Agent",
            "response": f"🔧 **Processing UI Modifications**\n\n"
                       f"**Task**: {plan['description']}\n"
                       f"**Priority**: {plan['priority']}\n"
                       f"**Estimated Time**: {plan['estimated_effort']}{target_files_display}\n\n"
                       f"**Implementation Plan**:\n" + "\n".join([f"• {item}" for item in plan['breakdown']]) + "\n\n"
                       f"🔄 **Status**: Dev Agent is now processing your request\n"
                       f"💡 **Updates**: You'll receive notification when complete\n\n"
                       f"✨ **Task ID**: {task_id}",
            "transcript": transcript,
            "requires_approval": False,
            "next_agent": "Dev Agent",
            "plan_details": plan
        }
        
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        return {
            "status": "error",
            "agent": "Orchestrator",
            "response": f"❌ **Processing Error**\n\nAn error occurred while processing your command: {str(e)}",
            "transcript": transcript
        }

async def handle_approval(action: str, task_id: str) -> dict:
    """Handle approval/rejection of agent steps."""
    try:
        # Parse approval action (approve_task_1234 or reject_task_1234)
        if action.startswith("approve_"):
            task_id = action.replace("approve_", "")
            return await approve_task(task_id)
        elif action.startswith("reject_"):
            task_id = action.replace("reject_", "")
            return await reject_task(task_id)
        else:
            return {
                "status": "error",
                "response": "Invalid approval command. Use 'approve_task_ID' or 'reject_task_ID'"
            }
    except Exception as e:
        return {
            "status": "error",
            "response": f"Error handling approval: {str(e)}"
        }

async def approve_task(task_id: str) -> dict:
    """Approve a pending task and start background processing."""
    if task_id not in pending_approvals:
        return {
            "status": "error",
            "response": f"❌ **Approval Error**\n\nNo pending approval found for task {task_id}"
        }
    
    approval_data = pending_approvals[task_id]
    current_step = approval_data["step"]
    
    # IMMEDIATELY remove from pending approvals to clear the approval window
    del pending_approvals[task_id]
    
    # Move from pending to active state IMMEDIATELY
    workflow_states["active"][task_id] = {
        "transcript": approval_data["transcript"],
        "plan": approval_data.get("plan", {}),
        "status": "in_progress",
        "approved_at": "2024-01-23T10:00:00Z",
        "current_step": "dev_agent"
    }
    
    # Remove from pending state immediately
    if task_id in workflow_states["pending"]:
        del workflow_states["pending"][task_id]
    
    if current_step == "dev_agent_approval" and approval_data["next_step"] == "execute_dev_agent":
        # Check rate limit status for user info
        from tools.rate_limiter import get_gemini_api_status
        rate_status = get_gemini_api_status()
        
        # Send immediate approval confirmation
        status_msg = "🔄 **Dev Agent Approved - Processing Started**"
        if rate_status['remaining_requests'] == 0:
            wait_time = rate_status.get('reset_in_seconds', 0)
            status_msg += f"\n⏳ **Rate Limited**: Processing will take ~{wait_time:.0f}s due to API limits"
        else:
            status_msg += f"\n🧠 **AI Processing**: Generating code changes in background..."
        
        # Start background processing
        import asyncio
        asyncio.create_task(process_task_in_background(task_id, approval_data))
        
        # Send processing started notification via WebSocket
        processing_message = {
            "type": "task_processing",
            "task_id": task_id,
            "status": "processing",
            "transcript": approval_data["transcript"],
            "target_files": approval_data.get('plan', {}).get('target_files', []),
            "message": f"🔄 **Dev Agent Processing**\n\n**{approval_data['transcript']}**\n\nModifying {len(approval_data.get('plan', {}).get('target_files', []))} files..."
        }
        
        # Broadcast to all connected WebSocket clients
        for connection in manager.active_connections:
            try:
                await connection.send_text(json.dumps(processing_message))
            except Exception as e:
                logger.warning(f"Failed to send processing notification to WebSocket client: {e}")
        
        return {
            "status": "processing",
            "task_id": task_id,
            "agent": "Dev Agent",
            "response": f"✅ **Dev Agent Approved**\n\n"
                       f"**Task**: {approval_data['transcript']}\n\n"
                       f"{status_msg}\n\n"
                       f"📁 **Files to Modify**: {', '.join(approval_data.get('plan', {}).get('target_files', []))}\n\n"
                       f"🔄 **Status**: Processing in background\n"
                       f"💡 **Updates**: You'll receive notification when complete\n\n"
                       f"✨ **Approval window closed** - task is now running",
            "transcript": approval_data["transcript"]
        }
    else:
        return {
            "status": "error",
            "response": f"❌ **Unknown Step**\n\nUnknown approval step: {current_step}"
        }

async def process_task_in_background(task_id: str, approval_data: dict):
    """Process the approved task in the background."""
    try:
        logger.info(f"Background processing started for task: {task_id}")
        
        plan = approval_data["plan"]
        dev_context = thought_manager.get_context_for_agent(task_id, "Dev Agent")
        
        # Show processing status
        logger.info(f"Starting UI editing for {len(plan.get('target_files', []))} files")
        
        # Always use UI editing workflow - modify existing todo-ui files using "Need-to-Know" architecture
        dev_result = process_ui_editing_plan(plan, approval_data["transcript"])
        
        logger.info(f"Dev result: {dev_result}")
        
        if dev_result["status"] not in ["success", "partial_success"]:
            # Task failed
            error_details = dev_result.get("errors", ["Unknown error"])
            
            # Check if it's a Gemini API rate limit error
            error_str = str(error_details).lower()
            is_rate_limit = "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str
            
            if is_rate_limit:
                # Rate limit error - ask user to change API key
                error_type = "api_rate_limit"
                error_message = "Gemini API rate limit exceeded"
                user_message = (
                    f"🚫 **API Rate Limit Exceeded**\n\n"
                    f"**Task**: {approval_data['transcript']}\n\n"
                    f"❌ **Error**: Gemini API has reached its rate limit (429 RESOURCE_EXHAUSTED)\n\n"
                    f"🔑 **Action Required**: Please update your Gemini API key\n\n"
                    f"**Steps to fix:**\n"
                    f"1. Get a new API key from Google AI Studio\n"
                    f"2. Update GEMINI_API_KEY in `vocalCommit/orchestrator/.env`\n"
                    f"3. Restart the orchestrator\n"
                    f"4. Retry your task\n\n"
                    f"💡 **Tip**: Free tier has limited requests per minute. Consider upgrading for higher limits."
                )
            else:
                # Other error
                error_type = "ui_editing_failed"
                error_message = "Dev agent failed to modify UI files"
                user_message = f"❌ **Task Failed**\n\n**{approval_data['transcript']}**\n\nErrors occurred during processing"
            
            completed_tasks[task_id] = {
                "task_id": task_id,
                "transcript": approval_data["transcript"],
                "status": "error",
                "completed_at": "2024-01-23T" + str(len(completed_tasks) + 10).zfill(2) + ":00:00Z",
                "type": error_type,
                "error": error_message,
                "error_details": error_details,
                "is_rate_limit": is_rate_limit
            }
            
            # Move to failed state
            workflow_states["failed"][task_id] = {
                "transcript": approval_data["transcript"],
                "status": "failed",
                "failed_at": "2024-01-23T10:00:00Z",
                "error": error_message,
                "error_details": error_details,
                "is_rate_limit": is_rate_limit
            }
            
            # Remove from active state
            if task_id in workflow_states["active"]:
                del workflow_states["active"][task_id]
            
            logger.error(f"Background processing failed for task {task_id}: {error_details}")
            
            # Send failure notification via WebSocket to connected clients
            failure_message = {
                "type": "task_failed",
                "task_id": task_id,
                "status": "failed",
                "transcript": approval_data["transcript"],
                "errors": error_details,
                "is_rate_limit": is_rate_limit,
                "error_type": error_type,
                "message": user_message
            }
            
            # Broadcast to all connected WebSocket clients
            for connection in manager.active_connections:
                try:
                    await connection.send_text(json.dumps(failure_message))
                except Exception as e:
                    logger.warning(f"Failed to send failure notification to WebSocket client: {e}")
            
            return
        
        # UI editing completed successfully
        modified_files = dev_result.get("modified_files", [])
        
        # Run comprehensive testing on the modified files
        logger.info(f"Running comprehensive testing for {len(modified_files)} modified files")
        test_result = run_testing_agent(approval_data["transcript"], modified_files)
        logger.info(f"Testing result: {test_result}")
        
        # Create thought signature for Dev Agent
        thought_manager.add_thought(task_id, "Dev Agent", {
            "summary": f"Modified UI files for task: {approval_data['transcript']}",
            "outputs": {"modified_files": modified_files},
            "recommendations": ["Check UI changes", "Test functionality"]
        })
        
        # Create thought signature for Testing Agent
        thought_manager.add_thought(task_id, "Testing Agent", {
            "summary": f"Tested implementation for task: {approval_data['transcript']}",
            "outputs": {"test_results": test_result},
            "recommendations": test_result.get("recommendations", [])
        })
        
        # Task completed
        task_data = {
            "id": task_id,
            "title": approval_data["transcript"],
            "description": f"Modified todo-ui for: {approval_data['transcript']}",
            "status": "completed",
            "priority": plan.get("priority", "medium"),
            "createdAt": "2024-01-23T10:00:00Z",
            "updatedAt": "2024-01-23T" + str(len(completed_tasks) + 10).zfill(2) + ":00:00Z",
            "modified_files": modified_files,
            "ui_changes": dev_result.get("ui_changes", []),
            "test_results": test_result,
            "type": "ui_editing"
        }
        
        # NEW WORKFLOW: Commit locally immediately, then ask for approval before pushing
        logger.info(f"[COMMIT] Starting local commit workflow for task {task_id}")
        
        # Step 1: Sync the todo-ui repository (pull existing changes)
        logger.info(f"[COMMIT] Step 1: Syncing TODO-UI repository")
        sync_result = github_ops.clone_or_pull_repo()
        if sync_result["status"] != "success":
            logger.error(f"[COMMIT] Failed to sync todo-ui repo: {sync_result.get('error', 'Unknown error')}")
            task_data["github_sync_error"] = sync_result.get("error", "Unknown error")
            task_data["commit_failed"] = True
        else:
            logger.info(f"[COMMIT] Successfully synced todo-ui repo: {sync_result['action']}")
        
        # Step 2: Get Gemini AI suggestions for the changes
        logger.info(f"[COMMIT] Step 2: Getting AI analysis")
        gemini_suggestions = github_ops.get_gemini_suggestions(
            approval_data["transcript"], 
            modified_files
        )
        
        if gemini_suggestions["status"] == "success":
            logger.info(f"[COMMIT] Gemini AI analysis completed with {gemini_suggestions['suggestions']['confidence']:.2f} confidence")
            task_data["gemini_analysis"] = gemini_suggestions["suggestions"]
        else:
            logger.warning(f"[COMMIT] Gemini AI analysis failed: {gemini_suggestions.get('error', 'Unknown error')}")
            task_data["gemini_analysis"] = gemini_suggestions.get("suggestions", {})
        
        # Step 3: Commit changes locally (DO NOT PUSH YET)
        if sync_result["status"] == "success":
            logger.info(f"[COMMIT] Step 3: Committing changes locally (no push)")
            commit_result = github_ops.commit_changes_locally(
                approval_data["transcript"],
                modified_files,
                {"suggestions": task_data.get("gemini_analysis", {})}
            )
            
            if commit_result["status"] == "success":
                logger.info(f"[COMMIT] ✅ Successfully committed locally: {commit_result['commit_hash']}")
                task_data["has_commit"] = True
                task_data["commit_info"] = {
                    "commit_hash": commit_result["commit_hash"],
                    "commit_message": commit_result["commit_message"],
                    "timestamp": commit_result["timestamp"],
                    "status": "committed_locally"
                }
                task_data["awaiting_push_approval"] = True
                task_data["github_pushed"] = False
            else:
                logger.error(f"[COMMIT] ❌ Failed to commit locally: {commit_result.get('error', 'Unknown error')}")
                task_data["commit_failed"] = True
                task_data["commit_error"] = commit_result.get("error", "Unknown error")
        else:
            logger.error(f"[COMMIT] Skipping commit due to sync failure")
            task_data["commit_failed"] = True
        
        logger.info(f"[COMMIT] Task {task_id} committed locally, awaiting approval to push to remote")
        
        completed_tasks[task_id] = task_data
        
        # Move from active to completed state
        workflow_states["completed"][task_id] = {
            "transcript": approval_data["transcript"],
            "status": "completed",
            "completed_at": "2024-01-23T" + str(len(completed_tasks) + 10).zfill(2) + ":00:00Z",
            "type": "ui_editing",
            "modified_files": modified_files,
            "test_results": test_result
        }
        
        # Remove from active state
        if task_id in workflow_states["active"]:
            del workflow_states["active"][task_id]
        
        logger.info(f"Background processing completed successfully for task {task_id}")
        
        # Send completion notification via WebSocket to connected clients
        github_info_msg = ""
        
        # Production mode: No local commits, only GitHub pushes
        if task_data.get("github_ready"):
            github_info_msg = f"\n🚀 **GitHub Ready**: Awaiting approval to push to TODO-UI production"
            if task_data.get("gemini_analysis", {}).get("risk_assessment"):
                risk = task_data["gemini_analysis"]["risk_assessment"]
                confidence = task_data["gemini_analysis"].get("confidence", 0.0)
                github_info_msg += f"\n🤖 **AI Analysis**: {risk.title()} risk ({confidence:.0%} confidence)"
        else:
            github_info_msg = f"\n⚠️ **GitHub Sync Failed**: {task_data.get('github_sync_error', 'Unknown error')}"
        
        completion_message = {
            "type": "task_completed",
            "task_id": task_id,
            "status": "completed",
            "transcript": approval_data["transcript"],
            "modified_files": modified_files,
            "ui_changes": dev_result.get("ui_changes", []),
            "test_results": test_result,
            "commit_info": task_data.get("commit_info"),
            "gemini_analysis": task_data.get("gemini_analysis"),
            "github_ready": task_data.get("github_ready", False),
            "pending_github_push": task_data.get("pending_github_push", False),
            "message": f"🎉 **Task Completed!**\n\n**{approval_data['transcript']}**\n\n📁 Modified {len(modified_files)} files\n🌐 View changes at http://localhost:5174{github_info_msg}"
        }
        
        # Broadcast to all connected WebSocket clients
        for connection in manager.active_connections:
            try:
                await connection.send_text(json.dumps(completion_message))
            except Exception as e:
                logger.warning(f"Failed to send completion notification to WebSocket client: {e}")
        
        logger.info(f"Sent completion notification to {len(manager.active_connections)} WebSocket clients")
        
    except Exception as e:
        logger.error(f"Error in background processing for task {task_id}: {str(e)}")
        
        # Move to failed state
        workflow_states["failed"][task_id] = {
            "transcript": approval_data["transcript"],
            "status": "failed",
            "failed_at": "2024-01-23T10:00:00Z",
            "error": str(e)
        }
        
        # Remove from active state
        if task_id in workflow_states["active"]:
            del workflow_states["active"][task_id]
        
        # Send failure notification via WebSocket to connected clients
        failure_message = {
            "type": "task_failed",
            "task_id": task_id,
            "status": "failed",
            "transcript": approval_data["transcript"],
            "error": str(e),
            "message": f"❌ **Task Failed**\n\n**{approval_data['transcript']}**\n\nUnexpected error: {str(e)}"
        }
        
        # Broadcast to all connected WebSocket clients
        for connection in manager.active_connections:
            try:
                await connection.send_text(json.dumps(failure_message))
            except Exception as ws_error:
                logger.warning(f"Failed to send failure notification to WebSocket client: {ws_error}")

async def reject_task(task_id: str) -> dict:
    """Reject a pending task and suspend the workflow."""
    if task_id not in pending_approvals:
        return {
            "status": "error",
            "response": f"No pending approval found for task {task_id}"
        }
    
    approval_data = pending_approvals[task_id]
    
    # Move to rejected state and suspend the workflow
    workflow_states["rejected"][task_id] = {
        "transcript": approval_data["transcript"],
        "plan": approval_data.get("plan", {}),
        "status": "rejected",
        "rejected_at": "2024-01-23T10:00:00Z",
        "reason": "Manual rejection by user"
    }
    
    # Add to suspended workflows to prevent reappearance
    suspended_workflows.add(task_id)
    
    # Remove from pending approvals and pending state
    del pending_approvals[task_id]
    if task_id in workflow_states["pending"]:
        del workflow_states["pending"][task_id]
    
    logger.info(f"Workflow {task_id} rejected and suspended: {approval_data['transcript']}")
    
    return {
        "status": "rejected",
        "task_id": task_id,
        "agent": "System",
        "response": f"❌ **Task Rejected & Suspended**\n\nTask '{approval_data['transcript']}' has been rejected and suspended.\n\n🚫 **Action**: Workflow terminated and will not reappear\n📝 **Reason**: Manual rejection by user\n\n💡 **Note**: Modify your voice command to create a new workflow if needed.",
        "transcript": approval_data["transcript"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
@app.get("/completed-workflows")
async def get_completed_workflows():
    """Get completed workflows (for history/archive view)."""
    workflows = []
    
    # Add completed workflows
    for task_id, data in completed_tasks.items():
        workflows.append(data)
    
    # Add rejected workflows
    for task_id, data in workflow_states["rejected"].items():
        workflows.append(data)
    
    # Add approved workflows
    for task_id, data in workflow_states.get("approved", {}).items():
        if task_id in completed_tasks:
            task_data = completed_tasks[task_id].copy()
            task_data["workflow_state"] = "approved"
            workflows.append(task_data)
    
    # Add rolled back workflows
    for task_id, data in workflow_states.get("rolled_back", {}).items():
        if task_id in completed_tasks:
            task_data = completed_tasks[task_id].copy()
            task_data["workflow_state"] = "rolled_back"
            workflows.append(task_data)
    
    return {"workflows": workflows}

@app.get("/active-processing")
async def get_active_processing():
    """Get all currently processing tasks."""
    active_tasks = []
    
    for task_id, data in workflow_states["active"].items():
        plan = data.get("plan", {})
        target_files = plan.get("target_files", [])
        
        active_tasks.append({
            "task_id": task_id,
            "transcript": data["transcript"],
            "status": "processing",
            "target_files": target_files,
            "progress": f"Processing {len(target_files)} files",
            "approved_at": data.get("approved_at"),
            "current_step": data.get("current_step", "dev_agent")
        })
    
    return {
        "active_tasks": active_tasks,
        "count": len(active_tasks)
    }

@app.get("/workflow-status/{task_id}")
async def get_workflow_status(task_id: str):
    """Get real-time status of a specific workflow."""
    # Check pending approvals
    if task_id in pending_approvals:
        data = pending_approvals[task_id]
        return {
            "task_id": task_id,
            "status": "pending_dev_approval",
            "step": data["step"],
            "next_step": data["next_step"],
            "transcript": data["transcript"],
            "message": f"Waiting for Dev Agent approval to modify files"
        }
    
    # Check active workflows
    if task_id in workflow_states["active"]:
        data = workflow_states["active"][task_id]
        
        # Get more detailed status based on plan
        plan = data.get("plan", {})
        target_files = plan.get("target_files", [])
        
        return {
            "task_id": task_id,
            "status": "in_progress",
            "step": data.get("current_step", "processing"),
            "transcript": data["transcript"],
            "target_files": target_files,
            "progress": f"Processing {len(target_files)} files",
            "message": f"🔄 Currently processing: {data.get('current_step', 'Unknown step')}"
        }
    
    # Check completed workflows
    if task_id in workflow_states["completed"]:
        data = workflow_states["completed"][task_id]
        return {
            "task_id": task_id,
            "status": "completed",
            "transcript": data["transcript"],
            "completed_at": data.get("completed_at"),
            "message": "Task completed successfully"
        }
    
    # Check failed workflows
    if task_id in workflow_states["failed"]:
        data = workflow_states["failed"][task_id]
        return {
            "task_id": task_id,
            "status": "failed",
            "transcript": data["transcript"],
            "error": data.get("error"),
            "failed_at": data.get("failed_at"),
            "message": f"Task failed: {data.get('error', 'Unknown error')}"
        }
    
    # Check rejected workflows
    if task_id in workflow_states["rejected"]:
        data = workflow_states["rejected"][task_id]
        return {
            "task_id": task_id,
            "status": "rejected",
            "transcript": data["transcript"],
            "rejected_at": data.get("rejected_at"),
            "message": "Task was rejected and suspended"
        }
    
    return {
        "task_id": task_id,
        "status": "not_found",
        "message": "Workflow not found"
    }

@app.get("/workflow-stats")
async def get_workflow_stats():
    """Get workflow statistics."""
    return {
        "pending": len(pending_approvals),
        "active": len(workflow_states["active"]),
        "completed": len([t for t in completed_tasks.values() if t.get("status") == "completed"]),
        "approved": len(workflow_states.get("approved", {})),
        "rolled_back": len(workflow_states.get("rolled_back", {})),
        "rejected": len(workflow_states["rejected"]),
        "suspended": len(suspended_workflows),
        "failed": len(workflow_states["failed"])
    }
@app.post("/clear-suspended/{task_id}")
async def clear_suspended_workflow(task_id: str):
    """Clear a specific suspended workflow to allow it to be recreated."""
    if task_id in suspended_workflows:
        suspended_workflows.remove(task_id)
        if task_id in workflow_states["rejected"]:
            del workflow_states["rejected"][task_id]
        
        return {
            "status": "success",
            "message": f"Workflow {task_id} has been cleared from suspended list",
            "task_id": task_id
        }
    else:
        return {
            "status": "error",
            "message": f"Workflow {task_id} is not in suspended list"
        }

@app.post("/clear-all-suspended")
async def clear_all_suspended_workflows():
    """Clear all suspended workflows."""
    count = len(suspended_workflows)
    suspended_workflows.clear()
    workflow_states["rejected"].clear()
    
    return {
        "status": "success",
        "message": f"Cleared {count} suspended workflows",
        "cleared_count": count
    }

@app.get("/github-status")
async def get_github_status():
    """Get GitHub repository status and sync state."""
    try:
        # Check if local repo exists and get status
        local_status = github_ops.get_last_commit_info()
        
        # Try to pull latest changes to check sync status
        sync_result = github_ops.clone_or_pull_repo()
        
        return {
            "status": "success",
            "local_repo_exists": local_status["status"] == "success",
            "last_commit": local_status if local_status["status"] == "success" else None,
            "sync_status": sync_result,
            "repo_url": github_ops.repo_url,
            "local_path": str(github_ops.local_path)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/sync-todo-ui")
async def sync_todo_ui_repo():
    """Sync the todo-ui repository (clone or pull latest changes)."""
    try:
        result = github_ops.clone_or_pull_repo()
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/revert-last-push")
async def revert_last_push():
    """Revert the last commit in the todo-ui repository."""
    try:
        result = github_ops.revert_last_commit()
        
        if result["status"] == "success":
            # Send revert notification via WebSocket
            revert_message = {
                "type": "commit_reverted",
                "status": "reverted",
                "reverted_commit": result["reverted_commit"],
                "commit_message": result["commit_message"],
                "changed_files": result["changed_files"],
                "message": f"🔄 **Commit Reverted**\n\n**Reverted**: {result['reverted_commit']}\n\n**Original**: {result['commit_message']}\n\n📁 **Files**: {len(result['changed_files'])} files affected"
            }
            
            # Broadcast to all connected WebSocket clients
            for connection in manager.active_connections:
                try:
                    await connection.send_text(json.dumps(revert_message))
                except Exception as e:
                    logger.warning(f"Failed to send revert notification to WebSocket client: {e}")
        
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/git-status")
async def get_git_status():
    """Get current git repository status."""
    try:
        status = git_ops.check_git_status()
        return status
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/commit-history")
async def get_commit_history(limit: int = 10):
    """Get recent commit history."""
    try:
        history = git_ops.get_commit_history(limit)
        return history
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/last-commit")
async def get_last_commit():
    """Get information about the last commit."""
    try:
        commit_info = git_ops.get_last_commit_info()
        return commit_info
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/logs")
async def get_logs(lines: int = 100, filter: str = None):
    """
    Get recent orchestrator logs.
    
    Args:
        lines: Number of log lines to return (default: 100)
        filter: Optional filter string (e.g., "APPROVAL", "GITHUB", "ERROR")
    """
    try:
        import os
        from pathlib import Path
        
        # Get log file path
        log_file = Path(__file__).parent.parent / "orchestrator.log"
        
        if not log_file.exists():
            return {
                "status": "success",
                "logs": [],
                "message": "Log file not found"
            }
        
        # Read last N lines
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Apply filter if provided
        if filter:
            recent_lines = [line for line in recent_lines if filter.upper() in line.upper()]
        
        return {
            "status": "success",
            "logs": recent_lines,
            "total_lines": len(recent_lines),
            "filter": filter
        }
    except Exception as e:
        logger.error(f"Error reading logs: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/rollback-commit/{task_id}")
async def rollback_task_commit(task_id: str, hard_rollback: bool = False):
    """
    Rollback the commit for a specific task.
    
    Args:
        task_id: Task identifier
        hard_rollback: If True, performs hard reset (discards changes). If False, soft reset (keeps changes unstaged)
    """
    try:
        # Check if task exists and has commit info
        if task_id not in completed_tasks:
            return {
                "status": "error",
                "error": f"Task {task_id} not found in completed tasks"
            }
        
        task = completed_tasks[task_id]
        if not task.get("commit_info", {}).get("commit_hash"):
            return {
                "status": "error",
                "error": f"Task {task_id} has no associated commit to rollback"
            }
        
        # Perform rollback
        if hard_rollback:
            rollback_result = git_ops.hard_rollback_last_commit(task_id)
        else:
            rollback_result = git_ops.rollback_last_commit(task_id)
        
        if rollback_result["status"] != "success":
            return rollback_result
        
        # Push the rollback to GitHub if the task was originally pushed
        github_push_result = None
        if task.get("github_pushed"):
            logger.info(f"Pushing rollback to GitHub for task {task_id}")
            try:
                # Sync the TODO-UI repository first
                sync_result = github_ops.clone_or_pull_repo()
                if sync_result["status"] == "success":
                    # Create a commit message for the rollback
                    rollback_message = f"Rollback task: {task.get('title', task_id)}"
                    
                    # Get the files that were originally modified
                    modified_files = task.get("modified_files", [])
                    
                    # Push the rollback to GitHub
                    github_push_result = github_ops.commit_and_push_changes(
                        rollback_message,
                        modified_files,
                        {"suggestions": {"summary": "Rollback operation", "risk_assessment": "low"}}
                    )
                    
                    if github_push_result["status"] == "success":
                        logger.info(f"Successfully pushed rollback to GitHub: {github_push_result['commit_hash']}")
                        task["github_rollback_info"] = {
                            "commit_hash": github_push_result["commit_hash"],
                            "pushed_at": "2024-01-23T" + str(len(completed_tasks) + 25).zfill(2) + ":00:00Z"
                        }
                    else:
                        logger.error(f"Failed to push rollback to GitHub: {github_push_result.get('error', 'Unknown error')}")
                else:
                    logger.error(f"Failed to sync TODO-UI repo for rollback push: {sync_result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Error pushing rollback to GitHub: {str(e)}")
                github_push_result = {"status": "error", "error": str(e)}
        
        # Update task status to indicate rollback
        task["status"] = "rolled_back"
        task["rollback_info"] = {
            "rolled_back_at": "2024-01-23T" + str(len(completed_tasks) + 20).zfill(2) + ":00:00Z",
            "rollback_type": "hard" if hard_rollback else "soft",
            "rolled_back_commit": rollback_result["rolled_back_commit"]
        }
        
        # Move task to a separate rollback state
        workflow_states["rolled_back"] = workflow_states.get("rolled_back", {})
        workflow_states["rolled_back"][task_id] = {
            "transcript": task["title"],
            "status": "rolled_back",
            "rolled_back_at": task["rollback_info"]["rolled_back_at"],
            "rollback_type": task["rollback_info"]["rollback_type"],
            "original_commit": task["commit_info"]["commit_hash"]
        }
        
        # Remove from completed state
        if task_id in workflow_states["completed"]:
            del workflow_states["completed"][task_id]
        
        logger.info(f"Successfully rolled back task {task_id} ({'hard' if hard_rollback else 'soft'} rollback)")
        
        # Send rollback notification via WebSocket
        github_status_msg = ""
        if task.get("github_pushed"):
            if github_push_result and github_push_result["status"] == "success":
                github_status_msg = f"\n🚀 **GitHub**: Rollback pushed to production ({task['github_rollback_info']['commit_hash'][:8]})"
            elif github_push_result:
                github_status_msg = f"\n⚠️ **GitHub**: Failed to push rollback - {github_push_result.get('error', 'Unknown error')}"
            else:
                github_status_msg = f"\n⚠️ **GitHub**: Rollback not pushed to production"
        
        rollback_message = {
            "type": "task_rolled_back",
            "task_id": task_id,
            "status": "rolled_back",
            "transcript": task["title"],
            "rollback_type": "hard" if hard_rollback else "soft",
            "rolled_back_commit": rollback_result["rolled_back_commit"],
            "github_rollback_pushed": github_push_result["status"] == "success" if github_push_result else False,
            "github_rollback_info": task.get("github_rollback_info"),
            "message": f"🔄 **Task Rolled Back**\n\n**{task['title']}**\n\n{'🗑️ Hard rollback: All changes discarded' if hard_rollback else '📝 Soft rollback: Changes kept as unstaged'}\n\n🔗 **Local Commit**: {rollback_result['rolled_back_commit']}{github_status_msg}"
        }
        
        # Broadcast to all connected WebSocket clients
        for connection in manager.active_connections:
            try:
                await connection.send_text(json.dumps(rollback_message))
            except Exception as e:
                logger.warning(f"Failed to send rollback notification to WebSocket client: {e}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "rollback_type": "hard" if hard_rollback else "soft",
            "rolled_back_commit": rollback_result["rolled_back_commit"],
            "message": rollback_result["message"],
            "task_status": "rolled_back"
        }
        
    except Exception as e:
        logger.error(f"Error rolling back task {task_id}: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/approve-github-push/{task_id}")
async def approve_github_push(task_id: str):
    """
    Approve pushing already committed changes to GitHub remote repository.
    
    Args:
        task_id: Task identifier
    """
    try:
        # Check if task exists and is ready for push
        if task_id not in completed_tasks:
            return {
                "status": "error",
                "error": f"Task {task_id} not found in completed tasks"
            }
        
        task = completed_tasks[task_id]
        
        if not task.get("awaiting_push_approval"):
            return {
                "status": "error",
                "error": f"Task {task_id} is not awaiting push approval"
            }
        
        if not task.get("has_commit"):
            return {
                "status": "error",
                "error": f"Task {task_id} has no local commit to push"
            }
        
        if task.get("github_pushed"):
            return {
                "status": "error",
                "error": f"Task {task_id} has already been pushed to GitHub"
            }
        
        logger.info(f"[APPROVAL] Pushing approved commit to GitHub for task {task_id}")
        
        # Push the already committed changes
        push_result = github_ops.push_committed_changes()
        
        if push_result["status"] != "success":
            return {
                "status": "error",
                "error": f"Failed to push to GitHub: {push_result.get('error', 'Unknown error')}",
                "push_result": push_result
            }
        
        # Update task status
        task["awaiting_push_approval"] = False
        task["github_pushed"] = True
        task["commit_info"]["status"] = "pushed_to_remote"
        task["commit_info"]["pushed_at"] = datetime.now().isoformat()
        
        logger.info(f"[APPROVAL] ✅ Task {task_id} successfully pushed to GitHub: {push_result['commit_hash']}")
        
        # Send GitHub push notification via WebSocket
        push_message = {
            "type": "github_pushed",
            "task_id": task_id,
            "status": "pushed",
            "transcript": task["title"],
            "commit_hash": push_result["commit_hash"],
            "gemini_analysis": task.get("gemini_analysis"),
            "message": f"🚀 **Pushed to Production!**\n\n**{task['title']}**\n\n🔗 **GitHub Commit**: {push_result['commit_hash']}\n📁 **Files**: {len(task['modified_files'])} files pushed\n\n✅ **Status**: Live in production repository"
        }
        
        # Broadcast to all connected WebSocket clients
        for connection in manager.active_connections:
            try:
                await connection.send_text(json.dumps(push_message))
            except Exception as e:
                logger.warning(f"Failed to send GitHub push notification to WebSocket client: {e}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "commit_hash": push_result["commit_hash"],
            "message": f"Task {task_id} successfully pushed to GitHub production repository",
            "commit_info": task["commit_info"]
        }
        
    except Exception as e:
        logger.error(f"Error approving GitHub push for task {task_id}: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/approve-commit/{task_id}")
async def approve_task_commit(task_id: str):
    """
    Approve a completed task's commit (marks it as final, no rollback available).
    
    Args:
        task_id: Task identifier
    """
    try:
        # Check if task exists and has commit info
        if task_id not in completed_tasks:
            return {
                "status": "error",
                "error": f"Task {task_id} not found in completed tasks"
            }
        
        task = completed_tasks[task_id]
        if not task.get("commit_info", {}).get("commit_hash"):
            return {
                "status": "error",
                "error": f"Task {task_id} has no associated commit to approve"
            }
        
        if task.get("status") == "approved":
            return {
                "status": "error",
                "error": f"Task {task_id} is already approved"
            }
        
        # Push to GitHub if not already pushed
        github_push_result = None
        if not task.get("github_pushed"):
            logger.info(f"[APPROVAL] Pushing approved commit to GitHub for task {task_id}")
            try:
                # Sync the TODO-UI repository first
                logger.info(f"[APPROVAL] Step 1: Cloning/pulling TODO-UI repository")
                sync_result = github_ops.clone_or_pull_repo()
                logger.info(f"[APPROVAL] Sync result: {sync_result}")
                
                if sync_result["status"] == "success":
                    # Get task details for GitHub push
                    modified_files = task.get("modified_files", [])
                    logger.info(f"[APPROVAL] Step 2: Syncing {len(modified_files)} modified files to GitHub repo")
                    logger.info(f"[APPROVAL] Modified files: {modified_files}")
                    
                    # Sync files from orchestrator/todo-ui to the GitHub repo
                    from pathlib import Path
                    source_base = Path("todo-ui")  # orchestrator/todo-ui
                    file_sync_result = github_ops.sync_files_to_repo(modified_files, source_base)
                    logger.info(f"[APPROVAL] File sync result: {file_sync_result}")
                    
                    if file_sync_result["status"] != "success":
                        error_msg = f"File sync failed: {file_sync_result.get('error', 'Unknown error')}"
                        logger.error(f"[APPROVAL] {error_msg}")
                        logger.error(f"[APPROVAL] Failed files: {file_sync_result.get('failed_files', [])}")
                        github_push_result = {"status": "error", "error": error_msg}
                    else:
                        logger.info(f"[APPROVAL] Successfully synced {file_sync_result['total_synced']} files to GitHub repo")
                        logger.info(f"[APPROVAL] Synced files: {file_sync_result.get('synced_files', [])}")
                        
                        # Push the approved commit to GitHub
                        logger.info(f"[APPROVAL] Step 3: Committing and pushing changes to GitHub")
                        github_push_result = github_ops.commit_and_push_changes(
                            task.get("title", f"Approved task {task_id}"),
                            modified_files,
                            {"suggestions": task.get("gemini_analysis", {"summary": "Approved commit", "risk_assessment": "low"})}
                        )
                        logger.info(f"[APPROVAL] GitHub push result: {github_push_result}")
                        
                        if github_push_result["status"] == "success":
                            logger.info(f"[APPROVAL] ✅ Successfully pushed approved commit to GitHub: {github_push_result['commit_hash']}")
                            task["github_pushed"] = True
                            task["github_commit_info"] = {
                                "commit_hash": github_push_result["commit_hash"],
                                "commit_message": github_push_result["commit_message"],
                                "timestamp": github_push_result["timestamp"],
                                "pushed_at": datetime.now().isoformat()
                            }
                        else:
                            error_msg = github_push_result.get('error', 'Unknown error')
                            logger.error(f"[APPROVAL] ❌ Failed to push approved commit to GitHub: {error_msg}")
                            if github_push_result.get('committed'):
                                logger.warning(f"[APPROVAL] Changes were committed locally but not pushed")
                else:
                    error_msg = f"Failed to sync TODO-UI repo: {sync_result.get('error', 'Unknown error')}"
                    logger.error(f"[APPROVAL] {error_msg}")
                    github_push_result = {"status": "error", "error": error_msg}
            except Exception as e:
                error_msg = f"Exception during GitHub push: {str(e)}"
                logger.error(f"[APPROVAL] {error_msg}", exc_info=True)
                github_push_result = {"status": "error", "error": error_msg}
        
        # Mark task as approved
        task["status"] = "approved"
        task["approval_info"] = {
            "approved_at": "2024-01-23T" + str(len(completed_tasks) + 30).zfill(2) + ":00:00Z",
            "commit_hash": task["commit_info"]["commit_hash"]
        }
        
        # Move to approved state
        workflow_states["approved"] = workflow_states.get("approved", {})
        workflow_states["approved"][task_id] = {
            "transcript": task["title"],
            "status": "approved",
            "approved_at": task["approval_info"]["approved_at"],
            "commit_hash": task["commit_info"]["commit_hash"]
        }
        
        # Remove from completed state (now it's approved)
        if task_id in workflow_states["completed"]:
            del workflow_states["completed"][task_id]
        
        logger.info(f"Task {task_id} commit approved and finalized")
        
        # Send approval notification via WebSocket
        github_status_msg = ""
        if github_push_result:
            if github_push_result["status"] == "success":
                github_status_msg = f"\n🚀 **GitHub**: Pushed to production ({task['github_commit_info']['commit_hash'][:8]})"
            else:
                github_status_msg = f"\n⚠️ **GitHub**: Failed to push - {github_push_result.get('error', 'Unknown error')}"
        elif task.get("github_pushed"):
            github_status_msg = f"\n🚀 **GitHub**: Already pushed to production"
        
        approval_message = {
            "type": "commit_approved",
            "task_id": task_id,
            "status": "approved",
            "transcript": task["title"],
            "commit_hash": task["commit_info"]["commit_hash"],
            "github_pushed": task.get("github_pushed", False),
            "github_commit_info": task.get("github_commit_info"),
            "message": f"✅ **Commit Approved**\n\n**{task['title']}**\n\n🔒 Changes are now final (rollback no longer available)\n\n🔗 **Local Commit**: {task['commit_info']['commit_hash']}{github_status_msg}"
        }
        
        # Broadcast to all connected WebSocket clients
        for connection in manager.active_connections:
            try:
                await connection.send_text(json.dumps(approval_message))
            except Exception as e:
                logger.warning(f"Failed to send approval notification to WebSocket client: {e}")
        
        response_data = {
            "status": "success",
            "task_id": task_id,
            "commit_hash": task["commit_info"]["commit_hash"],
            "message": f"Task {task_id} commit approved and finalized",
            "task_status": "approved",
            "github_pushed": task.get("github_pushed", False),
            "github_commit_info": task.get("github_commit_info")
        }
        
        logger.info(f"[APPROVAL] Returning response: {response_data}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error approving task {task_id}: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }