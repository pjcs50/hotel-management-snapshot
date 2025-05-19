#!/usr/bin/env python3
"""
Run database migrations to add missing columns to room_types table.

This script runs the necessary migrations to fix the 'no such column: room_types.amenities_json' error.
"""

import os
import sys
from flask import Flask
from flask_migrate import Migrate, upgrade

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app_factory import create_app
from db import db

def run_migrations():
    """Run all pending database migrations."""
    print("Running database migrations...")
    
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Create migration instance
        migrate = Migrate(app, db)
        
        # Run upgrade to apply migrations
        upgrade()
        
        print("Migrations completed successfully!")

if __name__ == "__main__":
    run_migrations() 