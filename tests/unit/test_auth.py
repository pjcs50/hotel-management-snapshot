"""
Unit tests for authentication functionality.

Tests user login, registration, and role-based access control.
"""

import pytest
from flask_login import current_user
from flask import url_for

from app.models.user import User
from app.models.customer import Customer
from app.models.staff_request import StaffRequest
from app.services.user_service import UserService


def test_user_loader(app, db_session):
    """Test the Flask-Login user loader function."""
    with app.app_context():
        # Create a test user
        user = User(
            username="testloader",
            email="testloader@example.com",
            role="customer"
        )
        user.set_password("password123")
        
        # Save the user to get an ID
        db_session.add(user)
        db_session.commit()
        
        # Import user_loader function from app
        from app_factory import login_manager
        user_loader_func = login_manager._user_callback
        
        # Test the user loader
        loaded_user = user_loader_func(user.id)
        assert loaded_user is not None
        assert loaded_user.id == user.id
        assert loaded_user.username == "testloader"
        
        # Test with invalid ID
        assert user_loader_func(9999) is None


class TestAuthViews:
    """Test suite for authentication views."""
    
    def test_login_view(self, client, auth):
        auth.logout()
        """Test the login page renders correctly."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Login' in response.data
        assert b'Email' in response.data
        assert b'Password' in response.data
    
    def test_login_success(self, client, db_session, app):
        """Test successful login."""
        with app.app_context():
            # Create a test user
            user = User(
                username="testlogin",
                email="testlogin@example.com",
                role="customer"
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()
        
        # Try to log in
        response = client.post('/auth/login', data={
            'email': 'testlogin@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Logged in successfully' in response.data
        
        # Check that the user is logged in
        with client.session_transaction() as session:
            assert '_user_id' in session
    
    def test_login_failure(self, client, db_session, app, auth):
        auth.logout()
        """Test login with invalid credentials."""
        with app.app_context():
            # Create a test user
            user = User(
                username="testlogin2",
                email="testlogin2@example.com",
                role="customer"
            )
            user.set_password("password123")
            db_session.add(user)
            db_session.commit()
        
        # Try to log in with wrong password
        response = client.post('/auth/login', data={
            'email': 'testlogin2@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        assert b'Invalid email or password' in response.data
        
        # Check that the user is not logged in
        with client.session_transaction() as session:
            assert '_user_id' not in session
    
    def test_register_view(self, client, auth):
        auth.logout()
        """Test the register page renders correctly."""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'Guest Registration' in response.data
        assert b'Full Name' in response.data
        assert b'Username' in response.data
        assert b'Email' in response.data
        assert b'Password' in response.data
    
    def test_register_success(self, client, app, db_session):
        """Test successful registration."""
        # Try to register
        response = client.post('/auth/register', data={
            'name': 'Test User',
            'username': 'testregister',
            'email': 'testregister@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Registration successful' in response.data
        
        # Check that the user was created in the database
        with app.app_context():
            user = User.query.filter_by(email='testregister@example.com').first()
            assert user is not None
            assert user.username == 'testregister'
            assert user.role == 'customer'
            
            # Check that a customer profile was created
            customer = Customer.query.filter_by(user_id=user.id).first()
            assert customer is not None
            assert customer.name == 'Test User'
    
    def test_logout(self, client, db_session, app, auth):
        """Test logout functionality."""
        # Ensure a clean state before this test specific login
        auth.logout()

        user_email_for_login = "testlogout_user@example.com" # Define email beforehand
        user_id_for_assertion = None # To store the ID after creation

        with app.app_context():
            # Create a test user specifically for this logout test
            local_user = User(
                username="testlogout_user_unique", # Ensure username is unique if run multiple times or if previous didn't rollback fully
                email=user_email_for_login, 
                role="customer"
            )
            local_user.set_password("password123")
            db_session.add(local_user)
            db_session.commit()
            user_id_for_assertion = local_user.id # Capture ID while user object is live
        
        # Log in this specific user
        login_response = client.post('/auth/login', data={
            'email': user_email_for_login, # Use the stored email
            'password': 'password123'
        }) # Not following redirects, expect 302 on successful login
        
        assert login_response.status_code == 302 # Successful login should redirect

        # Check that the user is logged in (session cookie exists)
        with client.session_transaction() as session:
            assert '_user_id' in session
            assert session['_user_id'] == str(user_id_for_assertion) # Compare with captured ID
        
        # Perform Logout using the auth fixture method (which follows redirects)
        response = auth.logout()
        assert response.status_code == 200
        assert b'Logged out successfully' in response.data # Flash message should be on the login page
        
        # Check that the user is logged out (session cookie is gone)
        with client.session_transaction() as session:
            assert '_user_id' not in session
    
    def test_staff_register_view(self, client, auth):
        auth.logout()
        """Test the staff register page renders correctly."""
        response = client.get('/auth/staff-register')
        assert response.status_code == 200
        assert b'Staff Registration' in response.data
        assert b'Username' in response.data
        assert b'Email' in response.data
        assert b'Role' in response.data
        assert b'Password' in response.data
    
    def test_staff_register_success(self, client, app, db_session):
        """Test successful staff registration."""
        # Try to register
        response = client.post('/auth/staff-register', data={
            'username': 'teststaff',
            'email': 'teststaff@example.com',
            'role_requested': 'receptionist',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Staff registration submitted for approval' in response.data
        
        # Check that the user was created in the database
        with app.app_context():
            user = User.query.filter_by(email='teststaff@example.com').first()
            assert user is not None
            assert user.username == 'teststaff'
            assert user.role == 'pending'
            assert user.role_requested == 'receptionist'
            assert user.is_active is False
            
            # Check that a staff request was created
            staff_request = StaffRequest.query.filter_by(user_id=user.id).first()
            assert staff_request is not None
            assert staff_request.role_requested == 'receptionist'
            assert staff_request.status == 'pending' 