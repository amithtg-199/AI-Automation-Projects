#!/bin/bash
echo "🚀 Setting up QA Mentor (Linux/WSL)..."

echo "1. Installing Root dependencies..."
npm install

echo "2. Installing Frontend dependencies..."
cd frontend
rm -rf node_modules package-lock.json
npm install
cd ..

echo "3. Backend setup will be handled automatically by 'uv run' during start!"

echo "✅ Setup Complete. Run 'npm start' to boot the application."
