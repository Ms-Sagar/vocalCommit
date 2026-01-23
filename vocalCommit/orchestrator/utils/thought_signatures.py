from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class ThoughtSignature:
    """Represents context and insights passed between agents."""
    
    def __init__(self, agent_name: str, task_id: str, content: Dict[str, Any]):
        self.agent_name = agent_name
        self.task_id = task_id
        self.content = content
        self.timestamp = datetime.utcnow().isoformat()
        self.signature_id = f"{agent_name}_{task_id}_{hash(str(content)) % 10000}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert thought signature to dictionary."""
        return {
            "signature_id": self.signature_id,
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        """Convert thought signature to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThoughtSignature':
        """Create ThoughtSignature from dictionary."""
        signature = cls(
            agent_name=data["agent_name"],
            task_id=data["task_id"],
            content=data["content"]
        )
        signature.timestamp = data.get("timestamp", signature.timestamp)
        signature.signature_id = data.get("signature_id", signature.signature_id)
        return signature

class ThoughtChain:
    """Manages a chain of thought signatures for a task."""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.signatures: List[ThoughtSignature] = []
        self.created_at = datetime.utcnow().isoformat()
    
    def add_signature(self, signature: ThoughtSignature):
        """Add a thought signature to the chain."""
        if signature.task_id != self.task_id:
            raise ValueError(f"Signature task_id {signature.task_id} doesn't match chain task_id {self.task_id}")
        
        self.signatures.append(signature)
        logger.info(f"Added signature from {signature.agent_name} to chain {self.task_id}")
    
    def get_context_for_agent(self, agent_name: str) -> Dict[str, Any]:
        """Get relevant context for a specific agent."""
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
        """Get the most recent thought signature."""
        return self.signatures[-1] if self.signatures else None
    
    def get_signature_by_agent(self, agent_name: str) -> Optional[ThoughtSignature]:
        """Get the most recent signature from a specific agent."""
        for signature in reversed(self.signatures):
            if signature.agent_name == agent_name:
                return signature
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert thought chain to dictionary."""
        return {
            "task_id": self.task_id,
            "created_at": self.created_at,
            "signatures": [sig.to_dict() for sig in self.signatures],
            "signature_count": len(self.signatures)
        }

class ThoughtManager:
    """Global manager for thought signatures and chains."""
    
    def __init__(self):
        self.chains: Dict[str, ThoughtChain] = {}
    
    def create_chain(self, task_id: str) -> ThoughtChain:
        """Create a new thought chain for a task."""
        if task_id in self.chains:
            logger.warning(f"Chain {task_id} already exists, returning existing chain")
            return self.chains[task_id]
        
        chain = ThoughtChain(task_id)
        self.chains[task_id] = chain
        logger.info(f"Created new thought chain for task {task_id}")
        return chain
    
    def get_chain(self, task_id: str) -> Optional[ThoughtChain]:
        """Get an existing thought chain."""
        return self.chains.get(task_id)
    
    def add_thought(self, task_id: str, agent_name: str, content: Dict[str, Any]) -> ThoughtSignature:
        """Add a thought signature to a task chain."""
        chain = self.get_chain(task_id)
        if not chain:
            chain = self.create_chain(task_id)
        
        signature = ThoughtSignature(agent_name, task_id, content)
        chain.add_signature(signature)
        
        return signature
    
    def get_context_for_agent(self, task_id: str, agent_name: str) -> Dict[str, Any]:
        """Get context for an agent working on a specific task."""
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
    """Convenience function to create and store a thought signature."""
    signature = thought_manager.add_thought(task_id, agent_name, content)
    return signature.to_json()

def get_agent_context(task_id: str, agent_name: str) -> Dict[str, Any]:
    """Convenience function to get context for an agent."""
    return thought_manager.get_context_for_agent(task_id, agent_name)
