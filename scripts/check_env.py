#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check for API key
api_key = os.getenv("API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

print("Environment Variable Check:")
print("--------------------------")

if api_key:
    print(f"✅ API_KEY found: {api_key[:3]}{'*' * (len(api_key) - 6)}{api_key[-3:]}")
    print("   Use this key in the X-API-Key header for all API requests.")
else:
    print("❌ API_KEY not found in .env file. Please add it.")
    print("   Example: API_KEY=your-secret-key")

if openai_key:
    print(f"✅ OPENAI_API_KEY found: {openai_key[:3]}{'*' * (len(openai_key) - 6)}{openai_key[-3:]}")
else:
    print("❌ OPENAI_API_KEY not found in .env file. Required for crew operations.")

print("\nAPI Request Example:")
print("--------------------------")
if api_key:
    print(f"""curl -X POST http://localhost:8000/run-crew/ \\
  -H "X-API-Key: {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{"crew_name": "my_research", "user_goal": "Research machine learning algorithms"}}'""")
else:
    print("Set API_KEY in .env file first to see an example request")

print("\nSwagger UI Usage:")
print("--------------------------")
print("1. Open http://localhost:8000/docs in your browser")
print("2. Click the 'Authorize' button at the top right")
if api_key:
    print(f"3. Enter '{api_key}' in the X-API-Key field")
else:
    print("3. Enter your API key from .env in the X-API-Key field")
print("4. Click 'Authorize' then 'Close'")
print("5. Now you can use the interactive docs with authentication") 