import uvicorn
import run_api

if __name__ == "__main__":
    print("Starting Research Crew API server with Supabase integration...")
    print(f"API will be available at http://{run_api.host}:{run_api.port}")
    print("Press Ctrl+C to stop the server")
    
    # Check if Supabase setup is needed
    try:
        from db.supabase import report_storage
        if not report_storage.is_connected():
            print("\n⚠️ Supabase connection not available.")
            print("To set up Supabase integration, run:")
            print("python scripts/setup_supabase.py")
    except ImportError:
        print("\n⚠️ Supabase modules not found.")
        print("To set up Supabase integration, run:")
        print("python scripts/setup_supabase.py")
    
    uvicorn.run(run_api.api_module, host=run_api.host, port=run_api.port, reload=run_api.reload) 