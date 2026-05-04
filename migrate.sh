#!/bin/bash

# Make sure the script stops on first error
set -e

# Install python-dotenv if not already installed
pip install python-dotenv

# Clean up
echo "Cleaning up existing migrations..."
rm -rf migrations/
rm -f *.db  # Remove existing database file if any

# Initialize fresh migrations
echo "Initializing new migrations..."
FLASK_APP=wsgi.py flask db init

# Create initial migration
echo "Creating new migration..."
FLASK_APP=wsgi.py flask db migrate -m "Initial migration"

# Apply migration
echo "Applying migration..."
FLASK_APP=wsgi.py flask db upgrade

echo "Migration completed successfully!"
