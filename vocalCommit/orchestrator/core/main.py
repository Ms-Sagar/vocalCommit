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

# Initialize agents
pm_agent = PMAgent()
dev_agent = DevAgent()
security_agent = SecurityAgent()
devops_agent = DevOpsAgent()

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
    """Process voice commands through the agent system."""
    try:
        # Create a task ID for this command
        task_id = f"task_{hash(transcript) % 10000}"
        
        # Step 1: PM Agent creates a plan
        logger.info(f"Processing command with PM Agent: {transcript}")
        pm_result = await pm_agent.plan_task(transcript)
        
        if pm_result["status"] != "success":
            return {
                "status": "error",
                "agent": "PM Agent",
                "response": "Failed to create task plan",
                "transcript": transcript
            }
        
        plan = pm_result["plan"]
        
        # Create thought signature for PM Agent
        thought_manager.add_thought(task_id, "PM Agent", {
            "summary": f"Created task plan for: {transcript}",
            "outputs": {"plan": plan},
            "recommendations": ["Proceed with development", "Consider security implications"]
        })
        
        # Step 2: Dev Agent generates code based on plan
        logger.info(f"Processing with Dev Agent for task: {task_id}")
        dev_context = thought_manager.get_context_for_agent(task_id, "Dev Agent")
        dev_result = await dev_agent.write_code(plan, json.dumps(dev_context))
        
        if dev_result["status"] != "success":
            return {
                "status": "error",
                "agent": "Dev Agent", 
                "response": "Failed to generate code",
                "transcript": transcript
            }
        
        code_output = dev_result["code_output"]
        
        # Create thought signature for Dev Agent
        thought_manager.add_thought(task_id, "Dev Agent", {
            "summary": f"Generated code for task: {transcript}",
            "outputs": {"code": code_output},
            "recommendations": ["Run security scan", "Prepare for deployment"]
        })
        
        # Step 3: Security Agent scans the generated code
        logger.info(f"Processing with Security Agent for task: {task_id}")
        main_code = code_output["files"].get("main.py", "")
        security_result = await security_agent.scan_code(main_code)
        
        # Create thought signature for Security Agent
        thought_manager.add_thought(task_id, "Security Agent", {
            "summary": f"Security scan completed for task: {transcript}",
            "outputs": {"security_report": security_result["scan_results"]},
            "recommendations": security_result["scan_results"]["recommendations"]
        })
        
        # Step 4: DevOps Agent creates deployment config
        logger.info(f"Processing with DevOps Agent for task: {task_id}")
        devops_result = await devops_agent.create_deployment_config(code_output["structure"])
        
        # Create thought signature for DevOps Agent
        thought_manager.add_thought(task_id, "DevOps Agent", {
            "summary": f"Deployment configuration created for task: {transcript}",
            "outputs": {"deployment": devops_result["deployment_config"]},
            "recommendations": ["Review configuration", "Deploy to staging first"]
        })
        
        # Compile final response
        return {
            "status": "success",
            "task_id": task_id,
            "agent": "Orchestrator",
            "response": f"✅ Task completed successfully!\n\n"
                       f"📋 **Plan**: {plan['description']}\n"
                       f"💻 **Code Generated**: {len(code_output['files'])} files\n"
                       f"🔒 **Security Risk**: {security_result['scan_results']['risk_level']}\n"
                       f"🚀 **Deployment**: {devops_result['deployment_config']['infrastructure']['cloud_provider']} ready\n\n"
                       f"All agents have processed your request: '{transcript}'",
            "transcript": transcript,
            "details": {
                "plan": plan,
                "code_files": list(code_output["files"].keys()),
                "security_findings": len(security_result["scan_results"]["findings"]),
                "deployment_ready": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        return {
            "status": "error",
            "agent": "Orchestrator",
            "response": f"An error occurred while processing your command: {str(e)}",
            "transcript": transcript
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
