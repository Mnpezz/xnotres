#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Recreate the database
python -c "from app import db; db.drop_all(); db.create_all()"

# Initialize the database
python -c "from app import init_db; init_db()"

# Add any other build steps here
