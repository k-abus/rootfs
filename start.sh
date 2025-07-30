#!/bin/bash
echo "Starting FSociety Discord Bot..."

# Set default port if not provided
export PORT=${PORT:-8000}

echo "🌐 Using port: $PORT"
echo "🚀 Starting Discord bot and Flask server..."

python app.py 