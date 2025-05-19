"""
Functional tests for booking routes.

This module contains tests for booking creation, viewing, and management routes.
"""

import pytest
from datetime import datetime, timedelta
from flask import url_for

from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking


def test_customer_bookings_unauthorized(client):
    """Test that unauthorized users cannot access bookings page."""
    response = client.get(url_for('customer.bookings'))
    assert response.status_code == 302  # Redirect to login


def test_customer_bookings_wrong_role(client, auth, app, db):
    """Test that non-customer users cannot access customer bookings."""
    with app.app_context():
        # Create receptionist user
        user = User(username="receptionist", email="receptionist@example.com", role="receptionist")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as receptionist
        auth.login(user.email, "password")
        
        # Try to access customer bookings
        response = client.get(url_for('customer.bookings'))
        assert response.status_code == 403  # Forbidden


def test_new_booking_unauthorized(client):
    """Test that unauthorized users cannot access new booking page."""
    response = client.get(url_for('customer.new_booking'))
    assert response.status_code == 302  # Redirect to login


def test_new_booking_no_profile(client, auth, app, db):
    """Test that customers without complete profiles are redirected to profile page."""
    with app.app_context():
        # Create customer user without complete profile
        user = User(username="customer_no_profile", email="customer_no_profile@example.com", role="customer")
        user.set_password("password")
        customer = Customer(user=user, name="Incomplete Customer")  # Missing required fields
        db.session.add_all([user, customer])
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Try to access new booking page
        response = client.get(url_for('customer.new_booking'))
        assert response.status_code == 302  # Redirect
        
        # Handle both absolute and relative URLs in the response
        profile_path = url_for('customer.profile')
        if profile_path.startswith('http'):
            # If URL has scheme and server, extract the path part
            from urllib.parse import urlparse
            profile_path = urlparse(profile_path).path
            
        assert profile_path in response.location


def test_customer_bookings_empty(client, auth, app, db):
    """Test that bookings page shows empty state when no bookings exist."""
    with app.app_context():
        # Create customer with complete profile
        user = User(username="customer_empty", email="customer_empty@example.com", role="customer")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="Complete Customer",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        db.session.add_all([user, customer])
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Access bookings page
        response = client.get(url_for('customer.bookings'))
        assert response.status_code == 200
        
        # Check that empty state message is shown
        assert b"You don't have any bookings yet" in response.data
        assert b"New Booking" in response.data


def test_new_booking_form(client, auth, app, db):
    """Test that new booking form is displayed correctly."""
    with app.app_context():
        # Create customer with complete profile
        user = User(username="customer_form", email="customer_form@example.com", role="customer")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="Complete Customer",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        
        # Create room type and room
        room_type = RoomType(name="Standard_form", description="Standard room", base_rate=100, capacity=2)
        room = Room(number="101_form", room_type=room_type, status=Room.STATUS_AVAILABLE)
        
        db.session.add_all([user, customer, room_type, room])
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Access new booking page
        response = client.get(url_for('customer.new_booking'))
        assert response.status_code == 200
        
        # Check form elements - verify presence of booking form elements using more generalized selectors
        assert b'<form method="post" action="/customer/new-booking">' in response.data
        assert b'<label for="check_in_date" class="form-label">Check-in Date' in response.data
        assert b'<label for="check_out_date" class="form-label">Check-out Date' in response.data
        assert b'<select class="form-select" id="room_id" name="room_id"' in response.data
        
        # Check room type info is displayed
        assert b"Standard_form" in response.data
        assert b"$100.00/night" in response.data


def test_create_booking(client, auth, app, db):
    """Test booking creation."""
    with app.app_context():
        # Create customer with complete profile
        user = User(username="customer_create", email="customer_create@example.com", role="customer")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="Complete Customer",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        
        # Create room type and room
        room_type = RoomType(name="Standard_create", description="Standard room", base_rate=100, capacity=2)
        room = Room(number="101_create", room_type=room_type, status=Room.STATUS_AVAILABLE)
        
        db.session.add_all([user, customer, room_type, room])
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Create a booking
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': room.id,
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'early_hours': 0,
                'late_hours': 0,
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )
        
        # Check that we're redirected to bookings page with success message
        assert response.status_code == 200
        assert b'Your booking has been created successfully' in response.data
        
        # Check that booking exists in database
        booking = Booking.query.filter_by(room_id=room.id, customer_id=customer.id).first()
        assert booking is not None
        assert booking.status == 'Reserved'
        
        # Check that room status is updated
        room = Room.query.get(room.id)
        assert room.status == Room.STATUS_BOOKED


