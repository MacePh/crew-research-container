import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Security, status
from fastapi.security.api_key import APIKeyHeader, APIKey
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json
import sqlite3

# Setup Python path to ensure the package can be imported
current_dir = os.path.abspath(os.path.dirname(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# Add the research_crew_crew source directory to the Python path
research_crew_src = os.path.join(workspace_root, "research_crew_crew", "src")
if os.path.exists(research_crew_src) and research_crew_src not in sys.path:
    sys.path.insert(0, research_crew_src)

# Try to import ResearchCrewCrew from different possible locations
try:
    from research_crew_crew.crew import ResearchCrewCrew
except ImportError:
    try:
        from research_crew_crew.src.research_crew_crew.crew import ResearchCrewCrew
    except ImportError:
        # Last resort: try to import directly from the file
        import importlib.util
        crew_path = os.path.join(workspace_root, "research_crew_crew", "src", "research_crew_crew", "crew.py")
        if not os.path.exists(crew_path):
            crew_path = os.path.join(workspace_root, "research_crew_crew", "crew.py")
        
        if os.path.exists(crew_path):
            spec = importlib.util.spec_from_file_location("crew", crew_path)
            crew_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(crew_module)
            ResearchCrewCrew = crew_module.ResearchCrewCrew
        else:
            raise ImportError("Could not find the crew module")

# Create reports directory if it doesn't exist
# Check for Docker environment first, then try relative paths
reports_dirs = [
    "/app/reports",                # Docker container path
    os.path.join(workspace_root, "reports"),  # Workspace root reports
    "reports",                     # Relative to current directory
    os.path.abspath("reports"),    # Absolute path relative to current directory
]

reports_dir = None
for path in reports_dirs:
    # Create directory if it doesn't exist
    os.makedirs(path, exist_ok=True)
    # Check if we can write to it
    try:
        test_file = os.path.join(path, ".test_write")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)  # Clean up
        reports_dir = path
        logger = logging.getLogger(__name__)
        logger.info(f"Using reports directory: {reports_dir}")
        break
    except (IOError, PermissionError):
        continue

if not reports_dir:
    # If all attempts fail, use the current directory
    reports_dir = os.getcwd()
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not find or create reports directory. Using current directory: {reports_dir}")

# Store global reports directory
REPORTS_DIR = reports_dir

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Research Crew API",
    description="""
    API for running and training research crews. All endpoints require API key authentication via the X-API-Key header.
    
    Reports can be retrieved in either markdown or JSON format by specifying the 'format' parameter.
    """,
    version="1.0.0",
    docs_url=None,  # Disable the default docs
    redoc_url=None,  # Disable the default redoc
)

# API Key security
API_KEY = os.getenv("API_KEY")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not API_KEY:
        # If no API key is set in env vars, don't enforce authentication
        logger.warning("No API_KEY set in environment variables. Running in insecure mode.")
        return None
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )

class CrewRequest(BaseModel):
    crew_name: str
    user_goal: str

class CrewResponse(BaseModel):
    status: str
    result: str = None
    message: str = None
    task_id: str = None

# In-memory storage for task results (in production, use a proper database)
task_results = {}

# Model for report listings
class ReportInfo(BaseModel):
    filename: str
    crew_name: str
    created: str

# Store problematic task IDs
BLOCKED_TASK_IDS = [
    "1e471e2b-948c-4695-be24-c63a2e84260d",
    # Add other known problematic IDs here
]

# Directory for storing task data
TASKS_DIR = os.path.join(os.path.dirname(__file__), "..", "tasks")
os.makedirs(TASKS_DIR, exist_ok=True)

def save_task_to_file(task_id, task_data):
    """Save task data to a file"""
    try:
        file_path = os.path.join(TASKS_DIR, f"{task_id}.json")
        with open(file_path, 'w') as f:
            json.dump(task_data, f)
    except Exception as e:
        logger.error(f"Error saving task {task_id} to file: {str(e)}")

def load_task_from_file(task_id):
    """Load task data from a file"""
    try:
        file_path = os.path.join(TASKS_DIR, f"{task_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading task {task_id} from file: {str(e)}")
        return None

