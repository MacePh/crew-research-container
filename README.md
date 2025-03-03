# Research Crew Container

A containerized application for running AI research crews using CrewAI, with Supabase integration for vector storage and RAG functionality.

## Overview

Research Crew Container is a comprehensive platform that enables you to run AI research crews powered by CrewAI. The system features a FastAPI backend that manages crew tasks, stores reports in Supabase, and provides vector search capabilities through RAG (Retrieval Augmented Generation).

The application allows you to:
- Run research crews with specialized AI agents
- Store detailed reports of research findings
- Search through reports using semantic vector search
- Access all functionality through a RESTful API

## Architecture

The system consists of the following components:

1. **FastAPI Backend**: Handles API requests, manages tasks, and interfaces with Supabase
2. **CrewAI Integration**: Runs specialized AI crews for research tasks
3. **Supabase Database**: Stores reports, report chunks, and task status information
4. **Vector Search**: Enables semantic search through reports using embeddings

## Prerequisites

- Python 3.9+
- Docker (optional, for containerized deployment)
- Supabase account and project
- OpenAI API key
- Serper API key (for web search capabilities)

## Environment Variables

Create a `.env` file with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
SERPER_API_KEY=your_serper_api_key
GITHUB_TOKEN=your_github_token
API_KEY=your_api_
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

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
5. Run the API server:
   ```bash
   python start_api.py
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

### Supabase Setup

For vector storage and RAG functionality:

1. Create a Supabase account at [supabase.com](https://supabase.com)
2. Run the setup script:
   ```bash
   python scripts/setup_supabase.py
   ```
3. Follow the prompts to create a new project and set up the database schema

## Usage

### Running the API

The simplest way to run the API is using the provided script:

```bash
# Activate your virtual environment first
source .venv/bin/activate  # On Linux/Mac
# OR
.venv\Scripts\activate     # On Windows

# Then run the API
python start_api.py
```

The API will be available at `http://localhost:8000` with Swagger documentation at `http://localhost:8000/docs`.

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

### RAG Endpoints

Once deployed with Supabase integration, additional RAG endpoints are available:

#### Search Reports
```bash
curl -X POST http://localhost:8000/search \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning algorithms", "limit": 5}'
```

#### Ask Questions About Reports
```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings about quantum computing?"}'
```

#### Generate Report Summary
```bash
curl -X GET http://localhost:8000/summary/quantum_research \
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

## Troubleshooting

### Docker Issues

- Ensure Docker Desktop is running
- Check Docker logs: `docker logs research-crew-container`
- Verify environment variables are correctly set
- Try rebuilding: `bash scripts/deploy.sh`

### API Issues

- Verify the API is running: `curl http://localhost:8000/health`
- Check API logs for errors: `docker logs research-crew-container`
- Ensure API keys are correctly set in your environment

### Path Issues

Run the path check utility:
```bash
python scripts/check_paths.py
```

## License

[MIT License](LICENSE)

## Acknowledgements

This project uses [CrewAI](https://github.com/joaomdmoura/crewAI) for agent orchestration.