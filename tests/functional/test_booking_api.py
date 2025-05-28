"""
Tests for booking API endpoints.

This module contains tests for the booking API endpoints to ensure
they work correctly.
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
def setup_api_test_data(app, db_session):
    """Set up test data for API tests."""
    with app.app_context():
        # Create a user and customer
        user = User(username="api_test_user", email="api_test@example.com")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="API Test Customer",
            phone="555-1234",
            address="123 API St",
            profile_complete=True
        )

        # Create room types
        standard_room_type = RoomType(
            name="Standard API Room",
            description="A standard room for API testing",
            base_rate=100.0,
            capacity=2,
            has_view=False,
            has_balcony=False,
            smoking_allowed=False,
            size_sqm=25.0,
            bed_type="Queen Bed",
            max_occupants=2,
            image_main="https://example.com/standard.jpg"
        )

        # Create rooms
        standard_room = Room(number="A101", room_type=standard_room_type, status=Room.STATUS_AVAILABLE)

        # Add to database
        db_session.add_all([user, customer, standard_room_type, standard_room])
        db_session.commit()

        return {
            'user': user,
            'customer': customer,
            'room_type': standard_room_type,
            'room': standard_room
        }


class TestBookingAPI:
    """Test suite for booking API endpoints."""

    def test_get_room_availability_api(self, client, setup_api_test_data, auth):
        """Test the room availability API endpoint."""
        # Login as test user
        auth.login(email="api_test@example.com", password="password")

        # Define date range
        today = datetime.now().date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)

        # Call the API
        response = client.get(
            '/api/availability',
            query_string={
                'check_in_date': check_in_date.strftime('%Y-%m-%d'),
                'check_out_date': check_out_date.strftime('%Y-%m-%d'),
                'room_type_id': setup_api_test_data['room_type'].id
            },
            headers={
                'X-Requested-With': 'XMLHttpRequest'
            }
        )

        # Check that the API call was successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'available' in data
        assert data['available'] is True

    def test_create_booking_api(self, client, setup_api_test_data, auth):
        """Test the create booking API endpoint."""
        # Login as test user
        auth.login(email="api_test@example.com", password="password")

        # Define date range
        today = datetime.now().date()
        check_in_date = today + timedelta(days=5)
        check_out_date = today + timedelta(days=7)

        # Call the API
        response = client.post(
            '/api/bookings',
            json={
                'room_id': setup_api_test_data['room'].id,
                'customer_id': setup_api_test_data['customer'].id,
                'check_in_date': check_in_date.strftime('%Y-%m-%d'),
                'check_out_date': check_out_date.strftime('%Y-%m-%d'),
                'num_guests': 2,
                'special_requests': 'API test booking',
                'early_hours': 0,
                'late_hours': 0
            },
            headers={
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        )

        # Check that the API call was successful
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'booking' in data
        assert data['booking']['room_id'] == setup_api_test_data['room'].id
        assert data['booking']['customer_id'] == setup_api_test_data['customer'].id

        # Verify booking was created in database
        booking_id = data['booking']['id']
        booking = Booking.query.get(booking_id)
        assert booking is not None
        assert booking.status == Booking.STATUS_RESERVED

    def test_update_booking_api(self, client, setup_api_test_data, auth):
        """Test the update booking API endpoint."""
        # Login as test user
        auth.login(email="api_test@example.com", password="password")

        # First create a booking
        today = datetime.now().date()
        check_in_date = today + timedelta(days=10)
        check_out_date = today + timedelta(days=12)

        booking = Booking(
            room=setup_api_test_data['room'],
            customer=setup_api_test_data['customer'],
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED,
            num_guests=2,
            special_requests="Original request",
            confirmation_code="API123",
            total_price=200.0
        )

        client.application.extensions['sqlalchemy'].db.session.add(booking)
        client.application.extensions['sqlalchemy'].db.session.commit()

        # Now update the booking via API
        new_check_in_date = today + timedelta(days=11)
        new_check_out_date = today + timedelta(days=14)

        response = client.put(
            f'/api/bookings/{booking.id}',
            json={
                'check_in_date': new_check_in_date.strftime('%Y-%m-%d'),
                'check_out_date': new_check_out_date.strftime('%Y-%m-%d'),
                'num_guests': 3,
                'special_requests': 'Updated request',
                'early_hours': 1,
                'late_hours': 1
            },
            headers={
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        )

        # Check that the API call was successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'booking' in data

        # Verify booking was updated in database
        updated_booking = Booking.query.get(booking.id)
        assert updated_booking.check_in_date == new_check_in_date
        assert updated_booking.check_out_date == new_check_out_date
        assert updated_booking.num_guests == 3
        assert updated_booking.special_requests == 'Updated request'

    def test_cancel_booking_api(self, client, setup_api_test_data, auth):
        """Test the cancel booking API endpoint."""
        # Login as test user
        auth.login(email="api_test@example.com", password="password")

        # First create a booking
        today = datetime.now().date()
        check_in_date = today + timedelta(days=15)
        check_out_date = today + timedelta(days=17)

        booking = Booking(
            room=setup_api_test_data['room'],
            customer=setup_api_test_data['customer'],
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED,
            num_guests=2,
            confirmation_code="APICANCEL",
            total_price=200.0
        )

        client.application.extensions['sqlalchemy'].db.session.add(booking)
        client.application.extensions['sqlalchemy'].db.session.commit()

        # Now cancel the booking via API
        response = client.delete(
            f'/api/bookings/{booking.id}',
            headers={
                'X-Requested-With': 'XMLHttpRequest'
            }
        )

        # Check that the API call was successful
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify booking was cancelled in database
        cancelled_booking = Booking.query.get(booking.id)
        assert cancelled_booking.status == Booking.STATUS_CANCELLED

        # Verify room status was updated
        room = Room.query.get(setup_api_test_data['room'].id)
        assert room.status == Room.STATUS_AVAILABLE
