# InfraScan — Phase 1: Backend Foundation

This starter project creates the initial FastAPI backend for InfraScan.

## Included

- FastAPI application
- `GET /` welcome endpoint
- `GET /health` health-check endpoint
- CORS configuration for common local React development ports
- Basic automated tests
- Example environment file and `.gitignore`

Database, authentication, image upload, and AI inference are intentionally left for later phases.

## Requirements

- Python 3.10 or newer
- `pip`

## Setup

### 1. Create and activate a virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the API

From the project root:

```bash
uvicorn app.main:app --reload
```

Expected local address: `http://127.0.0.1:8000`

## Try the endpoints

- Root: http://127.0.0.1:8000/
- Health: http://127.0.0.1:8000/health
- Interactive API docs: http://127.0.0.1:8000/docs

Expected health response:

```json
{
  "status": "ok",
  "service": "infrascan-api"
}
```

## Run tests

```bash
pytest
```

## Suggested Git initialization

```bash
git init
git add .
git commit -m "Set up InfraScan FastAPI foundation"
```

## Phase 1 completion checklist

- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] API starts without errors
- [ ] `/` and `/health` return HTTP 200
- [ ] Swagger UI opens at `/docs`
- [ ] Tests pass
- [ ] Initial commit created

## Next phase

Phase 2 will add PostgreSQL, SQLAlchemy, database configuration, and the first infrastructure/inspection data models.
## Docker Deployment

### Requirements
- Docker Desktop installed and running.

### Build the Docker image

Run this command from the project root directory, where the `Dockerfile` is located:

```powershell
docker build -t infrascan-api .
```

### Run the Docker container

```powershell
docker run --name infrascan-container -p 8000:8000 infrascan-api
```

### Access the API

After the container starts, open these addresses in your browser:

- **API Root:** http://localhost:8000/
- **Health Check:** http://localhost:8000/health
- **Swagger API Documentation:** http://localhost:8000/docs

### Stop the container

Open another PowerShell terminal and run:

```powershell
docker stop infrascan-container
```

### Run automated tests

From the project root, run:

```powershell
python -m pytest
```

