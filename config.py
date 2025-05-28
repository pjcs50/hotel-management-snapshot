"""
Configuration module for the Hotel Management System.

This module defines configuration classes for different environments
(development, testing, production). It loads environment variables
from a .env file using python-dotenv.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class with settings common to all environments."""

    # Flask configuration
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key-for-development-only"
    DEBUG = False
    TESTING = False
    # Allow external connections
    HOST = "0.0.0.0"

    # SQLAlchemy configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///hotel_management.db"
    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    # JWT configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    )

    # Flask-Mail configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 25))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "False").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

    # Logging configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", "app.log")

    # File upload configuration
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

    # Application specific settings
    HOTEL_NAME = os.environ.get("HOTEL_NAME", "Horizon Hotel")
    DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "USD")
    RESERVATION_TIMEOUT = int(os.environ.get("RESERVATION_TIMEOUT", 1800))  # 30 minutes
    ENABLE_NOTIFICATIONS = (
        os.environ.get("ENABLE_NOTIFICATIONS", "True").lower() == "true"
    )

    # Stripe settings
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_51OxXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_51OxXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")


class DevelopmentConfig(Config):
    """Configuration for development environment."""

    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Configuration for testing environment."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True

    def __init__(self):
        """Initialize testing configuration and set environment variables."""
        os.environ['TESTING'] = 'True'
        os.environ['FLASK_ENV'] = 'testing'


class ProductionConfig(Config):
    """Configuration for production environment."""

    pass  # Production-specific settings can be added here


# Configuration dictionary to easily switch between environments
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

# Get current configuration from environment or default to development
def get_config():
    """Returns the appropriate configuration class based on the environment."""
    env = os.environ.get("FLASK_ENV", "development")
    return config.get(env, config["default"])