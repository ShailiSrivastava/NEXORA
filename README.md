# NEXORA

NEXORA is an Agentic AI Career Intelligence Platform that helps candidates discover, rank, and explain job-fit opportunities with AI-driven tooling and retrieval.

## Current milestone

This repository currently contains the backend foundation for the first milestone:

- FastAPI application scaffold
- environment-based configuration
- health check endpoint
- initial pytest coverage
- Docker and project structure prepared for next milestones

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## Project structure

```text
NEXORA/
  backend/
    app/
      api/
      agents/
      tools/
      schemas/
      services/
      memory/
      retrieval/
      evaluation/
      database/
      config.py
      main.py
    tests/
    requirements.txt
    .env.example
    Dockerfile
  frontend/
  docker-compose.yml
  README.md
  .gitignore
```
