#!/usr/bin/env bash
# Exit on error
set -o errexit

# Optional: Run database migrations here if using Alembic
# alembic upgrade head

# Start the application using uvicorn
# We use host 0.0.0.0 to bind to all interfaces for Render
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
