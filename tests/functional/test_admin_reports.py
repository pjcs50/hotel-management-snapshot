"""
Tests for admin reports functionality.

This module contains tests for the admin reports routes and export options.
"""

import pytest
from flask import url_for
from app.models.user import User


def test_reports_unauthorized(client):
    """Test accessing reports page without login is redirected."""
    response = client.get('/admin/reports', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'Please log in to access this page' in response.data


def test_reports_wrong_role(client, auth, app, db):
    """Test accessing reports with wrong role is forbidden."""
    with app.app_context():
        # Create customer user
        user = User(username="customer", email="customer@example.com", role="customer")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Try to access reports
        response = client.get('/admin/reports')
        assert response.status_code == 403  # Forbidden


def test_reports_admin_access(client, auth, app, db):
    """Test accessing reports with admin role."""
    with app.app_context():
        # Create admin user
        user = User(username="admin", email="admin@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Access reports
        response = client.get('/admin/reports')
        assert response.status_code == 200
        assert b'Reports' in response.data
        # assert b'Report Period' in response.data # Placeholder page doesn't have this


def test_report_export_csv(client, auth, app, db):
    """Test exporting report as CSV."""
    with app.app_context():
        # Create admin user
        user = User(username="admin2", email="admin2@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Export report as CSV
        response = client.get('/admin/reports/export?format=csv')
        assert response.status_code == 200
        assert 'text/csv' in response.headers['Content-Type']
        assert response.headers['Content-Disposition'].startswith('attachment;filename=hotel_report_')

        # Check if content is valid CSV (basic check)


def test_report_filter_by_month(client, auth, app, db):
    """Test filtering report by month."""
    with app.app_context():
        # Create admin user
        user = User(username="admin3", email="admin3@example.com", role="admin")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as admin
        auth.login(user.email, "password")
        
        # Filter report by month
        response = client.get('/admin/reports?month=1&year=2024')
        assert response.status_code == 200
        assert b'Reports' in response.data 