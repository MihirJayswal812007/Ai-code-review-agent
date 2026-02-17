"""Helper script to verify the project setup and run a smoke test."""

import sys
import os
import subprocess
from pathlib import Path

def print_status(message, status):
    symbol = "✅" if status else "❌"
    print(f"{symbol} {message}")

def check_python_version():
    version = sys.version_info
    is_valid = version.major == 3 and version.minor >= 11
    print_status(f"Python 3.11+ (Current: {version.major}.{version.minor})", is_valid)
    return is_valid

def check_dependencies():
    try:
        import fastapi
        import uvicorn
        import httpx
        import pydantic
        import pydantic_settings
        import github
        import groq
        print_status("Dependencies installed", True)
        return True
    except ImportError as e:
        print_status(f"Dependencies missing: {e.name}", False)
        print("   Run: pip install -r requirements.txt")
        return False

def check_env_file():
    exists = os.path.exists(".env")
    print_status(".env file exists", exists)
    if not exists:
        print("   Run: copy .env.example .env (Windows) or cp .env.example .env (Linux/Mac)")
    return exists

def check_api_keys():
    if not os.path.exists(".env"):
        return False
    
    with open(".env") as f:
        content = f.read()
    
    has_groq = "GROQ_API_KEY" in content and "your_groq_api_key_here" not in content
    has_github = "GITHUB_TOKEN" in content and "your_github_pat_here" not in content
    
    print_status("GROQ_API_KEY configured", has_groq)
    print_status("GITHUB_TOKEN configured", has_github)
    
    return has_groq and has_github

def run_tests():
    print("\nRunning unit tests...")
    try:
        # Run pytest and capture output
        result = subprocess.run(
            ["pytest", "tests/", "-v"], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print_status("All unit tests passed", True)
            return True
        else:
            print_status("Unit tests failed", False)
            print(result.stdout)
            print(result.stderr)
            return False
    except FileNotFoundError:
        print_status("pytest not found", False)
        print("   Run: pip install -r requirements-dev.txt")
        return False

def main():
    print("🔍 Verifying AI Code Review Agent Setup...\n")
    
    checks = [
        check_python_version(),
        check_dependencies(),
        check_env_file(),
        # check_api_keys(), # Optional, user might not have them yet
        run_tests()
    ]
    
    print("\n" + "="*50)
    if all(checks):
        print("🎉 Setup looks great! You are ready to run the agent.")
        print("\nTo start the server:")
        print("   uvicorn src.app:app --reload")
        print("\nTo test with a real PR:")
        print("   Use the GitHub Action or configure the webhook.")
    else:
        print("⚠️  Some checks failed. Please review the issues above.")

if __name__ == "__main__":
    main()
