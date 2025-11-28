#!/usr/bin/env bash

#######################################
# VBRPG Backend Service Startup Script
#
# Usage: ./start.sh [dev|prod] [--reload] [--port PORT]
#
# Arguments:
#   dev     Development mode (default)
#   prod    Production mode
#   --reload  Enable hot reload (dev only)
#   --port    Specify port number (default: 8000)
#
# Platform: Linux/macOS
# Author: VBRPG Team
# Date: 2025-11-29
#######################################

set -euo pipefail

# =============================================================================
# Constants
# =============================================================================
readonly SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
readonly DEFAULT_PORT=8000
readonly DEFAULT_HOST="0.0.0.0"
readonly VENV_DIR=".venv"
readonly LOG_DIR="${SCRIPT_DIR}/logs"
readonly PID_FILE="${SCRIPT_DIR}/.server.pid"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================
log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "${level}" in
        INFO)
            printf "${GREEN}[%s] [INFO]${NC} %s\n" "${timestamp}" "${message}"
            ;;
        WARN)
            printf "${YELLOW}[%s] [WARN]${NC} %s\n" "${timestamp}" "${message}"
            ;;
        ERROR)
            printf "${RED}[%s] [ERROR]${NC} %s\n" "${timestamp}" "${message}" >&2
            ;;
        DEBUG)
            printf "${BLUE}[%s] [DEBUG]${NC} %s\n" "${timestamp}" "${message}"
            ;;
    esac
}

log_info() {
    log "INFO" "$1"
}

log_warn() {
    log "WARN" "$1"
}

log_error() {
    log "ERROR" "$1"
}

log_debug() {
    log "DEBUG" "$1"
}

# =============================================================================
# Helper Functions
# =============================================================================
show_help() {
    cat << EOF
VBRPG Backend Service Startup Script

Usage: $0 [OPTIONS] [MODE]

MODE:
    dev         Development mode with debug logging (default)
    prod        Production mode with optimized settings

OPTIONS:
    -h, --help      Show this help message
    -r, --reload    Enable auto-reload on file changes (dev only)
    -p, --port PORT Specify port number (default: ${DEFAULT_PORT})
    -w, --workers N Number of workers (prod only, default: auto)
    --host HOST     Specify host address (default: ${DEFAULT_HOST})

Examples:
    $0                      # Start in dev mode on port 8000
    $0 dev --reload         # Start in dev mode with hot reload
    $0 prod --workers 4     # Start in prod mode with 4 workers
    $0 --port 9000          # Start on port 9000

EOF
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    local python_version
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    log_info "Python version: ${python_version}"
    
    # Check if version >= 3.11
    if [[ "$(printf '%s\n' "3.11" "${python_version}" | sort -V | head -n1)" != "3.11" ]]; then
        log_error "Python 3.11+ is required, found ${python_version}"
        exit 1
    fi
}

setup_venv() {
    cd "${SCRIPT_DIR}"
    
    if [[ ! -d "${VENV_DIR}" ]]; then
        log_warn "Virtual environment not found, creating..."
        
        if command -v uv &> /dev/null; then
            log_info "Using uv to create virtual environment"
            uv venv "${VENV_DIR}"
        else
            log_info "Using python3 to create virtual environment"
            python3 -m venv "${VENV_DIR}"
        fi
    fi
    
    # Activate virtual environment
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    log_info "Virtual environment activated: ${VENV_DIR}"
}

install_deps() {
    log_info "Checking dependencies..."
    
    if command -v uv &> /dev/null; then
        uv pip install -e ".[dev]" --quiet
    else
        pip install -e ".[dev]" --quiet
    fi
    
    log_info "Dependencies are up to date"
}

check_env_file() {
    local env_file="${SCRIPT_DIR}/.env"
    
    if [[ ! -f "${env_file}" ]]; then
        log_warn ".env file not found"
        
        if [[ -f "${SCRIPT_DIR}/.env.example" ]]; then
            log_info "Copying .env.example to .env"
            cp "${SCRIPT_DIR}/.env.example" "${env_file}"
            log_warn "Please update .env with your configuration"
        else
            log_warn "No .env.example found, using default environment"
        fi
    fi
}

