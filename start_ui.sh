#!/bin/bash

# Start Backend
echo "Starting Backend Server..."
cd backend
python -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt --quiet
python -c "from database import init_db; init_db()" 2>/dev/null || true
python seed_data.py
python run.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start Frontend
echo "Starting Frontend Server..."
cd frontend
npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Backend running on http://localhost:8000 (PID: $BACKEND_PID)"
echo "Frontend running on http://localhost:3000 (PID: $FRONTEND_PID)"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
