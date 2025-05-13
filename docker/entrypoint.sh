#!/bin/bash
set -e

# Create modified supervisord configuration for Hugging Face Spaces if needed
if [ "$SPACE_ID" != "" ]; then
  echo "Running in Hugging Face Spaces environment"
  
  # Get the assigned port from HF Spaces or use default 7860
  HF_PORT=${PORT:-7860}
  
  # Create a modified supervisord.conf for HF Spaces
  cat > /etc/supervisor/conf.d/supervisord.conf << EOF
[supervisord]
nodaemon=true
logfile=/var/log/supervisord.log
logfile_maxbytes=50MB
loglevel=info

[program:backend]
command=uvicorn app.main:app --host 0.0.0.0 --port $HF_PORT
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
environment=PYTHONUNBUFFERED=1

[program:frontend]
command=serve -s frontend/build -l 3000
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF
  
  echo "Modified supervisord configuration for Hugging Face Spaces"
fi

# Start supervisord to manage all processes
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf 