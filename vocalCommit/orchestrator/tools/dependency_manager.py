#!/usr/bin/env python3
"""
Dynamic Dependency Manager for VocalCommit Orchestrator

Handles automatic detection and installation of new dependencies
when Gemini generates code that requires additional packages.
"""

import re
import os
import json
import subprocess
import logging
from typing import List, Dict, Set, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class DependencyManager:
    """Manages dynamic dependency detection and installation."""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.supported_languages = {
            'python': {
                'extensions': ['.py'],
                'package_files': ['requirements.txt', 'pyproject.toml', 'setup.py'],
                'install_command': 'pip install',
                'import_patterns': [
                    r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                    r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import',
                ]
            },
            'javascript': {
                'extensions': ['.js', '.jsx', '.ts', '.tsx'],
                'package_files': ['package.json'],
                'install_command': 'npm install',
                'import_patterns': [
                    r'import.*from\s+[\'"]([^\'\"]+)[\'"]',
                    r'require\([\'"]([^\'\"]+)[\'"]\)',
                ]
            }
        }
    
    def detect_dependencies_in_code(self, code: str, language: str) -> Set[str]:
        """Extract dependencies from generated code."""
        if language not in self.supported_languages:
            logger.warning(f"Unsupported language: {language}")
            return set()
        
        dependencies = set()
        lang_config = self.supported_languages[language]
        
        for pattern in lang_config['import_patterns']:
            matches = re.findall(pattern, code, re.MULTILINE)
            for match in matches:
                # Clean up the dependency name
                dep = match.split('.')[0].strip()  # Get root package and strip whitespace
                if dep and self._is_external_dependency(dep, language):  # Check if not empty
                    dependencies.add(dep)
        
        logger.info(f"Detected {len(dependencies)} potential dependencies: {dependencies}")
        return dependencies
    
    def _is_external_dependency(self, dep_name: str, language: str) -> bool:
        """Check if a dependency is external (not built-in or local)."""
        if language == 'python':
            # Python built-in modules (partial list)
            builtin_modules = {
                'os', 'sys', 'json', 're', 'time', 'datetime', 'math', 'random',
                'collections', 'itertools', 'functools', 'pathlib', 'logging',
                'urllib', 'http', 'socket', 'threading', 'multiprocessing',
                'asyncio', 'typing', 'dataclasses', 'enum', 'abc', 'copy',
                'pickle', 'csv', 'xml', 'html', 'email', 'base64', 'hashlib',
                'uuid', 'tempfile', 'shutil', 'glob', 'fnmatch', 'subprocess'
            }
            
            # Local modules (relative imports or project modules)
            if dep_name.startswith('.') or dep_name in ['core', 'agents', 'tools', 'utils']:
                return False
                
            return dep_name not in builtin_modules
        
        elif language == 'javascript':
            # Node.js built-in modules
            builtin_modules = {
                'fs', 'path', 'os', 'util', 'events', 'stream', 'buffer',
                'crypto', 'http', 'https', 'url', 'querystring', 'zlib',
                'child_process', 'cluster', 'worker_threads', 'async_hooks'
            }
            
            # React/Vite built-ins and local modules
            react_builtins = {
                'react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime'
            }
            
            # Local modules (relative imports or already installed)
            if (dep_name.startswith('./') or dep_name.startswith('../') or 
                dep_name in builtin_modules or dep_name in react_builtins):
                return False
            
            # Check if it's already in package.json
            package_json_path = os.path.join(self.project_root, 'todo-ui', 'package.json')
            if os.path.exists(package_json_path):
                try:
                    with open(package_json_path, 'r') as f:
                        package_data = json.load(f)
                        existing_deps = set()
                        existing_deps.update(package_data.get('dependencies', {}).keys())
                        existing_deps.update(package_data.get('devDependencies', {}).keys())
                        if dep_name in existing_deps:
                            return False
                except Exception:
                    pass
                
            return True
        
        return True
    
    def get_installed_dependencies(self, language: str) -> Set[str]:
        """Get currently installed dependencies for a language."""
        installed = set()
        
        if language == 'python':
            try:
                result = subprocess.run(['pip', 'list', '--format=freeze'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if '==' in line:
                            package = line.split('==')[0].lower()
                            installed.add(package)
            except Exception as e:
                logger.warning(f"Could not get Python packages: {e}")
        
        elif language == 'javascript':
            # Check todo-ui package.json first, then root
            package_json_paths = [
                os.path.join(self.project_root, 'todo-ui', 'package.json'),
                os.path.join(self.project_root, 'package.json')
            ]
            
            for package_json_path in package_json_paths:
                if os.path.exists(package_json_path):
                    try:
                        with open(package_json_path, 'r') as f:
                            package_data = json.load(f)
                            dependencies = package_data.get('dependencies', {})
                            dev_dependencies = package_data.get('devDependencies', {})
                            installed.update(dependencies.keys())
                            installed.update(dev_dependencies.keys())
                        logger.info(f"Found {len(installed)} installed packages in {package_json_path}")
                        break  # Use the first package.json found
                    except Exception as e:
                        logger.warning(f"Could not read {package_json_path}: {e}")
        
        return installed
    
    def install_dependencies(self, dependencies: Set[str], language: str) -> Dict[str, bool]:
        """Install missing dependencies."""
        if not dependencies:
            return {}
        
        installed = self.get_installed_dependencies(language)
        missing = dependencies - installed
        
        if not missing:
            logger.info("All dependencies already installed")
            return {dep: True for dep in dependencies}
        
        logger.info(f"Installing missing dependencies: {missing}")
        results = {}
        
        lang_config = self.supported_languages[language]
        install_cmd = lang_config['install_command']
        
        # Determine the correct working directory
        work_dir = self.project_root
        if language == 'javascript':
            # Check if we're in orchestrator and need to go to todo-ui
            todo_ui_path = os.path.join(self.project_root, 'todo-ui')
            if os.path.exists(todo_ui_path):
                work_dir = todo_ui_path
                logger.info(f"Using todo-ui directory for npm install: {work_dir}")
        
        for dep in missing:
            try:
                if language == 'python':
                    cmd = f"{install_cmd} {dep}".split()
                elif language == 'javascript':
                    cmd = f"{install_cmd} {dep}".split()
                
                logger.info(f"Running: {' '.join(cmd)} in {work_dir}")
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                      timeout=120, cwd=work_dir)
                
                if result.returncode == 0:
                    logger.info(f"Successfully installed {dep}")
                    results[dep] = True
                else:
                    logger.error(f"Failed to install {dep}: {result.stderr}")
                    results[dep] = False
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Timeout installing {dep}")
                results[dep] = False
            except Exception as e:
                logger.error(f"Error installing {dep}: {e}")
                results[dep] = False
        
        return results
    
    def update_requirements_file(self, dependencies: Set[str], language: str) -> Dict[str, bool]:
        """Update requirements/package files with new dependencies for deployment."""
        if not dependencies:
            return {}
        
        results = {}
        
        if language == 'python':
            # Update requirements.txt
            requirements_path = os.path.join(self.project_root, 'requirements.txt')
            try:
                # Read existing requirements
                existing_reqs = set()
                if os.path.exists(requirements_path):
                    with open(requirements_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Extract package name (before ==, >=, etc.)
                                pkg_name = re.split(r'[><=!]', line)[0].strip()
                                existing_reqs.add(pkg_name.lower())
                
                # Add new dependencies that aren't already there
                new_deps = []
                for dep in dependencies:
                    if dep.lower() not in existing_reqs:
                        new_deps.append(dep)
                        results[dep] = True
                    else:
                        results[dep] = True  # Already exists
                
                if new_deps:
                    # Append new dependencies to requirements.txt
                    with open(requirements_path, 'a') as f:
                        if os.path.getsize(requirements_path) > 0:
                            f.write('\n')  # Add newline if file isn't empty
                        for dep in new_deps:
                            f.write(f"{dep}\n")
                    
                    logger.info(f"Added {len(new_deps)} dependencies to requirements.txt: {new_deps}")
                else:
                    logger.info("All Python dependencies already in requirements.txt")
                    
            except Exception as e:
                logger.error(f"Error updating requirements.txt: {e}")
                for dep in dependencies:
                    results[dep] = False
        
        elif language == 'javascript':
            # For JavaScript, npm install automatically updates package.json
            # But we can verify the updates were made
            package_json_path = os.path.join(self.project_root, 'todo-ui', 'package.json')
            if not os.path.exists(package_json_path):
                package_json_path = os.path.join(self.project_root, 'package.json')
            
            try:
                if os.path.exists(package_json_path):
                    with open(package_json_path, 'r') as f:
                        package_data = json.load(f)
                    
                    existing_deps = set()
                    existing_deps.update(package_data.get('dependencies', {}).keys())
                    existing_deps.update(package_data.get('devDependencies', {}).keys())
                    
                    for dep in dependencies:
                        results[dep] = dep in existing_deps
                    
                    logger.info(f"Verified JavaScript dependencies in package.json: {results}")
                else:
                    logger.warning("No package.json found for JavaScript dependencies")
                    for dep in dependencies:
                        results[dep] = False
                        
            except Exception as e:
                logger.error(f"Error verifying package.json: {e}")
                for dep in dependencies:
                    results[dep] = False
        
        return results
    
    def detect_language_from_file(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        
        for lang, config in self.supported_languages.items():
            if ext in config['extensions']:
                return lang
        
        return 'unknown'
    
    def process_generated_code(self, file_path: str, code: str) -> Dict:
        """
        Main method to process generated code and handle dependencies.
        
        Returns:
            Dict with status, installed dependencies, and any errors
        """
        language = self.detect_language_from_file(file_path)
        
        if language == 'unknown':
            return {
                'status': 'skipped',
                'message': f'Unsupported file type: {file_path}',
                'dependencies_detected': [],
                'dependencies_installed': {}
            }
        
        # Detect dependencies in the generated code
        detected_deps = self.detect_dependencies_in_code(code, language)
        
        if not detected_deps:
            return {
                'status': 'success',
                'message': 'No external dependencies detected',
                'dependencies_detected': [],
                'dependencies_installed': {}
            }
        
        # Install missing dependencies
        install_results = self.install_dependencies(detected_deps, language)
        
        # Update requirements/package files for deployment
        requirements_results = self.update_requirements_file(detected_deps, language)
        
        # Check results
        failed_installs = [dep for dep, success in install_results.items() if not success]
        successful_installs = [dep for dep, success in install_results.items() if success]
        
        # Check requirements file updates
        failed_requirements = [dep for dep, success in requirements_results.items() if not success]
        successful_requirements = [dep for dep, success in requirements_results.items() if success]
        
        if failed_installs:
            return {
                'status': 'partial_success',
                'message': f'Some dependencies failed to install: {failed_installs}',
                'dependencies_detected': list(detected_deps),
                'dependencies_installed': install_results,
                'requirements_updated': requirements_results,
                'failed_dependencies': failed_installs,
                'successful_dependencies': successful_installs,
                'failed_requirements': failed_requirements,
                'successful_requirements': successful_requirements
            }
        else:
            return {
                'status': 'success',
                'message': f'All dependencies installed successfully: {successful_installs}',
                'dependencies_detected': list(detected_deps),
                'dependencies_installed': install_results,
                'requirements_updated': requirements_results,
                'successful_dependencies': successful_installs,
                'successful_requirements': successful_requirements
            }

# Global instance
dependency_manager = DependencyManager()

def handle_code_dependencies(file_path: str, code: str) -> Dict:
    """
    Convenience function to handle dependencies for generated code.
    
    Args:
        file_path: Path to the file being generated
        code: The generated code content
        
    Returns:
        Dict with dependency installation results
    """
    return dependency_manager.process_generated_code(file_path, code)