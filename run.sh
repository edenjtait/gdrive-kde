#!/bin/bash

# Exit on error
set -e

# Script directory
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
VENV_DIR="$SCRIPT_DIR/venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install required packages
echo "Installing required packages..."
pip install PyQt6

# Make sure src/main.py is executable
chmod +x "$SCRIPT_DIR/src/main.py"

# Run the application
echo "Starting application..."
"$SCRIPT_DIR/src/main.py"

# Deactivate venv when the app exits
deactivate
