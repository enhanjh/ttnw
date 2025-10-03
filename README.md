# TTNW Portfolio Management System

This project is set up using Docker Compose, allowing for flexible environment configurations. It includes a FastAPI backend, Celery worker, Celery scheduler, and a React frontend.

## Prerequisites

*   Docker
*   Docker Compose

## Configuration (.env file)

Create a `.env` file in the project root directory. This file will store environment-specific variables like database URLs and API keys. Docker Compose services will load these variables from the `.env` file at runtime.

### Development Environment (Cloud Databases)

For development, configure your `.env` to connect to cloud-based MongoDB and Redis services. Replace placeholders with your actual credentials.

```env
# Development Environment (using Cloud DBs)
DATABASE_URL=mongodb+srv://YOUR_CLOUD_MONGO_USER:YOUR_CLOUD_MONGO_PASSWORD@your-cluster.mongodb.net/your_db_name?retryWrites=true&w=majority
CELERY_BROKER_URL=rediss://YOUR_CLOUD_REDIS_USER:YOUR_CLOUD_REDIS_PASSWORD@your-redis-instance.upstash.io:6379/0
CELERY_RESULT_BACKEND=rediss://YOUR_CLOUD_REDIS_USER:YOUR_CLOUD_REDIS_PASSWORD@your-redis-instance.upstash.io:6379/0

# Optional: Korean Investment & Securities API Key
OPENDART_API_KEY=YOUR_OPENDART_API_KEY
```

### Production Environment (Local Docker Databases)

For production, you can choose to either explicitly define local database URLs in your `.env` or omit them to use the Docker Compose default values which point to the local `mongodb` and `redis` services.

```env
# Production Environment (using Local Docker DBs)
# Omit DATABASE_URL and CELERY_BROKER_URL if you want to use the default local Docker service names (mongodb, redis)
# Or, explicitly define them:
# DATABASE_URL=mongodb://mongodb:27017
# CELERY_BROKER_URL=redis://redis:6379/0
# CELERY_RESULT_BACKEND=redis://redis:6379/0

# Optional: Korean Investment & Securities API Key
OPENDART_API_KEY=YOUR_OPENDART_API_KEY
```

## Running the Application

### Development Environment

To run the application with cloud databases, execute the following command:

```bash
docker-compose up -d --build backend worker scheduler frontend
```

This command builds the necessary images and starts the backend, worker, scheduler, and frontend services. It does **not** start the local MongoDB or Redis containers defined under the `prod_infra` profile. Your application services will connect to the URLs specified in your `.env` file.

### Production Environment

To run the application with local Docker databases, use the `prod_infra` profile:

```bash
docker-compose --profile prod_infra up -d --build
```

This command builds the images, starts all application services, and importantly, also includes the local MongoDB and Redis containers. Your application services will connect to these local Docker services using their default hostnames (`mongodb`, `redis`).

## Managing Services

*   **View Logs**:
    ```bash
    docker-compose logs -f
    # View logs for a specific service (e.g., backend)
    docker-compose logs -f backend
    ```

*   **Stop All Services**:
    ```bash
    docker-compose down
    ```

*   **Remove Data Volumes (Caution: This deletes MongoDB data)**:
    ```bash
    docker-compose down -v
    ```