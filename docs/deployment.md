# Deployment Guide

This guide covers deploying the AI-Powered Tabletop Game Platform to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Deployment](#docker-deployment)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [Production Considerations](#production-considerations)
6. [Scaling Strategies](#scaling-strategies)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)
9. [Security Hardening](#security-hardening)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum** (50 concurrent games, 200 players):
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 20 GB SSD
- **Network**: 100 Mbps

**Recommended** (production):
- **CPU**: 8 cores
- **RAM**: 16 GB
- **Storage**: 50 GB SSD
- **Network**: 1 Gbps

### Software Requirements

- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **Linux**: Ubuntu 22.04 LTS / Debian 12 / RHEL 9 (recommended)
- **SSL Certificate**: For HTTPS (Let's Encrypt recommended)

---

## Docker Deployment

### Quick Start with Docker Compose

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/vbrpg.git
   cd vbrpg
   ```

2. **Create environment files**:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.production
   
   # Edit both files with production values
   nano backend/.env
   nano frontend/.env.production
   ```

3. **Create docker-compose.yml**:
   ```yaml
   version: '3.8'
   
   services:
     backend:
       build:
         context: ./backend
         dockerfile: Dockerfile
       container_name: vbrpg-backend
       restart: unless-stopped
       ports:
         - "8000:8000"
       volumes:
         - ./data:/app/data
         - ./logs:/app/logs
       env_file:
         - ./backend/.env
       environment:
         - DATABASE_URL=sqlite+aiosqlite:////app/data/game_platform.db
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
         start_period: 40s
       networks:
         - vbrpg-network
   
     frontend:
       build:
         context: ./frontend
         dockerfile: Dockerfile
         args:
           - VITE_API_URL=https://api.yourdomain.com
           - VITE_WS_URL=wss://api.yourdomain.com
       container_name: vbrpg-frontend
       restart: unless-stopped
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./ssl:/etc/nginx/ssl:ro
       depends_on:
         backend:
           condition: service_healthy
       networks:
         - vbrpg-network
   
   networks:
     vbrpg-network:
       driver: bridge
   
   volumes:
     data:
     logs:
   ```

4. **Start the application**:
   ```bash
   docker-compose up -d
   ```

5. **Check logs**:
   ```bash
   docker-compose logs -f
   ```

6. **Verify deployment**:
   ```bash
   curl http://localhost:8000/health
   ```

---

## Environment Configuration

### Backend Environment Variables

**Required Variables** (`backend/.env`):

```env
# LLM Configuration (REQUIRED)
OPENAI_API_KEY=sk-...your_key_here
ANTHROPIC_API_KEY=sk-ant-...your_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4

# Database
DATABASE_URL=sqlite+aiosqlite:////app/data/game_platform.db

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=generate_a_secure_random_key_here_minimum_32_chars
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=strict

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Server
LOG_LEVEL=INFO
WORKERS=4

# Game Settings
TURN_TIMEOUT_SECONDS=60
RECONNECTION_GRACE_PERIOD_MINUTES=5
GUEST_RETENTION_DAYS=30
GAME_WARNING_DURATION=120
GAME_MAX_DURATION=180

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

**Generate a secure SECRET_KEY**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Frontend Environment Variables

**Production Build** (`frontend/.env.production`):

```env
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
VITE_ENVIRONMENT=production
```

---

## Database Setup

### SQLite Production Configuration

1. **Enable WAL mode** (Write-Ahead Logging):
   ```bash
   sqlite3 data/game_platform.db "PRAGMA journal_mode=WAL;"
   ```

2. **Set proper permissions**:
   ```bash
   chmod 644 data/game_platform.db
   chown www-data:www-data data/game_platform.db
   ```

3. **Initialize database**:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

### Database Migrations in Production

```bash
# Create backup before migration
./backend/scripts/backup_database.sh

# Run migrations
docker-compose exec backend alembic upgrade head

# Verify migration
docker-compose exec backend alembic current
```

---

## Production Considerations

### SSL/TLS Configuration

**Using Let's Encrypt with Certbot**:

1. **Install Certbot**:
   ```bash
   sudo apt-get update
   sudo apt-get install certbot
   ```

2. **Obtain certificate**:
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
   ```

3. **Configure Nginx** (in frontend/nginx.conf):
   ```nginx
   server {
       listen 443 ssl http2;
       server_name yourdomain.com www.yourdomain.com;
       
       ssl_certificate /etc/nginx/ssl/fullchain.pem;
       ssl_certificate_key /etc/nginx/ssl/privkey.pem;
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers HIGH:!aNULL:!MD5;
       
       location / {
           root /usr/share/nginx/html;
           try_files $uri $uri/ /index.html;
       }
       
       location /api {
           proxy_pass http://backend:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       location /socket.io {
           proxy_pass http://backend:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   
   server {
       listen 80;
       server_name yourdomain.com www.yourdomain.com;
       return 301 https://$server_name$request_uri;
   }
   ```

4. **Auto-renewal**:
   ```bash
   sudo crontab -e
   # Add: 0 3 * * * certbot renew --quiet
   ```

### Reverse Proxy with Nginx

For production, run Nginx as a reverse proxy in front of the application:

```yaml
# Add to docker-compose.yml
  nginx:
    image: nginx:alpine
    container_name: vbrpg-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
    networks:
      - vbrpg-network
```

---

## Scaling Strategies

### Horizontal Scaling

**Load Balancer Configuration** (HAProxy):

```haproxy
frontend http_front
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/yourdomain.pem
    default_backend backend_servers

backend backend_servers
    balance roundrobin
    option httpchk GET /health
    server backend1 backend1:8000 check
    server backend2 backend2:8000 check
    server backend3 backend3:8000 check
```

**Multi-Instance Deployment**:

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

**Start with scaling**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale backend=3
```

### Vertical Scaling

**Increase resources per container**:

```yaml
services:
  backend:
    environment:
      - WORKERS=8  # Increase Uvicorn workers
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

### Database Scaling

For high load, consider migrating to PostgreSQL:

1. **Update backend/.env**:
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/vbrpg
   ```

2. **Add PostgreSQL to docker-compose.yml**:
   ```yaml
   postgres:
     image: postgres:15-alpine
     environment:
       POSTGRES_DB: vbrpg
       POSTGRES_USER: vbrpg_user
       POSTGRES_PASSWORD: secure_password
     volumes:
       - postgres_data:/var/lib/postgresql/data
   ```

---

## Monitoring & Logging

### Application Logs

**View logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

**Log rotation** (add to docker-compose.yml):
```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Metrics Collection

**Prometheus Configuration** (prometheus.yml):
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vbrpg'
    static_configs:
      - targets: ['backend:9090']
```

**Add Prometheus to docker-compose.yml**:
```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
```

### Health Checks

**Automated health monitoring**:
```bash
#!/bin/bash
# healthcheck.sh
while true; do
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "Health check failed at $(date)"
        # Send alert (email, Slack, etc.)
    fi
    sleep 60
done
```

---

## Backup & Recovery

### Automated Backups

**Backup script** (`scripts/backup.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
cp data/game_platform.db "$BACKUP_DIR/db_$DATE.db"
cp data/game_platform.db-wal "$BACKUP_DIR/db_wal_$DATE.db"

# Compress
gzip "$BACKUP_DIR/db_$DATE.db"

# Delete backups older than 7 days
find "$BACKUP_DIR" -name "db_*.db.gz" -mtime +7 -delete

echo "Backup completed: db_$DATE.db.gz"
```

**Cron job**:
```bash
0 2 * * * /app/scripts/backup.sh >> /var/log/backup.log 2>&1
```

### Recovery

**Restore from backup**:
```bash
# Stop application
docker-compose down

# Restore database
gunzip -c backups/db_20251108_020000.db.gz > data/game_platform.db

# Restart application
docker-compose up -d
```

---

## Security Hardening

### Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH (change port if needed)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

### Container Security

1. **Run as non-root user** (Dockerfile):
   ```dockerfile
   RUN adduser --disabled-password --gecos '' appuser
   USER appuser
   ```

2. **Read-only root filesystem**:
   ```yaml
   services:
     backend:
       read_only: true
       tmpfs:
         - /tmp
   ```

3. **Security scanning**:
   ```bash
   docker scan vbrpg-backend:latest
   ```

### Dependency Updates

```bash
# Backend
pip list --outdated
pip install -U package_name

# Frontend
npm outdated
npm update
```

---

## Troubleshooting

### Common Issues

**Issue: Container won't start**
```bash
# Check logs
docker-compose logs backend

# Check health
docker-compose ps

# Rebuild image
docker-compose build --no-cache backend
docker-compose up -d
```

**Issue: Database locked**
```bash
# Check WAL mode
sqlite3 data/game_platform.db "PRAGMA journal_mode;"

# If not WAL, enable it
sqlite3 data/game_platform.db "PRAGMA journal_mode=WAL;"
```

**Issue: High memory usage**
```bash
# Check container stats
docker stats

# Restart containers
docker-compose restart

# Increase memory limits in docker-compose.yml
```

**Issue: WebSocket disconnections**
```bash
# Check Nginx timeout settings
proxy_read_timeout 300s;
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
```

### Performance Debugging

**Enable profiling**:
```python
# In backend/src/main.py
from pyinstrument import Profiler

@app.middleware("http")
async def profile_request(request, call_next):
    profiler = Profiler()
    profiler.start()
    response = await call_next(request)
    profiler.stop()
    print(profiler.output_text())
    return response
```

**Database query analysis**:
```bash
sqlite3 data/game_platform.db "EXPLAIN QUERY PLAN SELECT * FROM game_rooms WHERE status='in_progress';"
```

---

## Production Checklist

Before going live:

- [ ] Environment variables set with production values
- [ ] SECRET_KEY is unique and secure (32+ characters)
- [ ] SSL/TLS certificates installed and auto-renewal configured
- [ ] Database backups automated and tested
- [ ] Monitoring and alerting configured
- [ ] Firewall rules configured
- [ ] Rate limiting enabled
- [ ] Log rotation configured
- [ ] Health checks working
- [ ] Load testing completed
- [ ] Security scan passed
- [ ] Dependencies updated
- [ ] Documentation reviewed
- [ ] Rollback plan documented
- [ ] Support contacts established

---

## Support

For deployment issues:
- GitHub Issues: https://github.com/yourusername/vbrpg/issues
- Documentation: https://github.com/yourusername/vbrpg/docs

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Vue.js Production Deployment](https://vuejs.org/guide/best-practices/production-deployment.html)
- [Let's Encrypt](https://letsencrypt.org/)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
