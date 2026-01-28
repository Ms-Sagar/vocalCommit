import google.genai as genai
from core.config import settings
from tools.dependency_manager import handle_code_dependencies
from tools.rate_limiter import wait_for_gemini_api
import logging
import os
import re

logger = logging.getLogger(__name__)

# Configure Gemini API
client = genai.Client(api_key=settings.gemini_api_key)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent sentence-like names and ensure proper format.
    
    Args:
        filename: Original filename that might contain sentences or invalid chars
        
    Returns:
        str: Sanitized filename with proper format
    """
    # If filename looks like a sentence (contains spaces and is long), extract meaningful parts
    if ' ' in filename and len(filename) > 15:
        # Try to extract a meaningful filename from a sentence
        # Look for patterns like "create a ThemeToggle component" -> "ThemeToggle"
        
        # Common patterns to extract component names
        patterns = [
            r'create\s+(?:a\s+)?(\w+(?:\w+)*)\s+component',  # Capture full camelCase names
            r'add\s+(?:a\s+)?(?:new\s+)?(\w+(?:\w+)*)\s+component',
            r'new\s+(\w+(?:\w+)*)\s+component',
            r'(\w+(?:\w+)*)\s+component',
            r'create\s+(\w+(?:\w+)*)\s+(?:css|styles)',
            r'(\w+(?:\w+)*)\s+(?:css|styles)',
            r'new\s+(use\w+(?:\w+)*)\s+hook',
            r'(use\w+(?:\w+)*)\s+hook',
            r'create\s+(\w+(?:\w+)*Context)\s+provider',
            r'(\w+(?:\w+)*Context)\s+provider',
            r'create\s+(\w+(?:\w+)*)',
            r'add\s+(\w+(?:\w+)*)',
            r'new\s+(\w+(?:\w+)*)',
        ]
        
        filename_lower = filename.lower()
        for pattern in patterns:
            match = re.search(pattern, filename_lower)
            if match:
                # Find the same match in the original string to preserve case
                original_match = re.search(pattern, filename, re.IGNORECASE)
                if original_match:
                    component_name = original_match.group(1)
                else:
                    component_name = match.group(1)
                
                # Preserve camelCase and capitalize properly
                if component_name.startswith('use'):
                    # Hook: useTheme
                    if component_name.lower() != component_name:
                        # Already has proper casing
                        component_name = component_name
                    else:
                        component_name = 'use' + component_name[3:].capitalize()
                elif component_name.lower().endswith('context'):
                    # Context: ThemeContext
                    if 'Context' in component_name:
                        component_name = component_name
                    else:
                        base_name = component_name[:-7].capitalize()
                        component_name = base_name + 'Context'
                else:
                    # Regular component: preserve camelCase if present, otherwise capitalize
                    if any(c.isupper() for c in component_name[1:]):
                        # Already has camelCase
                        component_name = component_name[0].upper() + component_name[1:]
                    else:
                        component_name = component_name.capitalize()
                
                # Determine file extension based on context
                if 'css' in filename_lower or 'style' in filename_lower:
                    return f"{component_name}.css"
                elif 'hook' in filename_lower or component_name.startswith('use'):
                    return f"{component_name}.ts"
                elif 'context' in filename_lower or component_name.endswith('Context'):
                    return f"{component_name}.tsx"
                else:
                    return f"{component_name}.tsx"
    
    # Handle wildcard patterns
    if filename.startswith('*'):
        # Extract meaningful part after wildcard
        if 'css' in filename.lower():
            return "Styles.css"
        elif 'tsx' in filename.lower() or 'component' in filename.lower():
            return "Component.tsx"
        elif 'ts' in filename.lower():
            return "Utils.ts"
        else:
            return "File.tsx"
    
    # Remove invalid characters
    sanitized = re.sub(r'[*?<>|"()[\]{}]', '', filename)
    
    # Replace spaces and special chars with appropriate separators
    sanitized = re.sub(r'[\s\-_]+', '', sanitized)
    
    # Ensure it has a proper extension
    if not any(sanitized.endswith(ext) for ext in ['.tsx', '.ts', '.jsx', '.js', '.css', '.html', '.json']):
        # Default to .tsx for React components
        if not sanitized.endswith('.'):
            sanitized += '.tsx'
        else:
            sanitized += 'tsx'
    
    # Ensure it starts with a letter and follows naming conventions
    if not re.match(r'^[A-Za-z]', sanitized):
        sanitized = 'Component' + sanitized
    
    return sanitized

def run_dev_agent(target_filename, user_instruction, related_files=None, file_context=None):
    """
    The Dev Agent: "The Surgeon"
    
    This function implements the "Need-to-Know" architecture with multi-file awareness:
    1. Reads the target file and related files for context
    2. Sends contextual information to Gemini for better coordination
    3. Overwrites the file with the complete rewritten version
    
    Args:
        target_filename: The specific file to modify (e.g., "App.css")
        user_instruction: What the user wants done (e.g., "Make the button blue")
        related_files: List of other files being modified in this task
        file_context: Dict of related file contents for context
    
    Returns:
        Success message or error
    """
    # Sanitize filename first to handle sentence-like names
    original_filename = target_filename
    target_filename = sanitize_filename(target_filename)
    
    if original_filename != target_filename:
        logger.info(f"Sanitized filename: '{original_filename}' -> '{target_filename}'")
    
    # Validate filename - prevent wildcard or invalid characters
    if any(char in target_filename for char in ['*', '?', '<', '>', '|', '"', '(', ')']):
        error_msg = f"Invalid filename: {target_filename}. Filenames cannot contain wildcards or special characters."
        logger.error(error_msg)
        return error_msg
    
    # Ensure filename has proper extension
    if not any(target_filename.endswith(ext) for ext in ['.tsx', '.ts', '.jsx', '.js', '.css', '.html', '.json']):
        error_msg = f"Unsupported file type: {target_filename}. Supported: .tsx, .ts, .jsx, .js, .css, .html, .json"
        logger.error(error_msg)
        return error_msg
        
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # 1. READ ONLY THE TARGET FILE
        # We do NOT load the whole repo.
        # Get the current working directory and construct the path properly
        current_dir = os.getcwd()
        logger.info(f"Current working directory: {current_dir}")
        
        # If we're in the orchestrator directory, the path is correct
        # If we're in the parent directory, we need to adjust
        # Handle case where target_filename already includes src/ prefix
        if target_filename.startswith('src/'):
            # Remove src/ prefix since we'll add it in the path construction
            clean_filename = target_filename[4:]  # Remove 'src/' prefix
        else:
            clean_filename = target_filename
            
        if current_dir.endswith('orchestrator'):
            file_path = f"todo-ui/src/{clean_filename}"
        else:
            file_path = f"vocalCommit/orchestrator/todo-ui/src/{clean_filename}"
        
        logger.info(f"Attempting to read file: {file_path}")
        logger.info(f"Full path: {os.path.abspath(file_path)}")
        
        # Check if file exists, if not, we'll create a new one
        file_exists = os.path.exists(file_path)
        
        if file_exists:
            try:
                with open(file_path, "r") as f:
                    current_code = f.read()
                logger.info(f"Successfully read {len(current_code)} characters from {target_filename}")
            except Exception as e:
                error_msg = f"Error reading existing file {file_path}: {str(e)}"
                logger.error(error_msg)
                return error_msg
        else:
            # File doesn't exist - we'll create a new one
            logger.info(f"File {file_path} doesn't exist, will create new file")
            current_code = ""
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 2. CONSTRUCT THE ENHANCED PROMPT WITH CONTEXT
        file_type = "CSS" if target_filename.endswith('.css') else "React/TypeScript"
        
        # Build context information
        context_info = ""
        if related_files and len(related_files) > 1:
            context_info = f"\n\nCONTEXT: This is part of a multi-file modification task. Other files being modified: {', '.join([f for f in related_files if f != target_filename])}"
            
            if file_context:
                context_info += "\n\nRELATED FILE CONTENTS:"
                for rel_file, content in file_context.items():
                    if rel_file != target_filename and content:
                        # Limit context to avoid token limits
                        preview = content[:500] + "..." if len(content) > 500 else content
                        context_info += f"\n\n{rel_file}:\n```\n{preview}\n```"
        
        # Determine if this is a new file or existing file
        file_status = "NEW FILE" if not file_exists else "EXISTING FILE"
        
        prompt = f"""You are a Senior {file_type} Developer working on a PRODUCTION React Todo application.

