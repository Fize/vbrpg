#!/bin/bash

# VBRPG Deployment Script
# Feature 002: Room Join & AI Agent Management
# 
# This script handles deployment with database migrations for the VBRPG platform.
# It runs Alembic migrations before starting the server to ensure schema is up-to-date.

set -e  # Exit immediately if a command exits with a non-zero status

# Color output helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default configuration
ENVIRONMENT="${ENVIRONMENT:-production}"
BACKEND_DIR="${BACKEND_DIR:-./backend}"
FRONTEND_DIR="${FRONTEND_DIR:-./frontend}"
SKIP_MIGRATION="${SKIP_MIGRATION:-false}"
BACKUP_DB="${BACKUP_DB:-true}"

info "Starting VBRPG deployment process..."
info "Environment: $ENVIRONMENT"
info "Backend directory: $BACKEND_DIR"
info "Frontend directory: $FRONTEND_DIR"

# Step 1: Pre-deployment checks
info "Step 1: Running pre-deployment checks..."

if [ ! -d "$BACKEND_DIR" ]; then
    error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

if [ ! -f "$BACKEND_DIR/alembic.ini" ]; then
    error "Alembic configuration not found: $BACKEND_DIR/alembic.ini"
    exit 1
fi

if [ ! -d "$BACKEND_DIR/alembic/versions" ]; then
    error "Alembic versions directory not found: $BACKEND_DIR/alembic/versions"
    exit 1
fi

info "✓ Pre-deployment checks passed"

# Step 2: Backup database (production only)
if [ "$ENVIRONMENT" = "production" ] && [ "$BACKUP_DB" = "true" ]; then
    info "Step 2: Backing up database..."
    
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKEND_DIR/data/vbrpg_backup_${BACKUP_TIMESTAMP}.db"
    DB_FILE="$BACKEND_DIR/data/vbrpg.db"
    
    if [ -f "$DB_FILE" ]; then
        mkdir -p "$BACKEND_DIR/data/backups"
        cp "$DB_FILE" "$BACKUP_FILE"
        info "✓ Database backed up to: $BACKUP_FILE"
    else
        warn "No existing database found, skipping backup"
    fi
else
    info "Step 2: Skipping database backup (BACKUP_DB=$BACKUP_DB or ENVIRONMENT=$ENVIRONMENT)"
fi

# Step 3: Run database migrations
if [ "$SKIP_MIGRATION" = "false" ]; then
    info "Step 3: Running database migrations..."
    
    cd "$BACKEND_DIR"
    
    # Check current migration version
    info "Current migration version:"
    alembic current || warn "Could not determine current migration version"
    
    # Run migrations
    info "Upgrading database schema..."
    if alembic upgrade head; then
        info "✓ Database migrations completed successfully"
    else
        error "Database migration failed!"
        error "To rollback, run: cd $BACKEND_DIR && alembic downgrade -1"
        exit 1
    fi
    
    # Show new migration version
    info "New migration version:"
    alembic current
    
    cd - > /dev/null
else
    warn "Step 3: Skipping database migrations (SKIP_MIGRATION=$SKIP_MIGRATION)"
fi

# Step 4: Build frontend (production only)
if [ "$ENVIRONMENT" = "production" ] && [ -d "$FRONTEND_DIR" ]; then
    info "Step 4: Building frontend..."
    
    cd "$FRONTEND_DIR"
    
    if [ ! -f "package.json" ]; then
        warn "No package.json found, skipping frontend build"
    else
        info "Installing frontend dependencies..."
        npm install --production
        
        info "Building frontend..."
        npm run build
        
        info "✓ Frontend build completed"
    fi
    
    cd - > /dev/null
else
    info "Step 4: Skipping frontend build (ENVIRONMENT=$ENVIRONMENT or no frontend directory)"
fi

# Step 5: Restart backend service
info "Step 5: Restarting backend service..."

if [ "$ENVIRONMENT" = "production" ]; then
    # Production: Use systemd or docker-compose
    if command -v systemctl &> /dev/null && systemctl is-active --quiet vbrpg-backend; then
        info "Restarting vbrpg-backend service..."
        sudo systemctl restart vbrpg-backend
        info "✓ Backend service restarted"
    elif command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        info "Restarting Docker containers..."
        docker-compose restart backend
        info "✓ Docker backend container restarted"
    else
        warn "No systemd service or docker-compose found"
        warn "Please restart the backend manually"
    fi
else
    # Development: Just show instructions
    info "Development environment - manual restart required"
    info "To start the backend, run:"
    info "  cd $BACKEND_DIR && uvicorn src.main:app --reload"
fi

# Step 6: Health check
info "Step 6: Running health check..."

sleep 2  # Wait for service to start

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
HEALTH_ENDPOINT="$BACKEND_URL/health"

info "Checking $HEALTH_ENDPOINT..."

if command -v curl &> /dev/null; then
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_ENDPOINT" || echo "000")
    
    if [ "$RESPONSE" = "200" ]; then
        info "✓ Backend is healthy (HTTP $RESPONSE)"
    else
        warn "Backend health check returned HTTP $RESPONSE"
        warn "The service may need more time to start"
    fi
else
    warn "curl not found, skipping health check"
fi

# Step 7: Post-deployment summary
info "=========================================="
info "Deployment completed successfully!"
info "=========================================="
info ""
info "Summary:"
info "  - Environment: $ENVIRONMENT"
info "  - Database migrations: $([ "$SKIP_MIGRATION" = "false" ] && echo "Applied" || echo "Skipped")"
info "  - Database backup: $([ "$BACKUP_DB" = "true" ] && echo "Created" || echo "Skipped")"
info "  - Frontend build: $([ "$ENVIRONMENT" = "production" ] && echo "Completed" || echo "Skipped")"
info "  - Backend service: $([ "$ENVIRONMENT" = "production" ] && echo "Restarted" || echo "Manual restart required")"
info ""
info "Next steps:"
info "  1. Test the deployment: curl $BACKEND_URL/health"
info "  2. Run smoke tests: ./scripts/smoke-tests.sh"
info "  3. Monitor logs for errors"
info ""

# Environment-specific notes
if [ "$ENVIRONMENT" = "staging" ]; then
    info "Staging deployment notes:"
    info "  - Run full E2E tests: cd frontend && npm run test:e2e"
    info "  - Test concurrent joins: cd backend && uv run pytest tests/performance/"
    info "  - Verify real-time events work across multiple clients"
fi

if [ "$ENVIRONMENT" = "production" ]; then
    info "Production deployment notes:"
    info "  - Monitor error logs: journalctl -u vbrpg-backend -f"
    info "  - Check database size: ls -lh $BACKEND_DIR/data/vbrpg.db"
    info "  - Backups located in: $BACKEND_DIR/data/backups/"
fi

info "=========================================="

exit 0
