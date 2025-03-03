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
import uuid
from fastapi.middleware.cors import CORSMiddleware

# Setup Python path to ensure the package can be imported
current_dir = os.path.abspath(os.path.dirname(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# Add the research_crew_crew source directory to the Python path
research_crew_src = os.path.join(workspace_root, "research_crew_crew", "src")
if os.path.exists(research_crew_src) and research_crew_src not in sys.path:
    sys.path.insert(0, research_crew_src)

# Add the research_crew_crew/src/research_crew_crew directory to the Python path
crew_module_dir = os.path.join(research_crew_src, "research_crew_crew")
if os.path.exists(crew_module_dir) and crew_module_dir not in sys.path:
    sys.path.insert(0, crew_module_dir)

# Try to import ResearchCrewCrew
try:
    print("Attempting to import ResearchCrewCrew...")
    from research_crew_crew.crew import ResearchCrewCrew
    print("Successfully imported ResearchCrewCrew from research_crew_crew.crew")
except ImportError:
    try:
        print("Attempting to import from research_crew_crew.src.research_crew_crew.crew...")
        from research_crew_crew.src.research_crew_crew.crew import ResearchCrewCrew
        print("Successfully imported ResearchCrewCrew from research_crew_crew.src.research_crew_crew.crew")
    except ImportError:
        try:
            print("Attempting to import directly from crew module...")
            sys.path.append(os.path.join(workspace_root, "research_crew_crew", "src", "research_crew_crew"))
            from crew import ResearchCrewCrew
            print("Successfully imported ResearchCrewCrew from crew")
        except ImportError as e:
            print(f"Failed to import ResearchCrewCrew: {str(e)}")
            raise ImportError(f"Could not import ResearchCrewCrew: {str(e)}")

# Import Supabase storage and RAG engine
try:
    from db.supabase import report_storage
    supabase_storage_available = report_storage.is_connected()
    
    # Only import rag_engine if report_storage is available
    if supabase_storage_available:
        try:
            from db.rag import rag_engine
            rag_available = True
        except ImportError:
            logging.warning("RAG engine not available. RAG functionality will be disabled.")
            rag_available = False
    else:
        rag_available = False
        
    supabase_available = supabase_storage_available
except ImportError:
    logging.warning("Supabase modules not found. Falling back to file-based storage.")
    supabase_available = False
    rag_available = False

# Create reports directory if it doesn't exist (fallback for when Supabase is not available)
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
    
    This API now supports Supabase for report storage and RAG (Retrieval Augmented Generation) functionality.
    """,
    version="1.1.0",
)

# API key security
API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Research Crew API")
    if supabase_available:
        logger.info("Supabase integration is available")
    else:
        logger.warning("Supabase integration is not available. Using file-based storage.")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not API_KEY:
        # If no API key is set in env vars, don't enforce authentication
        logger.warning("No API_KEY set in environment variables. Running in insecure mode.")
        return None
    
    # Log the received API key (first 10 chars) for debugging
    received_key_preview = api_key_header[:10] + "..." if api_key_header else "None"
    expected_key_preview = API_KEY[:10] + "..." if API_KEY else "None"
    logger.debug(f"Received API key: {received_key_preview}, Expected: {expected_key_preview}")
    
    if api_key_header == API_KEY:
        return api_key_header
    
    # Log the full keys if they don't match (be careful with this in production)
    logger.warning(f"API key mismatch. Received: {api_key_header}, Expected: {API_KEY}")
    
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

# Model for report listings
class ReportInfo(BaseModel):
    id: str = None
    crew_name: str
    created: str
    summary: str = None

# Model for RAG search
class SearchQuery(BaseModel):
    query: str
    limit: int = 5

# Model for RAG question answering
class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []

# In-memory storage for task results (in production, use a proper database)
task_results = {}

# Directory for storing task data (fallback for when Supabase is not available)
TASKS_DIR = os.path.join(os.path.dirname(__file__), "..", "tasks")
os.makedirs(TASKS_DIR, exist_ok=True)

def save_task_status(task_id, status_data):
    """Save task status to storage"""
    # Add timestamp to track task age
    status_data["updated_at"] = datetime.now().isoformat()
    if "created_at" not in status_data:
        status_data["created_at"] = status_data["updated_at"]
    
    # Try to save to Supabase first
    if supabase_available:
        try:
            success = report_storage.save_task_status(task_id, status_data)
            if success:
                return True
        except Exception as e:
            logger.error(f"Error saving task status to Supabase: {str(e)}")
    
    # Fallback to file-based storage
    try:
        file_path = os.path.join(TASKS_DIR, f"{task_id}.json")
        with open(file_path, 'w') as f:
            json.dump(status_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving task status to file: {str(e)}")
        return False

def load_task_status(task_id):
    """Load task status from storage"""
    # Try to load from Supabase first
    if supabase_available:
        try:
            result = report_storage.load_task_status(task_id)
            if result:
                return result
        except Exception as e:
            logger.error(f"Error loading task status from Supabase: {str(e)}")
    
    # Fallback to file-based storage
    try:
        file_path = os.path.join(TASKS_DIR, f"{task_id}.json")
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading task status from file: {str(e)}")
        return None

def save_report(crew_name, content, metadata=None):
    """Save report to Supabase storage"""
    if not supabase_available:
        logger.error("Supabase is not available. Cannot save report.")
        return False
        
    try:
        success = report_storage.save_report(crew_name, content, metadata)
        if success:
            logger.info(f"Report for crew '{crew_name}' saved to Supabase")
            return True
        else:
            logger.error(f"Failed to save report for crew '{crew_name}' to Supabase")
            return False
    except Exception as e:
        logger.error(f"Error saving report to Supabase: {str(e)}")
        return False

def get_report(crew_name):
    """Get a report by crew name"""
    if not supabase_available:
        logger.error("Supabase is not available. Cannot retrieve reports.")
        return None
        
    try:
        result = report_storage.get_report(crew_name)
        if result:
            return result
        else:
            logger.warning(f"Report for crew '{crew_name}' not found in Supabase")
            return None
    except Exception as e:
        logger.error(f"Error getting report from Supabase: {str(e)}")
        return None

def list_reports():
    """List all available reports"""
    if not supabase_available:
        logger.error("Supabase is not available. Cannot list reports.")
        return []
        
    try:
        results = report_storage.list_reports()
        
        # Format the results
        reports = []
        for report in results:
            # Extract summary from metadata if available
            summary = ""
            if "metadata" in report and "summary" in report["metadata"]:
                summary = report["metadata"]["summary"]
                
            reports.append({
                "id": str(report.get("id")),
                "crew_name": report.get("crew_name"),
                "created": report.get("created_at"),
                "summary": summary
            })
            
        return reports
    except Exception as e:
        logger.error(f"Error listing reports from Supabase: {str(e)}")
        return []

def run_crew_task(task_id: str, crew_name: str, user_goal: str):
    """Run a research crew task in the background"""
    try:
        # Update task status
        task_results[task_id] = {"status": "running", "message": "Task is running..."}
        save_task_status(task_id, {"status": "running", "message": "Task is running..."})
        
        # Use the ResearchCrewCrew class that was already imported at the top of the file
        logger.info(f"Using ResearchCrewCrew class that was imported at startup")
        
        # Initialize the crew
        crew = ResearchCrewCrew()
        crew.inputs = {"user_goal": user_goal}
        
        # Run the crew
        logger.info(f"Running crew for task {task_id} with goal: {user_goal}")
        result, enhanced_report = crew.run_crew(crew_name=crew_name)
        
        if result:
            # Convert the enhanced report to a string if it's not already
            if isinstance(enhanced_report, dict):
                import json
                report_content = json.dumps(enhanced_report, indent=2)
            else:
                report_content = str(enhanced_report)
            
            # Save report to Supabase
            metadata = {
                "goal": user_goal,
                "task_id": task_id,
                "completed_at": datetime.now().isoformat(),
                "task_count": len(enhanced_report.get("tasks", [])) if isinstance(enhanced_report, dict) else 0
            }
            
            if not supabase_available:
                error_msg = "Supabase is not available. Cannot save report."
                task_results[task_id] = {"status": "error", "message": error_msg}
                save_task_status(task_id, {"status": "error", "message": error_msg})
                logger.error(error_msg)
                return
                
            success = save_report(crew_name, report_content, metadata)
            
            if success:
                # Update task result
                task_results[task_id] = {"status": "success", "result": str(result)}
                save_task_status(task_id, {"status": "success", "result": str(result)})
                logger.info(f"Task {task_id} completed successfully")
            else:
                # Failed to save report
                error_msg = f"Failed to save report for crew '{crew_name}'"
                task_results[task_id] = {"status": "error", "message": error_msg}
                save_task_status(task_id, {"status": "error", "message": error_msg})
                logger.error(error_msg)
        else:
            # Crew execution failed
            error_msg = "Crew execution failed to produce a result"
            task_results[task_id] = {"status": "error", "message": error_msg}
            save_task_status(task_id, {"status": "error", "message": error_msg})
            logger.error(error_msg)
    except Exception as e:
        logger.error(f"Error in task {task_id}: {str(e)}")
        task_results[task_id] = {"status": "error", "message": str(e)}
        save_task_status(task_id, {"status": "error", "message": str(e)})

@app.get("/health", tags=["Health"])
def health_check():
    """Check if the API is healthy and required environment variables are set"""
    # Check if required environment variables are set
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    status_info = {
        "status": "healthy" if not missing_vars else "unhealthy",
        "supabase_available": supabase_available,
        "reports_dir": REPORTS_DIR
    }
    
    if missing_vars:
        status_info["missing_environment_variables"] = missing_vars
    
    return status_info

@app.post("/run", response_model=CrewResponse, tags=["Crew Operations"])
async def run_crew(
    request: CrewRequest, 
    background_tasks: BackgroundTasks,
    api_key: APIKey = Depends(get_api_key)
):
    """Run a research crew task in the background"""
    try:
        # Generate a task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task result both in memory and storage
        initial_status = {"status": "processing", "message": "Task started"}
        task_results[task_id] = initial_status
        save_task_status(task_id, initial_status)
        
        # Run the crew in the background
        background_tasks.add_task(run_crew_task, task_id, request.crew_name, request.user_goal)
        
        return {"status": "processing", "task_id": task_id, "message": "Task started"}
    except Exception as e:
        logger.error(f"Error starting crew task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/status/{task_id}", response_model=CrewResponse, tags=["Crew Operations"])
async def get_task_status(
    task_id: str,
    api_key: APIKey = Depends(get_api_key)
):
    """Get the status of a running task"""
    # First check in-memory cache
    result = task_results.get(task_id)
    
    # If not in memory, try to load from storage
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
        "message": result.get("message"),
        "task_id": task_id
    }

@app.get("/reports", tags=["Reports"])
@app.get("/reports/", tags=["Reports"])
async def list_reports(api_key: str = Depends(get_api_key)):
    """List all available reports"""
    try:
        if supabase_available:
            # Import the function if it's not already imported
            from db.supabase import get_all_reports
            reports = get_all_reports()
            return {"reports": reports}
        else:
            # Use file-based storage
            reports_dir = "reports"
            if os.path.exists(reports_dir):
                report_files = [f for f in os.listdir(reports_dir) if f.endswith(".md") or f.endswith(".html")]
                return {"reports": [{"crew_name": f.replace("_report.md", "")} for f in report_files]}
            else:
                return {"reports": []}
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing reports: {str(e)}",
        )

@app.get("/reports/{report_identifier}", tags=["Reports"])
async def get_report(report_identifier: str, format: str = None, api_key: str = Depends(get_api_key)):
    """Get a specific report by ID or crew name"""
    try:
        # Check if the identifier is a valid UUID
        is_uuid = False
        try:
            uuid_obj = uuid.UUID(report_identifier)
            is_uuid = True
        except ValueError:
            # Not a UUID, assume it's a crew name
            pass
        
        if is_uuid:
            # Get report by ID
            from db.supabase import get_report_by_id
            report = get_report_by_id(report_identifier)
        else:
            # Get report by crew name
            from db.supabase import get_report_by_name
            report_content = get_report_by_name(report_identifier)
            
            if report_content:
                # Create a simplified report object
                report = {
                    "crew_name": report_identifier,
                    "content": report_content
                }
            else:
                report = None
        
        if report:
            # Handle format parameter
            if format == "json":
                # Return just the content as JSON
                return {"content": report.get("content", "")}
            else:
                # Return the full report object
                return report
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with identifier '{report_identifier}' not found",
            )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting report: {str(e)}",
        )

@app.post("/search", tags=["RAG"])
async def search_reports(
    query: SearchQuery,
    api_key: APIKey = Depends(get_api_key)
):
    """Search reports using vector similarity"""
    if not supabase_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase integration is not available. RAG functionality is disabled."
        )
    
    try:
        results = rag_engine.search_reports(query.query, query.limit)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching reports: {str(e)}"
        )

@app.post("/ask", response_model=QuestionResponse, tags=["RAG"])
async def answer_question(
    request: QuestionRequest,
    api_key: APIKey = Depends(get_api_key)
):
    """Answer a question using RAG"""
    if not supabase_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase integration is not available. RAG functionality is disabled."
        )
    
    try:
        result = rag_engine.answer_question(request.question)
        return result
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error answering question: {str(e)}"
        )

@app.get("/summary/{crew_name}", tags=["RAG"])
async def generate_summary(
    crew_name: str,
    api_key: APIKey = Depends(get_api_key)
):
    """Generate a summary of a report"""
    if not supabase_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase integration is not available. RAG functionality is disabled."
        )
    
    try:
        summary = rag_engine.generate_summary(crew_name)
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report for crew '{crew_name}' not found or could not generate summary"
            )
        return {"summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI with API key authentication"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """ReDoc documentation"""
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

def custom_openapi():
    """Custom OpenAPI schema with authentication information"""
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

@app.get("/reports/{report_name}/details", tags=["Reports"])
async def get_report_details(report_name: str, api_key: str = Depends(get_api_key)):
    """Get detailed information about a specific report"""
    if supabase_available:
        try:
            # Get the report from Supabase
            report = get_report_by_name(report_name)
            if not report:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Report '{report_name}' not found",
                )
                
            # Get the metadata
            metadata = get_report_metadata(report_name)
            
            # Return all information
            return {
                "report_name": report_name,
                "content": report,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Error getting report details: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting report details: {str(e)}",
            )
    else:
        # Try to read the report file
        reports_dir = "reports"
        report_path = os.path.join(reports_dir, report_name)
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {
                "report_name": report_name,
                "content": content,
                "metadata": {"source": "file"}
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_name}' not found",
            )

def is_blocked(filename):
    """Check if a file is in the blocklist (always returns False now)"""
    return False  # No blocklist anymore

# Add RAG search endpoints
@app.get("/search", tags=["Search"])
async def search_reports_api(query: str, match_count: int = 5, api_key: str = Depends(get_api_key)):
    """Search for reports using vector similarity"""
    try:
        from db.rag import search_reports
        results = search_reports(query, match_count)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching reports: {str(e)}",
        )

@app.get("/search/chunks", tags=["Search"])
async def search_report_chunks_api(query: str, match_count: int = 10, api_key: str = Depends(get_api_key)):
    """Search for report chunks using vector similarity"""
    try:
        from db.rag import search_report_chunks
        results = search_report_chunks(query, match_count)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching report chunks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching report chunks: {str(e)}",
        )

@app.get("/reports/{report_id}/tasks", tags=["Reports"])
async def get_report_tasks(report_id: str, api_key: str = Depends(get_api_key)):
    """Get detailed task information for a specific report"""
    try:
        from db.supabase import get_report_by_id
        report = get_report_by_id(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID '{report_id}' not found",
            )
        
        # Try to parse the content as JSON
        try:
            import json
            content = json.loads(report["content"])
            
            # Extract tasks
            if isinstance(content, dict) and "tasks" in content:
                return {"tasks": content["tasks"]}
            else:
                return {"tasks": [], "message": "No structured task data found in report"}
        except (json.JSONDecodeError, TypeError):
            # Not JSON, return an error
            return {"tasks": [], "message": "Report content is not in JSON format"}
    except Exception as e:
        logger.error(f"Error getting report tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting report tasks: {str(e)}",
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port) 