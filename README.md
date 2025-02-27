# Research Crew

This repository contains:
1. A research crew built with CrewAI for conducting research
2. A FastAPI service for running and managing research crews

## Getting Started

### Prerequisites

- Python 3.10-3.13
- Docker (optional, for containerized deployment)

### Installation

#### Local Development
```bash
pip install -e .
```

#### Docker Deployment
```bash
bash scripts/deploy.sh
```

## API Usage

### Authentication

All API endpoints require an API key to be sent in the `X-API-Key`