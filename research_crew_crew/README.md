# Research Crew Container

A powerful research automation platform built with CrewAI that uses multiple specialized AI agents to perform in-depth research on any topic.

## Overview

Research Crew Container is a containerized application that orchestrates multiple AI agents to collaborate on research tasks. Each agent has a specialized role and works together to produce comprehensive research insights.

The crew consists of:
- **Research Specialist**: Conducts initial broad research on the topic
- **GitHub Explorer**: Searches GitHub repositories for relevant code and implementations
- **Flow Designer**: Creates a logical flow for the research process
- **Implementation Planner**: Develops an action plan for implementing findings
- **Prompt Generator**: Creates effective prompts for further research or applications

## Features

- �� **Multi-Agent Architecture**: Specialized agents with distinct roles collaborate to produce comprehensive outputs
- 🔄 **Sequential Process**: Structured workflow where each agent builds upon the previous work
- 🐳 **Docker Support**: Easy deployment with Docker containers
- 🔌 **API Interface**: RESTful API for easy integration with other systems
- 📊 **Report Generation**: Automatically compiles findings into a markdown report
- 🧠 **Training Support**: Train your crew for specific research domains

## Setup Instructions

### Prerequisites

- Python 3.8+
- Docker (for containerized deployment)
- OpenAI API key
- Serper API key (for web search)
- GitHub API token (for searching GitHub)

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
SERPER_API_KEY=your_serper_api_key
GITHUB_TOKEN=your_github_token
API_KEY=your_api_security_key
```

**IMPORTANT**: The SERPER_API_KEY is required for the application to start. If this environment variable is missing, the container will exit with an error.

### Local Setup

1. Clone this repository
2. Create your `.env` file with necessary API keys
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install the package in development mode:
   ```bash
   pip install -e .
   ```

### Docker Setup

For containerized deployment (recommended):

1. Make sure Docker is installed and running
2. Build and deploy using the provided script:
   ```bash
   bash scripts/deploy.sh
   ```
3. To restart the container without rebuilding:
   ```bash
   bash scripts/deploy.sh restart
   ```

### Server Deployment

For deploying on a remote server (e.g., DigitalOcean droplet):

1. SSH into your server
2. Clone the repository and navigate to the project directory
3. Create the `.env` file with your API keys
4. Run the deployment script:
   ```bash
   bash scripts/deploy.sh
   ```
5. Set up Nginx as a reverse proxy (see Nginx Configuration section)

## Usage

### API Endpoints

Once deployed, the API is available at `http://localhost:8000` with the following endpoints:

#### Run a Research Crew
```bash
curl -X POST http://localhost:8000/run-crew/ \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"crew_name": "my_research", "user_goal": "Research machine learning algorithms"}'
```

#### Check Task Status
```bash
curl -X GET http://localhost:8000/task/{task_id} \
  -H "X-API-Key: YOUR_API_KEY"
```

#### List Available Reports
```bash
curl -X GET http://localhost:8000/reports/ \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Get a Specific Report
```bash
curl -X GET http://localhost:8000/reports/{crew_name} \
  -H "X-API-Key: YOUR_API_KEY"
```

### Python Usage

You can also use the crew directly in your Python code:

```python
from research_crew_crew.crew import ResearchCrewCrew

# Initialize the crew
crew = ResearchCrewCrew()

# Set the research goal
crew.inputs = {"user_goal": "Research the impact of quantum computing on cryptography"}

