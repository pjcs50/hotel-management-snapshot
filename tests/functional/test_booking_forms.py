"""
Functional tests for booking forms.

This module contains tests for the customer and receptionist booking forms.
"""

import pytest
import re
from datetime import datetime, timedelta
from flask import url_for

from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking


@pytest.fixture
def setup_booking_form_data(app, db_session):
    """Set up test data for booking form tests."""
    with app.app_context():
        # Create a customer user
        user = User(username="customer_form", email="customer_form@example.com", role="customer")
        user.set_password("password")
        customer = Customer(user=user, name="Form Test Customer")
        
        # Create a receptionist user
        receptionist = User(username="receptionist_form", email="receptionist_form@example.com", role="receptionist")
        receptionist.set_password("password")
        
        # Create room types
        standard = RoomType(name="Standard_Form", description="Standard room", base_rate=100, capacity=2)
        deluxe = RoomType(name="Deluxe_Form", description="Deluxe room", base_rate=150, capacity=4)
        
        # Create rooms
        room1 = Room(number="101_Form", room_type=standard, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="201_Form", room_type=deluxe, status=Room.STATUS_AVAILABLE)
        
        db_session.add_all([user, customer, receptionist, standard, deluxe, room1, room2])
        db_session.commit()
        
        return {
            'customer_user': user,
            'customer': customer,
            'receptionist': receptionist,
            'standard': standard,
            'deluxe': deluxe,
            'room1': room1,
            'room2': room2
        }


class TestCustomerBookingForm:
    """Test suite for customer booking form."""
    
    def test_customer_new_booking_form_display(self, client, auth, setup_booking_form_data):
        """Test that the customer new booking form displays correctly."""
        # Log in as customer
        auth.login(email=setup_booking_form_data['customer_user'].email, password="password")
        
        # Access the new booking form
        response = client.get(url_for('customer.new_booking'))
        
        # Check that the form is displayed
        assert response.status_code == 200
        assert b'New Booking' in response.data
        assert b'Check-in Date' in response.data
        assert b'Check-out Date' in response.data
        assert b'Room' in response.data
        assert b'Number of Guests' in response.data
        assert b'Early Check-in Hours' in response.data
        assert b'Late Check-out Hours' in response.data
        assert b'Special Requests' in response.data
    
    def test_customer_new_booking_success(self, client, auth, setup_booking_form_data):
        """Test successful booking creation by customer."""
        # Log in as customer
        auth.login(email=setup_booking_form_data['customer_user'].email, password="password")
        
        # Define dates
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        check_out_date = (today + timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Submit the booking form
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_booking_form_data['room1'].id,
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'num_guests': 2,
                'early_hours': 2,
                'late_hours': 3,
                'special_requests': 'Test booking with early check-in and late check-out',
                'status': Booking.STATUS_RESERVED,
                'action': 'create_booking',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )
        
        # Check that booking was created successfully
        assert response.status_code == 200
        assert b'Your booking has been created successfully' in response.data
        
        # Check that booking exists in database
        from db import db
        booking = Booking.query.filter_by(
            room_id=setup_booking_form_data['room1'].id,
            customer_id=setup_booking_form_data['customer'].id
        ).first()
        
        assert booking is not None
        assert booking.early_hours == 2
        assert booking.late_hours == 3
        assert booking.special_requests == 'Test booking with early check-in and late check-out'
        
        # Check that price includes early check-in and late check-out fees
        base_price = setup_booking_form_data['standard'].base_rate * 2  # 2 nights
        early_fee = setup_booking_form_data['standard'].base_rate * 0.1 * 2  # 2 hours early
        late_fee = setup_booking_form_data['standard'].base_rate * 0.1 * 3  # 3 hours late
        expected_price = base_price + early_fee + late_fee
        
        assert booking.total_price == pytest.approx(expected_price, 0.01)
    
    def test_customer_new_booking_validation_errors(self, client, auth, setup_booking_form_data):
        """Test validation errors in customer booking form."""
        # Log in as customer
        auth.login(email=setup_booking_form_data['customer_user'].email, password="password")
        
        # Define dates
        today = datetime.now().date()
        
        # Test case 1: Check-out date before check-in date
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_booking_form_data['room1'].id,
                'check_in_date': (today + timedelta(days=3)).strftime('%Y-%m-%d'),
                'check_out_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
                'num_guests': 2,
                'early_hours': 0,
                'late_hours': 0,
                'special_requests': '',
                'status': Booking.STATUS_RESERVED,
                'action': 'create_booking',
                'csrf_token': client.get_csrf_token()
            }
        )
        
        # Check for validation error
        assert response.status_code == 200
        assert b'Check-out date must be after check-in date' in response.data
        
        # Test case 2: Too many guests for room
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_booking_form_data['room1'].id,  # Standard room with capacity 2
                'check_in_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
                'check_out_date': (today + timedelta(days=3)).strftime('%Y-%m-%d'),
                'num_guests': 3,  # Too many for standard room
                'early_hours': 0,
                'late_hours': 0,
                'special_requests': '',
                'status': Booking.STATUS_RESERVED,
                'action': 'create_booking',
                'csrf_token': client.get_csrf_token()
            }
        )
        
        # Check for validation error
        assert response.status_code == 200
        assert b'Number of guests exceeds room capacity' in response.data
        
        # Test case 3: Early hours too high
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_booking_form_data['room1'].id,
                'check_in_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
                'check_out_date': (today + timedelta(days=3)).strftime('%Y-%m-%d'),
                'num_guests': 2,
                'early_hours': 15,  # Too high (max is 12)
                'late_hours': 0,
                'special_requests': '',
                'status': Booking.STATUS_RESERVED,
                'action': 'create_booking',
                'csrf_token': client.get_csrf_token()
            }
        )
        
        # Check for validation error
        assert response.status_code == 200
        assert b'Early check-in hours must be between 0 and 12' in response.data


