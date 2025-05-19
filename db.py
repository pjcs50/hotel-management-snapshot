"""
Database module for the Hotel Management System.

This module initializes the SQLAlchemy database connection and
provides utility functions for database operations.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import MetaData

# Define naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()


def init_db(app):
    """Initialize database with Flask application."""
    db.init_app(app)
    migrate.init_app(app, db)


def reset_db():
    """Drop all tables and recreate them."""
    db.drop_all()
    db.create_all()


def commit_changes():
    """Commit changes to the database."""
    try:
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        raise e


def add_to_db(item):
    """Add an item to the database."""
    db.session.add(item)


def add_all_to_db(items):
    """Add multiple items to the database."""
    db.session.add_all(items)


def delete_from_db(item):
    """Delete an item from the database."""
    db.session.delete(item) 