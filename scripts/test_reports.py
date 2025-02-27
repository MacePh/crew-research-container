#!/usr/bin/env python
import os
import sys
import datetime

def test_reports_directory():
    """Test writing to various possible reports directories"""
    print("Testing Reports Directory Access")
    print("===============================")
    
    # Get current directory and workspace root
    current_dir = os.path.abspath(os.path.dirname(__file__))
    workspace_root = os.path.abspath(os.path.join(current_dir, ".."))
    
    # List of potential reports directories to test
    reports_dirs = [
        "/app/reports",                # Docker container path
        os.path.join(workspace_root, "reports"),  # Workspace root reports
        "reports",                     # Relative to current directory
        os.path.abspath("reports"),    # Absolute path relative to current directory
    ]
    
    # Test each directory
    for path in reports_dirs:
        print(f"\nTesting: {path}")
        
        # Check if directory exists
        if os.path.exists(path):
            print(f"  ✅ Directory exists")
        else:
            try:
                os.makedirs(path, exist_ok=True)
                print(f"  ✅ Created directory")
            except Exception as e:
                print(f"  ❌ Failed to create directory: {e}")
                continue
        
        # Test writing to the directory
        test_file = os.path.join(path, "test_report.md")
        try:
            with open(test_file, "w") as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"# Test Report\n\nGenerated at: {timestamp}\n")
            print(f"  ✅ Successfully wrote to {test_file}")
            
            # Read back the file
            with open(test_file, "r") as f:
                content = f.read()
            print(f"  ✅ Successfully read file: {len(content)} bytes")
            
        except Exception as e:
            print(f"  ❌ Failed to write/read file: {e}")
    
    print("\nTest complete")

if __name__ == "__main__":
    test_reports_directory() 