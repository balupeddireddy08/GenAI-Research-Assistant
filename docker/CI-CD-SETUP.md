# CI/CD Setup Guide for GenAI Research Assistant

This guide explains how to set up the Continuous Integration (CI) and Continuous Deployment (CD) pipeline for the GenAI Research Assistant application.

## Overview

The CI/CD pipeline consists of two main workflows:

1. **CI Workflow**: Builds and pushes the Docker image to DockerHub
2. **CD Workflow**: Deploys the Docker image from DockerHub to Hugging Face Spaces

## Prerequisites

Before you begin, you'll need:

1. A [DockerHub](https://hub.docker.com/) account
2. A [Hugging Face](https://huggingface.co/) account
3. A Hugging Face Space (create one if you don't have it)
4. GitHub repository with the GenAI Research Assistant code

## Setting Up Required Secrets

In your GitHub repository, go to Settings > Secrets and variables > Actions and add the following secrets:

### For DockerHub (CI Workflow)
- `DOCKERHUB_USERNAME`: Your DockerHub username
- `DOCKERHUB_TOKEN`: Your DockerHub access token (not your password)

### For Hugging Face (CD Workflow)
- `HF_TOKEN`: Your Hugging Face API token
- `HF_USERNAME`: Your Hugging Face username
- `HF_SPACE_NAME`: The name of your Hugging Face Space

## How It Works

### CI Workflow (.github/workflows/docker-build-push.yml)

Triggered by:
- Pushes to main/master branches
- Pull requests to main/master that modify Docker-related files
- Manual triggers via GitHub Actions UI

Actions performed:
1. Runs Python linting checks
2. Builds the Docker image
3. Pushes the image to DockerHub (only for pushes to main/master or manual triggers)

### CD Workflow (.github/workflows/huggingface-deploy.yml)

Triggered by:
- Successful completion of the CI workflow
- Manual triggers via GitHub Actions UI

Actions performed:
1. Clones your Hugging Face Space repository
2. Creates/updates Dockerfile that references your DockerHub image
3. Creates a custom entrypoint script for Hugging Face Spaces
4. Pushes changes to Hugging Face Space

## Hugging Face Spaces Considerations

Hugging Face Spaces has certain constraints that our deployment addresses:

1. **Permission Restrictions**: The standard container may not have write access to system directories. Our CD workflow creates a custom entrypoint script that writes configuration to `/tmp` instead of system directories.

2. **Port Requirements**: Hugging Face Spaces expects the application to listen on port 7860. Our configuration automatically routes the backend to this port.

3. **Single Container Requirement**: Hugging Face Spaces only supports single container deployments. Our setup combines frontend and backend in one container using supervisord.

## Environment Variables

After deployment to Hugging Face Spaces, set the following environment variables in your Space settings:

- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_API_KEY`: Your Google AI key
- `META_API_KEY`: Your Meta (Llama) API key
- `DATABASE_URL`: (Optional) Database connection string if not using the default SQLite

## Troubleshooting

### Common Issues

1. **Docker build fails**: Check the GitHub Actions logs for specific error messages

2. **Hugging Face deployment fails**: 
   - Ensure your HF_TOKEN has write permissions
   - Check if the Space is already running - you may need to stop it before redeploying

3. **Permission denied errors**:
   - These are handled by our custom entrypoint script that uses writable directories
   - If you see new permission errors, you may need to further modify the entrypoint script

4. **Application starts but doesn't work**: 
   - Verify environment variables are set correctly in Hugging Face Space settings
   - Check the application logs in the Space settings

### Logs

- View GitHub Actions logs in the "Actions" tab of your repository
- View Hugging Face Space logs in the Space settings under the "Logs" tab

## Manual Deployment

If you need to trigger the workflows manually:

1. Go to the "Actions" tab in your GitHub repository
2. Select the workflow you want to run
3. Click "Run workflow" and select the branch 