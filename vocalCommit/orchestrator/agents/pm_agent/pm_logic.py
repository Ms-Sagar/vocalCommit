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
            import google.genai as genai
            from core.config import settings
            from tools.rate_limiter import wait_for_gemini_api, get_gemini_api_status
            
            # Configure Gemini API
            if not settings.gemini_api_key:
                logger.warning("No Gemini API key found, using fallback response")
                return self._fallback_plan(transcript, is_ui_editing)
            
            client = genai.Client(api_key=settings.gemini_api_key)
            
            # Check rate limit status before proceeding
            rate_status = get_gemini_api_status()
            if rate_status['remaining_requests'] == 0:
                wait_time = rate_status.get('reset_in_seconds', 0)
                logger.info(f"PM Agent rate limited, will wait {wait_time:.1f} seconds")
            
            # Create specialized prompt based on task type
            if is_ui_editing:
                prompt = f"""
                As a Senior UI/UX Designer and Frontend Developer, analyze this UI modification request for a PRODUCTION React Todo application:
                
                Request: "{transcript}"
                
                CRITICAL: This is for a LIVE PRODUCTION SERVICE. Code will be deployed directly with automatic dependency management.
                
                Current Todo UI Structure:
                - src/App.tsx: Main React component with todo logic
                - src/App.css: Styling for all UI components
                - src/index.css: Global styles
                - src/components/: Additional React components
                - src/hooks/: Custom React hooks
                - src/context/: React context providers
                
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
                    "target_files": ["list of EXACT filenames - NO SENTENCES, NO DESCRIPTIONS"],
                    "dependencies": ["react", "css", etc],
                    "ui_considerations": "accessibility, responsiveness, UX notes"
                }}
                
                FILENAME RULES FOR target_files:
                - Use EXACT filenames only: "ThemeToggle.tsx", "useTheme.ts", "ThemeContext.tsx"
                - NO sentences: ❌ "create a theme toggle component"
                - NO descriptions: ❌ "component for theme switching"
                - NO wildcards: ❌ "*.tsx", ❌ "all components"
                - Follow naming conventions:
                  * Components: "ComponentName.tsx"
                  * Hooks: "useHookName.ts" 
                  * Context: "ContextNameContext.tsx"
                  * CSS: "ComponentName.css"
                
                THEME SYSTEM REQUIREMENTS (for dark mode, theming, color scheme requests):
                - Theme systems require React Context Provider pattern
                - Must create files in this order: Context → Hook → Component → CSS
                - Required files for theme system:
                  * "ThemeContext.tsx" (Context provider with state)
                  * "useTheme.ts" (Custom hook to consume context)
                  * "ThemeToggle.tsx" (UI component for switching)
                  * Update "App.css" (CSS variables with [data-theme] selectors)
                  * Update "main.tsx" (wrap App with ThemeProvider)
                - CSS variables must use [data-theme="dark"] and [data-theme="light"] selectors
                - Theme state must be applied via data-theme attribute on document element
                - All CSS variables need fallback values
                - Theme preference should persist in localStorage
                
                PRODUCTION CONSIDERATIONS:
                - Code must be immediately deployable
                - All functionality must be complete (no TODOs)
                - Include proper error handling and accessibility
                - Consider mobile responsiveness
                - Use TypeScript best practices
                
                Focus on practical, actionable steps with EXACT filenames only.
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
            
            # Rate limiting before API call
            wait_time = wait_for_gemini_api()
            if wait_time > 0:
                logger.info(f"PM Agent waited {wait_time:.1f} seconds due to rate limiting")
            
            # Log the API call attempt
            logger.info(f"PM Agent calling Gemini API for task planning...")
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            logger.info(f"PM Agent received Gemini response: {len(response.text) if response and response.text else 0} characters")
            
            # Try to parse JSON response, fallback if needed
            try:
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    ai_response = json.loads(json_match.group())
                    logger.info(f"PM Agent successfully parsed JSON response")
                else:
                    # If no JSON found, create structured response from text
                    logger.warning(f"PM Agent could not find JSON in response, parsing text")
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
                
                logger.info(f"PM Agent created plan with {len(plan.get('target_files', []))} target files")
                
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
            error_str = str(e)
            
            # Check if it's a rate limit error
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                logger.error(f"❌ Gemini API Rate Limit: 429 RESOURCE_EXHAUSTED")
                logger.error("🔑 ACTION REQUIRED: Update GEMINI_API_KEY in vocalCommit/orchestrator/.env")
                
                # Return error instead of fallback for rate limit issues
                return {
                    "status": "error",
                    "agent": self.name,
                    "error": "api_rate_limit",
                    "message": (
                        "🚫 Gemini API rate limit exceeded (429 RESOURCE_EXHAUSTED). "
                        "Please update your API key in the .env file and restart the orchestrator."
                    )
                }
            else:
                logger.error(f"Error calling Gemini API: {error_str}")
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
        
        # Start with AI suggestions if available and sanitize them
        target_files = set()
        if ai_suggested_files:
            for file in ai_suggested_files:
                # Import the sanitize function
                from agents.dev_agent.dev_logic import sanitize_filename
                sanitized = sanitize_filename(file)
                target_files.add(sanitized)
        
        # Analyze transcript for file requirements
        transcript_lower = transcript.lower()
        
        # Always include App.tsx for UI changes
        target_files.add("App.tsx")
        
        # Determine if CSS changes are needed
        css_keywords = [
            'style', 'styling', 'color', 'theme', 'dark mode', 'light mode',
            'background', 'font', 'size', 'layout', 'design', 'appearance',
            'css', 'responsive', 'mobile', 'desktop', 'button', 'modal',
            'animation', 'transition', 'hover', 'focus', 'border', 'shadow'
        ]
        
        if any(keyword in transcript_lower for keyword in css_keywords):
            target_files.add("App.css")
        
        # Determine if global styles are needed
        global_keywords = [
            'global', 'entire app', 'whole application', 'site-wide',
            'root', 'body', 'html', 'font family', 'base styles'
        ]
        
        if any(keyword in transcript_lower for keyword in global_keywords):
            target_files.add("index.css")
        
        # Determine if new components are needed
        component_keywords = [
            'new component', 'create component', 'add component',
            'separate component', 'reusable component', 'component for'
        ]
        
        if any(keyword in transcript_lower for keyword in component_keywords):
            # Extract component name from transcript
            import re
            patterns = [
                r'create\s+(?:a\s+)?(\w+)\s+component',
                r'add\s+(?:a\s+)?(\w+)\s+component', 
                r'new\s+(\w+)\s+component',
                r'(\w+)\s+component',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, transcript_lower)
                if match:
                    component_name = match.group(1).capitalize()
                    target_files.add(f"components/{component_name}.tsx")
                    target_files.add(f"components/{component_name}.css")
                    break
        
        # Specific feature-based file determination
        if 'dark mode' in transcript_lower or 'theme' in transcript_lower:
            target_files.update(["App.tsx", "App.css"])
            # Add theme-related files
            if 'context' in transcript_lower or 'provider' in transcript_lower:
                target_files.add("context/ThemeContext.tsx")
            if 'hook' in transcript_lower:
                target_files.add("hooks/useTheme.ts")
        
        if 'modal' in transcript_lower or 'popup' in transcript_lower:
            target_files.update(["App.tsx", "App.css"])
        
        if 'navigation' in transcript_lower or 'header' in transcript_lower or 'footer' in transcript_lower:
            target_files.update(["App.tsx", "App.css"])
        
        # Convert back to list and ensure we have at least one file
        result = list(target_files)
        if not result and is_ui_editing:
            result = ["App.tsx"]
        
        return result
    
    async def update_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        """Update task status and notify stakeholders."""
        logger.info(f"Updating task {task_id} status to {status}")
        
        return {
            "task_id": task_id,
            "status": status,
            "updated_by": self.name
        }
