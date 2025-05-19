"""
Tests for manager routes.

This module contains unit tests for the manager routes.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import url_for, g
import flask_login

from app.models.user import User
from app.models.room_type import RoomType
from app.models.pricing import Pricing
from app.models.staff_request import StaffRequest
from app.services.dashboard_service import DashboardService
from db import db


@pytest.fixture
def mock_manager_user(db_session):
    """Create a mock manager user for testing."""
    user = User(
        username='testmanager_mgr_routes',
        email='testmanager_mgr_routes@example.com',
        role='manager',
        is_active=True
    )
    user.set_password('password123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def mock_staff_user(db_session):
    """Create a mock staff user for testing."""
    user = User(
        username='teststaff_mgr_routes',
        email='teststaff_mgr_routes@example.com',
        role='receptionist',
        is_active=True
    )
    user.set_password('password123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def mock_staff_request(db_session, mock_staff_user):
    """Create a mock staff request for testing."""
    staff_request = StaffRequest(
        user_id=mock_staff_user.id,
        role_requested='housekeeping',
        status='pending',
        created_at=datetime.now()
    )
    db_session.add(staff_request)
    db_session.commit()
    return staff_request


@pytest.fixture
def mock_room_type(db_session):
    """Create a mock room type for testing."""
    room_type = RoomType(
        name='Deluxe Suite_mgr_routes',
        description='Spacious suite with king bed',
        base_rate=200.00  # Changed from base_price to base_rate
    )
    db_session.add(room_type)
    db_session.commit()
    return room_type


@pytest.fixture
def mock_room_pricing(db_session, mock_room_type):
    """Create mock room pricing for testing."""
    pricing = Pricing(
        room_type_id=mock_room_type.id,
        weekend_multiplier=1.25,
        peak_season_multiplier=1.5
    )
    db_session.add(pricing)
    db_session.commit()
    return pricing


class TestManagerDashboard:
    """Test cases for the manager dashboard."""

    @patch('app.routes.manager.DashboardService.get_manager_metrics')
    def test_dashboard_success(self, mock_get_metrics, client, mock_manager_user):
        """Test successful dashboard load."""
        
        # Mock metrics for the dashboard - defined early so it's available if needed
        mock_metrics_data = {
            'occupancy_rate': 75,
            'monthly_bookings': 150,
            'customer_count': 300,
            'room_status': {'Available': 25, 'Occupied': 75, 'Cleaning': 0, 'Maintenance': 0},
            'total_rooms': 100,
            'staff_counts': {'manager': 2, 'receptionist': 5, 'housekeeping': 10},
            'historical_occupancy': {
                '2023-01-01': 70,
                '2023-01-02': 75
            },
            'room_type_revenue': {
                'Standard': 5000,
                'Deluxe': 8000
            },
            'adr': 150.00, 
            'revpar': 112.50, 
            'alerts': [], 
            'top_performers': [], 
            'booking_forecast': {}, 
            'maintenance_status': {}, 
            'housekeeping_status': {} 
        }
        mock_get_metrics.return_value = mock_metrics_data

        with client.application.test_request_context(): # Ensure app context for login and request
            # Clear g to ensure fresh call for the route handler logic
            if hasattr(g, 'dashboard_metrics'):
                del g.dashboard_metrics
            
            # Fetch the committed mock_manager_user within this app context to ensure it's session-managed
            # The mock_manager_user fixture commits the user, so it should be queryable.
            live_manager_user = db.session.query(User).filter_by(email=mock_manager_user.email).first()
            assert live_manager_user is not None, "Manager user not found in DB for login"
            flask_login.login_user(live_manager_user) 
            
            # Access dashboard
            response = client.get(url_for('manager.dashboard'))
        
        # Verify response
        assert response.status_code == 200
        assert b'Manager Dashboard' in response.data
        assert b'Room Occupancy Rate' in response.data
        assert b'75%' in response.data
        
        # Verify service was called
        mock_get_metrics.assert_called_once()


class TestManagerStaffManagement:
    """Test cases for staff management functionality."""

    def test_staff_list(self, client, mock_manager_user, mock_staff_user, login_user):
        """Test staff listing page."""
        # Login as manager
        login_user(mock_manager_user)
        
        # Access staff management page
        response = client.get(url_for('manager.staff'))
        
        # Verify response
        assert response.status_code == 200
        assert b'Staff Management' in response.data
        assert mock_staff_user.username.encode() in response.data
        assert mock_staff_user.email.encode() in response.data
    
    def test_view_staff(self, client, mock_manager_user, mock_staff_user, login_user):
        """Test viewing staff details."""
        # Login as manager
        login_user(mock_manager_user)
        
        # View staff details
        response = client.get(url_for('manager.view_staff', staff_id=mock_staff_user.id))
        
        # Verify response
        assert response.status_code == 200
        assert b'Staff Details' in response.data
        assert mock_staff_user.username.encode() in response.data
        assert mock_staff_user.email.encode() in response.data
    
    def test_edit_staff(self, client, mock_manager_user, mock_staff_user, login_user, db_session):
        """Test editing staff details."""
        # Login as manager
        login_user(mock_manager_user)
        
        # Get edit form
        response = client.get(url_for('manager.edit_staff', staff_id=mock_staff_user.id))
        assert response.status_code == 200
        assert b'Edit Staff' in response.data
        
        # Submit edit form
        new_username = 'updatedstaff'
        response = client.post(
            url_for('manager.edit_staff', staff_id=mock_staff_user.id),
            data={
                'username': new_username,
                'email': mock_staff_user.email,
                'role': 'housekeeping',
                'is_active': 'y'  # Checkbox value
            },
            follow_redirects=True
        )
        
        # Verify response and database update
        assert response.status_code == 200
        assert b'Staff Details' in response.data
        assert new_username.encode() in response.data
        
        # Refresh staff user from database
        refreshed_user = db_session.get(User, mock_staff_user.id)
        assert refreshed_user.username == new_username
        assert refreshed_user.role == 'housekeeping'


class TestManagerStaffRequests:
    """Test cases for staff requests functionality."""

    def test_staff_requests_list(self, client, mock_manager_user, mock_staff_request, login_user):
        """Test staff requests listing page."""
        # Login as manager
        login_user(mock_manager_user)
        
        # Access staff requests page
        response = client.get(url_for('manager.staff_requests'))
        
        # Verify response
        assert response.status_code == 200
        assert b'Staff Requests' in response.data
        # Should see the staff user's username
        assert mock_staff_request.user.username.encode() in response.data
        # Should see the requested role
        assert b'Housekeeping' in response.data
    
    def test_approve_staff_request(self, client, mock_manager_user, mock_staff_request, login_user, db_session):
        """Test approving a staff request."""
        # Login as manager
        login_user(mock_manager_user)
        
        # Approve the request
        response = client.post(
            url_for('manager.approve_staff_request', request_id=mock_staff_request.id),
            follow_redirects=True
        )
        
        # Verify response
        assert response.status_code == 200
        assert b'has been approved' in response.data
        
        # Refresh objects from database
        refreshed_request = db_session.get(StaffRequest, mock_staff_request.id)
        refreshed_user = db_session.get(User, mock_staff_request.user_id)
            
        # Verify database updates
        assert refreshed_request.status == 'approved'
        assert refreshed_user.role == 'housekeeping'
        assert refreshed_user.role_requested is None
    
    def test_deny_staff_request(self, client, mock_manager_user, mock_staff_request, login_user, db_session):
        """Test denying a staff request."""
        # Login as manager
        login_user(mock_manager_user)
        
        # Set role_requested on the user
        user_to_update = db_session.get(User, mock_staff_request.user_id)
        user_to_update.role_requested = 'housekeeping'
        db_session.commit() # commit this change before testing the deny action
        
        # Deny the request
        response = client.post(
            url_for('manager.deny_staff_request', request_id=mock_staff_request.id),
            follow_redirects=True
        )
        
        # Verify response
        assert response.status_code == 200
        assert b'has been denied' in response.data
        
        # Refresh objects from database
        refreshed_request = db_session.get(StaffRequest, mock_staff_request.id)
        refreshed_user = db_session.get(User, mock_staff_request.user_id)
            
        # Verify database updates
        assert refreshed_request.status == 'denied'
        assert refreshed_user.role_requested is None


class TestManagerPricing:
    """Test cases for room pricing functionality."""

    def test_pricing_page(self, client, mock_manager_user, mock_room_type, mock_room_pricing, login_user):
        """Test room pricing page."""
        # Login as manager
        login_user(mock_manager_user)
        
        # Access pricing page
        response = client.get(url_for('manager.pricing'))
        
        # Verify response
        assert response.status_code == 200
        assert b'Room Pricing Management' in response.data
        assert mock_room_type.name.encode() in response.data
        # assert b'200.00' in response.data  # Original assertion for Base price
        assert b'value="200.0"' in response.data # Check specific input value format
        assert b'Save Changes' in response.data # Changed to match button text
    
    def test_update_pricing(self, client, mock_manager_user, mock_room_type, mock_room_pricing, login_user, db_session):
        """Test updating room prices."""
        # Login as manager
        login_user(mock_manager_user)
        
        # Submit new prices
        new_base_rate = 250.00
        # These multipliers are what we expect to be stored based on the new base_rate
        # The form likely sends absolute prices, and the route calculates multipliers.
        # For the purpose of this test, let's assume the form sends new multipliers as well, or the route is smart.
        # However, the original test was sending prices. Let's stick to that and assume route derives multipliers.
        # The route should update room_type.base_rate and pricing.weekend_multiplier, pricing.peak_season_multiplier.

        # Let's assume the form still sends prices, and the route has to handle this.
        # The test previously sent: f'base_price_{mock_room_type.id}': new_base_price
        # and similar for weekend and peak prices. We need to ensure the route updates RoomType.base_rate
        # and the Pricing object's multipliers correctly.

        new_weekend_price_sent = 312.50 # This implies a 1.25 multiplier if base is 250
        new_peak_price_sent = 375.00    # This implies a 1.5 multiplier if base is 250

        response = client.post(
            url_for('manager.pricing'),
            data={
                f'base_rate_{mock_room_type.id}': new_base_rate, # Changed key to base_rate
                f'weekend_price_{mock_room_type.id}': new_weekend_price_sent, # Assuming these keys are used by form
                f'peak_price_{mock_room_type.id}': new_peak_price_sent      # Assuming these keys are used by form
            },
            follow_redirects=True
        )
        
        # Verify response
        assert response.status_code == 200
        assert b'Room prices updated successfully' in response.data # Ensure this matches actual flash message
        
        # Refresh objects from database
        db_session.refresh(mock_room_type)
        db_session.refresh(mock_room_pricing) # Refresh the original mock_room_pricing
        
        # Verify database updates
        assert mock_room_type.base_rate == new_base_rate
        # The multipliers should be re-calculated and stored if the route logic is correct
        # Weekend Multiplier = 312.50 / 250.00 = 1.25
        # Peak Multiplier = 375.00 / 250.00 = 1.5
        assert mock_room_pricing.weekend_multiplier == 1.25 
        assert mock_room_pricing.peak_season_multiplier == 1.5


class TestManagerReporting:
    """Test cases for reporting functionality."""

    def test_reports_page(self, client, mock_manager_user, login_user):
        """Test reports page."""
        # Login as manager
        login_user(mock_manager_user)
        
        # Access reports page
        response = client.get(url_for('manager.reports'))
        
        # Verify response
        assert response.status_code == 200
        assert b'Occupancy Report' in response.data
    
    @patch('app.services.report_service.ReportService.export_to_csv')
    def test_export_report_csv(self, mock_export_csv, client, mock_manager_user, login_user):
        """Test exporting a report as CSV."""
        # Mock CSV export
        mock_csv_data = b'date,occupancy\n2023-01-01,75\n2023-01-02,80'
        mock_export_csv.return_value = mock_csv_data
        
        # Login as manager
        login_user(mock_manager_user)
        
        # Export report as CSV
        response = client.get(
            url_for('manager.export_report', 
                    report_type='occupancy',
                    start_date='2023-01-01',
                    end_date='2023-01-02',
                    format='csv')
        )
        
        # Verify response
        assert response.status_code == 200
        assert response.data == mock_csv_data
        assert 'text/csv' in response.headers['Content-Type']
        assert 'attachment' in response.headers['Content-Disposition']
        assert 'occupancy_report' in response.headers['Content-Disposition'] 