def test_invalid_booking_dates(client, auth, app, db):
    """Test validation for invalid booking dates."""
    with app.app_context():
        # Create customer with complete profile
        user = User(username="customer_invalid", email="customer_invalid@example.com", role="customer")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="Complete Customer",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        
        # Create room type and room
        room_type = RoomType(name="Standard_invalid", description="Standard room", base_rate=100, capacity=2)
        room = Room(number="101_invalid", room_type=room_type, status=Room.STATUS_AVAILABLE)
        
        db.session.add_all([user, customer, room_type, room])
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Test case 1: Check-out date before check-in date
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        check_out_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': room.id,
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'early_hours': 0,
                'late_hours': 0,
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            }
        )
        
        # Should fail with check-out date error
        assert response.status_code == 200
        assert b'Check-out date must be after check-in date' in response.data
        
        # Test case 2: Dates in the past
        past_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")
        check_out_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': room.id,
                'check_in_date': past_date,
                'check_out_date': check_out_date,
                'early_hours': 0,
                'late_hours': 0,
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            }
        )
        
        # Should fail with dates in past error
        assert response.status_code == 200
        assert b'cannot be in the past' in response.data


def test_double_booking_prevention(client, auth, app, db):
    """Test that system prevents double-bookings."""
    with app.app_context():
        # Create customer with complete profile
        user = User(username="customer_double", email="customer_double@example.com", role="customer")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="Complete Customer",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        
        # Create second user/customer for clarity
        user2 = User(username="customer_double2", email="customer_double2@example.com", role="customer")
        user2.set_password("password")
        customer2 = Customer(
            user=user2,
            name="Complete Customer 2",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        
        # Create room type and room
        room_type = RoomType(name="Standard_double", description="Standard room", base_rate=100, capacity=2)
        room1 = Room(number="101_double", room_type=room_type, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="102_double", room_type=room_type, status=Room.STATUS_AVAILABLE) # Another room of same type
        
        db.session.add_all([user, customer, user2, customer2, room_type, room1, room2])
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Create first booking
        today = datetime.now().date()
        check_in_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        check_out_date = (today + timedelta(days=5)).strftime("%Y-%m-%d")
        
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': room1.id,
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'early_hours': 0,
                'late_hours': 0,
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )
        
        # Check that first booking was created successfully
        assert response.status_code == 200
        assert b'Your booking has been created successfully' in response.data
        
        # Log in as second customer
        auth.login(user2.email, "password")
        
        # Try to create overlapping booking
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': room1.id,
                'check_in_date': (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                'check_out_date': (today + timedelta(days=7)).strftime("%Y-%m-%d"),
                'early_hours': 0,
                'late_hours': 0,
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            }
        )
        
        # Check that booking is rejected - looking for form validation error
        assert response.status_code == 200  # Form is redisplayed
        assert b'Not a valid choice' in response.data


def test_cancel_booking(client, auth, app, db):
    """Test booking cancellation."""
    with app.app_context():
        # Create customer with complete profile
        user = User(username="customer_cancel", email="customer_cancel@example.com", role="customer")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="Complete Customer",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        
        # Create room type and room
        room_type = RoomType(name="Standard_cancel", description="Standard room", base_rate=100, capacity=2)
        room = Room(number="101_cancel", room_type=room_type, status=Room.STATUS_BOOKED)
        
        # Create booking
        today = datetime.now().date()
        booking = Booking(
            room=room,
            customer=customer,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        
        db.session.add_all([user, customer, room_type, room, booking])
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Cancel booking
        response = client.post(
            url_for('customer.cancel_booking', booking_id=booking.id),
            data={'csrf_token': client.get_csrf_token()},
            follow_redirects=True
        )
        
        # Check that booking was cancelled - look for success message
        assert response.status_code == 200
        assert b'has been cancelled' in response.data
        
        # Check that booking status is updated in database
        booking = Booking.query.get(booking.id)
        assert booking.status == Booking.STATUS_CANCELLED
        
        # Check that room status is updated
        room = Room.query.get(room.id)
        assert room.status == Room.STATUS_AVAILABLE


def test_cancel_checked_in_booking_fails(client, auth, app, db):
    """Test that cancelling a checked-in booking fails."""
    with app.app_context():
        # Create customer with complete profile
        user = User(username="customer_cancel_checked", email="customer_cancel_checked@example.com", role="customer")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="Complete Customer",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        
        # Create room type and room
        room_type = RoomType(name="Standard_cancel_checked", description="Standard room", base_rate=100, capacity=2)
        room = Room(number="101_cancel_checked", room_type=room_type, status=Room.STATUS_OCCUPIED)
        
        # Create booking that's already checked in
        today = datetime.now().date()
        booking = Booking(
            room=room,
            customer=customer,
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=Booking.STATUS_CHECKED_IN
        )
        
        db.session.add_all([user, customer, room_type, room, booking])
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Try to cancel checked-in booking
        response = client.post(
            url_for('customer.cancel_booking', booking_id=booking.id),
            data={'csrf_token': client.get_csrf_token()},
            follow_redirects=True
        )
        
        # Check that cancellation is rejected - look for error message
        assert response.status_code == 200
        assert b'Cannot cancel a booking that is already checked in' in response.data
        
        # Check that booking status remains unchanged
        booking = Booking.query.get(booking.id)
        assert booking.status == Booking.STATUS_CHECKED_IN 