FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server and shared components
COPY minigit_server/ ./minigit_server/
COPY minigit_server.py .
COPY .env ./.env

# Create storage directory for repositories and database persistence
RUN mkdir -p /app/storage/repos

# Environment defaults (override via Dokploy / Docker env vars)
ENV MINIGIT_SERVER_HOST=0.0.0.0
ENV MINIGIT_SERVER_PORT=3000
ENV PYTHONUNBUFFERED=1

EXPOSE ${MINIGIT_SERVER_PORT}

# Run the server
CMD ["python", "minigit_server.py"]
