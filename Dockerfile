# Use Node.js as base image for frontend build
FROM node:18 AS frontend-build

# Set working directory for frontend
WORKDIR /app/frontend

# Set Node.js OpenSSL legacy provider for compatibility
ENV NODE_OPTIONS=--openssl-legacy-provider

# Copy frontend package.json and package-lock.json
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm install

# Copy frontend source code
COPY frontend/ ./

# Build frontend production
RUN npm run build

# Use Python as base image for final image
FROM python:3.11-slim

# Install Node.js, npm, supervisor, and nginx for proxy
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    supervisor \
    curl \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Set working directory for backend
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY app/ ./app/

# Copy frontend build from previous stage
COPY --from=frontend-build /app/frontend/build ./frontend/build

# Install serve for frontend
RUN npm install -g serve

# Create Supervisor configuration file
RUN mkdir -p /etc/supervisor/conf.d
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create directory for persistent storage
RUN mkdir -p /app/tmp

# Setup NGINX configuration for Hugging Face Spaces
COPY docker/nginx.conf /etc/nginx/sites-available/default

# Expose port 7860 for Hugging Face Spaces compatibility
# Also keep 8000 and 3000 for local/DockerHub usage
EXPOSE 7860 8000 3000

# Set environment variables
ENV PYTHONPATH=/app
ENV NODE_ENV=production
ENV PORT=7860

# Copy a script to handle port mapping for Hugging Face Spaces
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use entrypoint script to handle different environments
ENTRYPOINT ["/entrypoint.sh"] 