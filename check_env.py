import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for required API keys
serper_api_key = os.getenv("SERPER_API_KEY")
github_token = os.getenv("GITHUB_TOKEN")

print("Environment variables check:")
print(f"SERPER_API_KEY: {'✓ Found' if serper_api_key else '✗ Missing'}")
print(f"GITHUB_TOKEN: {'✓ Found' if github_token else '✗ Missing (optional)'}")

# Check Python path
import sys
print("\nPython path:")
for path in sys.path:
    print(f"- {path}")

# Check if the research_crew_crew module can be imported
try:
    import research_crew_crew
    print("\nresearch_crew_crew module can be imported successfully")
    print(f"Module location: {research_crew_crew.__file__}")
except ImportError as e:
    print(f"\nFailed to import research_crew_crew module: {e}")

# Check if the config files can be found
try:
    import yaml
    from pathlib import Path
    
    # Try different possible paths for config files
    base_paths = [
        Path("research_crew_crew/src/research_crew_crew/config"),
        Path("src/research_crew_crew/config"),
        Path("config"),
        Path.cwd() / "research_crew_crew" / "src" / "research_crew_crew" / "config",
        Path.cwd() / "src" / "research_crew_crew" / "config",
        Path.cwd() / "config",
    ]
    
    found_tasks = False
    found_agents = False
    
    for base_path in base_paths:
        tasks_path = base_path / "tasks.yaml"
        agents_path = base_path / "agents.yaml"
        
        if tasks_path.exists():
            print(f"\nFound tasks.yaml at: {tasks_path}")
            found_tasks = True
        
        if agents_path.exists():
            print(f"Found agents.yaml at: {agents_path}")
            found_agents = True
        
        if found_tasks and found_agents:
            break
    
    if not found_tasks:
        print("\nCould not find tasks.yaml")
    
    if not found_agents:
        print("Could not find agents.yaml")
        
except Exception as e:
    print(f"\nError checking config files: {e}") 