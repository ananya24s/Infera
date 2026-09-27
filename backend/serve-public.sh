#!/bin/bash
# Brings the backend up locally and exposes it at the permanent public URL
# (https://tingly-swapping-backless.ngrok-free.dev) via ngrok's free static
# domain. Run this from backend/. Requires: .venv already set up, Ollama
# installed, and `ngrok config add-authtoken ...` already run once.
#
# The frontend is deployed separately on Vercel and always points at that
# same ngrok URL — this script only needs to run whenever you want the site
# to actually be reachable (it's live only while this is running).
set -e
cd "$(dirname "$0")"

echo "Starting backend..."
.venv/bin/python3 -m uvicorn app.main:app --port 8001 &
BACKEND_PID=$!

echo "Waiting for backend to warm up (this can take a minute on a cold model cache)..."
until curl -sf http://localhost:8001/health > /dev/null 2>&1; do sleep 2; done
echo "Backend is up."

echo "Starting ngrok tunnel..."
ngrok http --url=tingly-swapping-backless.ngrok-free.dev 8001 &
NGROK_PID=$!

echo ""
echo "Live at: https://tingly-swapping-backless.ngrok-free.dev"
echo "Frontend: https://infera-five.vercel.app"
echo ""
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $NGROK_PID 2>/dev/null" EXIT
wait