check_database() {
    log_info "Checking database connection..."
    
    if python3 -c "
from src.database import engine
import asyncio
async def check():
    async with engine.begin() as conn:
        await conn.execute('SELECT 1')
asyncio.run(check())
" 2>/dev/null; then
        log_info "Database connection successful"
    else
        log_warn "Database connection failed, service may not work properly"
    fi
}

run_migrations() {
    log_info "Running database migrations..."
    
    if [[ -f "${SCRIPT_DIR}/alembic.ini" ]]; then
        alembic upgrade head
        log_info "Database migrations completed"
    else
        log_warn "alembic.ini not found, skipping migrations"
    fi
}

cleanup() {
    log_info "Cleaning up..."
    
    if [[ -f "${PID_FILE}" ]]; then
        rm -f "${PID_FILE}"
    fi
}

# =============================================================================
# Main Functions
# =============================================================================
start_dev() {
    local port="$1"
    local host="$2"
    local reload="$3"
    
    log_info "Starting backend in DEVELOPMENT mode..."
    log_info "Server: http://${host}:${port}"
    log_info "API Docs: http://localhost:${port}/docs"
    
    local cmd="uvicorn main:app --host ${host} --port ${port}"
    
    if [[ "${reload}" == "true" ]]; then
        cmd="${cmd} --reload"
        log_info "Hot reload enabled"
    fi
    
    # Set development environment
    export ENVIRONMENT="development"
    export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
    
    log_info "Press Ctrl+C to stop the server"
    echo ""
    
    exec ${cmd}
}

start_prod() {
    local port="$1"
    local host="$2"
    local workers="$3"
    
    log_info "Starting backend in PRODUCTION mode..."
    log_info "Server: http://${host}:${port}"
    
    # Auto-calculate workers if not specified
    if [[ "${workers}" == "auto" ]]; then
        workers=$(($(nproc) * 2 + 1))
        log_info "Auto-detected workers: ${workers}"
    fi
    
    # Set production environment
    export ENVIRONMENT="production"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    
    # Create log directory
    mkdir -p "${LOG_DIR}"
    
    local cmd="uvicorn main:app \
        --host ${host} \
        --port ${port} \
        --workers ${workers} \
        --access-log \
        --log-level info"
    
    log_info "Workers: ${workers}"
    log_info "Press Ctrl+C to stop the server"
    echo ""
    
    exec ${cmd}
}

main() {
    local mode="dev"
    local port="${DEFAULT_PORT}"
    local host="${DEFAULT_HOST}"
    local reload="false"
    local workers="auto"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -r|--reload)
                reload="true"
                shift
                ;;
            -p|--port)
                if [[ -z "${2:-}" ]]; then
                    log_error "Port number required"
                    exit 1
                fi
                port="$2"
                shift 2
                ;;
            --host)
                if [[ -z "${2:-}" ]]; then
                    log_error "Host address required"
                    exit 1
                fi
                host="$2"
                shift 2
                ;;
            -w|--workers)
                if [[ -z "${2:-}" ]]; then
                    log_error "Worker count required"
                    exit 1
                fi
                workers="$2"
                shift 2
                ;;
            dev|prod)
                mode="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Setup trap for cleanup
    trap cleanup EXIT INT TERM
    
    log_info "=========================================="
    log_info "  VBRPG Backend Service"
    log_info "=========================================="
    
    # Pre-flight checks
    check_python
    setup_venv
    check_env_file
    install_deps
    
    # Change to script directory
    cd "${SCRIPT_DIR}"
    
    # Start server based on mode
    case "${mode}" in
        dev)
            start_dev "${port}" "${host}" "${reload}"
            ;;
        prod)
            if [[ "${reload}" == "true" ]]; then
                log_warn "Hot reload is not supported in production mode, ignoring..."
            fi
            run_migrations
            start_prod "${port}" "${host}" "${workers}"
            ;;
        *)
            log_error "Invalid mode: ${mode}"
            show_help
            exit 1
            ;;
    esac
}

# =============================================================================
# Entry Point
# =============================================================================
main "$@"
