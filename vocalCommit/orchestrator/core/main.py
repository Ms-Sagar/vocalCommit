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
from agents.dev_agent.dev_logic import DevAgent
from agents.security_agent.sec_logic import SecurityAgent
from agents.devops_agent.ops_logic import DevOpsAgent
from utils.thought_signatures import thought_manager
from tools.ui_file_watcher import create_ui_watcher

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
dev_agent = DevAgent()
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

@app.get("/tasks")
async def get_all_tasks():
    """Get manual todos only (not admin workflows)."""
    return {"tasks": list(manual_todos.values())}

@app.get("/admin-workflows")
async def get_admin_workflows():
    """Get admin workflows (pending and completed)."""
    workflows = []
    
    # Add pending workflows
    for task_id, data in pending_approvals.items():
        workflows.append({
            "id": task_id,
            "title": data["transcript"],
            "description": f"Task plan created, waiting for approval to proceed to {data['next_step'].replace('_', ' ')}",
            "status": "pending_approval",
            "priority": "medium",
            "createdAt": "2024-01-23T" + str(len(workflows)).zfill(2) + ":00:00Z",
            "updatedAt": "2024-01-23T" + str(len(workflows)).zfill(2) + ":00:00Z",
            "step": data["step"],
            "next_step": data["next_step"],
            "plan": data.get("plan", {})
        })
    
    # Add completed workflows
    for task_id, data in completed_tasks.items():
        workflows.append(data)
    
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

