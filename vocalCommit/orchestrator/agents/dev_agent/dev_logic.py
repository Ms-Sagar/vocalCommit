import google.generativeai as genai
from core.config import settings

# Configure Gemini API
genai.configure(api_key=settings.gemini_api_key)
client = genai.GenerativeModel('models/gemini-2.5-flash')

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
        
        try:
            with open(file_path, "r") as f:
                current_code = f.read()
            logger.info(f"Successfully read {len(current_code)} characters from {target_filename}")
        except FileNotFoundError as e:
            error_msg = f"Error: File not found at {file_path}"
            logger.error(error_msg)
            return error_msg
        
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
        
        prompt = f"""You are a {file_type} Developer working on a React Todo application.

The user wants: "{user_instruction}"

Current file: `{target_filename}`
```{file_type.lower()}
{current_code}
```{context_info}

CRITICAL INSTRUCTIONS:
1. Rewrite the ENTIRE file with the requested changes applied
2. Maintain all existing functionality while adding the new features
3. If this is a CSS file, ensure proper theming and responsive design
4. If this is a React file, maintain TypeScript types and component structure
5. Consider how this file works with the other files in the project
6. OUTPUT ONLY THE RAW CODE - NO MARKDOWN BLOCKS, NO EXPLANATIONS, NO ```
7. DO NOT wrap your response in markdown code blocks (```)
8. Start directly with the code content

Rewrite the complete file (raw code only):"""
        
        logger.info(f"Calling Gemini with enhanced prompt for {target_filename}")
        
        # 3. CALL GEMINI (Fast & Cheap because context is small)
        try:
            response = client.generate_content(prompt)
        except Exception as e:
            error_msg = f"Error calling Gemini API for {target_filename}: {str(e)}"
            logger.error(error_msg)
            return error_msg
        
        if not response or not response.text:
            error_msg = f"Error: Gemini returned empty response for {target_filename}"
            logger.error(error_msg)
            return error_msg
        
        logger.info(f"Gemini returned {len(response.text)} characters")
        
        # 4. OVERWRITE THE FILE (The "Replace" Strategy)
        new_code = response.text
        with open(file_path, "w") as f:
            f.write(new_code)
        
        logger.info(f"Successfully wrote {len(new_code)} characters to {target_filename}")
        return f"Updated {target_filename} successfully."
        
    except Exception as e:
        error_msg = f"Error in run_dev_agent for {target_filename}: {str(e)}"
        logger.error(error_msg)
        return error_msg

def process_ui_editing_plan(plan, user_instruction):
    """
    Process a UI editing plan from the PM Agent with multi-file coordination.
    
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
    
    logger.info(f"Processing UI editing plan with multi-file coordination")
    logger.info(f"User instruction: {user_instruction}")
    logger.info(f"Target files: {target_files}")
    logger.info(f"Full plan: {plan}")
    
    # 1. GATHER CONTEXT FROM ALL TARGET FILES
    file_context = {}
    current_dir = os.getcwd()
    
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
                logger.warning(f"Could not load context for {target_file}: file not found")
                file_context[target_file] = None
        except Exception as e:
            logger.warning(f"Error loading context for {target_file}: {str(e)}")
            file_context[target_file] = None
    
    # 2. PROCESS FILES IN OPTIMAL ORDER
    # Process CSS files first, then React files to ensure styling is available
    css_files = [f for f in target_files if f.endswith('.css')]
    react_files = [f for f in target_files if not f.endswith('.css')]
    ordered_files = css_files + react_files
    
    logger.info(f"Processing files in order: {ordered_files}")
    
    for target_file in ordered_files:
        try:
            logger.info(f"Processing target file: {target_file}")
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
    
    logger.info(f"Modified files: {modified_files}")
    logger.info(f"Errors: {errors}")
    
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