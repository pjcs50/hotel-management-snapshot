"""
Functional tests for admin navigation features.

This module contains tests for the admin navigation menu and
the dashboard navigation features.
"""

import pytest
from flask import url_for
from app.models.user import User


def test_admin_navbar_unauthorized(client):
    """Test admin navbar links are not accessible without login."""
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    # Admin nav links shouldn't be in the response
    assert b'href="/admin/guests"' not in response.data
    assert b'href="/admin/reservations"' not in response.data
    assert b'href="/admin/reports"' not in response.data


def test_admin_navbar_non_admin_user(client, auth, app, db):
    """Test admin navbar links are not visible to non-admin users."""
    with app.app_context():
        # Create customer user
        user = User(username="customer_nav", email="nav_customer@example.com", role="customer")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Check navbar (follow redirects)
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200
        assert b'href="/admin/guests"' not in response.data
        assert b'href="/admin/reservations"' not in response.data
        assert b'href="/admin/reports"' not in response.data


def test_admin_navbar_visible_to_admin(client, auth, app, db):
    """Test admin navbar links are visible to admin users."""
    with app.app_context():
        # Create admin user
        user = User(username="admin_nav", email="nav_admin@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Check navbar (follow redirects)
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200
        assert b'href="/admin/guests"' in response.data
        assert b'href="/admin/reservations"' in response.data
        assert b'href="/admin/reports"' in response.data


def test_admin_dashboard_nav_cards(client, auth, app, db):
    """Test admin dashboard navigation cards are present."""
    with app.app_context():
        # Create admin user
        user = User(username="admin_dash", email="dash_admin@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Check admin dashboard
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        
        # Check for navigation cards
        assert b'<div class="card bg-primary text-white h-100">' in response.data
        assert b'<div class="card bg-success text-white h-100">' in response.data
        assert b'<div class="card bg-info text-white h-100">' in response.data
        assert b'<div class="card bg-warning text-dark h-100">' in response.data
        
        # Check for correct icons and labels
        assert b'bi-speedometer2' in response.data  # Dashboard icon
        assert b'bi-person-vcard' in response.data  # Guests icon 
        assert b'bi-calendar-check' in response.data  # Reservations icon
        assert b'bi-graph-up' in response.data  # Reports icon


def test_admin_dashboard_quick_links(client, auth, app, db):
    """Test admin dashboard quick links are present."""
    with app.app_context():
        # Create admin user
        user = User(username="admin_links", email="links_admin@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Check admin dashboard
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        
        # Check for quick links
        assert b'Quick Links' in response.data
        assert b'href="/admin/users"' in response.data
        assert b'href="/admin/roles"' in response.data
        assert b'href="/admin/guests"' in response.data
        assert b'href="/admin/reservations"' in response.data
        assert b'href="/admin/reports"' in response.data


def test_navigation_between_admin_pages(client, auth, app, db):
    """Test navigation between admin pages."""
    with app.app_context():
        # Create admin user
        user = User(username="admin_nav_test", email="nav_test_admin@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Start at dashboard
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        
        # Navigate to guests page
        response = client.get('/admin/guests')
        assert response.status_code == 200
        assert b'Guest Management' in response.data
        assert b'Back to Dashboard' in response.data
        
        # Navigate to reservations page
        response = client.get('/admin/reservations')
        assert response.status_code == 200
        assert b'Reservation Management' in response.data
        assert b'Back to Dashboard' in response.data
        
        # Navigate to reports page
        response = client.get('/admin/reports')
        assert response.status_code == 200
        assert b'Reports' in response.data
        assert b'Back to Dashboard' in response.data
        
        # Navigate back to dashboard
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        assert b'Admin Dashboard' in response.data 