# Initialize database
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        status TEXT,
        result TEXT,
        message TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    conn.commit()
    conn.close()

# Call this at startup
init_db()

def save_task_to_db(task_id, task_data):
    """Save task data to database"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        
        # Check if task exists
        c.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
        exists = c.fetchone()
        
        now = datetime.now().isoformat()
        
        if exists:
            # Update existing task
            c.execute(
                "UPDATE tasks SET status = ?, result = ?, message = ?, updated_at = ? WHERE id = ?",
                (
                    task_data.get("status"),
                    task_data.get("result", ""),
                    task_data.get("message", ""),
                    now,
                    task_id
                )
            )
        else:
            # Insert new task
            c.execute(
                "INSERT INTO tasks (id, status, result, message, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    task_data.get("status"),
                    task_data.get("result", ""),
                    task_data.get("message", ""),
                    now,
                    now
                )
            )
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving task {task_id} to database: {str(e)}")

def load_task_from_db(task_id):
    """Load task data from database"""
    try:
        conn = sqlite3.connect('tasks.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = c.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"Error loading task {task_id} from database: {str(e)}")
        return None

# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    # Check if required environment variables are set
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        return {
            "status": "unhealthy",
            "missing_environment_variables": missing_vars
        }
    
    return {"status": "healthy"}

def run_crew_task(task_id: str, crew_name: str, user_goal: str):
    try:
        # Check for required environment variables
        if not os.getenv("OPENAI_API_KEY"):
            task_results[task_id] = {"status": "error", "message": "OPENAI_API_KEY not configured"}
            return
            
        # Initialize task result
        task_results[task_id] = {"status": "processing"}
        save_task_to_file(task_id, {"status": "processing"})
        
        # Initialize the crew
        crew = ResearchCrewCrew()
        crew.inputs = {
            "crew_name": crew_name,
            "user_goal": user_goal
        }
        
        # Run the crew
        result = crew.crew().kickoff()
        
        # Update task result
        task_results[task_id] = {"status": "success", "result": str(result)}
        save_task_to_file(task_id, {"status": "success", "result": str(result)})
        logger.info(f"Task {task_id} completed successfully")
    except Exception as e:
        logger.error(f"Error in task {task_id}: {str(e)}")
        task_results[task_id] = {"status": "error", "message": str(e)}
        save_task_to_file(task_id, {"status": "error", "message": str(e)})

@app.post("/run-crew/", response_model=CrewResponse, tags=["Crew Operations"])
async def run_crew(
    request: CrewRequest, 
    background_tasks: BackgroundTasks,
    api_key: APIKey = Depends(get_api_key)
):
    try:
        # Generate a task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Initialize task result both in memory and file
        initial_status = {"status": "processing", "message": "Task started"}
        task_results[task_id] = initial_status
        save_task_status(task_id, initial_status)
        
        # Run the crew in the background
        background_tasks.add_task(run_crew_task, task_id, request.crew_name, request.user_goal)
        
        return {"status": "processing", "task_id": task_id, "message": "Task started"}
    except Exception as e:
        logger.error(f"Error starting crew task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/task/{task_id}", response_model=CrewResponse, tags=["Crew Operations"])
async def get_task_status(
    task_id: str,
    api_key: APIKey = Depends(get_api_key)
):
    # Check if task is blocked
    if task_id in BLOCKED_TASK_IDS:
        return {
            "status": "blocked",
            "result": "",
            "message": "This task ID is blocked due to known issues"
        }
    
    # First check in-memory cache
    result = task_results.get(task_id)
    
    # If not in memory, try to load from file
    if result is None:
        result = load_task_status(task_id)
    
    # If still not found, return 404
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Ensure the result field is a string (required by the response model)
    if result.get("result") is None and result.get("status") == "error":
        result["result"] = str(result.get("message", "Unknown error"))
    elif result.get("result") is None:
        result["result"] = ""
        
    return {
        "status": result.get("status", "unknown"),
        "result": result.get("result", ""),
        "message": result.get("message")
    }

def train_crew_task(task_id: str, crew_name: str, user_goal: str):
    try:
        # Check for required environment variables
        if not os.getenv("OPENAI_API_KEY"):
            task_results[task_id] = {"status": "error", "message": "OPENAI_API_KEY not configured"}
            return
            
        # Use the global reports directory
        global REPORTS_DIR
        
        # Initialize the crew
        crew = ResearchCrewCrew()
        crew.inputs = {
            "crew_name": crew_name,
            "user_goal": user_goal
        }
        
        # Train the crew with filepath in reports directory
        training_file = os.path.join(REPORTS_DIR, f"{crew_name}_training_data.json")
        crew.crew().train(n_iterations=5, filename=training_file)
        
        # Store the result
        task_results[task_id] = {"status": "success", "message": f"Crew training completed. Data saved to {training_file}"}
        logger.info(f"Training task {task_id} completed successfully")
    except Exception as e:
        logger.error(f"Error in training task {task_id}: {str(e)}")
        task_results[task_id] = {"status": "error", "message": str(e)}

@app.post("/train-crew/", response_model=CrewResponse, tags=["Crew Operations"])
async def train_crew(
    request: CrewRequest, 
    background_tasks: BackgroundTasks,
    api_key: APIKey = Depends(get_api_key)
):
    try:
        # Generate a task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Initialize task result
        task_results[task_id] = {"status": "processing"}
        
        # Train the crew in the background
        background_tasks.add_task(train_crew_task, task_id, request.crew_name, request.user_goal)
        
        return {"status": "processing", "task_id": task_id, "message": "Training started"}
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting training task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Custom docs with clearer API key instructions
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="/favicon.ico",
        init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
        },
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description + "\n\n## Authentication\n\nAll API endpoints require an API key to be sent in the `X-API-Key` header. Click the 'Authorize' button and enter your API key to use the interactive docs.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Endpoint to list all available reports
@app.get("/reports/", response_model=List[ReportInfo], tags=["Reports"])
async def list_reports(api_key: APIKey = Depends(get_api_key)):
    """List all available reports"""
    global REPORTS_DIR
    
    try:
        # Get all markdown files
        report_files = [f for f in os.listdir(REPORTS_DIR) if f.endswith("_report.md")]
        
        results = []
        for filename in report_files:
            # Extract crew name from filename (remove _report.md suffix)
            crew_name = filename.replace("_report.md", "")
            
            # Get file creation time
            file_path = os.path.join(REPORTS_DIR, filename)
            created = datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
            
            results.append(ReportInfo(
                filename=filename,
                crew_name=crew_name,
                created=created
            ))
        
        return results
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing reports: {str(e)}")

def parse_markdown_to_json(markdown_text: str) -> Dict[str, Any]:
    """Convert markdown report to structured JSON format"""
    sections = {}
    current_section = "overview"
    current_subsection = None
    lines = markdown_text.split("\n")
    
    # Initialize with empty content
    sections["title"] = ""
    sections["content"] = []
    
    for line in lines:
        line = line.rstrip()
        
        # Handle title (level 1 heading)
        if line.startswith("# "):
            sections["title"] = line[2:].strip()
        
        # Handle main sections (level 2 headings)
        elif line.startswith("## "):
            current_section = line[3:].strip().lower().replace(" ", "_")
            current_subsection = None
            if current_section not in sections:
                sections[current_section] = []
        
        # Handle subsections (level 3 headings)
        elif line.startswith("### "):
            if current_section not in sections:
                sections[current_section] = []
            
            subsection_title = line[4:].strip()
            current_subsection = {"heading": subsection_title, "content": []}
            sections[current_section].append(current_subsection)
        
        # Handle content lines
        elif line.strip():
            # If we're in a subsection
            if current_subsection is not None:
                current_subsection["content"].append(line.strip())
            # If we're in a main section but not a subsection
            elif current_section in sections:
                # Add directly to the section if it's a list
                if isinstance(sections[current_section], list):
                    # Check if the last item is not a subsection dict
                    if not sections[current_section] or not isinstance(sections[current_section][-1], dict) or "heading" not in sections[current_section][-1]:
                        sections[current_section].append(line.strip())
                    # Otherwise create a new entry
                    else:
                        sections[current_section].append(line.strip())
                else:
                    # Convert to list if it wasn't already
                    sections[current_section] = [line.strip()]
            # If we're before any section, add to general content
            else:
                sections["content"].append(line.strip())
    
    # Clean up empty sections
    sections = {k: v for k, v in sections.items() if v}
    
    return sections

@app.get("/reports/{crew_name}", response_model=Union[str, Dict[str, Any]])
async def get_report(
    crew_name: str, 
    format: str = "markdown", 
    api_key: APIKey = Depends(get_api_key)
):
    """
    Get a specific research report by crew name.
    
    Parameters:
    - crew_name: Name of the crew/report
    - format: Response format - "markdown" (default) or "json"
    
    Returns:
    - Markdown string or JSON object based on format parameter
    """
    # Fix the file path to use _report.md suffix
    report_path = os.path.join(REPORTS_DIR, f"{crew_name}_report.md")
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"Report for {crew_name} not found")
    
    # Read the report content
    with open(report_path, "r") as f:
        report_content = f.read()
    
    # Return appropriate format
    if format.lower() == "json":
        structured_report = parse_markdown_to_json(report_content)
        return JSONResponse(content=structured_report)
    else:
        # Return original markdown
        return report_content

# Endpoint to get training data by crew name
@app.get("/training-data/{crew_name}", tags=["Reports"])
async def get_training_data(crew_name: str, api_key: APIKey = Depends(get_api_key)):
    """Get training data for a specific crew"""
    global REPORTS_DIR
    file_path = os.path.join(REPORTS_DIR, f"{crew_name}_training_data.json")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Training data for crew '{crew_name}' not found")
    
    return FileResponse(
        file_path, 
        media_type="application/json",
        filename=f"{crew_name}_training_data.json"
    )

@app.get("/task-blocklist", tags=["System"])
async def get_task_blocklist(api_key: APIKey = Depends(get_api_key)):
    """Get a list of known problematic task IDs that should not be polled"""
    return {"blocked_task_ids": BLOCKED_TASK_IDS}

@app.get("/cleanup-tasks", tags=["Maintenance"])
async def cleanup_old_tasks(days: int = 7, api_key: APIKey = Depends(get_api_key)):
    """Remove task files older than the specified number of days"""
    try:
        import time
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_timestamp = cutoff_date.timestamp()
        
        count = 0
        for filename in os.listdir(TASKS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(TASKS_DIR, filename)
                file_timestamp = os.path.getmtime(file_path)
                
                if file_timestamp < cutoff_timestamp:
                    os.remove(file_path)
                    count += 1
        
        return {"message": f"Removed {count} task files older than {days} days"}
    except Exception as e:
        logger.error(f"Error cleaning up tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up tasks: {str(e)}")

# Add a cleanup function to remove old tasks
@app.get("/admin/cleanup-tasks", tags=["Admin"])
async def cleanup_old_tasks(days: int = 7, api_key: APIKey = Depends(get_api_key)):
    """Remove tasks older than the specified number of days"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        
        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        c.execute("DELETE FROM tasks WHERE created_at < ?", (cutoff_date,))
        deleted_count = c.rowcount
        
        conn.commit()
        conn.close()
        
        return {"message": f"Deleted {deleted_count} tasks older than {days} days"}
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up tasks: {str(e)}")

def save_task_status(task_id, status_data):
    """Save task status to a JSON file"""
    try:
        # Add timestamp to track task age
        status_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in status_data:
            status_data["created_at"] = status_data["updated_at"]
            
        file_path = os.path.join(TASKS_DIR, f"{task_id}.json")
        with open(file_path, 'w') as f:
            json.dump(status_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving task status: {str(e)}")
        return False

def load_task_status(task_id):
    """Load task status from a JSON file"""
    try:
        file_path = os.path.join(TASKS_DIR, f"{task_id}.json")
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading task status: {str(e)}")
        return None

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port) 
