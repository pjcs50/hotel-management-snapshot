"""
PyTest configuration file.

This module provides fixtures and configuration for pytest.
"""

import os
import pytest
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_login import login_user, logout_user
from flask import url_for

from app_factory import create_app
from db import db as _db
from config import TestingConfig
from app.models.user import User


# Set SERVER_NAME for url_for to work outside a request context
TestingConfig.SERVER_NAME = 'localhost.localdomain'


@pytest.fixture(scope="session")
def app():
    """Create a Flask app context for the tests."""
    app = create_app(TestingConfig)
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def db(app):
    """Create a database for the tests."""
    # _db.app = app # This is typically handled by db.init_app(app)
    with app.app_context():  # Ensure operations are within app context
        _db.create_all()
    yield _db
    with app.app_context():  # Ensure operations are within app context
        _db.drop_all()


@pytest.fixture(scope="function")
def db_session(db):
    """Yields a SQLAlchemy session with a transaction that is rolled back after the test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Clear all data from tables before each test
    # Ensure tables are created if they weren't (e.g. if drop_all was aggressive)
    # db.create_all() # This might be too slow if called for every function
    for table in reversed(db.metadata.sorted_tables):
        connection.execute(table.delete())
    # connection.commit() # Commit the deletions - No, this should be part of the test's transaction
    # Re-begin transaction for the test - Not needed if commit isn't called above
    # The initial transaction = connection.begin() is what the test will use.

    db.session = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=connection)
    )

    yield db.session

    db.session.remove()
    transaction.rollback()  # This rollback should undo the deletes if test fails early or any test data
    connection.close()

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    client = app.test_client()
    
    # Add a method to get CSRF token from a page
    def get_csrf_token(self):
        """Extract CSRF token from any page with a form."""
        with app.test_request_context():
            # Use a route that should show a form with CSRF token
            response = self.get('/auth/login')
            data = response.get_data(as_text=True)
            match = re.search(r'name="csrf_token" value="(.+?)"', data)
            if match:
                return match.group(1)
            else:
                # Use app's CSRF token directly if we can't find it in the page
                from flask_wtf.csrf import generate_csrf
                return generate_csrf()
    
    # Attach the method to the client
    client.get_csrf_token = get_csrf_token.__get__(client)
    
    return client

@pytest.fixture
def customer_user(db_session):
    """Create a customer user for testing."""
    user = User(
        username="customer",
        email="customer@example.com",
        role="customer",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def receptionist_user(db_session):
    """Create a receptionist user for testing."""
    # Use a unique email address to avoid conflicts
    user = User(
        username="receptionist_unique",
        email="receptionist_unique@example.com",
        role="receptionist",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def manager_user(db_session):
    """Create a manager user for testing."""
    user = User(
        username="manager",
        email="manager@example.com",
        role="manager",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def housekeeping_user(db_session):
    """Create a housekeeping user for testing."""
    user = User(
        username="housekeeping",
        email="housekeeping@example.com",
        role="housekeeping",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="admin",
        email="admin@example.com",
        role="admin",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user

class AuthActions:
    """Helper class for authentication actions in tests."""
    
    def __init__(self, client):
        self._client = client
        
    def login(self, email, password):
        """Log in with the given credentials."""
        return self._client.post(
            "/auth/login",
            data={"email": email, "password": password},
            follow_redirects=True
        )
    
    def logout(self):
        """Log out the current user."""
        return self._client.get("/auth/logout", follow_redirects=True)

@pytest.fixture
def auth(client):
    """Create an AuthActions instance for testing."""
    return AuthActions(client) 

@pytest.fixture
def login_user(client):
    """Fixture to log in a user for testing."""
    def _login_user(user):
        return client.post('/auth/login', data={
            'email': user.email,
            'password': 'password'
        }, follow_redirects=True)
    return _login_user

# Add pytest-mock fixture if it's not available
try:
    import pytest_mock
except ImportError:
    @pytest.fixture
    def mocker():
        """Mock fixture to replace pytest-mock when it's not available."""
        from unittest.mock import patch, MagicMock
        
        class SimpleMocker:
            def patch(self, *args, **kwargs):
                return patch(*args, **kwargs)
                
            def MagicMock(self, *args, **kwargs):
                return MagicMock(*args, **kwargs)
                
        return SimpleMocker() 