"""
AI-Powered Commit Message Generator
Generates meaningful, descriptive, and educational commit messages using AI.
"""

import json
import os
import subprocess
import re
from logger import logger
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import openai
from anthropic import Anthropic
import re
from logger import logger
import google.generativeai as genai


class AICommitGenerator:
    """AI-powered commit message generator with multiple provider support."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the AI commit generator with configuration."""
        self.config = self._load_config(config_path)
        self.ai_config = self.config.get("ai_commit", {})
        self.git_config = self.config.get("git", {})
        
        # Initialize AI client based on provider
        self.client = self._initialize_ai_client()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
    
    def _initialize_ai_client(self):
        """Initialize the appropriate AI client based on configuration."""
        provider = self.ai_config.get("provider", "openai").lower()
        api_key = self.ai_config.get("api_key") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            logger.warning("AI API key not found. AI commit messages will be disabled.")
            return None
        
        if provider == "openai":
            openai.api_key = api_key
            return openai
        elif provider == "anthropic":
            return Anthropic(api_key=api_key)
        elif provider == "gemini":
            genai.configure(api_key=api_key)
            return genai
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    def get_git_diff(self, staged: bool = True) -> str:
        """Get git diff for staged or unstaged changes."""
        try:
            cmd = ["git", "diff", "--cached"] if staged else ["git", "diff"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    def get_git_status(self) -> str:
        """Get current git status."""
        try:
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    def get_changed_files(self) -> List[str]:
        """Get list of changed files."""
        status_output = self.get_git_status()
        files = []
        for line in status_output.split('\n'):
            if line.strip():
                # Parse git status format: XY filename
                filename = line[3:].strip()
                files.append(filename)
        return files
    
    def analyze_changes(self) -> Dict:
        """Analyze the changes made to the repository."""
        diff = self.get_git_diff(staged=False)
        if not diff:
            diff = self.get_git_diff(staged=True)
        
        status = self.get_git_status()
        changed_files = self.get_changed_files()
        
        # Count additions and deletions
        additions = len(re.findall(r'^\\+[^+]', diff, re.MULTILINE))
        deletions = len(re.findall(r'^-[^-]', diff, re.MULTILINE))
        
        # Detect change types
        change_types = self._detect_change_types(diff, changed_files)
        
        return {
            "diff": diff,
            "status": status,
            "changed_files": changed_files,
            "additions": additions,
            "deletions": deletions,
            "change_types": change_types,
            "timestamp": datetime.now().isoformat()
        }
    
    def _detect_change_types(self, diff: str, files: List[str]) -> List[str]:
        """Detect the types of changes made."""
        types = []
        
        # File type analysis
        file_extensions = set()
        for file in files:
            if '.' in file:
                ext = file.split('.')[-1].lower()
                file_extensions.add(ext)
        
        # Pattern matching for common change types
        if any(ext in ['py', 'js', 'ts', 'java', 'cpp', 'c'] for ext in file_extensions):
            if 'def ' in diff or 'function ' in diff or 'class ' in diff:
                types.append("function/class changes")
            if 'import ' in diff or '#include' in diff:
                types.append("dependency changes")
            if 'test' in diff.lower():
                types.append("test changes")
        
        if any(ext in ['json', 'yaml', 'yml', 'xml'] for ext in file_extensions):
            types.append("configuration changes")
        
        if any(ext in ['md', 'txt', 'rst'] for ext in file_extensions):
            types.append("documentation changes")
        
        if any(ext in ['css', 'scss', 'sass'] for ext in file_extensions):
            types.append("styling changes")
        
        if any(ext in ['html', 'jsx', 'tsx', 'vue'] for ext in file_extensions):
            types.append("UI changes")
        
        # Special keywords
        if 'fix' in diff.lower() or 'bug' in diff.lower():
            types.append("bug fix")
        if 'add' in diff.lower() or '+' in diff:
            types.append("feature addition")
        if 'remove' in diff.lower() or 'delete' in diff.lower():
            types.append("removal/cleanup")
        
        return types if types else ["general changes"]
    
    def _create_prompt(self, analysis: Dict) -> str:
        """Create a prompt for the AI based on the change analysis."""
        language = self.ai_config.get("preferred_language", "tr")
        
        if language == "tr":
            base_prompt = """Sen bir yazılım geliştirme uzmanısın. Git commit mesajı oluşturman gerekiyor.

KURALLARI:
1. Commit mesajı açık, anlamlı ve öğretici olmalı
2. İlk satır kısa özet (50 karakter altı), ikinci satır boş, üçüncü satırdan itibaren detay
3. Türkçe olmalı ama teknik terimler İngilizce kalabilir
4. Gelecek zaman kullan (örn: "Kullanıcı login sistemini ekle")
5. Ne yapıldığını VE neden yapıldığını açıkla

DEĞİŞİKLİK ANALİZİ:
- Değişen dosyalar: {files}
- Değişiklik türleri: {types}
- Eklenen satırlar: {additions}
- Silinen satırlar: {deletions}

DIFF (ilk 1000 karakter):
{diff_preview}

Lütfen bu değişiklikler için profesyonel bir commit mesajı oluştur:"""
        else:
            base_prompt = """You are a software development expert. You need to create a git commit message.

RULES:
1. Commit message should be clear, meaningful, and educational
2. First line short summary (under 50 chars), second line empty, third line onwards details
3. Use imperative mood (e.g., "Add user authentication system")
4. Explain WHAT was done AND WHY it was done

CHANGE ANALYSIS:
- Changed files: {files}
- Change types: {types}
- Added lines: {additions}
- Deleted lines: {deletions}

DIFF (first 1000 characters):
{diff_preview}

Please create a professional commit message for these changes:"""
        
        return base_prompt.format(
            files=", ".join(analysis["changed_files"][:5]),
            types=", ".join(analysis["change_types"]),
            additions=analysis["additions"],
            deletions=analysis["deletions"],
            diff_preview=analysis["diff"][:1000] if analysis["diff"] else "No diff available"
        )
    
    def generate_commit_message(self, custom_context: str = "") -> str:
        """Generate an AI-powered commit message."""
        if not self.ai_config.get("enabled", False):
            return self._fallback_commit_message()
        
        try:
            analysis = self.analyze_changes()
            
            if not analysis["changed_files"]:
                return "docs: Update project files"
            
            prompt = self._create_prompt(analysis)
            if custom_context:
                prompt += f"\n\nEK BAĞLAM: {custom_context}"
            
            # Generate message using AI
            message = self._call_ai_api(prompt)
            
            # Clean and validate message
            return self._clean_commit_message(message)
            
        except Exception as e:
            print(f"AI commit generation failed: {e}")
            return self._fallback_commit_message()
    
    def _call_ai_api(self, prompt: str) -> str:
        """Call the AI API to generate commit message."""
        provider = self.ai_config.get("provider", "openai").lower()
        model = self.ai_config.get("model", "gpt-4")
        max_tokens = self.ai_config.get("max_tokens", 200)
        temperature = self.ai_config.get("temperature", 0.3)
        
        if provider == "openai":
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant specialized in creating excellent git commit messages."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
            
        elif provider == "anthropic":
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
            
        elif provider == "gemini":
            # Use Gemini model
            model_name = model if model.startswith("gemini") else "gemini-2.0-flash"
            model = genai.GenerativeModel(model_name)
            
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            return response.text.strip()
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _clean_commit_message(self, message: str) -> str:
        """Clean and format the commit message."""
        # Remove any quotes or extra formatting
        message = message.strip().strip('"').strip("'")
        
        # Ensure proper format
        lines = message.split('\n')
        if len(lines) == 1:
            # Single line message, keep it simple
            return lines[0][:72]  # Git recommended max line length
        
        # Multi-line message
        summary = lines[0][:50]  # Summary line limit
        if len(lines) > 1 and lines[1].strip():
            # Insert empty line after summary if not present
            body = '\n'.join([''] + lines[1:])
        else:
            body = '\n'.join(lines[1:])
        
        return summary + body
    
    def _fallback_commit_message(self) -> str:
        """Generate a fallback commit message when AI is not available."""
        analysis = self.analyze_changes()
        files = analysis["changed_files"]
        
        if not files:
            return "chore: Update project files"
        
        # Simple rule-based message generation
        if len(files) == 1:
            file = files[0]
            if file.endswith('.md'):
                return f"docs: Update {file}"
            elif file.endswith(('.py', '.js', '.ts')):
                return f"feat: Update {file}"
            else:
                return f"chore: Update {file}"
        else:
            file_types = set()
            for file in files:
                if '.' in file:
                    ext = file.split('.')[-1]
                    file_types.add(ext)
            
            if 'md' in file_types:
                return f"docs: Update documentation ({len(files)} files)"
            elif any(ext in file_types for ext in ['py', 'js', 'ts', 'java']):
                return f"feat: Update source code ({len(files)} files)"
            else:
                return f"chore: Update project files ({len(files)} files)"


def main():
    """Main function for testing the AI commit generator."""
    try:
        generator = AICommitGenerator()
        message = generator.generate_commit_message()
        print("Generated commit message:")
        print("-" * 50)
        print(message)
        print("-" * 50)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
