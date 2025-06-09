#!/usr/bin/env python3
"""
Test script to debug environment variable loading
"""
import os
from dotenv import load_dotenv

print("=== Environment Variable Loading Test ===")

# Test 1: Check current working directory
print(f"Current working directory: {os.getcwd()}")

# Test 2: Check if .env file exists
env_file_path = "../env"
env_file_exists = os.path.exists(env_file_path)
print(f".env file exists: {env_file_exists}")

if env_file_exists:
    print(f".env file path: {os.path.abspath(env_file_path)}")

# Test 3: Load environment variables without specifying path
print("\n--- Loading with load_dotenv() ---")
result1 = load_dotenv()
print(f"load_dotenv() result: {result1}")

# Test 4: Load environment variables with explicit path
print("\n--- Loading with load_dotenv(dotenv_path='.env') ---")
result2 = load_dotenv(dotenv_path=".env")
print(f"load_dotenv(dotenv_path='.env') result: {result2}")

# Test 5: Check specific environment variables
print("\n--- Environment Variables ---")
env_vars = [
    "MONGODB_URI",
    "MONGODB_DATABASE", 
    "MONGODB_COLLECTION",
    "GOOGLE_API_KEY",
    "GOOGLE_MODEL",
    "EMBEDDING_MODEL",
    "MAX_CHUNK_TOKENS",
    "CHUNK_OVERLAP_TOKENS",
    "MAX_CONTEXT_CHUNKS",
    "MIN_SIMILARITY_SCORE",
    "NOTION_API_KEY"
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "API_KEY" in var or "URI" in var:
            masked_value = value[:10] + "..." + value[-5:] if len(value) > 15 else "***"
            print(f"{var}: {masked_value}")
        else:
            print(f"{var}: {value}")
    else:
        print(f"{var}: NOT SET")

# Test 6: Read .env file manually
print("\n--- Manual .env file reading ---")
if env_file_exists:
    try:
        with open(".env", "r") as f:
            lines = f.readlines()
        print(f"Number of lines in .env: {len(lines)}")
        for i, line in enumerate(lines[:5], 1):  # Show first 5 lines
            line = line.strip()
            if line and not line.startswith("#"):
                key = line.split("=")[0] if "=" in line else "INVALID"
                print(f"Line {i}: {key}=...")
    except Exception as e:
        print(f"Error reading .env file: {e}")