"""
Custom Documentation Generator for Git Repositories
Uses Groq API to analyze codebase and generate comprehensive README
"""

import os
import subprocess
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

class RepoDocGenerator:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        
    def get_tree_structure(self) -> str:
        """Get repository tree structure"""
        try:
            result = subprocess.run(
                ["tree", "/F", "/A"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except Exception as e:
            return f"Error getting tree: {e}"
    
    def get_git_stats(self) -> dict:
        """Get basic git statistics"""
        stats = {}
        try:
            # Get commit count
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            stats["total_commits"] = result.stdout.strip()
            
            # Get contributors
            result = subprocess.run(
                ["git", "shortlog", "-sn", "--all"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            stats["contributors"] = result.stdout.strip()
            
            # Get recent commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            stats["recent_commits"] = result.stdout.strip()
            
        except Exception as e:
            stats["error"] = str(e)
        
        return stats
    
    def analyze_codebase(self) -> dict:
        """Analyze main source files"""
        analysis = {
            "files": [],
            "structure": {}
        }
        
        # Key directories to analyze
        src_dir = self.repo_path / "src"
        if src_dir.exists():
            for file in src_dir.glob("*.py"):
                if file.name != "__init__.py":
                    try:
                        content = file.read_text(encoding='utf-8')
                        # Get first 100 lines or docstring
                        lines = content.split('\n')[:100]
                        analysis["files"].append({
                            "name": file.name,
                            "path": str(file.relative_to(self.repo_path)),
                            "preview": '\n'.join(lines)
                        })
                    except Exception as e:
                        print(f"Error reading {file}: {e}")
        
        return analysis
    
    def generate_readme_with_llm(self, context: dict) -> str:
        """Use Groq LLM to generate comprehensive README"""
        
        prompt = f"""You are a technical documentation expert. Analyze this repository and generate a comprehensive, professional README.md file.

Repository Context:

## File Structure:
```
{context.get('tree_structure', 'N/A')}
```

## Git Statistics:
- Total Commits: {context.get('git_stats', {}).get('total_commits', 'N/A')}
- Contributors:
{context.get('git_stats', {}).get('contributors', 'N/A')}

- Recent Commits:
{context.get('git_stats', {}).get('recent_commits', 'N/A')}

## Key Source Files:
{json.dumps(context.get('codebase_analysis', {}).get('files', [])[:5], indent=2)}

## Current README (if exists):
{context.get('existing_readme', 'No existing README')}

Generate a comprehensive README.md with these sections:
1. Project Title and Description
2. Key Features (infer from code)
3. Technology Stack
4. Installation & Setup
5. Usage Examples
6. Project Structure (use the tree output)
7. API/Architecture Overview
8. Configuration
9. Testing
10. Contributing Guidelines
11. License Info
12. Git Statistics Summary

Make it professional, clear, and developer-friendly. Use proper markdown formatting with emojis where appropriate.
Focus on being accurate based on the actual code structure provided.
"""

        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical documentation expert specializing in creating professional README files for GitHub repositories."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4096
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating README: {e}"
    
    def generate_documentation(self, output_file: str = "README_GENERATED.md"):
        """Main method to generate complete documentation"""
        
        print("🔍 Analyzing repository...")
        
        # Gather context
        context = {
            "tree_structure": self.get_tree_structure(),
            "git_stats": self.get_git_stats(),
            "codebase_analysis": self.analyze_codebase()
        }
        
        # Get existing README if it exists
        readme_path = self.repo_path / "README.md"
        if readme_path.exists():
            context["existing_readme"] = readme_path.read_text(encoding='utf-8')
        
        print("🤖 Generating documentation with Groq AI...")
        
        # Generate README
        generated_readme = self.generate_readme_with_llm(context)
        
        # Save to file
        output_path = self.repo_path / output_file
        output_path.write_text(generated_readme, encoding='utf-8')
        
        print(f"✅ Documentation generated: {output_path}")
        print(f"\n📊 Git Stats:")
        print(f"   Total Commits: {context['git_stats'].get('total_commits', 'N/A')}")
        print(f"   Files Analyzed: {len(context['codebase_analysis']['files'])}")
        
        return str(output_path)


def main():
    # Get current directory
    repo_path = os.getcwd()
    
    print(f"📁 Repository: {repo_path}")
    
    # Generate documentation
    generator = RepoDocGenerator(repo_path)
    output_file = generator.generate_documentation()
    
    print(f"\n🎉 Done! Check {output_file}")


if __name__ == "__main__":
    main()
