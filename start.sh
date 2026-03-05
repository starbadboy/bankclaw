#!/bin/bash

# Kill any existing Streamlit processes
echo "🛑 Stopping existing Streamlit processes..."
pkill -f "streamlit run" 2>/dev/null || true
sleep 2

# Start Streamlit
echo "🚀 Starting Streamlit app..."
cd "$(dirname "$0")"
uv run streamlit run webapp/app.py --server.headless=true --server.port=8501

echo ""
echo "✨ App is running at http://localhost:8501"
