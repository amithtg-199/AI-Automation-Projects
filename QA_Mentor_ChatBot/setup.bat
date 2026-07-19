@echo off
echo 🚀 Setting up QA Mentor (Windows)...

echo 1. Installing Root dependencies...
call npm install

echo 2. Installing Frontend dependencies...
cd frontend
call npm install
cd ..

echo 3. Backend setup will be handled automatically by 'uv run' during start!

echo ✅ Setup Complete. Run 'npm start' to boot the application.
pause
