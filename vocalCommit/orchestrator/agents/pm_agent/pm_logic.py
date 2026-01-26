from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class PMAgent:
    """Project Management Agent - Handles task planning and project coordination."""
    
    def __init__(self):
        self.name = "PM Agent"
        self.role = "Project Manager"
    
    async def plan_task(self, transcript: str, is_ui_editing: bool = False) -> Dict[str, Any]:
        """
        Analyze voice transcript and create a structured task plan using Gemini AI.
        
        Args:
            transcript: Voice command transcript
            is_ui_editing: Whether this is a UI editing task
            
        Returns:
            Dict containing task breakdown, priorities, and dependencies
        """
        logger.info(f"PM Agent processing transcript with Gemini AI: {transcript} (UI Editing: {is_ui_editing})")
        
        try:
            import google.generativeai as genai
            from core.config import settings
            
            # Configure Gemini API
            if not settings.gemini_api_key:
                logger.warning("No Gemini API key found, using fallback response")
                return self._fallback_plan(transcript, is_ui_editing)
            
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
                # Create specialized prompt based on task type
            if is_ui_editing:
                prompt = f"""
                As a Senior UI/UX Designer and Frontend Developer, analyze this UI modification request for a React Todo application:
                
                Request: "{transcript}"
                
                Current Todo UI Structure:
                - src/App.tsx: Main React component with todo logic
                - src/App.css: Styling for all UI components
                - src/index.css: Global styles
                - src/components/: Additional React components
                
                Current Features:
                - Manual todo creation and management
                - Status filtering (all, pending, in-progress, completed)
                - Priority levels (low, medium, high)
                - Real-time updates every 10 seconds
                - CRUD operations for todos
                - Modal for adding new todos
                - Statistics dashboard
                
                Please provide a structured response in JSON format with:
                {{
                    "description": "Clear description of the UI changes needed",
                    "priority": "low/medium/high",
                    "estimated_effort": "e.g., 30 minutes, 1-2 hours",
                    "breakdown": ["step1", "step2", "step3", "step4"],
                    "target_files": ["list of files that need modification"],
                    "dependencies": ["react", "css", etc],
                    "ui_considerations": "accessibility, responsiveness, UX notes"
                }}
                
                IMPORTANT: For target_files, consider:
                - If adding new UI elements or modifying layout: include both src/App.tsx AND src/App.css
                - If adding dark mode/theming: include src/App.tsx, src/App.css, and potentially src/index.css
                - If creating new components: include src/components/ComponentName.tsx and related CSS
                - If modifying existing functionality: identify the specific files that need changes
                
                Focus on practical, actionable steps and identify ALL files that need modification.
                """
            else:
                prompt = f"""
                As a Senior Project Manager, analyze this development request and create a detailed task plan:
                
                Request: "{transcript}"
                
                Please provide a structured response in JSON format with:
                1. A clear description of what needs to be built
                2. Priority level (low/medium/high)
                3. Estimated effort (e.g., "2-4 hours", "1-2 days")
                4. Detailed breakdown of implementation steps (4-6 steps)
                5. Key dependencies/technologies needed
                6. Potential challenges or considerations
                
                Focus on practical, actionable steps for a development team.
                """
            
            response = model.generate_content(prompt)
            
            # Try to parse JSON response, fallback if needed
            try:
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    ai_response = json.loads(json_match.group())
                else:
                    # If no JSON found, create structured response from text
                    ai_response = self._parse_text_response(response.text, transcript, is_ui_editing)
                
                plan = {
                    "task_id": f"task_{hash(transcript) % 10000}",
                    "description": ai_response.get("description", transcript),
                    "breakdown": ai_response.get("breakdown", self._extract_steps(response.text, is_ui_editing)),
                    "priority": ai_response.get("priority", "medium"),
                    "estimated_effort": ai_response.get("estimated_effort", "1-2 hours" if is_ui_editing else "2-4 hours"),
                    "dependencies": ai_response.get("dependencies", []),
                    "assigned_agents": ["dev_agent"],
                    "ai_insights": response.text[:500] + "..." if len(response.text) > 500 else response.text,
                    "is_ui_editing": is_ui_editing,
                    "target_files": self._determine_target_files(ai_response.get("target_files", []), transcript, is_ui_editing)
                }
                
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Could not parse Gemini response as JSON: {e}")
                plan = self._parse_text_response(response.text, transcript, is_ui_editing)
            
            return {
                "status": "success",
                "agent": self.name,
                "plan": plan,
                "ai_powered": True
            }
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return self._fallback_plan(transcript, is_ui_editing)
    
    def _fallback_plan(self, transcript: str, is_ui_editing: bool = False) -> Dict[str, Any]:
        """Fallback plan when Gemini API is not available."""
        if is_ui_editing:
            plan = {
                "task_id": f"task_{hash(transcript) % 10000}",
                "description": transcript,
                "breakdown": [
                    "Analyze current UI structure and components",
                    "Identify specific elements to modify",
                    "Update React components with new features",
                    "Test UI changes and responsiveness",
                    "Verify accessibility and user experience"
                ],
                "priority": "medium",
                "estimated_effort": "1-2 hours",
                "dependencies": ["react", "typescript"],
                "assigned_agents": ["dev_agent"],
                "ai_powered": False,
                "is_ui_editing": True,
                "target_files": self._determine_target_files([], transcript, is_ui_editing)
            }
        else:
            plan = {
                "task_id": f"task_{hash(transcript) % 10000}",
                "description": transcript,
                "breakdown": [
                    "Analyze requirements",
                    "Design solution architecture", 
                    "Implement core functionality",
                    "Add testing and validation",
                    "Deploy and document"
                ],
                "priority": "medium",
                "estimated_effort": "2-4 hours",
                "dependencies": [],
                "assigned_agents": ["dev_agent"],
                "ai_powered": False,
                "is_ui_editing": False
            }
        
        return {
            "status": "success",
            "agent": self.name,
            "plan": plan
        }
    
    def _parse_text_response(self, text: str, transcript: str, is_ui_editing: bool = False) -> Dict[str, Any]:
        """Parse text response when JSON parsing fails."""
        return {
            "task_id": f"task_{hash(transcript) % 10000}",
            "description": transcript,
            "breakdown": self._extract_steps(text, is_ui_editing),
            "priority": self._extract_priority(text),
            "estimated_effort": self._extract_effort(text, is_ui_editing),
            "dependencies": self._extract_dependencies(text, is_ui_editing),
            "assigned_agents": ["dev_agent"],
            "ai_insights": text[:300] + "..." if len(text) > 300 else text,
            "is_ui_editing": is_ui_editing,
            "target_files": self._determine_target_files([], transcript, is_ui_editing)
        }
    
    def _extract_steps(self, text: str, is_ui_editing: bool = False) -> list:
        """Extract implementation steps from text."""
        import re
        steps = re.findall(r'(?:^\d+\.|\-|\*)\s*(.+)', text, re.MULTILINE)
        if steps and len(steps) >= 3:
            return steps[:6]  # Limit to 6 steps
        
        if is_ui_editing:
            return [
                "Analyze current UI structure and identify modification points",
                "Update React components with requested changes",
                "Modify styling and layout as needed",
                "Test UI changes for responsiveness and accessibility",
                "Verify functionality and user experience"
            ]
        else:
            return [
                "Analyze requirements from the request",
                "Design the solution architecture",
                "Implement core functionality",
                "Add testing and validation",
                "Deploy and document the solution"
            ]
    
    def _extract_priority(self, text: str) -> str:
        """Extract priority from text."""
        text_lower = text.lower()
        if 'high' in text_lower or 'urgent' in text_lower or 'critical' in text_lower:
            return 'high'
        elif 'low' in text_lower or 'minor' in text_lower:
            return 'low'
        return 'medium'
    
    def _extract_effort(self, text: str, is_ui_editing: bool = False) -> str:
        """Extract effort estimate from text."""
        import re
        effort_patterns = [
            r'(\d+[-–]\d+\s*(?:hours?|days?|weeks?))',
            r'(\d+\s*(?:hours?|days?|weeks?))',
        ]
        
        for pattern in effort_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "1-2 hours" if is_ui_editing else "2-4 hours"
    
    def _extract_dependencies(self, text: str, is_ui_editing: bool = False) -> list:
        """Extract dependencies from text."""
        import re
        
        if is_ui_editing:
            # UI editing typically involves React/TypeScript
            return ["react", "typescript", "css"]
        
        # Look for common technology mentions
        tech_patterns = [
            r'\b(react|vue|angular|node|python|django|flask|fastapi|express)\b',
            r'\b(postgresql|mysql|mongodb|redis|sqlite)\b',
            r'\b(docker|kubernetes|aws|gcp|azure)\b'
        ]
        
        dependencies = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dependencies.extend([match.lower() for match in matches])
        
        return list(set(dependencies))  # Remove duplicates
    
    def _determine_target_files(self, ai_suggested_files: list, transcript: str, is_ui_editing: bool = False) -> list:
        """Intelligently determine which files need to be modified based on the request."""
        if not is_ui_editing:
            return ai_suggested_files or []
        
        # Start with AI suggestions if available
        target_files = set(ai_suggested_files) if ai_suggested_files else set()
        
        # Analyze transcript for file requirements
        transcript_lower = transcript.lower()
        
        # Always include App.tsx for UI changes
        target_files.add("src/App.tsx")
        
        # Determine if CSS changes are needed
        css_keywords = [
            'style', 'styling', 'color', 'theme', 'dark mode', 'light mode',
            'background', 'font', 'size', 'layout', 'design', 'appearance',
            'css', 'responsive', 'mobile', 'desktop', 'button', 'modal',
            'animation', 'transition', 'hover', 'focus', 'border', 'shadow'
        ]
        
        if any(keyword in transcript_lower for keyword in css_keywords):
            target_files.add("src/App.css")
        
        # Determine if global styles are needed
        global_keywords = [
            'global', 'entire app', 'whole application', 'site-wide',
            'root', 'body', 'html', 'font family', 'base styles'
        ]
        
        if any(keyword in transcript_lower for keyword in global_keywords):
            target_files.add("src/index.css")
        
        # Determine if new components are needed
        component_keywords = [
            'new component', 'create component', 'add component',
            'separate component', 'reusable component', 'component for'
        ]
        
        if any(keyword in transcript_lower for keyword in component_keywords):
            # For now, we'll stick to modifying existing files
            # In the future, this could create new component files
            pass
        
        # Specific feature-based file determination
        if 'dark mode' in transcript_lower or 'theme' in transcript_lower:
            target_files.update(["src/App.tsx", "src/App.css"])
        
        if 'modal' in transcript_lower or 'popup' in transcript_lower:
            target_files.update(["src/App.tsx", "src/App.css"])
        
        if 'navigation' in transcript_lower or 'header' in transcript_lower or 'footer' in transcript_lower:
            target_files.update(["src/App.tsx", "src/App.css"])
        
        # Convert back to list and ensure we have at least one file
        result = list(target_files)
        if not result and is_ui_editing:
            result = ["src/App.tsx"]
        
        return result
    
    async def update_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        """Update task status and notify stakeholders."""
        logger.info(f"Updating task {task_id} status to {status}")
        
        return {
            "task_id": task_id,
            "status": status,
            "updated_by": self.name
        }
