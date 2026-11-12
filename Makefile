.PHONY: up down build restart logs ps clean

# Start all services
up:
	docker compose up -d

# Start all services and rebuild images
build:
	docker compose up -d --build

# Stop all services
down:
	docker compose down

# Restart all services
restart:
	docker compose restart

# Display logs
logs:
	docker compose logs -f

# Display running containers
ps:
	docker compose ps

# Stop and remove containers, networks and volumes
clean:
	docker compose down -v --remove-orphans