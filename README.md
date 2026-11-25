## Docker Compose Deployment

### Requirements
- Docker Desktop installed and running.
- Docker Compose available through Docker Desktop.

### 1. Configure environment variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace the placeholder password with a strong password.

**Important:** Never upload `.env` to GitHub.

### 2. Build and start the application

Run from the project root:

```powershell
docker compose up -d --build
```

### 3. Check running containers

```powershell
docker compose ps
```

### 4. Access the application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 5. View application logs

```powershell
docker compose logs
```

### 6. Stop the application

```powershell
docker compose down
```

This stops the containers but preserves the PostgreSQL data volume.

**Important:** Do not use `docker compose down -v` unless you intentionally want to delete the database volume.