class TestReceptionistBookingForm:
    """Test suite for receptionist booking form."""
    
    def test_receptionist_new_booking_form_display(self, client, auth, setup_booking_form_data):
        """Test that the receptionist new booking form displays correctly."""
        # Log in as receptionist
        auth.login(email=setup_booking_form_data['receptionist'].email, password="password")
        
        # Access the new booking form
        response = client.get(url_for('receptionist.new_booking'))
        
        # Check that the form is displayed
        assert response.status_code == 200
        assert b'Create New Booking' in response.data
        assert b'Guest Information' in response.data
        assert b'Booking Details' in response.data
        assert b'Check-in Date' in response.data
        assert b'Check-out Date' in response.data
        assert b'Room' in response.data
        assert b'Number of Guests' in response.data
        assert b'Early Check-in Hours' in response.data
        assert b'Late Check-out Hours' in response.data
        assert b'Special Requests' in response.data
        assert b'Search Guest' in response.data
    
    def test_receptionist_new_booking_success(self, client, auth, setup_booking_form_data):
        """Test successful booking creation by receptionist."""
        # Log in as receptionist
        auth.login(email=setup_booking_form_data['receptionist'].email, password="password")
        
        # Define dates
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        check_out_date = (today + timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Submit the booking form with existing customer
        response = client.post(
            url_for('receptionist.new_booking'),
            data={
                'customer_id': setup_booking_form_data['customer'].id,
                'room_id': setup_booking_form_data['room2'].id,
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'num_guests': 3,
                'early_hours': 2,
                'late_hours': 3,
                'special_requests': 'Receptionist test booking with early check-in and late check-out',
                'status': Booking.STATUS_RESERVED,
                'action': 'create_booking',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )
        
        # Check that booking was created successfully
        assert response.status_code == 200
        assert b'Booking created successfully' in response.data
        
        # Check that booking exists in database
        from db import db
        booking = Booking.query.filter_by(
            room_id=setup_booking_form_data['room2'].id,
            customer_id=setup_booking_form_data['customer'].id
        ).first()
        
        assert booking is not None
        assert booking.early_hours == 2
        assert booking.late_hours == 3
        assert booking.special_requests == 'Receptionist test booking with early check-in and late check-out'
        
        # Check that price includes early check-in and late check-out fees
        base_price = setup_booking_form_data['deluxe'].base_rate * 2  # 2 nights
        early_fee = setup_booking_form_data['deluxe'].base_rate * 0.1 * 2  # 2 hours early
        late_fee = setup_booking_form_data['deluxe'].base_rate * 0.1 * 3  # 3 hours late
        expected_price = base_price + early_fee + late_fee
        
        assert booking.total_price == pytest.approx(expected_price, 0.01)
    
    def test_receptionist_new_booking_with_new_customer(self, client, auth, setup_booking_form_data):
        """Test booking creation by receptionist with a new customer."""
        # Log in as receptionist
        auth.login(email=setup_booking_form_data['receptionist'].email, password="password")
        
        # Define dates
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        check_out_date = (today + timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Submit the booking form with new customer
        response = client.post(
            url_for('receptionist.new_booking'),
            data={
                'guest_name': 'New Test Guest',
                'guest_email': 'newguest@example.com',
                'guest_phone': '555-123-4567',
                'room_id': setup_booking_form_data['room1'].id,
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'num_guests': 2,
                'early_hours': 1,
                'late_hours': 1,
                'special_requests': 'New customer test',
                'status': Booking.STATUS_RESERVED,
                'action': 'create_booking',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )
        
        # Check that booking was created successfully
        assert response.status_code == 200
        assert b'Booking created successfully' in response.data
        
        # Check that new customer was created
        from db import db
        customer = Customer.query.filter_by(name='New Test Guest').first()
        assert customer is not None
        assert customer.email == 'newguest@example.com'
        assert customer.phone == '555-123-4567'
        
        # Check that booking exists in database
        booking = Booking.query.filter_by(
            room_id=setup_booking_form_data['room1'].id,
            customer_id=customer.id
        ).first()
        
        assert booking is not None
        assert booking.early_hours == 1
        assert booking.late_hours == 1
