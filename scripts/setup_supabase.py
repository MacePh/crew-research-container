#!/usr/bin/env python3
"""
Setup script for Supabase integration with Research Crew Container.
This script helps users set up their Supabase project for storing research reports
and implementing RAG functionality.
"""

import os
import sys
import argparse
import subprocess
import webbrowser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_supabase_cli():
    """Check if Supabase CLI is installed."""
    try:
        subprocess.run(["supabase", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def create_supabase_project(project_name):
    """Create a new Supabase project."""
    print(f"Creating Supabase project: {project_name}")
    
    # Open Supabase dashboard in browser
    webbrowser.open("https://app.supabase.com/projects")
    
    print("\nPlease follow these steps in the Supabase dashboard:")
    print("1. Click 'New Project'")
    print("2. Enter project name: " + project_name)
    print("3. Set a secure database password")
    print("4. Choose a region close to your users")
    print("5. Click 'Create new project'")
    
    input("\nPress Enter once you've created the project...")

def get_supabase_credentials():
    """Get Supabase credentials from the user."""
    print("\nNow we need your Supabase project credentials.")
    print("You can find these in the Supabase dashboard under Project Settings > API")
    
    url = input("Enter your Supabase URL: ").strip()
    key = input("Enter your Supabase anon key: ").strip()
    
    return url, key

def update_env_file(supabase_url, supabase_key):
    """Update .env file with Supabase credentials."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    
    # Read existing .env file
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Check if Supabase variables already exist
    supabase_url_exists = False
    supabase_key_exists = False
    
    for i, line in enumerate(lines):
        if line.startswith("SUPABASE_URL="):
            lines[i] = f"SUPABASE_URL={supabase_url}\n"
            supabase_url_exists = True
        elif line.startswith("SUPABASE_KEY="):
            lines[i] = f"SUPABASE_KEY={supabase_key}\n"
            supabase_key_exists = True
    
    # Add variables if they don't exist
    if not supabase_url_exists:
        lines.append(f"SUPABASE_URL={supabase_url}\n")
    if not supabase_key_exists:
        lines.append(f"SUPABASE_KEY={supabase_key}\n")
    
    # Write updated .env file
    with open(env_path, "w") as f:
        f.writelines(lines)
    
    print(f"\nUpdated .env file with Supabase credentials at {env_path}")

def setup_database_schema():
    """Set up the database schema in Supabase."""
    print("\nSetting up database schema...")
    
    # Path to SQL script
    sql_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "setup_supabase.sql")
    
    print(f"\nPlease follow these steps to set up the database schema:")
    print("1. Go to the SQL Editor in your Supabase dashboard")
    print("2. Open the following SQL file:")
    print(f"   {sql_path}")
    print("3. Copy the contents and paste them into the SQL Editor")
    print("4. Click 'Run' to execute the SQL commands")
    
    # Open SQL file for the user
    try:
        if sys.platform == "win32":
            os.startfile(sql_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", sql_path], check=True)
        else:
            subprocess.run(["xdg-open", sql_path], check=True)
    except:
        print(f"Could not open {sql_path}. Please open it manually.")
    
    # Open Supabase SQL Editor
    webbrowser.open("https://app.supabase.com/project/_/sql")
    
    input("\nPress Enter once you've set up the database schema...")

def test_connection():
    """Test the connection to Supabase."""
    print("\nTesting connection to Supabase...")
    
    try:
        # Add the parent directory to the Python path
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)
        
        # Import the Supabase module
        from db.supabase import report_storage
        
        if report_storage.is_connected():
            print("✅ Successfully connected to Supabase!")
            return True
        else:
            print("❌ Could not connect to Supabase. Please check your credentials.")
            return False
    except Exception as e:
        print(f"❌ Error testing connection: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Set up Supabase for Research Crew Container")
    parser.add_argument("--project-name", default="research-crew-container", help="Name for the Supabase project")
    args = parser.parse_args()
    
    print("=== Research Crew Container - Supabase Setup ===\n")
    
    # Check if Supabase CLI is installed
    if check_supabase_cli():
        print("✅ Supabase CLI is installed")
    else:
        print("ℹ️ Supabase CLI is not installed. It's recommended but not required for this setup.")
        print("   You can install it later from: https://supabase.com/docs/guides/cli")
    
    # Create Supabase project
    create_supabase_project(args.project_name)
    
    # Get Supabase credentials
    supabase_url, supabase_key = get_supabase_credentials()
    
    # Update .env file
    update_env_file(supabase_url, supabase_key)
    
    # Set up database schema
    setup_database_schema()
    
    # Test connection
    if test_connection():
        print("\n🎉 Supabase setup complete! Your Research Crew Container is now configured to use Supabase for report storage and RAG.")
    else:
        print("\n⚠️ Supabase setup completed with warnings. Please check the errors above.")
    
    print("\nNext steps:")
    print("1. Restart your API server to apply the changes")
    print("2. Run a test crew to verify reports are being saved to Supabase")
    print("3. Try the new RAG endpoints to search and query your reports")

if __name__ == "__main__":
    main() 