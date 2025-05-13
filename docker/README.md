# GenAI Research Assistant Docker Setup

This directory contains Docker configuration files for running the GenAI Research Assistant application in a containerized environment.

## Overview

The Docker setup consists of:

- `Dockerfile`: Multi-stage build that compiles the frontend and sets up the backend
- `supervisord.conf`: Configuration for running both frontend and backend processes in parallel
- `docker-compose.yml`: Simplifies building and running the container

## Requirements

- Docker installed on your system
- Docker Compose v3 or later

## Running the Application

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/genai-research-assistant.git
   cd genai-research-assistant
   ```

2. Build and start the container:
   ```
   docker-compose up --build
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Environment Variables

You can customize the application by setting environment variables in the `docker-compose.yml` file:

- `DATABASE_URL`: Database connection string (default: SQLite)
- `DEBUG`: Enable/disable debug mode
- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_API_KEY`: Your Google API key
- `META_API_KEY`: Your Meta API key

## Persistent Storage

Database files are stored in a volume mounted at `/app/tmp` to ensure data persistence between container restarts.

## Troubleshooting

If you encounter issues:

1. Check the logs:
   ```
   docker-compose logs
   ```

2. Access specific service logs:
   ```
   docker-compose logs backend
   docker-compose logs frontend
   ```

3. Rebuild the containers:
   ```
   docker-compose down
   docker-compose up --build
   ``` 