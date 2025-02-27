#!/usr/bin/env python
import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    exists = os.path.exists(file_path)
    print(f"{description} at {file_path}: {'✅ Found' if exists else '❌ Not found'}")
    return exists

def main():
    print("Path Check Utility for Research Crew")
    print("====================================")
    
    # Get current directory and workspace root
    current_dir = os.path.abspath(os.path.dirname(__file__))
    workspace_root = os.path.abspath(os.path.join(current_dir, ".."))
    
    print(f"Current directory: {current_dir}")
    print(f"Workspace root: {workspace_root}")
    print("------------------------------------")
    
    # Check for configuration files
    config_paths = [
        os.path.join(workspace_root, "research_crew_crew", "src", "research_crew_crew", "config", "tasks.yaml"),
        os.path.join(workspace_root, "research_crew_crew", "src", "research_crew_crew", "config", "agents.yaml"),
        os.path.join(workspace_root, "src", "research_crew_crew", "config", "tasks.yaml"),
        os.path.join(workspace_root, "src", "research_crew_crew", "config", "agents.yaml"),
        "research_crew_crew/src/research_crew_crew/config/tasks.yaml",
        "research_crew_crew/src/research_crew_crew/config/agents.yaml",
        "src/research_crew_crew/config/tasks.yaml",
        "src/research_crew_crew/config/agents.yaml",
    ]
    
    print("Checking configuration files:")
    found_config = False
    for path in config_paths:
        if check_file_exists(path, "Configuration file"):
            found_config = True
    
    if not found_config:
        print("⚠️ Warning: No configuration files found in the expected paths")
    
    print("------------------------------------")
    
    # Check for report directory
    reports_dir = os.path.join(workspace_root, "reports")
    check_file_exists(reports_dir, "Reports directory")
    
    # Check if Python package is importable
    try:
        sys.path.insert(0, workspace_root)
        import research_crew_crew
        print("✅ 'research_crew_crew' package is importable")
    except ImportError as e:
        print(f"❌ Cannot import 'research_crew_crew' package: {e}")
    
    print("------------------------------------")
    print("Path check complete")

if __name__ == "__main__":
    main() 