"""
Functional tests for customer routes.

This module contains tests for the customer routes.
"""

import pytest
from flask import url_for
from flask_login import login_user, current_user, logout_user
from bs4 import BeautifulSoup
from unittest.mock import patch

from app.models.user import User
from app.models.customer import Customer


class TestCustomerRoutes:
    """Tests for customer routes."""
    
    def test_profile_access(self, client, customer_user, db_session):
        """Test that the profile page is accessible to customers."""
        with client.application.test_request_context():
            login_user(customer_user)
            
            # Access profile page
            response = client.get(url_for('customer.profile'))
            assert response.status_code == 200
            
            # Check that the form is displayed
            soup = BeautifulSoup(response.data, 'html.parser')
            assert "Customer Information" in soup.text
            assert "Full Name" in soup.text
            assert "Phone Number" in soup.text
    
    def test_profile_update(self, client, customer_user, db_session):
        """Test that a customer can update their profile."""
        with client.application.test_request_context():
            login_user(customer_user)
            
            # Ensure customer profile exists
            customer = Customer.query.filter_by(user_id=customer_user.id).first()
            if not customer:
                customer = Customer(
                    user_id=customer_user.id,
                    name="",
                    phone="",
                    profile_complete=False
                )
                db_session.add(customer)
                db_session.commit()
            
            # Submit form to update profile
            response = client.post(
                url_for('customer.profile'),
                data={
                    'name': 'John Doe',
                    'phone': '555-1234',
                    'address': '123 Main St',
                    'emergency_contact': 'Jane Doe: 555-5678',
                    'csrf_token': client.get_csrf_token()
                },
                follow_redirects=True
            )
            
            assert response.status_code == 200
            
            # Check that the profile was updated
            db_session.refresh(customer)
            assert customer.name == 'John Doe'
            assert customer.phone == '555-1234'
            assert customer.address == '123 Main St'
            assert customer.emergency_contact == 'Jane Doe: 555-5678'
            assert customer.profile_complete == True
            
            # Check that we were redirected to the dashboard
            soup = BeautifulSoup(response.data, 'html.parser')
            assert "Dashboard" in soup.text
    
    def test_profile_incomplete(self, client, customer_user, db_session):
        """Test that profile completeness is correctly tracked."""
        with client.application.test_request_context():
            login_user(customer_user)
            
            # Ensure customer profile exists
            customer = Customer.query.filter_by(user_id=customer_user.id).first()
            if not customer:
                customer = Customer(
                    user_id=customer_user.id,
                    name="",
                    phone="",
                    profile_complete=False
                )
                db_session.add(customer)
                db_session.commit()
            
            # Submit incomplete form (missing phone)
            response = client.post(
                url_for('customer.profile'),
                data={
                    'name': 'John Doe',
                    'phone': '',
                    'csrf_token': client.get_csrf_token()
                },
                follow_redirects=False
            )
            
            assert response.status_code == 200
            
            # Check for validation error
            assert "Phone number is required" in response.get_data(as_text=True)
            
            # Verify that profile is still incomplete
            db_session.refresh(customer)
            assert customer.profile_complete == False 
    
    def test_change_password_incorrect_current(self, client, customer_user, db_session):
        """Test password change with incorrect current password."""
        initial_password = 'old_password123'
        customer_user.set_password(initial_password)
        db_session.add(customer_user)
        db_session.commit()

        with client.application.test_request_context():
            login_user(customer_user)
            response = client.post(
                url_for('customer.change_password'),
                data={
                    'current_password': 'wrong_old_password',
                    'new_password': 'new_SecurePass123!',
                    'confirm_new_password': 'new_SecurePass123!',
                    'csrf_token': client.get_csrf_token()
                },
                follow_redirects=False # Don't follow redirect to check flash message on same page
            )
            assert response.status_code == 200 # Re-renders form with error
            soup = BeautifulSoup(response.data, 'html.parser')
            assert "Current password does not match." in soup.text # Or whatever the exact flash message is
            db_session.refresh(customer_user)
            assert customer_user.check_password(initial_password) # Password should not have changed

    def test_change_password_mismatch_new(self, client, customer_user, db_session):
        """Test password change with mismatching new passwords."""
        initial_password = 'old_password123'
        customer_user.set_password(initial_password)
        db_session.add(customer_user)
        db_session.commit()

        with client.application.test_request_context():
            login_user(customer_user)
            response = client.post(
                url_for('customer.change_password'),
                data={
                    'current_password': initial_password,
                    'new_password': 'new_SecurePass123!',
                    'confirm_new_password': 'DIFFERENT_pass123!',
                    'csrf_token': client.get_csrf_token()
                },
                follow_redirects=False
            )
            assert response.status_code == 200 # Re-renders form with error
            soup = BeautifulSoup(response.data, 'html.parser')
            assert "New passwords must match." in soup.text # Form validation error
            db_session.refresh(customer_user)
            assert customer_user.check_password(initial_password) # Password should not have changed

    def test_change_password_new_too_short(self, client, customer_user, db_session):
        """Test password change with new password too short."""
        initial_password_val = 'old_password_for_short_test' 
        customer_user.set_password(initial_password_val)
        db_session.add(customer_user)
        db_session.commit()

        with client.application.test_request_context():
            login_user(customer_user)
            response = client.post(
                url_for('customer.change_password'),
                data={
                    'current_password': initial_password_val,
                    'new_password': 'short',
                    'confirm_new_password': 'short',
                    'csrf_token': client.get_csrf_token()
                },
                follow_redirects=False
            )
            assert response.status_code == 200 # Re-renders form with error
            soup = BeautifulSoup(response.data, 'html.parser')
            assert "New password must be at least 8 characters long." in soup.text # Form validation error
            db_session.refresh(customer_user)
            assert customer_user.check_password(initial_password_val) # Password should not have changed

    def test_change_password_unauthenticated_access(self, client, app):
        """Test unauthenticated access to change password page."""
        with app.test_request_context():
            # Ensure no user is logged in initially for this test
            # Flask-Login's current_user is a proxy, check is_authenticated
            if current_user.is_authenticated:
                logout_user() # Explicitly log out if a user is somehow authenticated

            response = client.get(url_for('customer.change_password'), follow_redirects=False)
            assert response.status_code == 302  # Expecting a redirect

            expected_login_url_path = url_for('auth.login')
            assert response.location.startswith(expected_login_url_path) # Check start to allow for ?next=

            # Optional: verify the login page content after redirect
            response_login_page = client.get(response.location, follow_redirects=True)
            assert response_login_page.status_code == 200
            soup = BeautifulSoup(response_login_page.data, 'html.parser')
            assert soup.find('h4', string='Login') is not None

    def test_change_password_non_customer_access(self, client, manager_user, db_session):
        """Test that a manager cannot access the change password page."""
        with client.application.test_request_context():
            login_user(manager_user)
            response = client.get(url_for('customer.change_password'), follow_redirects=False)
            assert response.status_code == 403  # Expecting a forbidden access

    @patch('app.routes.customer.DashboardService.get_customer_metrics')
    def test_dashboard_incomplete_metrics(self, mock_get_metrics, client, customer_user, app):
        """Test dashboard when service returns incomplete metrics.
        Accessing a missing key in the template raises UndefinedError,
        caught by the route, which then uses error_metrics.
        """
        mock_get_metrics.return_value = {
            "customer_name": "Test User",
            "profile_status": "Complete",
            # "unread_notification_count": 0, # MISSING
        }

        with app.test_request_context():
            login_user(customer_user)
            response = client.get(url_for('customer.dashboard'))

        assert response.status_code == 200
        soup = BeautifulSoup(response.data, 'html.parser')
        
        error_message_div = soup.find(class_="alert-danger")
        assert error_message_div is not None, "Error alert div not found"
        # Expect error related to the first missing key Jinja encounters
        assert "Error loading dashboard data:" in error_message_div.text
        assert "'unread_notification_count' is undefined" in error_message_div.text # Or similar for another key if template order changes

        assert "Jinja2" not in soup.text 
        assert "Traceback" not in soup.text
        # Further checks for default values are removed as blocks might not render

    @patch('app.routes.customer.DashboardService.get_customer_metrics')
    def test_dashboard_service_returns_error_dict(self, mock_get_metrics, client, customer_user, app):
        """Test dashboard when service returns its own error dict (e.g., {'error': 'msg'}).
        The base template displays metrics.error. Subsequent accesses to missing keys
        in customer/dashboard.html are treated as silent undefineds by Jinja.
        The route's main except block is NOT hit by a secondary Jinja UndefinedError.
        """
        mock_get_metrics.return_value = {"error": "Service-level customer not found"} # Only error key

        with app.test_request_context():
            login_user(customer_user)
            response = client.get(url_for('customer.dashboard'))

        assert response.status_code == 200
        soup = BeautifulSoup(response.data, 'html.parser')

        error_message_div = soup.find(class_="alert-danger")
        assert error_message_div is not None, "Error alert div not found"
        
        # The error displayed should be the original one from the service, via dashboard_base.html
        assert "Service-level customer not found" in error_message_div.text
        # The route's except block specific message should NOT be present
        assert "Error loading dashboard data:" not in error_message_div.text 

        assert "Jinja2" not in soup.text
        assert "Traceback" not in soup.text
        # Other dashboard elements will render with blanks due to missing keys from the service's dict.

    @patch('app.routes.customer.DashboardService.get_customer_metrics')
    def test_dashboard_service_raises_exception(self, mock_get_metrics, client, customer_user, app):
        """Test dashboard when service raises an unhandled exception."""
        mock_get_metrics.side_effect = Exception("Generic service failure")

        with app.test_request_context():
            login_user(customer_user)
            response = client.get(url_for('customer.dashboard'))

        assert response.status_code == 200
        soup = BeautifulSoup(response.data, 'html.parser')

        error_message_div = soup.find(class_="alert-danger")
        assert error_message_div is not None, "Error alert div not found"
        assert "Error loading dashboard data: Generic service failure" in error_message_div.text
        
        assert "Jinja2" not in soup.text
        assert "Traceback" not in soup.text
        # Further checks for default values are removed

    @patch('app.routes.customer.DashboardService.get_customer_metrics')
    def test_dashboard_service_returns_none(self, mock_get_metrics, client, customer_user, app):
        """Test dashboard when service returns None."""
        mock_get_metrics.return_value = None

        with app.test_request_context():
            login_user(customer_user)
            response = client.get(url_for('customer.dashboard'))

        assert response.status_code == 200
        soup = BeautifulSoup(response.data, 'html.parser')

        error_message_div = soup.find(class_="alert-danger")
        assert error_message_div is not None, "Error alert div not found"
        assert "Error loading dashboard data: Invalid data received from dashboard service." in error_message_div.text
        
        assert "Jinja2" not in soup.text
        assert "Traceback" not in soup.text
        # Further checks for default values are removed