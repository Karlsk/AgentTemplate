#!/bin/bash
# TerraChatBi Project Management Script
# Usage: ./manager.sh <command> [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Validate environment
validate_env() {
    local env=$1
    if [[ ! "$env" =~ ^(development|staging|production)$ ]]; then
        log_error "Invalid environment. Must be one of: development, staging, production"
        exit 1
    fi
}

# Show help
show_help() {
    cat << EOF
TerraChatBi Project Manager

Usage: ./manager.sh <command> [options]

Commands:
  install                              Install all dependencies
  dev                                  Start full stack in development mode
  stop                                 Stop all services

Docker Build Commands (separate):
  backend-docker-build [ENV]           Build backend Docker image
  frontend-docker-build                Build frontend Docker image
  docker-build [ENV]                   Build all Docker images

Docker Runtime Commands (unified):
  docker-up [ENV] [--with-monitoring]  Start all services with Docker
  docker-down                          Stop all Docker services
  docker-logs [SERVICE]                View service logs
  monitoring-up                        Start monitoring stack only
  monitoring-down                      Stop monitoring stack

Backend Local Commands:
  backend-install                      Install backend dependencies
  backend-dev [ENV]                    Run backend locally

Frontend Local Commands:
  frontend-install                     Install frontend dependencies
  frontend-dev                         Run frontend development server
  frontend-build                       Build frontend for production

Examples:
  ./manager.sh install
  ./manager.sh docker-build production
  ./manager.sh docker-up production
  ./manager.sh docker-up production --with-monitoring
  ./manager.sh docker-down
  ./manager.sh monitoring-up

EOF
}

# Install all dependencies
cmd_install() {
    log_step "Installing backend dependencies..."
    cd backend && pip install uv && uv sync
    cd ..
    
    log_step "Installing frontend dependencies..."
    cd frontend && npm install
    cd ..
    
    log_info "All dependencies installed successfully"
}

# Backend local development
cmd_backend_dev() {
    local env=${1:-development}
    validate_env "$env"
    log_step "Starting backend in $env mode..."
    cd backend
    source scripts/set_env.sh "$env"
    uv run uvicorn app.main:app --reload --port 8000 --loop uvloop
}

# Backend Docker build
cmd_backend_docker_build() {
    local env=${1:-development}
    validate_env "$env"
    log_step "Building backend Docker image ($env)..."
    docker compose build app --build-arg APP_ENV="$env"
    log_info "Backend Docker image built successfully"
}

# Frontend Docker build
cmd_frontend_docker_build() {
    log_step "Building frontend Docker image..."
    docker compose build frontend
    log_info "Frontend Docker image built successfully"
}

# Build all Docker images
cmd_docker_build() {
    local env=${1:-development}
    validate_env "$env"
    log_step "Building all Docker images ($env)..."
    APP_ENV="$env" docker compose build
    log_info "All Docker images built successfully"
}

# Full stack Docker up (unified)
cmd_docker_up() {
    local env=${1:-development}
    local with_monitoring=false
    
    # Parse arguments
    shift || true
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --with-monitoring)
                with_monitoring=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    validate_env "$env"
    log_step "Starting all services with Docker ($env)..."
    
    # Start main stack
    APP_ENV="$env" docker compose up -d
    
    # Start monitoring if requested
    if [ "$with_monitoring" = true ]; then
        log_step "Starting monitoring stack..."
        docker compose -f docker-compose.monitoring.yml up -d
    fi
    
    log_info "All services started:"
    log_info "  - Frontend: http://localhost:18080"
    log_info "  - Backend API: http://localhost:8000"
    log_info "  - API Docs: http://localhost:8000/docs"
    
    if [ "$with_monitoring" = true ]; then
        log_info "  - Grafana: http://localhost:3000"
        log_info "  - Prometheus: http://localhost:9090"
        log_info "  - cAdvisor: http://localhost:8080"
    fi
}

# Full stack Docker down
cmd_docker_down() {
    log_step "Stopping all Docker services..."
    docker compose down 2>/dev/null || true
    docker compose -f docker-compose.monitoring.yml down 2>/dev/null || true
    log_info "All services stopped"
}

# View logs
cmd_docker_logs() {
    local service=${1:-}
    if [ -n "$service" ]; then
        docker compose logs -f "$service"
    else
        docker compose logs -f
    fi
}

# Monitoring up
cmd_monitoring_up() {
    log_step "Starting monitoring stack..."
    docker compose -f docker-compose.monitoring.yml up -d
    log_info "Monitoring stack started:"
    log_info "  - Grafana: http://localhost:3000 (admin/admin)"
    log_info "  - Prometheus: http://localhost:9090"
    log_info "  - cAdvisor: http://localhost:8080"
}

# Monitoring down
cmd_monitoring_down() {
    log_step "Stopping monitoring stack..."
    docker compose -f docker-compose.monitoring.yml down
    log_info "Monitoring stack stopped"
}

# Frontend install
cmd_frontend_install() {
    log_step "Installing frontend dependencies..."
    cd frontend && npm install
    cd ..
    log_info "Frontend dependencies installed"
}

# Frontend dev
cmd_frontend_dev() {
    log_step "Starting frontend development server..."
    cd frontend && npm run dev
}

# Frontend build
cmd_frontend_build() {
    log_step "Building frontend..."
    cd frontend && npm run build
    log_info "Frontend built successfully"
}

# Full stack dev mode
cmd_dev() {
    log_step "Starting full stack in development mode..."
    cmd_docker_up development
    log_info "Full stack started:"
    log_info "  - Frontend: http://localhost:18080"
    log_info "  - Backend API: http://localhost:8000"
}

# Stop all services
cmd_stop() {
    cmd_docker_down
}

# Main command dispatcher
main() {
    local cmd=$1
    shift || true
    
    case "$cmd" in
        # Installation
        install)
            cmd_install
            ;;
        
        # Docker build commands (separate)
        backend-docker-build)
            cmd_backend_docker_build "$@"
            ;;
        frontend-docker-build)
            cmd_frontend_docker_build
            ;;
        docker-build)
            cmd_docker_build "$@"
            ;;
        
        # Docker runtime commands (unified)
        docker-up)
            cmd_docker_up "$@"
            ;;
        docker-down)
            cmd_docker_down
            ;;
        docker-logs)
            cmd_docker_logs "$@"
            ;;
        
        # Monitoring
        monitoring-up)
            cmd_monitoring_up
            ;;
        monitoring-down)
            cmd_monitoring_down
            ;;
        
        # Backend local
        backend-install)
            cd backend && pip install uv && uv sync
            ;;
        backend-dev)
            cmd_backend_dev "$@"
            ;;
        
        # Frontend local
        frontend-install)
            cmd_frontend_install
            ;;
        frontend-dev)
            cmd_frontend_dev
            ;;
        frontend-build)
            cmd_frontend_build
            ;;
        
        # Full stack
        dev)
            cmd_dev
            ;;
        stop)
            cmd_stop
            ;;
        
        # Help
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $cmd"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
