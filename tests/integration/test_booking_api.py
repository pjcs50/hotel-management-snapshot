"""
Integration tests for booking API endpoints.

This module contains tests for the booking API endpoints.
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
def setup_test_data(app, db_session):
    """Set up test data for booking API tests."""
    with app.app_context():
        # Create a user and customer
        user = User(username="testuser_api", email="test_api@example.com")
        user.set_password("password")
        customer = Customer(user=user, name="Test Customer")
        
        # Create room type
        room_type = RoomType(name="Standard_API", description="Standard room", base_rate=100, capacity=2)
        
        # Create rooms
        room1 = Room(number="101_API", room_type=room_type, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="102_API", room_type=room_type, status=Room.STATUS_AVAILABLE)
        
        # Add to database
        db_session.add_all([user, customer, room_type, room1, room2])
        db_session.commit()
        
        return {
            'user': user,
            'customer': customer,
            'room_type': room_type,
            'room1': room1,
            'room2': room2
        }


def test_get_availability(client, setup_test_data):
    """Test the GET /api/availability endpoint."""
    # Define date range
    today = datetime.now().date()
    check_in_date = today + timedelta(days=1)
    check_out_date = today + timedelta(days=3)
    
    # Make request
    response = client.get(
        url_for('api.get_availability', 
                check_in_date=check_in_date.strftime('%Y-%m-%d'),
                check_out_date=check_out_date.strftime('%Y-%m-%d'))
    )
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'available_rooms' in data
    assert len(data['available_rooms']) >= 2  # At least our two test rooms


def test_create_booking(client, setup_test_data, auth):
    """Test the POST /api/bookings endpoint."""
    # Login as test user
    auth.login(username="testuser_api", password="password")
    
    # Define date range
    today = datetime.now().date()
    check_in_date = today + timedelta(days=1)
    check_out_date = today + timedelta(days=3)
    
    # Make request
    response = client.post(
        url_for('api.create_booking'),
        json={
            'room_id': setup_test_data['room1'].id,
            'customer_id': setup_test_data['customer'].id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'num_guests': 2,
            'special_requests': 'Extra pillows please'
        }
    )
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'booking' in data
    assert data['booking']['room_id'] == setup_test_data['room1'].id
    assert data['booking']['customer_id'] == setup_test_data['customer'].id
    
    # Check that room status was updated
    room = Room.query.get(setup_test_data['room1'].id)
    assert room.status == Room.STATUS_BOOKED


def test_get_booking(client, setup_test_data, auth):
    """Test the GET /api/bookings/{booking_id} endpoint."""
    # Login as test user
    auth.login(username="testuser_api", password="password")
    
    # Create a booking
    today = datetime.now().date()
    booking = Booking(
        room_id=setup_test_data['room1'].id,
        customer_id=setup_test_data['customer'].id,
        check_in_date=today + timedelta(days=1),
        check_out_date=today + timedelta(days=3),
        status=Booking.STATUS_RESERVED
    )
    from db import db
    db.session.add(booking)
    db.session.commit()
    
    # Make request
    response = client.get(url_for('api.get_booking', booking_id=booking.id))
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'booking' in data
    assert data['booking']['id'] == booking.id


def test_update_booking(client, setup_test_data, auth):
    """Test the PUT /api/bookings/{booking_id} endpoint."""
    # Login as test user
    auth.login(username="testuser_api", password="password")
    
    # Create a booking
    today = datetime.now().date()
    booking = Booking(
        room_id=setup_test_data['room1'].id,
        customer_id=setup_test_data['customer'].id,
        check_in_date=today + timedelta(days=1),
        check_out_date=today + timedelta(days=3),
        status=Booking.STATUS_RESERVED
    )
    from db import db
    db.session.add(booking)
    db.session.commit()
    
    # Make request to update booking
    new_check_out_date = today + timedelta(days=4)
    response = client.put(
        url_for('api.update_booking', booking_id=booking.id),
        json={
            'check_out_date': new_check_out_date.strftime('%Y-%m-%d'),
            'num_guests': 1,
            'special_requests': 'No special requests'
        }
    )
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'booking' in data
    assert data['booking']['check_out_date'] == new_check_out_date.strftime('%Y-%m-%d')
    assert data['booking']['num_guests'] == 1
