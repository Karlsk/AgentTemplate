#!/bin/bash
set -e

# Print initial environment values (before loading .env)
echo "Starting with these environment variables:"
echo "APP_ENV: ${APP_ENV:-development}"
echo "Initial Database Server: $( [[ -n ${POSTGRES_SERVER:-} ]] && echo 'set' || echo 'Not set' )"
echo "Initial Database Port: $( [[ -n ${POSTGRES_PORT:-} ]] && echo 'set' || echo 'Not set' )"
echo "Initial Database Name: $( [[ -n ${POSTGRES_DB:-} ]] && echo 'set' || echo 'Not set' )"
echo "Initial Database User: $( [[ -n ${POSTGRES_USER:-} ]] && echo 'set' || echo 'Not set' )"

# Load environment variables from the appropriate .env file
if [ -f ".env.${APP_ENV}" ]; then
    echo "Loading environment from .env.${APP_ENV}"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # Extract the key
        key=$(echo "$line" | cut -d '=' -f 1)

        # Only set if not already set in environment
        if [[ -z "${!key}" ]]; then
            export "$line"
        else
            echo "Keeping existing value for $key"
        fi
    done <".env.${APP_ENV}"
elif [ -f ".env" ]; then
    echo "Loading environment from .env"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # Extract the key
        key=$(echo "$line" | cut -d '=' -f 1)

        # Only set if not already set in environment
        if [[ -z "${!key}" ]]; then
            export "$line"
        else
            echo "Keeping existing value for $key"
        fi
    done <".env"
else
    echo "Warning: No .env file found. Using system environment variables."
fi

# Print final environment info
echo -e "\nFinal environment configuration:"
echo "Environment: ${APP_ENV:-development}"
echo "Database Server: $( [[ -n ${POSTGRES_SERVER:-} ]] && echo 'set' || echo 'Not set' )"
echo "Database Port: $( [[ -n ${POSTGRES_PORT:-} ]] && echo 'set' || echo 'Not set' )"
echo "Database Name: $( [[ -n ${POSTGRES_DB:-} ]] && echo 'set' || echo 'Not set' )"
echo "Database User: $( [[ -n ${POSTGRES_USER:-} ]] && echo 'set' || echo 'Not set' )"
echo "Debug Mode: ${DEBUG:-false}"

# Run database migrations if necessary
# e.g., alembic upgrade head
echo "Running database migrations..."
cd /app && .venv/bin/python -m alembic upgrade head || {
    echo "Warning: Alembic migration failed, continuing startup..."
}

# Execute the CMD
exec "$@"
