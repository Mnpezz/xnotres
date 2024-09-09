#!/usr/bin/env bash
# exit on error
set -o errexit

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Add any other build steps here
