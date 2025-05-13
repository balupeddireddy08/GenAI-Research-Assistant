# Run the GenAI Research Assistant application using Docker

# Function to check if Docker is installed
function Check-Docker {
    try {
        $null = docker --version
        $null = docker-compose --version
    } catch {
        Write-Host "Docker or Docker Compose is not installed. Please install Docker Desktop and try again." -ForegroundColor Red
        exit 1
    }
}

# Function to set environment variables
function Setup-Env {
    if (-not (Test-Path ".env")) {
        Write-Host "Creating .env file..." -ForegroundColor Yellow
        @"
# Database settings
DATABASE_URL=sqlite+aiosqlite:///./app.db

# Debug mode
DEBUG=false

# API Keys (replace with your actual keys)
OPENAI_API_KEY=
GOOGLE_API_KEY=
META_API_KEY=
"@ | Out-File -FilePath ".env" -Encoding utf8
        Write-Host ".env file created. Please edit it to add your API keys." -ForegroundColor Green
    }
}

# Main function
function Main {
    Check-Docker
    Setup-Env
    
    Write-Host "Starting GenAI Research Assistant..." -ForegroundColor Green
    docker-compose up --build
}

# Run the main function
Main 