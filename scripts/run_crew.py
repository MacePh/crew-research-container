#!/usr/bin/env python
import os
import sys
from pathlib import Path

def setup_environment():
    """Set up environment to ensure the project can be run properly"""
    
    # Get script directory and workspace root
    script_dir = os.path.abspath(os.path.dirname(__file__))
    workspace_root = os.path.abspath(os.path.join(script_dir, ".."))
    
    # Add workspace root to Python path
    if workspace_root not in sys.path:
        sys.path.insert(0, workspace_root)
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(workspace_root, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    # Print environment information
    print(f"Working Directory: {os.getcwd()}")
    print(f"Script Directory: {script_dir}")
    print(f"Workspace Root: {workspace_root}")
    print(f"Python Path: {sys.path}")

def run_crew():
    """Run the research crew"""
    setup_environment()
    
    try:
        from research_crew_crew.crew import ResearchCrewCrew
        
        # Set up inputs
        inputs = {"user_goal": "Analyze paths in a Python codebase"}
        
        # Initialize and run the crew
        crew = ResearchCrewCrew()
        crew.inputs = inputs
        
        # Run the crew with a name for the report
        if hasattr(crew, 'run_crew'):
            crew.run_crew(crew_name="path_analysis")
        else:
            # Fall back to the original method if run_crew doesn't exist
            result = crew.crew().kickoff()
            print("Crew execution complete")
            
        print(f"Report saved to reports/path_analysis_report.md")
        
    except ImportError as e:
        print(f"Error importing ResearchCrewCrew: {e}")
        print("Make sure the project is properly installed or in PYTHONPATH")
        sys.exit(1)
    except Exception as e:
        print(f"Error running crew: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_crew() 