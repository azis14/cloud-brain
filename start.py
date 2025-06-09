#!/usr/bin/env python3
"""
Startup script for the Second Brain API
"""
import sys
import subprocess
from pathlib import Path

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Please create a .env file with your NOTION_API_KEY")
        print("Example:")
        print("NOTION_API_KEY=your_notion_integration_token_here")
        return False
    
    # Read .env file and check for NOTION_API_KEY
    with open(env_file, 'r') as f:
        content = f.read()
        if "NOTION_API_KEY" not in content:
            print("❌ NOTION_API_KEY not found in .env file!")
            print("Please add your Notion integration token to the .env file")
            return False
        
        # Check if the key has a value
        for line in content.split('\n'):
            if line.startswith('NOTION_API_KEY='):
                value = line.split('=', 1)[1].strip('"\'')
                if not value or value == "your_notion_integration_token_here":
                    print("❌ NOTION_API_KEY is empty or has placeholder value!")
                    print("Please set a valid Notion integration token")
                    return False
    
    print("✅ .env file configured correctly")
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import notion_client
        import pydantic
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install dependencies with: pip install -r requirements.txt")
        return False

def main():
    """Main startup function"""
    print("🚀 Starting Second Brain API...\n")
    
    # Check environment setup
    if not check_env_file():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    print("\n🌟 Starting FastAPI server...")
    print("📖 API Documentation will be available at:")
    print("   - http://localhost:8000/docs (Swagger UI)")
    print("   - http://localhost:8000/redoc (ReDoc)")
    print("\n🔗 API Endpoints:")
    print("   - GET  /health - Health check")
    print("   - GET  /databases - List databases")
    print("   - GET  /notion/database/{id}/schema - Get database schema")
    print("   - GET  /notion/database/{id}/pages/simplified - Get simplified pages")
    print("   - POST /notion/database/query/simple - Query with filters")
    print("\n⚡ Press Ctrl+C to stop the server\n")
    
    try:
        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--reload", 
            "--host", "127.0.0.1", 
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()