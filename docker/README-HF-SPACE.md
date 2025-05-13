# Deploying to Hugging Face Spaces

This document provides instructions for deploying the GenAI Research Assistant to Hugging Face Spaces.

## Overview

The application is packaged as a single Docker container that runs both the frontend and backend. This is specifically designed to work with Hugging Face Spaces, which doesn't support multi-container deployments.

## Deployment Steps

### 1. Push Docker Image to DockerHub

First, push your Docker image to DockerHub using GitHub Actions:

1. Set up GitHub Actions workflow (in `.github/workflows/docker-build-push.yml`):

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
        
      - name: Login to DockerHub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
          
      - name: Build and push
        uses: docker/build-push-action@v3
        with:
          context: .
          push: true
          tags: yourusername/genai-research-assistant:latest
```

2. Add your DockerHub credentials to GitHub repository secrets.

### 2. Create a New Hugging Face Space

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and click "Create New Space"
2. Choose "Docker" as the space type
3. Configure the Space:
   - Set a name and visibility
   - Under "Docker settings", enter your DockerHub image: `yourusername/genai-research-assistant:latest`

### 3. Setting Environment Variables

On your Hugging Face Space settings page, add the following environment variables:

- `DATABASE_URL`: Your database connection string
- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_API_KEY`: Your Google API key
- `META_API_KEY`: Your Meta API key

### 4. Updating the Space

When you push a new version to DockerHub, you have two options to update your Hugging Face Space:

1. **Automatic updates**: Enable "Active Dockerhub Integration" in your Space settings
2. **Manual updates**: Click "Factory Reset" in your Space settings to pull the latest image

## Troubleshooting

If you encounter issues:

1. Check the Space logs in the Hugging Face UI
2. Verify environment variables are set correctly
3. Ensure the Docker image is accessible on DockerHub
4. Check the port configuration (the app should listen on port 7860)

## Limitations

- Persistent storage in Hugging Face Spaces may be limited
- The application accesses all APIs through the single exposed port (7860)
- Database persistence depends on the Hugging Face Space configuration 