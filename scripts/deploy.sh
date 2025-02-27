#!/bin/bash

# Check if the first argument is "restart"
if [ "$1" = "restart" ]; then
    echo "Restarting container without rebuilding..."
    
    # Check if container exists
    if docker ps -a --format '{{.Names}}' | grep -q "^research-crew-container$"; then
        echo "Stopping existing container..."
        docker stop research-crew-container
        echo "Starting container..."
        docker start research-crew-container
        
        if [ $? -eq 0 ]; then
            echo "Container restarted successfully!"
            echo "API is available at http://localhost:8000"
        else
            echo "Failed to restart container."
        fi
    else
        echo "Container 'research-crew-container' does not exist."
        echo "Please run the script without the 'restart' argument first to build and create the container."
    fi
    
    exit 0
fi

echo "Stopping any existing containers..."
docker stop research-crew-container 2>/dev/null || true
docker rm research-crew-container 2>/dev/null || true

echo "Building Docker image..."
# Use the Dockerfile from the docker/ directory
docker build -t research-crew -f docker/Dockerfile .

if [ $? -eq 0 ]; then
    echo "Starting container..."
    # Run Docker container with environment variables from .env file
    docker run -d --name research-crew-container -p 8000:8000 --env-file .env \
        research-crew uvicorn api.api:app --host 0.0.0.0 --port 8000
    
    if [ $? -eq 0 ]; then
        echo "Container started successfully!"
        echo "API is available at http://localhost:8000"
        echo ""
        echo "Example curl command:"
        echo "curl -X POST http://localhost:8000/run-crew/ \\"
        echo "  -H \"X-API-Key: YOUR_API_KEY\" \\"
        echo "  -H \"Content-Type: application/json\" \\"
        echo "  -d '{\"crew_name\": \"my_research\", \"user_goal\": \"Research machine learning algorithms\"}'"
        echo ""
        echo "Replace YOUR_API_KEY with the API key from your .env file"
        echo ""
        echo "To restart the container without rebuilding, run: bash scripts/deploy.sh restart"
    else
        echo "Failed to start container."
    fi
else
    echo "Docker build failed."
    echo "Make sure Docker Desktop is running and properly configured."
    echo "If using WSL, check that Docker integration is enabled in Docker Desktop settings."
fi 