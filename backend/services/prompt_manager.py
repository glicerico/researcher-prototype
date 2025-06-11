import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import importlib.util
import sys

from logging_config import get_logger

logger = get_logger(__name__)


class PromptManager:
    """Manages prompt templates with version control and metadata."""
    
    def __init__(self):
        self.prompts_file = "prompts.py"
        self.backup_dir = Path("storage_data/prompt_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Load current prompts
        self._load_prompts()
    
    def _load_prompts(self):
        """Load prompts from the prompts.py file."""
        try:
            # Import prompts module dynamically
            spec = importlib.util.spec_from_file_location("prompts", self.prompts_file)
            prompts_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(prompts_module)
            
            # Extract all prompt variables (those ending with _PROMPT)
            self.prompts = {}
            for attr_name in dir(prompts_module):
                if attr_name.endswith('_PROMPT') and not attr_name.startswith('_'):
                    prompt_value = getattr(prompts_module, attr_name)
                    if isinstance(prompt_value, str):
                        self.prompts[attr_name] = {
                            'name': attr_name,
                            'content': prompt_value,
                            'category': self._categorize_prompt(attr_name),
                            'description': self._get_prompt_description(attr_name),
                            'variables': self._extract_variables(prompt_value)
                        }
            
            logger.info(f"Loaded {len(self.prompts)} prompts from {self.prompts_file}")
            
        except Exception as e:
            logger.error(f"Error loading prompts: {str(e)}")
            self.prompts = {}
    
    def _categorize_prompt(self, prompt_name: str) -> str:
        """Categorize prompts based on their names."""
        name_lower = prompt_name.lower()
        
        if 'router' in name_lower:
            return 'Router'
        elif 'search' in name_lower or 'perplexity' in name_lower:
            return 'Search'
        elif 'analysis' in name_lower or 'analyzer' in name_lower:
            return 'Analysis'
        elif 'integrator' in name_lower:
            return 'Integrator'
        elif 'response' in name_lower or 'renderer' in name_lower:
            return 'Response'
        elif 'research' in name_lower:
            return 'Research'
        elif 'topic' in name_lower:
            return 'Topic Extraction'
        elif 'memory' in name_lower or 'context' in name_lower:
            return 'Context'
        else:
            return 'Other'
    
    def _get_prompt_description(self, prompt_name: str) -> str:
        """Generate description for prompts based on their names."""
        descriptions = {
            'ROUTER_SYSTEM_PROMPT': 'Routes user messages to appropriate modules (chat, search, analysis)',
            'SEARCH_OPTIMIZER_SYSTEM_PROMPT': 'Optimizes user questions into effective search queries',
            'ANALYSIS_REFINER_SYSTEM_PROMPT': 'Refines user requests into structured analytical tasks',
            'PERPLEXITY_SYSTEM_PROMPT': 'System prompt for web search functionality',
            'INTEGRATOR_SYSTEM_PROMPT': 'Integrates information from multiple sources into coherent responses',
            'RESPONSE_RENDERER_SYSTEM_PROMPT': 'Formats and styles responses according to user preferences',
            'TOPIC_EXTRACTOR_SYSTEM_PROMPT': 'Extracts research-worthy topics from conversations',
            'RESEARCH_QUERY_GENERATION_PROMPT': 'Generates optimized queries for autonomous research',
            'RESEARCH_FINDINGS_QUALITY_ASSESSMENT_PROMPT': 'Assesses quality of research findings'
        }
        
        return descriptions.get(prompt_name, f"System prompt for {prompt_name.replace('_', ' ').lower()}")
    
    def _extract_variables(self, prompt_content: str) -> List[str]:
        """Extract template variables from prompt content."""
        # Find all {variable} patterns
        variables = re.findall(r'\{([^}]+)\}', prompt_content)
        return list(set(variables))  # Remove duplicates
    
    def get_all_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all prompts with metadata."""
        return self.prompts
    
    def get_prompt(self, prompt_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific prompt by name."""
        return self.prompts.get(prompt_name)
    
    def update_prompt(self, prompt_name: str, new_content: str, admin_user: str = "admin") -> bool:
        """Update a prompt and save changes."""
        try:
            if prompt_name not in self.prompts:
                logger.error(f"Prompt {prompt_name} not found")
                return False
            
            # Create backup
            self._create_backup(prompt_name, admin_user)
            
            # Update prompt content
            old_content = self.prompts[prompt_name]['content']
            self.prompts[prompt_name]['content'] = new_content
            self.prompts[prompt_name]['variables'] = self._extract_variables(new_content)
            
            # Write changes to file
            if self._write_prompts_file():
                logger.info(f"Successfully updated prompt {prompt_name}")
                return True
            else:
                # Rollback on failure
                self.prompts[prompt_name]['content'] = old_content
                return False
                
        except Exception as e:
            logger.error(f"Error updating prompt {prompt_name}: {str(e)}")
            return False
    
    def _create_backup(self, prompt_name: str, admin_user: str):
        """Create a backup of the current prompt."""
        try:
            backup_data = {
                'prompt_name': prompt_name,
                'content': self.prompts[prompt_name]['content'],
                'timestamp': datetime.now().isoformat(),
                'admin_user': admin_user,
                'variables': self.prompts[prompt_name]['variables']
            }
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prompt_name}_{timestamp}.json"
            backup_path = self.backup_dir / filename
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
                
            logger.info(f"Created backup for {prompt_name} at {backup_path}")
            
        except Exception as e:
            logger.error(f"Error creating backup for {prompt_name}: {str(e)}")
    
    def get_prompt_history(self, prompt_name: str) -> List[Dict[str, Any]]:
        """Get version history for a specific prompt."""
        try:
            history = []
            
            # Find all backup files for this prompt
            pattern = f"{prompt_name}_*.json"
            backup_files = list(self.backup_dir.glob(pattern))
            
            for backup_file in sorted(backup_files, reverse=True):  # Most recent first
                try:
                    with open(backup_file, 'r') as f:
                        backup_data = json.load(f)
                        history.append({
                            'timestamp': backup_data['timestamp'],
                            'admin_user': backup_data.get('admin_user', 'unknown'),
                            'content': backup_data['content'],
                            'variables': backup_data.get('variables', []),
                            'backup_file': backup_file.name
                        })
                except Exception as e:
                    logger.error(f"Error reading backup file {backup_file}: {str(e)}")
                    continue
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting history for {prompt_name}: {str(e)}")
            return []
    
    def restore_prompt(self, prompt_name: str, backup_filename: str, admin_user: str = "admin") -> bool:
        """Restore a prompt from a backup."""
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                logger.error(f"Backup file {backup_filename} not found")
                return False
            
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            # Create backup of current state before restoring
            self._create_backup(prompt_name, f"{admin_user}_pre_restore")
            
            # Restore the content
            return self.update_prompt(prompt_name, backup_data['content'], f"{admin_user}_restore")
            
        except Exception as e:
            logger.error(f"Error restoring prompt {prompt_name}: {str(e)}")
            return False
    
    def _write_prompts_file(self) -> bool:
        """Write the updated prompts back to the prompts.py file."""
        try:
            # Read the current file to preserve structure and comments
            with open(self.prompts_file, 'r') as f:
                lines = f.readlines()
            
            # Update prompt values in the file
            updated_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Check if line starts a prompt definition
                for prompt_name in self.prompts:
                    if line.strip().startswith(f'{prompt_name} = """') or line.strip().startswith(f"{prompt_name} = '''"):
                        # Found prompt start, replace entire prompt
                        quote_type = '"""' if '"""' in line else "'''"
                        
                        # Add the prompt definition line
                        updated_lines.append(f'{prompt_name} = {quote_type}\n')
                        
                        # Add the new content
                        updated_lines.append(self.prompts[prompt_name]['content'])
                        
                        # Add closing quotes
                        if not self.prompts[prompt_name]['content'].endswith('\n'):
                            updated_lines.append('\n')
                        updated_lines.append(f'{quote_type}\n')
                        
                        # Skip original prompt content
                        i += 1
                        while i < len(lines) and not (lines[i].strip().endswith(quote_type) and lines[i].strip() != quote_type):
                            i += 1
                        i += 1  # Skip the closing quote line
                        break
                else:
                    # Not a prompt line, keep as is
                    updated_lines.append(line)
                    i += 1
            
            # Write back to file
            with open(self.prompts_file, 'w') as f:
                f.writelines(updated_lines)
            
            # Reload prompts to verify
            self._load_prompts()
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing prompts file: {str(e)}")
            return False
    
    def test_prompt(self, prompt_name: str, test_variables: Dict[str, str]) -> Dict[str, Any]:
        """Test a prompt with provided variables."""
        try:
            if prompt_name not in self.prompts:
                return {
                    'success': False,
                    'error': f'Prompt {prompt_name} not found'
                }
            
            prompt_content = self.prompts[prompt_name]['content']
            
            # Try to format the prompt with test variables
            try:
                formatted_prompt = prompt_content.format(**test_variables)
                
                return {
                    'success': True,
                    'formatted_prompt': formatted_prompt,
                    'original_prompt': prompt_content,
                    'variables_used': test_variables,
                    'missing_variables': []
                }
                
            except KeyError as e:
                # Missing variable
                missing_var = str(e).strip("'\"")
                required_vars = self.prompts[prompt_name]['variables']
                provided_vars = list(test_variables.keys())
                missing_vars = [var for var in required_vars if var not in provided_vars]
                
                return {
                    'success': False,
                    'error': f'Missing required variable: {missing_var}',
                    'required_variables': required_vars,
                    'provided_variables': provided_vars,
                    'missing_variables': missing_vars
                }
                
        except Exception as e:
            logger.error(f"Error testing prompt {prompt_name}: {str(e)}")
            return {
                'success': False,
                'error': f'Error testing prompt: {str(e)}'
            }


# Global prompt manager instance
prompt_manager = PromptManager() 