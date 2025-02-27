import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Security, status
from fastapi.security.api_key import APIKeyHeader, APIKey
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from dotenv import load_dotenv
from research_crew_crew.crew import ResearchCrewCrew
from fastapi.responses import FileResponse
from typing import List
from datetime import datetime

# Setup Python path to ensure the package can be imported
current_dir = os.path.abspath(os.path.dirname(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

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
    description="API for running and training research crews. All endpoints require API key authentication via the X-API-Key header.",
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
            
        # Initialize the crew
        crew = ResearchCrewCrew()
        crew.inputs = {
            "crew_name": crew_name,
            "user_goal": user_goal
        }
        
        # Run the crew
        result = crew.crew().kickoff()
        
        # Store the result
        task_results[task_id] = {"status": "success", "result": str(result)}
        logger.info(f"Task {task_id} completed successfully")
    except Exception as e:
        logger.error(f"Error in task {task_id}: {str(e)}")
        task_results[task_id] = {"status": "error", "message": str(e)}

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
        
        # Initialize task result
        task_results[task_id] = {"status": "processing"}
        
        # Run the crew in the background
        background_tasks.add_task(run_crew_task, task_id, request.crew_name, request.user_goal)
        
        return {"status": "processing", "task_id": task_id, "message": "Task started"}
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting crew task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/task/{task_id}", response_model=CrewResponse, tags=["Crew Operations"])
async def get_task_status(
    task_id: str,
    api_key: APIKey = Depends(get_api_key)
):
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = task_results[task_id]
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

# Endpoint to get a specific report by crew name
@app.get("/reports/{crew_name}", tags=["Reports"])
async def get_report(crew_name: str, api_key: APIKey = Depends(get_api_key)):
    """Get a specific report by crew name"""
    global REPORTS_DIR
    file_path = os.path.join(REPORTS_DIR, f"{crew_name}_report.md")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Report for crew '{crew_name}' not found")
    
    return FileResponse(
        file_path, 
        media_type="text/markdown",
        filename=f"{crew_name}_report.md"
    )

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port) 