#!/bin/bash

# Exit on error
set -e

# Find script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "===================================================="
echo "🚀 Starting SAARTHI.AI Application"
echo "===================================================="

# Port pre-flight check.
#
# WHY: an unrelated project's leftover dev server once ended up bound to
# 127.0.0.1:8000 while this app's backend bound to 0.0.0.0:8000 — both
# coexist as distinct sockets, and http://localhost:8000 (what the frontend
# calls by default) silently routed to the WRONG app. Every dashboard
# request 404'd, and the UI just showed empty states — no error, no
# indication anything was wrong. This check catches that class of bug at
# startup instead of leaving you to debug a "blank dashboard" later.
check_port() {
    local port="$1" name="$2"
    local pids
    # -sTCP:LISTEN matters: a plain `lsof -ti :$port` also matches CLIENTS
    # with an open connection to that port (e.g. a browser tab with the
    # dashboard open, or an active SSE stream) — those aren't occupying the
    # port, they're talking to whatever already is. Only the LISTEN socket
    # identifies the actual process to worry about.
    pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
    if [ -n "$pids" ]; then
        echo "❌ Port $port ($name) is already in use by PID(s): $pids"
        echo "   $(ps -o command= -p $(echo "$pids" | head -1) 2>/dev/null || echo '(process details unavailable)')"
        echo ""
        echo "   This is exactly the failure mode that once made the dashboard show"
        echo "   stale/blank data with no error — a different process silently"
        echo "   answered requests meant for this app."
        echo ""
        echo "   Inspect it, and if it's safe to stop:  kill \$(lsof -ti :$port)"
        echo "   Then re-run this script."
        exit 1
    fi
}

check_port 8000 "backend API"
check_port 3000 "frontend UI"
echo "✅ Ports 8000 and 3000 are free."
echo ""

# Locate the Python binary of the conda environment we created
PYTHON_BIN="/opt/anaconda3/envs/darpanai/bin/python3"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "⚠️  Conda environment 'darpanai' not found at $PYTHON_BIN"
    echo "Attempting to run using local conda command..."
    if command -v conda &> /dev/null; then
        PYTHON_BIN="conda run -n darpanai python3"
    else
        echo "❌ Conda is not found. Please ensure conda is installed and try again."
        exit 1
    fi
fi

# Define cleanup function to terminate both processes cleanly on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down backend and frontend..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

echo "📦 Starting Backend API..."
PYTHONUNBUFFERED=1 $PYTHON_BIN -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "🖥️  Starting Frontend Next.js..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✨ SAARTHI.AI is running!"
echo "   - Backend API: http://localhost:8000"
echo "   - Frontend UI: http://localhost:3000"
echo "   - Press Ctrl+C to stop both servers."
echo ""

# Keep script running to wait for background jobs
wait
