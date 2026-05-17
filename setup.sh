#!/bin/bash

# VSAE Setup Script
# This script sets up the Vector Space Ablation Engine environment

echo "🚀 Setting up VSAE (Vector Space Ablation Engine)..."
echo ""

# Check Python version
echo "📋 Checking Python version..."
python3 --version || { echo "❌ Python 3 not found. Please install Python 3.10+"; exit 1; }

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your HINDSIGHT_API_KEY"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "1. Edit .env and add your HINDSIGHT_API_KEY (get it from https://hindsight.dev)"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Start the server: uvicorn backend.main:app --reload"
echo "4. Open http://localhost:8000 in your browser"
echo ""
echo "🎉 Happy ablating!"

# Made with Bob
