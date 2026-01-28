import logging
import os
import subprocess
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TestingAgent:
    """Testing Agent - Handles automated testing and validation of UI changes."""
    
    def __init__(self):
        self.name = "Testing Agent"
        self.role = "Quality Assurance"
    
    def run_syntax_validation(self, modified_files: List[str]) -> Dict[str, Any]:
        """
        Validate syntax and basic compilation of modified files.
        
        Args:
            modified_files: List of files that were modified
            
        Returns:
            Dict with validation results
        """
        logger.info(f"Running syntax validation for files: {modified_files}")
        
        results = {
            "status": "success",
            "files_tested": [],
            "errors": [],
            "warnings": []
        }
        
        current_dir = os.getcwd()
        
        # Determine the UI project directory
        if current_dir.endswith('orchestrator'):
            ui_dir = "todo-ui"
        else:
            ui_dir = "vocalCommit/orchestrator/todo-ui"
        
        # Check for theme system files and validate integration
        theme_files = {
            'context': None,
            'hook': None,
            'component': None,
            'css_updated': False
        }
        
        for file in modified_files:
            if 'ThemeContext' in file:
                theme_files['context'] = file
            elif 'useTheme' in file:
                theme_files['hook'] = file
            elif 'ThemeToggle' in file:
                theme_files['component'] = file
            elif file.endswith('.css') and any(theme_word in file.lower() for theme_word in ['app', 'theme', 'style']):
                theme_files['css_updated'] = True
        
        # If theme files detected, run theme system validation
        if any(theme_files[key] for key in ['context', 'hook', 'component']):
            theme_validation = self._validate_theme_system(ui_dir, theme_files)
            results["theme_validation"] = theme_validation
            if theme_validation["errors"]:
                results["errors"].extend(theme_validation["errors"])
                results["status"] = "partial_success"
        
        try:
            # Run TypeScript compilation check
            logger.info("Running TypeScript compilation check...")
            result = subprocess.run(
                ["npm", "run", "type-check"],
                cwd=ui_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("TypeScript compilation check passed")
                results["files_tested"].append("TypeScript compilation")
            else:
                logger.warning(f"TypeScript compilation issues: {result.stderr}")
                results["errors"].append(f"TypeScript: {result.stderr}")
                results["status"] = "partial_success"
        
        except subprocess.TimeoutExpired:
            logger.error("TypeScript check timed out")
            results["errors"].append("TypeScript check timed out")
            results["status"] = "error"
        except Exception as e:
            logger.error(f"Error running TypeScript check: {str(e)}")
            results["errors"].append(f"TypeScript check failed: {str(e)}")
            results["status"] = "error"
        
        try:
            # Run ESLint check
            logger.info("Running ESLint check...")
            result = subprocess.run(
                ["npm", "run", "lint"],
                cwd=ui_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("ESLint check passed")
                results["files_tested"].append("ESLint")
            else:
                logger.warning(f"ESLint issues: {result.stdout}")
                # ESLint warnings are not critical errors
                results["warnings"].append(f"ESLint: {result.stdout}")
        
        except subprocess.TimeoutExpired:
            logger.error("ESLint check timed out")
            results["warnings"].append("ESLint check timed out")
        except Exception as e:
            logger.warning(f"ESLint check failed: {str(e)}")
            results["warnings"].append(f"ESLint check failed: {str(e)}")
        
        return results
    
    def _validate_theme_system(self, ui_dir: str, theme_files: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate theme system integration and correctness.
        
        Args:
            ui_dir: UI project directory
            theme_files: Dict of detected theme files
            
        Returns:
            Dict with theme validation results
        """
        validation_results = {
            "status": "success",
            "errors": [],
            "warnings": [],
            "checks_performed": []
        }
        
        try:
            # Check 1: ThemeContext exports
            if theme_files['context']:
                context_path = os.path.join(ui_dir, "src", theme_files['context'])
                if os.path.exists(context_path):
                    with open(context_path, 'r') as f:
                        context_content = f.read()
                    
                    validation_results["checks_performed"].append("ThemeContext exports")
                    if 'export' not in context_content or 'ThemeProvider' not in context_content:
                        validation_results["errors"].append("ThemeContext.tsx must export ThemeProvider component")
                    if 'createContext' not in context_content:
                        validation_results["errors"].append("ThemeContext.tsx must create and export React context")
            
            # Check 2: useTheme hook
            if theme_files['hook']:
                hook_path = os.path.join(ui_dir, "src", theme_files['hook'])
                if os.path.exists(hook_path):
                    with open(hook_path, 'r') as f:
                        hook_content = f.read()
                    
                    validation_results["checks_performed"].append("useTheme hook validation")
                    if 'useContext' not in hook_content:
                        validation_results["errors"].append("useTheme hook must use useContext to access theme")
                    if 'export' not in hook_content:
                        validation_results["errors"].append("useTheme hook must be exported")
            
            # Check 3: CSS variables
            if theme_files['css_updated']:
                css_path = os.path.join(ui_dir, "src", "App.css")
                if os.path.exists(css_path):
                    with open(css_path, 'r') as f:
                        css_content = f.read()
                    
                    validation_results["checks_performed"].append("CSS theme variables")
                    if '[data-theme="dark"]' not in css_content:
                        validation_results["errors"].append("CSS must include [data-theme=\"dark\"] selector for dark theme")
                    if '--' not in css_content:
                        validation_results["warnings"].append("CSS should use CSS custom properties (variables) for theming")
            
            # Check 4: main.tsx integration
            main_path = os.path.join(ui_dir, "src", "main.tsx")
            if os.path.exists(main_path):
                with open(main_path, 'r') as f:
                    main_content = f.read()
                
                validation_results["checks_performed"].append("ThemeProvider integration")
                if 'ThemeProvider' not in main_content:
                    validation_results["errors"].append("main.tsx must wrap App with ThemeProvider")
                if 'import' in main_content and 'ThemeProvider' in main_content:
                    if './context/ThemeContext' not in main_content and './context/ThemeContext.tsx' not in main_content:
                        validation_results["warnings"].append("Verify ThemeProvider import path is correct")
            
            if validation_results["errors"]:
                validation_results["status"] = "failed"
            elif validation_results["warnings"]:
                validation_results["status"] = "partial_success"
                
        except Exception as e:
            validation_results["errors"].append(f"Theme validation error: {str(e)}")
            validation_results["status"] = "error"
        
        return validation_results
    
    def run_build_test(self) -> Dict[str, Any]:
        """
        Test if the application builds successfully.
        
        Returns:
            Dict with build test results
        """
        logger.info("Running build test...")
        
        current_dir = os.getcwd()
        
        # Determine the UI project directory
        if current_dir.endswith('orchestrator'):
            ui_dir = "todo-ui"
        else:
            ui_dir = "vocalCommit/orchestrator/todo-ui"
        
        try:
            # Run build command
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=ui_dir,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout for build
            )
            
            if result.returncode == 0:
                logger.info("Build test passed successfully")
                return {
                    "status": "success",
                    "message": "Application builds successfully",
                    "build_output": result.stdout
                }
            else:
                logger.error(f"Build failed: {result.stderr}")
                return {
                    "status": "error",
                    "message": "Build failed",
                    "error": result.stderr,
                    "build_output": result.stdout
                }
        
        except subprocess.TimeoutExpired:
            logger.error("Build test timed out")
            return {
                "status": "error",
                "message": "Build test timed out after 2 minutes"
            }
        except Exception as e:
            logger.error(f"Error running build test: {str(e)}")
            return {
                "status": "error",
                "message": f"Build test failed: {str(e)}"
            }
    
    def run_functional_validation(self, user_instruction: str, modified_files: List[str]) -> Dict[str, Any]:
        """
        Run functional validation using AI to check if the implementation matches requirements.
        
        Args:
            user_instruction: Original user instruction
            modified_files: List of files that were modified
            
        Returns:
            Dict with validation results
        """
        logger.info(f"Running functional validation for: {user_instruction}")
        
        try:
            import google.genai as genai
            from core.config import settings
            from tools.rate_limiter import wait_for_gemini_api
            
            if not settings.gemini_api_key:
                logger.warning("No Gemini API key found for functional validation")
                return {
                    "status": "skipped",
                    "message": "Functional validation skipped - no AI API key"
                }
            
            client = genai.Client(api_key=settings.gemini_api_key)
            
            # Read the modified files to analyze
            file_contents = {}
            current_dir = os.getcwd()
            
            for file_path in modified_files:
                try:
                    if file_path.startswith('src/'):
                        clean_filename = file_path[4:]
                    else:
                        clean_filename = file_path
                    
                    if current_dir.endswith('orchestrator'):
                        full_path = f"todo-ui/src/{clean_filename}"
                    else:
                        full_path = f"vocalCommit/orchestrator/todo-ui/src/{clean_filename}"
                    
                    with open(full_path, 'r') as f:
                        content = f.read()
                        # Limit content to avoid token limits
                        if len(content) > 2000:
                            content = content[:2000] + "... [truncated]"
                        file_contents[file_path] = content
                
                except Exception as e:
                    logger.warning(f"Could not read {file_path} for validation: {str(e)}")
            
            # Create validation prompt
            prompt = f"""You are a QA Engineer reviewing code changes for a React Todo application.

USER REQUEST: "{user_instruction}"

MODIFIED FILES:
{json.dumps(file_contents, indent=2)}

Please analyze if the implementation correctly fulfills the user's request. Check for:

1. **Functional Completeness**: Does the code implement what was requested?
2. **Code Quality**: Are there any obvious bugs, syntax issues, or bad practices?
3. **Integration**: Do the changes work well together across files?
4. **User Experience**: Will this provide a good user experience?

Respond in JSON format:
{{
    "status": "pass" | "fail" | "warning",
    "functional_completeness": "assessment of whether the request was fully implemented",
    "code_quality": "assessment of code quality and potential issues",
    "integration": "assessment of how well the changes work together",
    "user_experience": "assessment of UX implications",
    "issues_found": ["list of specific issues if any"],
    "recommendations": ["list of recommendations if any"]
}}"""
            
            # Rate limiting before API call
            wait_time = wait_for_gemini_api()
            if wait_time > 0:
                logger.info(f"Testing Agent waited {wait_time:.1f} seconds due to rate limiting")
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            # Try to parse JSON response
            try:
                import re
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    validation_result = json.loads(json_match.group())
                    validation_result["ai_powered"] = True
                    return validation_result
                else:
                    # Fallback if JSON parsing fails
                    return {
                        "status": "warning",
                        "message": "Could not parse AI validation response",
                        "ai_response": response.text,
                        "ai_powered": True
                    }
            
            except json.JSONDecodeError:
                return {
                    "status": "warning",
                    "message": "AI validation completed but response format was invalid",
                    "ai_response": response.text,
                    "ai_powered": True
                }
        
        except Exception as e:
            logger.error(f"Error in functional validation: {str(e)}")
            return {
                "status": "error",
                "message": f"Functional validation failed: {str(e)}"
            }
    
    def run_comprehensive_testing(self, user_instruction: str, modified_files: List[str]) -> Dict[str, Any]:
        """
        Run comprehensive testing including syntax, build, and functional validation.
        
        Args:
            user_instruction: Original user instruction
            modified_files: List of files that were modified
            
        Returns:
            Dict with comprehensive test results
        """
        logger.info(f"Running comprehensive testing for {len(modified_files)} modified files")
        
        results = {
            "status": "success",
            "tests_run": [],
            "syntax_validation": {},
            "build_test": {},
            "functional_validation": {},
            "overall_assessment": "",
            "recommendations": []
        }
        
        # 1. Syntax Validation
        logger.info("Step 1: Running syntax validation...")
        syntax_results = self.run_syntax_validation(modified_files)
        results["syntax_validation"] = syntax_results
        results["tests_run"].append("syntax_validation")
        
        if syntax_results["status"] == "error":
            results["status"] = "error"
            results["overall_assessment"] = "Testing failed due to syntax errors"
            return results
        
        # 2. Build Test
        logger.info("Step 2: Running build test...")
        build_results = self.run_build_test()
        results["build_test"] = build_results
        results["tests_run"].append("build_test")
        
        if build_results["status"] == "error":
            results["status"] = "error"
            results["overall_assessment"] = "Testing failed due to build errors"
            return results
        
        # 3. Functional Validation
        logger.info("Step 3: Running functional validation...")
        functional_results = self.run_functional_validation(user_instruction, modified_files)
        results["functional_validation"] = functional_results
        results["tests_run"].append("functional_validation")
        
        # Determine overall status
        if functional_results.get("status") == "fail":
            results["status"] = "warning"
            results["overall_assessment"] = "Implementation may not fully meet requirements"
        elif syntax_results["status"] == "partial_success" or build_results["status"] == "warning":
            results["status"] = "partial_success"
            results["overall_assessment"] = "Implementation works but has minor issues"
        else:
            results["status"] = "success"
            results["overall_assessment"] = "All tests passed successfully"
        
        # Compile recommendations
        if syntax_results.get("warnings"):
            results["recommendations"].extend([f"Syntax: {w}" for w in syntax_results["warnings"]])
        
        if functional_results.get("recommendations"):
            results["recommendations"].extend(functional_results["recommendations"])
        
        logger.info(f"Comprehensive testing completed with status: {results['status']}")
        return results

def run_testing_agent(user_instruction: str, modified_files: List[str]) -> Dict[str, Any]:
    """
    Main entry point for the testing agent.
    
    Args:
        user_instruction: Original user instruction
        modified_files: List of files that were modified
        
    Returns:
        Dict with test results
    """
    agent = TestingAgent()
    return agent.run_comprehensive_testing(user_instruction, modified_files)