# Run the crew
crew.run_crew(crew_name="quantum_research")
```

## Project Structure

```
├── api/                # API implementation
│   └── api.py          # FastAPI implementation
├── docker/             # Docker configuration
│   └── Dockerfile      # Container definition
├── research_crew_crew/ # Main package
│   ├── src/            # Source code
│   │   └── research_crew_crew/
│   │       ├── config/ # Configuration files
│   │       │   ├── agents.yaml
│   │       │   └── tasks.yaml
│   │       ├── tools/  # Custom tools 
│   │       ├── crew.py # Crew implementation
│   │       └── main.py # CLI entrypoint
├── scripts/            # Utility scripts
│   ├── deploy.sh       # Docker deployment
│   └── check_paths.py  # Path validator
├── reports/            # Generated reports directory
├── requirements.txt    # Dependencies
└── .env                # Environment variables
```

## How It Works

1. The Research Specialist agent performs initial research on the topic
2. The GitHub Explorer searches for relevant code repositories and implementations
3. The Flow Designer creates a logical flow for processing the research
4. The Implementation Planner develops a practical action plan
5. The Prompt Generator creates effective prompts for further research

All findings are compiled into a comprehensive report saved in the `reports` directory.

## Comprehensive Troubleshooting Guide

### Environment Variable Issues

#### Missing SERPER_API_KEY
If the container exits with error code 1 and logs show `ValueError: SERPER_API_KEY not found in environment variables`:

1. **Check if .env file exists**:
   ```bash
   ls -la .env
   ```

2. **Verify .env is not ignored in Docker build**:
   ```bash
   cat .dockerignore | grep .env
   ```
   Make sure `.env` is not listed or is commented out.

3. **Pass environment variables directly to container**:
   ```bash
   docker run -d --name research-crew-container -p 8000:8000 \
     -e SERPER_API_KEY=your_serper_api_key \
     -e OPENAI_API_KEY=your_openai_api_key \
     -e API_KEY=your_api_key \
     -e GITHUB_TOKEN=your_github_token \
     research-crew
   ```

4. **Modify Dockerfile to include environment variables**:
   Add these lines to your Dockerfile before the CMD line:
   ```dockerfile
   ENV SERPER_API_KEY=""
   ENV OPENAI_API_KEY=""
   ENV API_KEY=""
   ENV GITHUB_TOKEN=""
   ```
   Then rebuild with `bash scripts/deploy.sh`

### Docker Issues

#### Container Not Starting
If the container doesn't start or exits immediately:

1. **Check container status**:
   ```bash
   docker ps -a
   ```

2. **View container logs**:
   ```bash
   docker logs research-crew-container
   ```

3. **Check Docker service status**:
   ```bash
   sudo systemctl status docker
   ```

4. **Verify Docker network**:
   ```bash
   docker network ls
   docker network inspect bridge
   ```

5. **Check if docker0 interface is up**:
   ```bash
   ip addr show docker0
   ```
   If it shows "state DOWN", bring it up:
   ```bash
   sudo ip link set docker0 up
   sudo systemctl restart docker
   ```

#### Port Binding Issues
If the container starts but the API is not accessible:

1. **Check port bindings**:
   ```bash
   docker port research-crew-container
   ```

2. **Verify if anything is listening on port 8000**:
   ```bash
   sudo netstat -tuln | grep 8000
   ```

3. **Test local access**:
   ```bash
   curl -v http://localhost:8000/docs
   ```

### Networking Issues

#### API Not Accessible Externally

1. **Check firewall settings**:
   ```bash
   sudo ufw status
   sudo iptables -L -n
   ```
   Ensure ports 80 and 8000 are open.

2. **Verify DigitalOcean firewall**:
   Check the Networking page in DigitalOcean dashboard to ensure HTTP (port 80) is allowed.

3. **Check for incorrect NAT rules**:
   ```bash
   sudo iptables -t nat -L -n -v
   ```
   Look for any DNAT or MASQUERADE rules pointing to incorrect IP addresses.

4. **Test connection from server**:
   ```bash
   curl -v http://localhost:8000/docs
   ```
   If this works but external access fails, it's likely a networking issue.

### Nginx Configuration

If you're using Nginx as a reverse proxy and experiencing issues:

1. **Create a basic Nginx configuration**:
   ```bash
   sudo nano /etc/nginx/sites-available/api
   ```
   Add this configuration:
   ```nginx
   server {
       listen 80;
       server_name _;  # This will match any hostname

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # Add timeout and buffer settings
           proxy_connect_timeout 75s;
           proxy_read_timeout 300s;
           proxy_send_timeout 300s;
           proxy_buffering off;
       }
   }
   ```

2. **Enable the configuration**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/api /etc/nginx/sites-enabled/
   sudo rm /etc/nginx/sites-enabled/default  # Remove default if it exists
   ```

3. **Test and restart Nginx**:
   ```bash
   sudo nginx -t
   sudo systemctl restart nginx
   ```

4. **Check Nginx logs if issues persist**:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   sudo tail -f /var/log/nginx/access.log
   ```

### Empty Response from Server

If you get "Empty reply from server" when accessing externally:

1. **Simplify Nginx configuration**:
   ```nginx
   server {
       listen 80 default_server;
       listen [::]:80 default_server;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
       }
   }
   ```

2. **Check if Nginx is binding to all interfaces**:
   ```bash
   sudo ss -tulpn | grep nginx
   ```
   Should show something like `*:80` indicating it's listening on all interfaces.

3. **Test with curl from different sources**:
   - From server: `curl -v http://localhost/docs`
   - From server using IP: `curl -v http://your_server_ip/docs`
   - From external machine: `curl -v http://your_server_ip/docs`

### Application-Specific Issues

1. **Check for Pydantic deprecation warnings**:
   These warnings in the logs are normal and don't affect functionality:
   ```
   PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead.
   ```

2. **Verify API authentication**:
   If you get 401 Unauthorized errors, check that you're passing the correct API key:
   ```bash
   curl -v -H "X-API-Key: YOUR_API_KEY" http://your_server_ip/docs
   ```

3. **Check for file permission issues**:
   ```bash
   ls -la reports/
   ls -la db/
   ```
   Ensure these directories are writable by the container user.

## Maintenance and Monitoring

### Container Management

1. **Set container to restart automatically**:
   ```bash
   docker update --restart=always research-crew-container
   ```

2. **Monitor container logs**:
   ```bash
   docker logs -f research-crew-container
   ```

3. **Check container resource usage**:
   ```bash
   docker stats research-crew-container
   ```

### Nginx Monitoring

1. **Check Nginx status**:
   ```bash
   sudo systemctl status nginx
   ```

2. **Monitor access logs**:
   ```bash
   sudo tail -f /var/log/nginx/access.log
   ```

3. **Check error logs**:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

### Backup Strategy

1. **Backup reports directory**:
   ```bash
   tar -czvf reports_backup.tar.gz reports/
   ```

2. **Backup Docker container**:
   ```bash
   docker commit research-crew-container research-crew-backup
   docker save research-crew-backup > research-crew-backup.tar
   ```

3. **Create DigitalOcean snapshot**:
   Use the DigitalOcean dashboard to create a snapshot of your droplet.

## License

[MIT License](LICENSE)

## Acknowledgements

This project uses [CrewAI](https://github.com/joaomdmoura/crewAI) for agent orchestration.
