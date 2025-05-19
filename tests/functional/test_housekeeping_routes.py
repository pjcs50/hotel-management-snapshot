"""
Tests for housekeeping routes.

This module contains tests for the housekeeping routes functionality.
"""

import pytest
from flask import url_for, session
from app.models.user import User


def test_housekeeping_dashboard_unauthorized(client):
    """Test accessing housekeeping dashboard without login is redirected."""
    response = client.get('/housekeeping/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'Please log in to access this page' in response.data


def test_housekeeping_dashboard_wrong_role(client, auth, app, db_session):
    """Test accessing housekeeping dashboard with wrong role is forbidden."""
    with app.app_context():
        # Create customer user
        user = User(username="customer_hk_dash", email="customer_hk_dash@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Try to access housekeeping dashboard
        response = client.get('/housekeeping/dashboard')
        assert response.status_code == 403  # Forbidden


def test_housekeeping_dashboard(client, auth, app, db_session):
    """Test accessing housekeeping dashboard with correct role."""
    with app.app_context():
        # Create housekeeping user
        user = User(username="housekeeper_hk_dash", email="housekeeper_hk_dash@example.com", role="housekeeping")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as housekeeping
        auth.login(user.email, "password")
        
        # Access housekeeping dashboard
        response = client.get('/housekeeping/dashboard')
        assert response.status_code == 200
        assert b'Housekeeping Dashboard' in response.data


def test_housekeeping_checkout_rooms_unauthorized(client):
    """Test accessing checkout rooms without login is redirected."""
    response = client.get('/housekeeping/checkout-rooms', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data


def test_housekeeping_checkout_rooms_wrong_role(client, auth, app, db_session):
    """Test accessing checkout rooms with wrong role is forbidden."""
    with app.app_context():
        # Create customer user
        user = User(username="customer_hk_checkout", email="customer_hk_checkout@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Try to access checkout rooms
        response = client.get('/housekeeping/checkout-rooms')
        assert response.status_code == 403  # Forbidden


def test_housekeeping_checkout_rooms(client, auth, app, db_session):
    """Test accessing checkout rooms with correct role."""
    with app.app_context():
        # Create housekeeping user
        user = User(username="housekeeper_hk_checkout", email="housekeeper_hk_checkout@example.com", role="housekeeping")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as housekeeping
        auth.login(user.email, "password")
        
        # Access checkout rooms
        response = client.get('/housekeeping/checkout-rooms')
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "Checkout Rooms - Not yet implemented" in data["message"]


def test_housekeeping_cleaning_schedule_unauthorized(client):
    """Test accessing cleaning schedule without login is redirected."""
    response = client.get('/housekeeping/cleaning-schedule', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data


def test_housekeeping_cleaning_schedule_wrong_role(client, auth, app, db_session):
    """Test accessing cleaning schedule with wrong role is forbidden."""
    with app.app_context():
        # Create receptionist user
        user = User(username="receptionist_hk_clean", email="receptionist_hk_clean@example.com", role="receptionist")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as receptionist
        auth.login(user.email, "password")
        
        # Try to access cleaning schedule
        response = client.get('/housekeeping/cleaning-schedule')
        assert response.status_code == 403  # Forbidden


def test_housekeeping_cleaning_schedule(client, auth, app, db_session):
    """Test accessing cleaning schedule with correct role."""
    with app.app_context():
        # Create housekeeping user
        user = User(username="housekeeper_hk_clean", email="housekeeper_hk_clean@example.com", role="housekeeping")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as housekeeping
        auth.login(user.email, "password")
        
        # Access cleaning schedule
        response = client.get('/housekeeping/cleaning-schedule')
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "Cleaning Schedule - Not yet implemented" in data["message"]


def test_housekeeping_inventory_unauthorized(client):
    """Test accessing inventory without login is redirected."""
    response = client.get('/housekeeping/inventory', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data


def test_housekeeping_inventory_wrong_role(client, auth, app, db_session):
    """Test accessing inventory with wrong role is forbidden."""
    with app.app_context():
        # Create manager user
        user = User(username="manager_hk_inv", email="manager_hk_inv@example.com", role="manager")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as manager
        auth.login(user.email, "password")
        
        # Try to access inventory
        response = client.get('/housekeeping/inventory')
        assert response.status_code == 403  # Forbidden


def test_housekeeping_inventory(client, auth, app, db_session):
    """Test accessing inventory with correct role."""
    with app.app_context():
        # Create housekeeping user
        user = User(username="housekeeper_hk_inv", email="housekeeper_hk_inv@example.com", role="housekeeping")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as housekeeping
        auth.login(user.email, "password")
        
        # Access inventory
        response = client.get('/housekeeping/inventory')
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "Housekeeping Inventory - Not yet implemented" in data["message"]


def test_housekeeping_rooms_to_clean(client, auth, app, db_session):
    """Test accessing rooms to clean with correct role."""
    with app.app_context():
        # Create housekeeping user
        user = User(username="housekeeper_hk_rtc", email="housekeeper_hk_rtc@example.com", role="housekeeping")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as housekeeping
        auth.login(user.email, "password")
        
        # Access rooms to clean
        response = client.get('/housekeeping/rooms-to-clean')
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "Rooms To Clean - Not yet implemented" in data["message"]


def test_housekeeping_maintenance_requests(client, auth, app, db_session):
    """Test accessing maintenance requests with correct role."""
    with app.app_context():
        # Create housekeeping user
        user = User(username="housekeeper_hk_maint", email="housekeeper_hk_maint@example.com", role="housekeeping")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as housekeeping
        auth.login(user.email, "password")
        
        # Access maintenance requests
        response = client.get('/housekeeping/maintenance-requests')
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "Maintenance Requests - Not yet implemented" in data["message"]


def test_housekeeping_room_status(client, auth, app, db_session):
    """Test accessing room status with correct role."""
    with app.app_context():
        # Create housekeeping user
        user = User(username="housekeeper_hk_status", email="housekeeper_hk_status@example.com", role="housekeeping")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # Log in as housekeeping
        auth.login(user.email, "password")
        
        # Access room status
        response = client.get('/housekeeping/room-status')
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "Room Status Updates - Not yet implemented" in data["message"] 