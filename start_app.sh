#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "Starting Backend API on port 8000..."
source .venv/bin/activate
export HF_HUB_OFFLINE=1
export LD_LIBRARY_PATH="/usr/local/lib/ollama/cuda_v12:$LD_LIBRARY_PATH"
python3 api.py &
BACKEND_PID=$!

echo "Starting Frontend on port 5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo "Both servers are running."
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
