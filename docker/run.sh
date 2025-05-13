#!/bin/bash

# Run the GenAI Research Assistant application using Docker

# Function to check if Docker is installed
check_docker() {
  if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker and try again."
    exit 1
  fi
  
  if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
  fi
}

# Function to set environment variables
setup_env() {
  if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Database settings
DATABASE_URL=sqlite+aiosqlite:///./app.db

# Debug mode
DEBUG=false

# API Keys (replace with your actual keys)
OPENAI_API_KEY=
GOOGLE_API_KEY=
META_API_KEY=
EOF
    echo ".env file created. Please edit it to add your API keys."
  fi
}

# Main function
main() {
  check_docker
  setup_env
  
  echo "Starting GenAI Research Assistant..."
  docker-compose up --build
}

# Run the main function
main 