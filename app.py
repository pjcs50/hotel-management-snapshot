"""
Main application module for the Hotel Management System.

This module creates the Flask application instance and defines
the main route.
"""

from datetime import datetime
from flask import render_template, redirect, url_for
from flask_login import current_user

from app_factory import create_app

# Create app instance for 'flask run' command
app = create_app()

# Note: The index route is already defined in app_factory.py, 
# so we don't need to redefine it here to avoid conflicts

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"], host=app.config.get("HOST", "127.0.0.1"), port=5001) 