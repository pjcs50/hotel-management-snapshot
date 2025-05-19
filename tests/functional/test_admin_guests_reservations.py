"""
Tests for admin guests and reservations functionality.

This module contains tests for the admin guest and reservation management routes.
"""

import pytest
from flask import url_for
from app.models.user import User
from app.models.customer import Customer
from app.models.booking import Booking


def test_guests_unauthorized(client):
    """Test accessing guests page without login is redirected."""
    response = client.get('/admin/guests', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'Please log in to access this page' in response.data


def test_guests_wrong_role(client, auth, app, db):
    """Test accessing guests with wrong role is forbidden."""
    with app.app_context():
        # Create receptionist user
        user = User(username="receptionist", email="receptionist@example.com", role="receptionist")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as receptionist
        auth.login(user.email, "password")
        
        # Try to access guests
        response = client.get('/admin/guests')
        assert response.status_code == 403  # Forbidden


def test_guests_admin_access(client, auth, app, db):
    """Test accessing guests with admin role."""
    with app.app_context():
        # Create admin user
        user = User(username="admin", email="admin@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Access guests
        response = client.get('/admin/guests')
        assert response.status_code == 200
        assert b'Guest Management' in response.data
        assert b'Guest Directory' in response.data


def test_guest_details(client, auth, app, db):
    """Test viewing guest details."""
    with app.app_context():
        # Create admin user
        admin = User(username="admin2", email="admin2@example.com", role="admin")
        admin.set_password("password")
        db.session.add(admin)
        
        # Create customer user with profile
        user = User(username="testcustomer", email="testcustomer@example.com", role="customer")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()
        
        # Create customer profile
        customer = Customer(
            user_id=user.id,
            name="Test Customer",
            phone="123-456-7890",
            address="123 Test St",
            profile_complete=True
        )
        db.session.add(customer)
        db.session.commit()
        
        # Log in as admin
        auth.login(admin.email, "password")
        
        # View guest details
        response = client.get(f'/admin/guests/{customer.id}')
        assert response.status_code == 200
        assert b'Guest Details' in response.data
        assert b'Test Customer' in response.data
        assert b'123-456-7890' in response.data


def test_reservations_unauthorized(client):
    """Test accessing reservations page without login is redirected."""
    response = client.get('/admin/reservations', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'Please log in to access this page' in response.data


def test_reservations_wrong_role(client, auth, app, db):
    """Test accessing reservations with wrong role is forbidden."""
    with app.app_context():
        # Create housekeeping user
        user = User(username="housekeeper", email="housekeeper@example.com", role="housekeeping")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as housekeeping
        auth.login(user.email, "password")
        
        # Try to access reservations
        response = client.get('/admin/reservations')
        assert response.status_code == 403  # Forbidden


def test_reservations_admin_access(client, auth, app, db):
    """Test accessing reservations with admin role."""
    with app.app_context():
        # Create admin user
        user = User(username="admin3", email="admin3@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Access reservations
        response = client.get('/admin/reservations')
        assert response.status_code == 200
        assert b'Reservation Management' in response.data
        assert b'Search & Filters' in response.data


def test_reservations_filter(client, auth, app, db):
    """Test filtering reservations."""
    with app.app_context():
        # Create admin user
        user = User(username="admin4", email="admin4@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Filter reservations by status
        response = client.get('/admin/reservations?status=Reserved')
        assert response.status_code == 200
        assert b'Reservation Management' in response.data
        
        # Filter by date range
        response = client.get('/admin/reservations?date_from=2024-01-01&date_to=2024-12-31')
        assert response.status_code == 200
        assert b'Reservation Management' in response.data 