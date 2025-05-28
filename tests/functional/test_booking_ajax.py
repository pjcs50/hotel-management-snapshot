"""
Functional tests for booking form AJAX functionality.

This module contains tests for the AJAX functionality in the booking forms.
"""

import pytest
import json
from datetime import datetime, timedelta
from flask import url_for

from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking


@pytest.fixture
def setup_ajax_test_data(app, db_session):
    """Set up test data for AJAX functionality tests."""
    with app.app_context():
        # Create a customer user
        user = User(username="customer_ajax", email="customer_ajax@example.com", role="customer")
        user.set_password("password")
        customer = Customer(user=user, name="Ajax Test Customer")
        
        # Create a receptionist user
        receptionist = User(username="receptionist_ajax", email="receptionist_ajax@example.com", role="receptionist")
        receptionist.set_password("password")
        
        # Create room types
        standard = RoomType(name="Standard_Ajax", description="Standard room", base_rate=100, capacity=2)
        deluxe = RoomType(name="Deluxe_Ajax", description="Deluxe room", base_rate=150, capacity=4)
        
        # Create rooms
        room1 = Room(number="101_Ajax", room_type=standard, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="201_Ajax", room_type=deluxe, status=Room.STATUS_AVAILABLE)
        
        # Create additional customers for search testing
        customer2 = Customer(name="John Smith", email="john@example.com", phone="555-111-2222")
        customer3 = Customer(name="Jane Doe", email="jane@example.com", phone="555-333-4444")
        
        db_session.add_all([user, customer, receptionist, standard, deluxe, room1, room2, customer2, customer3])
        db_session.commit()
        
        return {
            'customer_user': user,
            'customer': customer,
            'receptionist': receptionist,
            'standard': standard,
            'deluxe': deluxe,
            'room1': room1,
            'room2': room2,
            'customer2': customer2,
            'customer3': customer3
        }


class TestCustomerBookingAjax:
    """Test suite for customer booking form AJAX functionality."""
    
    def test_update_room_options_ajax(self, client, auth, setup_ajax_test_data):
        """Test AJAX request to update room options based on dates."""
        # Log in as customer
        auth.login(email=setup_ajax_test_data['customer_user'].email, password="password")
        
        # Define dates
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        check_out_date = (today + timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Make AJAX request to update room options
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'action': 'update_options',
                'csrf_token': client.get_csrf_token()
            },
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'room_options' in data
        
        # Verify room options include our test rooms
        room_ids = [option['value'] for option in data['room_options']]
        assert setup_ajax_test_data['room1'].id in room_ids
        assert setup_ajax_test_data['room2'].id in room_ids
    
    def test_calculate_price_ajax(self, client, auth, setup_ajax_test_data):
        """Test AJAX request to calculate price based on selected options."""
        # Log in as customer
        auth.login(email=setup_ajax_test_data['customer_user'].email, password="password")
        
        # Define dates
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        check_out_date = (today + timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Make AJAX request to calculate price
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_ajax_test_data['room1'].id,
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'early_hours': 2,
                'late_hours': 3,
                'action': 'update_options',
                'csrf_token': client.get_csrf_token()
            },
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'estimated_price' in data
        
        # Calculate expected price
        base_price = setup_ajax_test_data['standard'].base_rate * 2  # 2 nights
        early_fee = setup_ajax_test_data['standard'].base_rate * 0.1 * 2  # 2 hours early
        late_fee = setup_ajax_test_data['standard'].base_rate * 0.1 * 3  # 3 hours late
        expected_price = base_price + early_fee + late_fee
        
        # Verify price calculation
        assert data['estimated_price'] == pytest.approx(expected_price, 0.01)
    
    def test_create_booking_ajax(self, client, auth, setup_ajax_test_data):
        """Test AJAX request to create a booking."""
        # Log in as customer
        auth.login(email=setup_ajax_test_data['customer_user'].email, password="password")
        
        # Define dates
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        check_out_date = (today + timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Make AJAX request to create booking
        response = client.post(
            url_for('api.create_booking'),
            json={
                'room_id': setup_ajax_test_data['room1'].id,
                'customer_id': setup_ajax_test_data['customer'].id,
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'num_guests': 2,
                'early_hours': 2,
                'late_hours': 3,
                'special_requests': 'AJAX booking test'
            },
            headers={'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json'}
        )
        
        # Check response
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'booking' in data
        
        # Verify booking was created
        booking_id = data['booking']['id']
        from db import db
        booking = Booking.query.get(booking_id)
        assert booking is not None
        assert booking.room_id == setup_ajax_test_data['room1'].id
        assert booking.customer_id == setup_ajax_test_data['customer'].id
        assert booking.early_hours == 2
        assert booking.late_hours == 3


class TestReceptionistBookingAjax:
    """Test suite for receptionist booking form AJAX functionality."""
    
    def test_search_customers_ajax(self, client, auth, setup_ajax_test_data):
        """Test AJAX request to search for customers."""
        # Log in as receptionist
        auth.login(email=setup_ajax_test_data['receptionist'].email, password="password")
        
        # Make AJAX request to search for customers
        response = client.get(
            url_for('receptionist.search_customers', q='John'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'customers' in data
        
        # Verify customer was found
        assert len(data['customers']) == 1
        assert data['customers'][0]['name'] == 'John Smith'
        assert data['customers'][0]['email'] == 'john@example.com'
        
        # Search for another customer
        response = client.get(
            url_for('receptionist.search_customers', q='Jane'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'customers' in data
        
        # Verify customer was found
        assert len(data['customers']) == 1
        assert data['customers'][0]['name'] == 'Jane Doe'
        assert data['customers'][0]['email'] == 'jane@example.com'
        
        # Search with partial match
        response = client.get(
            url_for('receptionist.search_customers', q='Ajax'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'customers' in data
        
        # Verify customer was found
        assert len(data['customers']) == 1
        assert data['customers'][0]['name'] == 'Ajax Test Customer'
    
    def test_update_room_options_receptionist_ajax(self, client, auth, setup_ajax_test_data):
        """Test AJAX request to update room options in receptionist form."""
        # Log in as receptionist
        auth.login(email=setup_ajax_test_data['receptionist'].email, password="password")
        
        # Define dates
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        check_out_date = (today + timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Make AJAX request to update room options
        response = client.post(
            url_for('receptionist.new_booking'),
            data={
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'action': 'update_options',
                'csrf_token': client.get_csrf_token()
            },
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'room_options' in data
        
        # Verify room options include our test rooms
        room_ids = [option['value'] for option in data['room_options']]
        assert setup_ajax_test_data['room1'].id in room_ids
        assert setup_ajax_test_data['room2'].id in room_ids
        
        # Verify room details are included
        for option in data['room_options']:
            if option['value'] == setup_ajax_test_data['room1'].id:
                assert option['room_type'] == 'Standard_Ajax'
                assert option['capacity'] == 2
                assert option['rate'] == 100
            elif option['value'] == setup_ajax_test_data['room2'].id:
                assert option['room_type'] == 'Deluxe_Ajax'
                assert option['capacity'] == 4
                assert option['rate'] == 150
