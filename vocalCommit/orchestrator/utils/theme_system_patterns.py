#!/usr/bin/env python3
"""
Theme System Patterns and Validation

This module contains knowledge about React theme system implementation patterns
to help the orchestrator understand and validate theme-related code changes.
"""

import re
import os
from typing import Dict, List, Any, Optional

class ThemeSystemValidator:
    """Validates React theme system implementations."""
    
    def __init__(self):
        self.required_patterns = {
            'context': {
                'file_pattern': r'.*Context\.tsx$',
                'content_patterns': [
                    r'createContext',
                    r'export.*ThemeProvider',
                    r'useState.*theme',
                    r'localStorage'
                ],
                'description': 'Theme context with provider and state management'
            },
            'hook': {
                'file_pattern': r'use.*\.ts$',
                'content_patterns': [
                    r'useContext',
                    r'export.*use\w+',
                    r'throw.*Error.*must be used within'
                ],
                'description': 'Custom hook to consume theme context'
            },
            'component': {
                'file_pattern': r'.*Toggle\.tsx$',
                'content_patterns': [
                    r'use\w+\(\)',
                    r'onClick.*toggle',
                    r'aria-label'
                ],
                'description': 'UI component for theme switching'
            },
            'css': {
                'file_pattern': r'.*\.css$',
                'content_patterns': [
                    r'\[data-theme="dark"\]',
                    r'--[\w-]+:',
                    r'var\(--[\w-]+.*\)'
                ],
                'description': 'CSS with theme variables and selectors'
            }
        }
    
    def detect_theme_files(self, file_list: List[str]) -> Dict[str, List[str]]:
        """Detect theme-related files from a list of filenames."""
        theme_files = {
            'context': [],
            'hook': [],
            'component': [],
            'css': []
        }
        
        for file in file_list:
            for category, pattern_info in self.required_patterns.items():
                if re.search(pattern_info['file_pattern'], file, re.IGNORECASE):
                    theme_files[category].append(file)
        
        return theme_files
    
    def validate_theme_implementation(self, ui_dir: str, theme_files: Dict[str, List[str]]) -> Dict[str, Any]:
        """Validate that theme files implement the correct patterns."""
        results = {
            'status': 'success',
            'errors': [],
            'warnings': [],
            'missing_files': [],
            'pattern_matches': {}
        }
        
        # Check for required file types
        required_types = ['context', 'hook', 'css']
        for req_type in required_types:
            if not theme_files[req_type]:
                results['missing_files'].append(f"Missing {req_type} file for theme system")
                results['status'] = 'failed'
        
        # Validate content patterns
        for category, files in theme_files.items():
            if not files:
                continue
                
            pattern_info = self.required_patterns[category]
            results['pattern_matches'][category] = {}
            
            for file in files:
                file_path = os.path.join(ui_dir, 'src', file)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        
                        matches = {}
                        for pattern in pattern_info['content_patterns']:
                            matches[pattern] = bool(re.search(pattern, content))
                        
                        results['pattern_matches'][category][file] = matches
                        
                        # Check for missing critical patterns
                        missing_patterns = [p for p, found in matches.items() if not found]
                        if missing_patterns:
                            results['warnings'].append(
                                f"{file}: Missing patterns: {', '.join(missing_patterns)}"
                            )
                            if results['status'] == 'success':
                                results['status'] = 'partial_success'
                    
                    except Exception as e:
                        results['errors'].append(f"Error reading {file}: {str(e)}")
                        results['status'] = 'failed'
                else:
                    results['errors'].append(f"File not found: {file}")
                    results['status'] = 'failed'
        
        return results
    
    def get_theme_system_requirements(self) -> Dict[str, Any]:
        """Get the requirements for a complete theme system."""
        return {
            'architecture': {
                'description': 'React Context API pattern for theme management',
                'components': [
                    'ThemeContext with createContext()',
                    'ThemeProvider component with state',
                    'Custom hook (useTheme) to consume context',
                    'UI component for theme switching',
                    'CSS variables with theme selectors'
                ]
            },
            'file_structure': {
                'context/ThemeContext.tsx': 'Context provider with theme state',
                'hooks/useTheme.ts': 'Custom hook to access theme',
                'components/ThemeToggle.tsx': 'UI component for switching themes',
                'App.css': 'CSS variables with [data-theme] selectors',
                'main.tsx': 'App wrapped with ThemeProvider'
            },
            'integration_requirements': [
                'ThemeProvider must wrap entire App in main.tsx',
                'Theme state applied via data-theme attribute on document element',
                'CSS variables must have fallback values',
                'Theme preference should persist in localStorage',
                'All components use theme via custom hook, not direct context'
            ],
            'css_requirements': [
                'Use [data-theme="light"] and [data-theme="dark"] selectors',
                'Define CSS custom properties (--variable-name)',
                'Provide fallback values: var(--color, #default)',
                'Apply variables to all themeable properties'
            ]
        }

def get_theme_system_knowledge() -> ThemeSystemValidator:
    """Get an instance of the theme system validator."""
    return ThemeSystemValidator()

# Common theme system patterns for AI prompts
THEME_SYSTEM_PROMPT_ADDITIONS = """
THEME SYSTEM ARCHITECTURE REQUIREMENTS:
- Theme systems use React Context API pattern: Context → Provider → Hook → Components
- Required files: ThemeContext.tsx, useTheme.ts, ThemeToggle.tsx, updated CSS
- ThemeProvider must wrap entire App in main.tsx
- Theme state applied via data-theme attribute on document.documentElement
- CSS uses [data-theme="dark"] and [data-theme="light"] selectors
- All CSS variables need fallback values: var(--color-bg, #ffffff)
- Components consume theme via custom hook, never direct context access
- Theme preference should persist in localStorage
"""