"""
Comprehensive functional tests for the booking system.

This module contains end-to-end tests for the entire booking workflow,
including room availability checking, booking creation, modification,
and cancellation.
"""

import pytest
import json
from datetime import datetime, timedelta
from flask import url_for
from bs4 import BeautifulSoup

from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking
from app.services.booking_service import BookingService, RoomNotAvailableError


@pytest.fixture
def setup_booking_test_data(app, db_session):
    """Set up test data for booking system tests."""
    with app.app_context():
        # Create a user and customer
        user = User(username="test_booking_user", email="test_booking@example.com")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="Test Booking Customer",
            phone="555-1234",
            address="123 Test St",
            profile_complete=True
        )

        # Create room types with different characteristics
        standard_room_type = RoomType(
            name="Standard Test Room",
            description="A standard room for testing",
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

        deluxe_room_type = RoomType(
            name="Deluxe Test Room",
            description="A deluxe room for testing",
            base_rate=200.0,
            capacity=4,
            has_view=True,
            has_balcony=True,
            smoking_allowed=False,
            size_sqm=40.0,
            bed_type="King Bed",
            max_occupants=4,
            image_main="https://example.com/deluxe.jpg"
        )

        # Create rooms
        standard_room1 = Room(number="S101", room_type=standard_room_type, status=Room.STATUS_AVAILABLE)
        standard_room2 = Room(number="S102", room_type=standard_room_type, status=Room.STATUS_AVAILABLE)
        deluxe_room1 = Room(number="D101", room_type=deluxe_room_type, status=Room.STATUS_AVAILABLE)
        deluxe_room2 = Room(number="D102", room_type=deluxe_room_type, status=Room.STATUS_AVAILABLE)

        # Add to database
        db_session.add_all([
            user, customer,
            standard_room_type, deluxe_room_type,
            standard_room1, standard_room2, deluxe_room1, deluxe_room2
        ])
        db_session.commit()

        return {
            'user': user,
            'customer': customer,
            'standard_room_type': standard_room_type,
            'deluxe_room_type': deluxe_room_type,
            'standard_room1': standard_room1,
            'standard_room2': standard_room2,
            'deluxe_room1': deluxe_room1,
            'deluxe_room2': deluxe_room2
        }


class TestBookingSystem:
    """Test suite for the complete booking system."""

    def test_room_types_page_loads(self, client, setup_booking_test_data, auth):
        """Test that the room types page loads correctly."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # Access room types page
        response = client.get(url_for('customer.room_types'))
        assert response.status_code == 200

        # Check that room types are displayed
        soup = BeautifulSoup(response.data, 'html.parser')
        room_type_cards = soup.find_all('div', class_='card-header')

        # Verify both room types are shown
        room_type_names = [card.find('h3').text.strip() for card in room_type_cards]
        assert setup_booking_test_data['standard_room_type'].name in room_type_names
        assert setup_booking_test_data['deluxe_room_type'].name in room_type_names

    def test_room_availability_check(self, client, setup_booking_test_data, auth):
        """Test that room availability checking works correctly."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # Define date range for availability check
        today = datetime.now().date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)

        # Check availability
        response = client.get(
            url_for('customer.room_types',
                    check_in_date=check_in_date.strftime('%Y-%m-%d'),
                    check_out_date=check_out_date.strftime('%Y-%m-%d'))
        )
        assert response.status_code == 200

        # Verify availability is shown
        soup = BeautifulSoup(response.data, 'html.parser')
        availability_alerts = soup.find_all('div', class_='alert-success')
        assert len(availability_alerts) >= 2  # At least our two room types should be available

        # Verify "Book Now" buttons are present
        book_now_buttons = soup.find_all('a', string=lambda text: 'Book Now' in text if text else False)
        assert len(book_now_buttons) >= 2

    def test_new_booking_page_loads(self, client, setup_booking_test_data, auth):
        """Test that the new booking page loads correctly."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # Define date range
        today = datetime.now().date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)

        # Access new booking page with room type pre-selected
        response = client.get(
            url_for('customer.new_booking',
                    room_type_id=setup_booking_test_data['standard_room_type'].id,
                    check_in_date=check_in_date.strftime('%Y-%m-%d'),
                    check_out_date=check_out_date.strftime('%Y-%m-%d'))
        )
        assert response.status_code == 200

        # Check that the form is displayed
        soup = BeautifulSoup(response.data, 'html.parser')
        assert "Room Reservation" in soup.text
        assert "Check-in Date" in soup.text
        assert "Check-out Date" in soup.text

        # Verify room selection contains our rooms
        room_select = soup.find('select', id='room_id_select')
        assert room_select is not None
        room_options = room_select.find_all('option')
        assert len(room_options) >= 2  # At least our standard rooms should be available

    def test_create_booking_success(self, client, setup_booking_test_data, auth):
        """Test successful booking creation."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # Define date range
        today = datetime.now().date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)

        # Create a booking
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_booking_test_data['standard_room1'].id,
                'customer_id': setup_booking_test_data['customer'].id,
                'check_in_date': check_in_date.strftime('%Y-%m-%d'),
                'check_out_date': check_out_date.strftime('%Y-%m-%d'),
                'num_guests': 2,
                'special_requests': 'Extra pillows please',
                'early_hours': 0,
                'late_hours': 0,
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )

        # Check that we're redirected to booking confirmation page
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, 'html.parser')
        assert "Booking Confirmed" in soup.text

        # Verify booking was created in database
        booking = Booking.query.filter_by(
            room_id=setup_booking_test_data['standard_room1'].id,
            customer_id=setup_booking_test_data['customer'].id
        ).first()
        assert booking is not None
        assert booking.status == 'Reserved'
        assert booking.check_in_date == check_in_date
        assert booking.check_out_date == check_out_date

        # Verify room status was updated
        room = Room.query.get(setup_booking_test_data['standard_room1'].id)
        assert room.status == Room.STATUS_BOOKED

    def test_create_booking_with_early_late_hours(self, client, setup_booking_test_data, auth):
        """Test booking creation with early check-in and late check-out."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # Define date range
        today = datetime.now().date()
        check_in_date = today + timedelta(days=2)
        check_out_date = today + timedelta(days=4)

        # Create a booking with early check-in and late check-out
        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_booking_test_data['deluxe_room1'].id,
                'customer_id': setup_booking_test_data['customer'].id,
                'check_in_date': check_in_date.strftime('%Y-%m-%d'),
                'check_out_date': check_out_date.strftime('%Y-%m-%d'),
                'num_guests': 3,
                'special_requests': 'Ocean view preferred',
                'early_hours': 2,  # 2 hours early check-in
                'late_hours': 3,   # 3 hours late check-out
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )

        # Check that we're redirected to booking confirmation page
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, 'html.parser')
        assert "Booking Confirmed" in soup.text

        # Verify booking was created with early/late hours
        booking = Booking.query.filter_by(
            room_id=setup_booking_test_data['deluxe_room1'].id,
            customer_id=setup_booking_test_data['customer'].id
        ).first()
        assert booking is not None
        assert booking.early_hours == 2
        assert booking.late_hours == 3

        # Verify total price includes early/late hour fees
        # Base rate is 200 per night for 2 nights = 400
        # Early fee: 2 hours * (200 * 0.1) = 40
        # Late fee: 3 hours * (200 * 0.1) = 60
        # Total should be at least 500
        assert booking.total_price >= 500

    def test_booking_date_validation(self, client, setup_booking_test_data, auth):
        """Test validation of booking dates."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # Try to create a booking with check-out before check-in
        today = datetime.now().date()
        check_in_date = today + timedelta(days=3)
        check_out_date = today + timedelta(days=2)  # Before check-in!

        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_booking_test_data['standard_room2'].id,
                'customer_id': setup_booking_test_data['customer'].id,
                'check_in_date': check_in_date.strftime('%Y-%m-%d'),
                'check_out_date': check_out_date.strftime('%Y-%m-%d'),
                'num_guests': 2,
                'special_requests': '',
                'early_hours': 0,
                'late_hours': 0,
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )

        # Check that we get an error message
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, 'html.parser')
        error_messages = soup.find_all('div', class_='invalid-feedback')
        assert any("must be after" in msg.text for msg in error_messages)

        # Verify no booking was created
        booking = Booking.query.filter_by(
            room_id=setup_booking_test_data['standard_room2'].id,
            customer_id=setup_booking_test_data['customer'].id
        ).first()
        assert booking is None

    def test_booking_guest_limit_validation(self, client, setup_booking_test_data, auth):
        """Test validation of guest limits for rooms."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # Try to create a booking with too many guests for a standard room
        today = datetime.now().date()
        check_in_date = today + timedelta(days=4)
        check_out_date = today + timedelta(days=6)

        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_booking_test_data['standard_room2'].id,
                'customer_id': setup_booking_test_data['customer'].id,
                'check_in_date': check_in_date.strftime('%Y-%m-%d'),
                'check_out_date': check_out_date.strftime('%Y-%m-%d'),
                'num_guests': 5,  # Too many for standard room (max 2)
                'special_requests': '',
                'early_hours': 0,
                'late_hours': 0,
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )

        # Check that we get an error message
        assert response.status_code == 200
        assert "exceeds room capacity" in response.data.decode() or "Number of guests must be between" in response.data.decode()

        # Verify no booking was created
        booking = Booking.query.filter_by(
            room_id=setup_booking_test_data['standard_room2'].id,
            customer_id=setup_booking_test_data['customer'].id
        ).first()
        assert booking is None

    def test_edit_booking(self, client, setup_booking_test_data, auth):
        """Test editing an existing booking."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # First create a booking
        today = datetime.now().date()
        check_in_date = today + timedelta(days=5)
        check_out_date = today + timedelta(days=7)

        booking_service = BookingService(db_session=client.application.extensions['sqlalchemy'].db.session)
        booking = booking_service.create_booking(
            room_id=setup_booking_test_data['standard_room2'].id,
            customer_id=setup_booking_test_data['customer'].id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            num_guests=2,
            special_requests='Original request'
        )

        # Now edit the booking
        new_check_in_date = today + timedelta(days=6)
        new_check_out_date = today + timedelta(days=9)

        response = client.post(
            url_for('customer.edit_booking', booking_id=booking.id),
            data={
                'room_id': setup_booking_test_data['deluxe_room2'].id,  # Change room
                'check_in_date': new_check_in_date.strftime('%Y-%m-%d'),
                'check_out_date': new_check_out_date.strftime('%Y-%m-%d'),
                'num_guests': 3,  # Change number of guests
                'special_requests': 'Updated request',
                'early_hours': 1,
                'late_hours': 1,
                'status': 'Reserved',  # Status should remain the same
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )

        # Check that the edit was successful
        assert response.status_code == 200
        assert "Booking updated successfully" in response.data.decode()

        # Verify booking was updated in database
        updated_booking = Booking.query.get(booking.id)
        assert updated_booking.room_id == setup_booking_test_data['deluxe_room2'].id
        assert updated_booking.check_in_date == new_check_in_date
        assert updated_booking.check_out_date == new_check_out_date
        assert updated_booking.num_guests == 3
        assert "Updated request" in updated_booking.special_requests

    def test_cancel_booking(self, client, setup_booking_test_data, auth):
        """Test cancelling a booking."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # First create a booking
        today = datetime.now().date()
        check_in_date = today + timedelta(days=10)
        check_out_date = today + timedelta(days=12)

        booking_service = BookingService(db_session=client.application.extensions['sqlalchemy'].db.session)
        booking = booking_service.create_booking(
            room_id=setup_booking_test_data['deluxe_room1'].id,
            customer_id=setup_booking_test_data['customer'].id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            num_guests=2
        )

        # Now cancel the booking
        response = client.post(
            url_for('customer.cancel_booking', booking_id=booking.id),
            data={
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )

        # Check that the cancellation was successful
        assert response.status_code == 200
        assert "has been cancelled" in response.data.decode()

        # Verify booking was cancelled in database
        cancelled_booking = Booking.query.get(booking.id)
        assert cancelled_booking.status == Booking.STATUS_CANCELLED

        # Verify room status was updated back to available
        room = Room.query.get(setup_booking_test_data['deluxe_room1'].id)
        assert room.status == Room.STATUS_AVAILABLE

    def test_overlapping_booking_prevention(self, client, setup_booking_test_data, auth):
        """Test that overlapping bookings are prevented."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # First create a booking
        today = datetime.now().date()
        check_in_date = today + timedelta(days=15)
        check_out_date = today + timedelta(days=18)

        booking_service = BookingService(db_session=client.application.extensions['sqlalchemy'].db.session)
        booking = booking_service.create_booking(
            room_id=setup_booking_test_data['standard_room1'].id,
            customer_id=setup_booking_test_data['customer'].id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            num_guests=2
        )

        # Try to create an overlapping booking
        overlap_check_in = today + timedelta(days=17)  # Overlaps with first booking
        overlap_check_out = today + timedelta(days=20)

        response = client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': setup_booking_test_data['standard_room1'].id,  # Same room
                'customer_id': setup_booking_test_data['customer'].id,
                'check_in_date': overlap_check_in.strftime('%Y-%m-%d'),
                'check_out_date': overlap_check_out.strftime('%Y-%m-%d'),
                'num_guests': 2,
                'special_requests': '',
                'early_hours': 0,
                'late_hours': 0,
                'status': 'Reserved',
                'csrf_token': client.get_csrf_token()
            },
            follow_redirects=True
        )

        # Check that we get an error message
        assert response.status_code == 200
        assert "not available for the requested dates" in response.data.decode()

        # Verify no overlapping booking was created
        overlapping_bookings = Booking.query.filter(
            Booking.room_id == setup_booking_test_data['standard_room1'].id,
            Booking.id != booking.id,
            Booking.check_in_date < check_out_date,
            check_in_date < Booking.check_out_date
        ).all()
        assert len(overlapping_bookings) == 0

    def test_booking_api_endpoint(self, client, setup_booking_test_data, auth):
        """Test the booking API endpoint."""
        # Login as test user
        auth.login(email="test_booking@example.com", password="password")

        # Define date range
        today = datetime.now().date()
        check_in_date = today + timedelta(days=20)
        check_out_date = today + timedelta(days=22)

        # Create a booking via API
        response = client.post(
            '/api/bookings',
            json={
                'room_id': setup_booking_test_data['deluxe_room2'].id,
                'customer_id': setup_booking_test_data['customer'].id,
                'check_in_date': check_in_date.strftime('%Y-%m-%d'),
                'check_out_date': check_out_date.strftime('%Y-%m-%d'),
                'num_guests': 3,
                'special_requests': 'API booking test',
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

        # Verify booking was created in database
        booking_id = data['booking']['id']
        booking = Booking.query.get(booking_id)
        assert booking is not None
        assert booking.room_id == setup_booking_test_data['deluxe_room2'].id
        assert booking.customer_id == setup_booking_test_data['customer'].id
        assert booking.status == Booking.STATUS_RESERVED

    def test_booking_confirmation_page(self, client, setup_booking_test_data, auth):
        """Test the booking confirmation page."""
        # Login as test user
        auth.login(username="test_booking_user", password="password")

        # First create a booking
        today = datetime.now().date()
        check_in_date = today + timedelta(days=25)
        check_out_date = today + timedelta(days=27)

        booking_service = BookingService(db_session=client.application.extensions['sqlalchemy'].db.session)
        booking = booking_service.create_booking(
            room_id=setup_booking_test_data['standard_room1'].id,
            customer_id=setup_booking_test_data['customer'].id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            num_guests=2
        )

        # Access the booking confirmation page
        response = client.get(url_for('customer.booking_confirmation', booking_id=booking.id))
        assert response.status_code == 200

        # Check that the confirmation page shows the correct information
        soup = BeautifulSoup(response.data, 'html.parser')
        assert "Booking Confirmed" in soup.text
        assert booking.confirmation_code in soup.text
        assert setup_booking_test_data['standard_room1'].number in soup.text
        assert check_in_date.strftime('%Y-%m-%d') in response.data.decode()
        assert check_out_date.strftime('%Y-%m-%d') in response.data.decode()

    def test_booking_details_page(self, client, setup_booking_test_data, auth):
        """Test the booking details page."""
        # Login as test user
        auth.login(username="test_booking_user", password="password")

        # First create a booking
        today = datetime.now().date()
        check_in_date = today + timedelta(days=30)
        check_out_date = today + timedelta(days=32)

        booking_service = BookingService(db_session=client.application.extensions['sqlalchemy'].db.session)
        booking = booking_service.create_booking(
            room_id=setup_booking_test_data['deluxe_room1'].id,
            customer_id=setup_booking_test_data['customer'].id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            num_guests=3,
            special_requests='Test special request'
        )

        # Access the booking details page
        response = client.get(url_for('customer.booking_details', booking_id=booking.id))
        assert response.status_code == 200

        # Check that the details page shows the correct information
        soup = BeautifulSoup(response.data, 'html.parser')
        assert booking.confirmation_code in soup.text
        assert setup_booking_test_data['deluxe_room1'].number in soup.text
        assert "Test special request" in response.data.decode()
        assert check_in_date.strftime('%Y-%m-%d') in response.data.decode()
        assert check_out_date.strftime('%Y-%m-%d') in response.data.decode()

        # Check that the edit and cancel buttons are present
        edit_button = soup.find('a', string=lambda text: 'Edit Booking' in text if text else False)
        assert edit_button is not None
        cancel_button = soup.find('button', string=lambda text: 'Cancel Booking' in text if text else False)
        assert cancel_button is not None