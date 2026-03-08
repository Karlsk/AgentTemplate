#!/bin/bash
set -e

# Script to view Docker Compose logs

if [ $# -lt 1 ]; then
  echo "Usage: $0 <environment> [service]"
  echo "Environments: development, staging, production"
  echo "Services: app, db (optional, default: all core services)"
  exit 1
fi

ENV=$1
SERVICE=${2:-}

# Validate environment
if [[ ! "$ENV" =~ ^(development|staging|production)$ ]]; then
  echo "Invalid environment. Must be one of: development, staging, production"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [ -n "$SERVICE" ]; then
  echo "Viewing logs for $SERVICE in $ENV environment (Ctrl+C to exit)"
  APP_ENV=$ENV docker compose logs -f "$SERVICE"
else
  echo "Viewing logs for all core services in $ENV environment (Ctrl+C to exit)"
  APP_ENV=$ENV docker compose logs -f
fi 