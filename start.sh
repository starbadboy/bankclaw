#!/bin/bash

# Kill any existing server processes
echo "Stopping existing server processes..."
pkill -f "uvicorn webapp.api" 2>/dev/null || true
pkill -f "streamlit run" 2>/dev/null || true
sleep 1

# Start FastAPI + React dashboard
echo "Starting Bankclaw API server..."
cd "$(dirname "$0")"
uv run uvicorn webapp.api:app --host 0.0.0.0 --port 8501 --reload

echo ""
echo "App is running at http://localhost:8501"