CRITICAL: This code will be deployed DIRECTLY to a running service. Dependencies are automatically managed.

User Request: "{user_instruction}"

File: `{target_filename}` ({file_status})
```{file_type.lower()}
{current_code if current_code else "// New file - create complete implementation"}
```{context_info}

PRODUCTION REQUIREMENTS:
1. {"Write a complete, production-ready " + file_type + " file" if not file_exists else "Rewrite the ENTIRE file maintaining all existing functionality"}
2. Code must be immediately runnable - no placeholders, no TODOs, no incomplete functions
3. All imports must use exact, correct paths (dependencies are auto-installed)
4. Follow React/TypeScript best practices and proper error handling
5. Include proper TypeScript types and interfaces
6. Ensure accessibility (ARIA labels, semantic HTML)
7. Make responsive and mobile-friendly
8. Use modern React patterns (hooks, functional components)

OUTPUT REQUIREMENTS:
- OUTPUT ONLY RAW CODE - NO MARKDOWN BLOCKS, NO EXPLANATIONS
- DO NOT wrap in ```typescript or ```css blocks
- Start immediately with the actual code content
- Code must be complete and production-ready

{"Generate complete new " + file_type + " file:" if not file_exists else "Rewrite complete file:"}"""
        
        logger.info(f"Calling Gemini with enhanced prompt for {target_filename}")
        
        # 3. RATE LIMITING - Wait if needed before calling Gemini
        wait_time = wait_for_gemini_api()
        if wait_time > 0:
            logger.info(f"Waited {wait_time:.1f} seconds due to rate limiting")
        
        # 4. CALL GEMINI (Fast & Cheap because context is small)
        try:
            # Log the API call with context info
            logger.info(f"Calling Gemini API for {target_filename} (context: {len(current_code)} chars)")
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            logger.info(f"Gemini API response received for {target_filename}: {len(response.text) if response and response.text else 0} characters")
            
        except Exception as e:
            error_msg = f"Error calling Gemini API for {target_filename}: {str(e)}"
            logger.error(error_msg)
            return error_msg
        
        if not response or not response.text:
            error_msg = f"Error: Gemini returned empty response for {target_filename}"
            logger.error(error_msg)
            return error_msg
        
        logger.info(f"Gemini returned {len(response.text)} characters")
        
        # 5. HANDLE DEPENDENCIES (Before writing the file)
        new_code = response.text
        dependency_result = handle_code_dependencies(file_path, new_code)
        
        if dependency_result['status'] == 'partial_success':
            logger.warning(f"Some dependencies failed to install: {dependency_result.get('failed_dependencies', [])}")
        elif dependency_result['status'] == 'success' and dependency_result.get('successful_dependencies'):
            logger.info(f"Successfully installed dependencies: {dependency_result['successful_dependencies']}")
        
        # 6. OVERWRITE THE FILE (The "Replace" Strategy)
        with open(file_path, "w") as f:
            f.write(new_code)
        
        # Prepare success message with dependency info
        success_msg = f"Updated {target_filename} successfully."
        if dependency_result.get('successful_dependencies'):
            success_msg += f" Installed dependencies: {', '.join(dependency_result['successful_dependencies'])}"
        if dependency_result.get('successful_requirements'):
            success_msg += f" Updated requirements file with: {', '.join(dependency_result['successful_requirements'])}"
        if dependency_result.get('failed_dependencies'):
            success_msg += f" Warning: Failed to install: {', '.join(dependency_result['failed_dependencies'])}"
        if dependency_result.get('failed_requirements'):
            success_msg += f" Warning: Failed to update requirements: {', '.join(dependency_result['failed_requirements'])}"
        
        logger.info(success_msg)
        return success_msg
        
    except Exception as e:
        error_msg = f"Error in run_dev_agent for {target_filename}: {str(e)}"
        logger.error(error_msg)
        return error_msg

def process_ui_editing_plan(plan, user_instruction):
    """
    Process a UI editing plan from the PM Agent with multi-file coordination and status updates.
    
    Args:
        plan: Task plan from PM Agent containing target_files
        user_instruction: Original user instruction
    
    Returns:
        Dict with status and results
    """
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    
    target_files = plan.get("target_files", ["App.tsx"])
    modified_files = []
    errors = []
    
    logger.info(f"Dev Agent processing UI editing plan with multi-file coordination")
    logger.info(f"User instruction: {user_instruction}")
    logger.info(f"Target files: {target_files}")
    logger.info(f"Full plan: {plan}")
    
    # Check rate limit status before starting
    from tools.rate_limiter import get_gemini_api_status
    rate_status = get_gemini_api_status()
    
    if rate_status['remaining_requests'] == 0:
        wait_time = rate_status.get('reset_in_seconds', 0)
        logger.warning(f"Dev Agent rate limited, will wait up to {wait_time:.1f} seconds per file")
    
    # 1. GATHER CONTEXT FROM ALL TARGET FILES
    file_context = {}
    current_dir = os.getcwd()
    
    logger.info(f"Dev Agent gathering context from {len(target_files)} target files")
    
    for target_file in target_files:
        try:
            # Handle file path construction
            if target_file.startswith('src/'):
                clean_filename = target_file[4:]
            else:
                clean_filename = target_file
                
            if current_dir.endswith('orchestrator'):
                file_path = f"todo-ui/src/{clean_filename}"
            else:
                file_path = f"vocalCommit/orchestrator/todo-ui/src/{clean_filename}"
            
            try:
                with open(file_path, "r") as f:
                    file_context[target_file] = f.read()
                logger.info(f"Loaded context for {target_file}: {len(file_context[target_file])} characters")
            except FileNotFoundError:
                logger.warning(f"Could not load context for {target_file}: file not found (will create new)")
                file_context[target_file] = None
        except Exception as e:
            logger.warning(f"Error loading context for {target_file}: {str(e)}")
            file_context[target_file] = None
    
    # 2. PROCESS FILES IN OPTIMAL ORDER
    # Process CSS files first, then React files to ensure styling is available
    css_files = [f for f in target_files if f.endswith('.css')]
    react_files = [f for f in target_files if not f.endswith('.css')]
    ordered_files = css_files + react_files
    
    logger.info(f"Dev Agent processing files in order: {ordered_files}")
    
    for i, target_file in enumerate(ordered_files, 1):
        try:
            logger.info(f"Dev Agent processing file {i}/{len(ordered_files)}: {target_file}")
            
            # Show progress for multiple files
            if len(ordered_files) > 1:
                logger.info(f"Progress: {i}/{len(ordered_files)} files ({(i/len(ordered_files)*100):.0f}%)")
            
            result = run_dev_agent(
                target_file, 
                user_instruction, 
                related_files=target_files,
                file_context=file_context
            )
            logger.info(f"Result for {target_file}: {result}")
            
            if "successfully" in result:
                modified_files.append(target_file)
                # Update file context with the new content for subsequent files
                try:
                    if target_file.startswith('src/'):
                        clean_filename = target_file[4:]
                    else:
                        clean_filename = target_file
                        
                    if current_dir.endswith('orchestrator'):
                        file_path = f"todo-ui/src/{clean_filename}"
                    else:
                        file_path = f"vocalCommit/orchestrator/todo-ui/src/{clean_filename}"
                    
                    with open(file_path, "r") as f:
                        file_context[target_file] = f.read()
                    logger.info(f"Updated context for {target_file} after modification")
                except Exception as e:
                    logger.warning(f"Could not update context for {target_file}: {str(e)}")
            else:
                errors.append(f"{target_file}: {result}")
        except Exception as e:
            error_msg = f"{target_file}: {str(e)}"
            logger.error(f"Exception for {target_file}: {str(e)}")
            errors.append(error_msg)
    
    logger.info(f"Dev Agent completed processing. Modified files: {modified_files}, Errors: {errors}")
    
    if modified_files and not errors:
        return {
            "status": "success",
            "modified_files": modified_files,
            "ui_changes": [f"Applied coordinated changes to {', '.join(modified_files)}"]
        }
    elif modified_files and errors:
        return {
            "status": "partial_success", 
            "modified_files": modified_files,
            "errors": errors,
            "ui_changes": [f"Applied changes to {', '.join(modified_files)}", f"Errors: {'; '.join(errors)}"]
        }
    else:
        return {
            "status": "error",
            "errors": errors,
            "ui_changes": []
        }