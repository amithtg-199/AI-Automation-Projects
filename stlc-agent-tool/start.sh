#!/bin/bash
set -e

# Change to the script's directory
cd "$(dirname "$0")"

echo "=================================="
echo " Starting STLC Agentic Tool Setup "
echo "=================================="

# Clean up lingering processes from previous runs
echo "Cleaning up any existing processes on ports 8000 and 5173..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true

# 1. Backend Setup & Start
echo ""
echo "[1/2] Building Backend..."
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' is not installed. Please install it first (e.g., curl -LsSf https://astral.sh/uv/install.sh | sh)"
    exit 1
fi

cd backend
uv sync
cd ..

export PYTHONPATH="."
echo "Starting FastAPI Backend on port 8000 in the background..."
backend/.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Trap SIGINT and SIGTERM to clean up background process
trap 'kill $BACKEND_PID 2>/dev/null; exit' SIGINT SIGTERM EXIT

# Wait for backend to fully initialize
echo "Waiting for backend to fully start..."
TIMEOUT=180
while ! curl -s --max-time 2 http://127.0.0.1:8000/docs > /dev/null; do
    sleep 1
    TIMEOUT=$((TIMEOUT - 1))
    if [ $TIMEOUT -le 0 ]; then
        echo "Error: Backend failed to start within 180 seconds."
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
done

echo "Backend startup complete!"

# 2. Frontend Setup & Start
echo ""
echo "[2/2] Building Frontend..."
if ! command -v npm &> /dev/null; then
    echo "Error: 'npm' is not installed. Please install Node.js."
    exit 1
fi

cd frontend
npm install

echo "Starting React Frontend..."
npm run dev
