#!/bin/bash

# Create and activate virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "Error: Could not find virtual environment activation script"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install -e .
pip install -r requirements.txt

# Run the application
echo "Starting the application..."
python -m src.main 