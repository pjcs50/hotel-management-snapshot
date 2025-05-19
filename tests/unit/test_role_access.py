"""
Unit tests for role-based access control.

This module tests that the role-based access controls work correctly.
"""

import pytest
from flask import url_for
from flask_login import login_user

from app.models.user import User

class TestRoleAccess:
    """Test role-based access control."""
    
    def test_customer_role_access(self, client, customer_user):
        """Test that customer role access control works correctly."""
        # Login as customer
        with client.application.test_request_context():
            login_user(customer_user)
            # Customer should access customer dashboard
            response = client.get(url_for('customer.dashboard'))
            assert response.status_code == 200
            
            # Customer should not access other role dashboards
            response = client.get(url_for('receptionist.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('manager.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('housekeeping.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('admin.dashboard'))
            assert response.status_code == 403
    
    def test_receptionist_role_access(self, client, receptionist_user):
        """Test that receptionist role access control works correctly."""
        # Login as receptionist
        with client.application.test_request_context():
            login_user(receptionist_user)
            # Receptionist should access receptionist dashboard
            response = client.get(url_for('receptionist.dashboard'))
            assert response.status_code == 200
            
            # Receptionist should not access other role dashboards
            response = client.get(url_for('customer.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('manager.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('housekeeping.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('admin.dashboard'))
            assert response.status_code == 403

    def test_manager_role_access(self, client, manager_user):
        """Test that manager role access control works correctly."""
        # Login as manager
        with client.application.test_request_context():
            login_user(manager_user)
            # Manager should access manager dashboard
            response = client.get(url_for('manager.dashboard'))
            assert response.status_code == 200
            
            # Manager should not access other role dashboards
            response = client.get(url_for('customer.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('receptionist.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('housekeeping.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('admin.dashboard'))
            assert response.status_code == 403
            
    def test_housekeeping_role_access(self, client, housekeeping_user):
        """Test that housekeeping role access control works correctly."""
        # Login as housekeeping
        with client.application.test_request_context():
            login_user(housekeeping_user)
            # Housekeeping should access housekeeping dashboard
            response = client.get(url_for('housekeeping.dashboard'))
            assert response.status_code == 200
            
            # Housekeeping should not access other role dashboards
            response = client.get(url_for('customer.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('receptionist.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('manager.dashboard'))
            assert response.status_code == 403
            
            response = client.get(url_for('admin.dashboard'))
            assert response.status_code == 403
            
    def test_admin_role_access(self, client, admin_user):
        """Test that admin role access control works correctly."""
        # Login as admin
        with client.application.test_request_context():
            login_user(admin_user)
            # Admin should access admin dashboard
            response = client.get(url_for('admin.dashboard'))
            assert response.status_code == 200
            
            # For this test we don't check if admin can access other dashboards
            # because that depends on business requirements - some systems allow
            # admins to access all areas, some don't 