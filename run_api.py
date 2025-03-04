import os
import sys

# Add the current directory to the Python path
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add the research_crew_crew source directory to the Python path
research_crew_src = os.path.join(current_dir, "research_crew_crew", "src")
if os.path.exists(research_crew_src) and research_crew_src not in sys.path:
    sys.path.insert(0, research_crew_src)

# Add the research_crew_crew directory itself to the path
research_crew_dir = os.path.join(current_dir, "research_crew_crew")
if os.path.exists(research_crew_dir) and research_crew_dir not in sys.path:
    sys.path.insert(0, research_crew_dir)

# Also add the parent directory of research_crew_crew in case it's installed as a package
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Print the Python path for debugging
print(f"Python path: {sys.path}")

# Try to import the module to verify it works
try:
    from research_crew_crew.crew import ResearchCrewCrew
    print("Successfully imported ResearchCrewCrew")
except ImportError as e:
    print(f"Warning: Could not import ResearchCrewCrew: {e}")
    print("The API may not function correctly.")

# Check if Supabase integration is available
try:
    from db.supabase import report_storage
    if report_storage.is_connected():
        print("✅ Supabase integration is available")
        
        # Check if RAG engine is available
        try:
            from db.rag import rag_engine
            print("✅ RAG functionality is available")
        except ImportError:
            print("⚠️ RAG engine not available. RAG functionality will be disabled.")
    else:
        print("⚠️ Supabase connection not available. Using file-based storage.")
except ImportError:
    print("⚠️ Supabase modules not found. Using file-based storage.")

# Configuration for the API
api_module = "api.api_supabase:app"  # Use the Supabase-enabled API
host = "0.0.0.0"
port = 8000
reload = True

# Start the FastAPI server using uvicorn
if __name__ == "__main__":
    import uvicorn
    try:
        print(f"Starting FastAPI server with module: {api_module}")
        uvicorn.run(api_module, host=host, port=port, reload=reload)
    except Exception as e:
        print(f"Error starting FastAPI server: {e}") 