@app.get("/generate-files/{task_id}")
async def generate_files_to_frontend(task_id: str):
    """Generate files from a completed task to the frontend."""
    if task_id not in completed_tasks:
        return {"error": "Task not found or not completed"}
    
    task = completed_tasks[task_id]
    if "code_files" not in task:
        return {"error": "No code files available for this task"}
    
    try:
        from tools.file_ops import write_to_frontend
        
        generated_files = []
        for filename, content in task["code_files"].items():
            result = write_to_frontend(f"generated/{task_id}/{filename}", content)
            if result["status"] == "success":
                generated_files.append({
                    "filename": filename,
                    "path": result["file_path"],
                    "size": result["size_bytes"]
                })
            else:
                return {"error": f"Failed to write {filename}: {result['error']}"}
        
        return {
            "status": "success",
            "task_id": task_id,
            "generated_files": generated_files,
            "message": f"Generated {len(generated_files)} files for task: {task['title']}"
        }
        
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
    """Process voice commands through the agent system with manual approval."""
    try:
        # Create a task ID for this command
        task_id = f"task_{hash(transcript) % 10000}"
        
        # Handle approval commands
        if command_type == "approval":
            return await handle_approval(transcript, task_id)
        
        # Check if this is a UI editing command
        ui_keywords = ['todo ui', 'todo-ui', 'ui', 'interface', 'frontend', 'change ui', 'modify ui', 'update ui']
        is_ui_command = any(keyword in transcript.lower() for keyword in ui_keywords)
        
        # Step 1: PM Agent creates a plan
        logger.info(f"Processing command with PM Agent: {transcript}")
        pm_result = await pm_agent.plan_task(transcript, is_ui_editing=is_ui_command)
        
        if pm_result["status"] != "success":
            return {
                "status": "error",
                "agent": "PM Agent",
                "response": "Failed to create task plan",
                "transcript": transcript
            }
        
        plan = pm_result["plan"]
        
        # Store for approval with UI editing flag
        pending_approvals[task_id] = {
            "step": "pm_completed",
            "plan": plan,
            "transcript": transcript,
            "next_step": "dev_agent",
            "is_ui_editing": is_ui_command
        }
        
        # Create thought signature for PM Agent
        thought_manager.add_thought(task_id, "PM Agent", {
            "summary": f"Created task plan for: {transcript}",
            "outputs": {"plan": plan},
            "recommendations": ["Proceed with development", "Consider UI/UX implications" if is_ui_command else "Consider security implications"]
        })
        
        ui_indicator = "🎨 **UI Editing Task**" if is_ui_command else "💻 **Code Generation Task**"
        
        return {
            "status": "pending_approval",
            "task_id": task_id,
            "agent": "PM Agent",
            "response": f"📋 **Task Plan Created**\n\n"
                       f"{ui_indicator}\n"
                       f"**Description**: {plan['description']}\n"
                       f"**Priority**: {plan['priority']}\n"
                       f"**Estimated Effort**: {plan['estimated_effort']}\n\n"
                       f"**Breakdown**:\n" + "\n".join([f"• {item}" for item in plan['breakdown']]) + "\n\n"
                       f"⏳ **Waiting for approval to proceed to Dev Agent**\n"
                       f"Use task ID: {task_id}",
            "transcript": transcript,
            "requires_approval": True,
            "next_agent": "Dev Agent",
            "plan_details": plan,
            "is_ui_editing": is_ui_command
        }
        
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        return {
            "status": "error",
            "agent": "Orchestrator",
            "response": f"An error occurred while processing your command: {str(e)}",
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
    """Approve a pending task and proceed to next step."""
    if task_id not in pending_approvals:
        return {
            "status": "error",
            "response": f"No pending approval found for task {task_id}"
        }
    
    approval_data = pending_approvals[task_id]
    current_step = approval_data["step"]
    
    try:
        if current_step == "pm_completed" and approval_data["next_step"] == "dev_agent":
            # Send immediate approval confirmation
            approval_confirmation = {
                "status": "approval_confirmed",
                "task_id": task_id,
                "agent": "System",
                "response": f"✅ **Approval Confirmed**\n\nTask '{approval_data['transcript']}' has been approved.\n\n🔄 **Proceeding to Dev Agent...**\nGenerating code implementation now.",
                "transcript": approval_data["transcript"]
            }
            
            # Proceed to Dev Agent with UI editing flag
            logger.info(f"Approved PM step, proceeding to Dev Agent for task: {task_id}")
            
            plan = approval_data["plan"]
            is_ui_editing = approval_data.get("is_ui_editing", False)
            dev_context = thought_manager.get_context_for_agent(task_id, "Dev Agent")
            
            if is_ui_editing:
                # UI editing workflow - modify existing todo-ui files
                dev_result = await dev_agent.edit_ui_files(plan, json.dumps(dev_context))
            else:
                # Regular code generation workflow
                dev_result = await dev_agent.write_code(plan, json.dumps(dev_context))
            
            if dev_result["status"] != "success":
                del pending_approvals[task_id]
                return {
                    "status": "error",
                    "agent": "Dev Agent",
                    "response": "Failed to generate code",
                    "task_id": task_id
                }
            
            if is_ui_editing:
                # UI editing completed
                modified_files = dev_result.get("modified_files", [])
                
                # Create thought signature for Dev Agent
                thought_manager.add_thought(task_id, "Dev Agent", {
                    "summary": f"Modified UI files for task: {approval_data['transcript']}",
                    "outputs": {"modified_files": modified_files},
                    "recommendations": ["Check UI changes", "Test functionality"]
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
                    "type": "ui_editing"
                }
                
                completed_tasks[task_id] = task_data
                del pending_approvals[task_id]
                
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "agent": "Dev Agent",
                    "response": f"✅ **UI Editing Completed Successfully!**\n\n"
                               f"🎨 **Files Modified**: {len(modified_files)} files\n"
                               f"📁 **Modified Files**: {', '.join(modified_files)}\n"
                               f"🔄 **Auto-reload**: Changes should be visible immediately\n\n"
                               f"**UI Changes Made**:\n" + 
                               "\n".join([f"• {change}" for change in dev_result.get("ui_changes", [])]) + "\n\n"
                               f"🎯 **Task**: {approval_data['transcript']}\n\n"
                               f"🌐 **Check UI**: http://localhost:5174",
                    "transcript": approval_data["transcript"],
                    "modified_files": modified_files,
                    "ui_changes": dev_result.get("ui_changes", [])
                }
            else:
                # Regular code generation workflow
                code_output = dev_result["code_output"]
                
                # Create thought signature for Dev Agent
                thought_manager.add_thought(task_id, "Dev Agent", {
                    "summary": f"Generated code for task: {approval_data['transcript']}",
                    "outputs": {"code": code_output},
                    "recommendations": ["Review code", "Test implementation"]
                })
                
                # Task completed (since Security and DevOps are disabled)
                task_data = {
                    "id": task_id,
                    "title": approval_data["transcript"],
                    "description": f"Generated code for: {approval_data['transcript']}",
                    "status": "completed",
                    "priority": plan.get("priority", "medium"),
                    "createdAt": "2024-01-23T10:00:00Z",
                    "updatedAt": "2024-01-23T" + str(len(completed_tasks) + 10).zfill(2) + ":00:00Z",
                    "files": list(code_output["files"].keys()),
                    "dependencies": code_output["dependencies"],
                    "code_files": code_output["files"],
                    "implementation_notes": code_output["implementation_notes"],
                    "type": "code_generation"
                }
                
                completed_tasks[task_id] = task_data
                del pending_approvals[task_id]
                
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "agent": "Dev Agent",
                    "response": f"✅ **Task Completed Successfully!**\n\n"
                               f"💻 **Code Generated**: {len(code_output['files'])} files\n"
                               f"📁 **Files Created**: {', '.join(code_output['files'].keys())}\n"
                               f"📦 **Dependencies**: {', '.join(code_output['dependencies'])}\n\n"
                               f"**Implementation Notes**:\n" + 
                               "\n".join([f"• {note}" for note in code_output['implementation_notes']]) + "\n\n"
                               f"🎯 **Task**: {approval_data['transcript']}\n\n"
                               f"🎉 **Ready for file generation!** Click 'Generate Files to Frontend' to create the actual files.",
                    "transcript": approval_data["transcript"],
                    "code_files": code_output["files"],
                    "dependencies": code_output["dependencies"]
                }
        
        else:
            return {
                "status": "error",
                "response": f"Unknown approval step: {current_step}"
            }
            
    except Exception as e:
        logger.error(f"Error in approval process: {str(e)}")
        return {
            "status": "error",
            "response": f"Error processing approval: {str(e)}"
        }

async def reject_task(task_id: str) -> dict:
    """Reject a pending task."""
    if task_id not in pending_approvals:
        return {
            "status": "error",
            "response": f"No pending approval found for task {task_id}"
        }
    
    approval_data = pending_approvals[task_id]
    del pending_approvals[task_id]
    
    return {
        "status": "rejected",
        "task_id": task_id,
        "agent": "System",
        "response": f"❌ **Task Rejected**\n\nTask '{approval_data['transcript']}' has been rejected and removed from the queue.\n\n🗑️ **Action**: Task workflow terminated\n📝 **Reason**: Manual rejection by user",
        "transcript": approval_data["transcript"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
