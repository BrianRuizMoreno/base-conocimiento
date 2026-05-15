---
name: docker-deploy
description: Docker + Docker Compose deployment on Portainer/VPS. Backend + frontend containers, PostgreSQL external. Uses pnpm in frontend. Health checks, restart policies.
---

# Docker Deployment Patterns

## Services
Only 2 containers needed (PostgreSQL already exists):
- `rag-backend`: FastAPI + Python
- `rag-frontend`: React static build served by Nginx

## docker-compose.yml
```yaml
version: "3.8"

services:
  rag-backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: rag-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ADMIN_PIN_HASH=${ADMIN_PIN_HASH}
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - TAVILY_API_KEY=${TAVILY_API_KEY:-}
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=${ENVIRONMENT:-production}
    volumes:
      - ./data:/app/data
      - ./backend/app:/app/app  # dev hot-reload
    networks:
      - rag-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  rag-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: rag-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    depends_on:
      - rag-backend
    networks:
      - rag-network
    environment:
      - VITE_API_URL=http://rag-backend:8000/api/v1

networks:
  rag-network:
    driver: bridge
```

## Backend Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ ./app/
COPY alembic.ini ./

# Run migrations and start
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

## Frontend Dockerfile (pnpm)
```dockerfile
# Build stage
FROM node:22-slim AS builder

# Install pnpm
RUN npm install -g pnpm

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm run build

# Serve stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

## nginx.conf (frontend)
```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://rag-backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Portainer Deployment
1. Go to Portainer → Stacks → Add Stack
2. Paste docker-compose content
3. Upload `.env` file or set env vars in Portainer UI
4. Deploy
5. Verify: `http://your-vps-ip:8000` (backend) and `http://your-vps-ip:3000` (frontend)

## .env.example
```env
# Database (your existing PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/rag_system

# Admin
ADMIN_PIN_HASH=$2b$12$...  # bcrypt hash of your PIN
SECRET_KEY=your-random-secret-key-32-chars

# Providers (fill those you want to use)
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
TAVILY_API_KEY=your-tavily-key

# Environment
ENVIRONMENT=production
```

## Generate Admin PIN Hash
```python
import bcrypt
pin = "1234"  # change this!
hashed = bcrypt.hashpw(pin.encode(), bcrypt.gensalt())
print(hashed.decode())
```
