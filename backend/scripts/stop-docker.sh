#!/bin/bash
set -e

# Script to stop Docker Compose services

if [ $# -ne 1 ]; then
    echo "Usage: $0 <environment>"
    echo "Environments: development, staging, production"
    exit 1
fi

ENV=$1

# Validate environment
if [[ ! "$ENV" =~ ^(development|staging|production)$ ]]; then
    echo "Invalid environment. Must be one of: development, staging, production"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Stopping services for $ENV environment"

# Stop core services
echo "Stopping core services..."
APP_ENV=$ENV docker compose down

# Stop monitoring services if they are running
if [ -f "docker-compose.monitoring.yml" ]; then
    echo "Stopping monitoring services..."
    docker compose -f docker-compose.monitoring.yml down 2>/dev/null || echo "Monitoring services were not running"
fi

echo "All services stopped successfully"
