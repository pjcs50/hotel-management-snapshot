"""
Functional tests for booking routes.

These tests verify that all booking-related API endpoints work correctly,
including the customer booking flow, staff booking management, and error handling.
"""

import unittest
import json
import os
import tempfile
from datetime import datetime, timedelta, date
from flask import url_for

from app_factory import create_app
from db import db as _db
from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking
from app.models.seasonal_rate import SeasonalRate


class TestBookingRoutes(unittest.TestCase):
    """Test suite for booking-related API endpoints."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before all tests."""
        # Create a temporary database file
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{cls.db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'WTF_CSRF_ENABLED': False  # Disable CSRF for testing
        })
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Initialize database
        _db.init_app(cls.app)
        _db.create_all()
        
        # Create test data
        cls._create_test_data()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        cls.app_context.pop()
        os.close(cls.db_fd)
        os.unlink(cls.db_path)

    def setUp(self):
        """Set up test fixtures before each test."""
        self.client = self.app.test_client()
        # Begin transaction
        self.session = _db.session
        self.session.begin_nested()
        
        # Login as customer user
        with self.client as c:
            c.post('/auth/login', data={
                'username': 'customer_user',
                'password': 'password'
            }, follow_redirects=True)

    def tearDown(self):
        """Clean up after each test."""
        # Logout
        with self.client as c:
            c.get('/auth/logout', follow_redirects=True)
        
        # Rollback transaction
        self.session.rollback()

    @classmethod
    def _create_test_data(cls):
        """Create test data for all tests."""
        session = _db.session
        
        # Create customer user
        customer_user = User(
            username='customer_user',
            email='customer@example.com',
            role='customer',
            is_active=True
        )
        customer_user.set_password('password')
        session.add(customer_user)
        session.flush()
        
        # Create customer profile
        customer = Customer(
            user_id=customer_user.id,
            name='Test Customer',
            email='customer@example.com',
            phone='123-456-7890',
            address='123 Test St',
            loyalty_points=100
        )
        session.add(customer)
        
        # Create staff user
        staff_user = User(
            username='staff_user',
            email='staff@example.com',
            role='receptionist',
            is_active=True
        )
        staff_user.set_password('password')
        session.add(staff_user)
        
        # Create room types
        standard_room = RoomType(
            name='Standard',
            description='Standard room with queen bed',
            base_rate=100.0,
            capacity=2,
            max_occupants=2
        )
        
        deluxe_room = RoomType(
            name='Deluxe',
            description='Deluxe room with king bed',
            base_rate=150.0,
            capacity=2,
            max_occupants=3
        )
        
        session.add_all([standard_room, deluxe_room])
        session.flush()
        
        # Create rooms
        rooms = []
        for i in range(1, 6):  # 5 standard rooms
            room = Room(
                number=f'S{i}',
                room_type_id=standard_room.id,
                status=Room.STATUS_AVAILABLE
            )
            rooms.append(room)
        
        for i in range(1, 4):  # 3 deluxe rooms
            room = Room(
                number=f'D{i}',
                room_type_id=deluxe_room.id,
                status=Room.STATUS_AVAILABLE
            )
            rooms.append(room)
        
        session.add_all(rooms)
        session.flush()
        
        # Create existing booking
        existing_booking = Booking(
            room_id=rooms[0].id,
            customer_id=customer.id,
            check_in_date=date.today() + timedelta(days=10),
            check_out_date=date.today() + timedelta(days=12),
            status=Booking.STATUS_RESERVED,
            num_guests=1,
            confirmation_code='TEST123',
            source='website',
            booking_date=datetime.now()
        )
        session.add(existing_booking)
        
        # Create seasonal rates
        summer_start = date(date.today().year, 6, 1)
        summer_end = date(date.today().year, 8, 31)
        
        summer_rate = SeasonalRate(
            room_type_id=standard_room.id,
            start_date=summer_start,
            end_date=summer_end,
            rate_multiplier=1.25,
            name='Summer Rate'
        )
        session.add(summer_rate)
        
        # Commit changes
        session.commit()

    def test_view_new_booking_page(self):
        """Test viewing the new booking page."""
        response = self.client.get('/customer/new-booking')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'New Booking', response.data)
        self.assertIn(b'Check-in Date', response.data)
        self.assertIn(b'Check-out Date', response.data)

    def test_create_booking_success(self):
        """Test creating a new booking successfully."""
        # Get available room
        room = Room.query.filter_by(status=Room.STATUS_AVAILABLE).first()
        customer = Customer.query.first()
        
        # Define booking data
        check_in_date = date.today() + timedelta(days=5)
        check_out_date = check_in_date + timedelta(days=2)
        booking_data = {
                'room_id': room.id,
            'customer_id': customer.id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'num_guests': 1,
            'special_requests': 'Extra pillows please',
            'status': 'Reserved'
        }
        
        # Submit booking form
        response = self.client.post('/customer/new-booking', data=booking_data, follow_redirects=True)
        
        # Verify success response
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your booking has been created successfully', response.data)
        
        # Verify booking was created in the database
        booking = Booking.query.filter_by(
            room_id=room.id, 
            check_in_date=check_in_date
        ).first()
        
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, Booking.STATUS_RESERVED)
        self.assertEqual(booking.num_guests, 1)
        
        # Verify room status was updated
        room = Room.query.get(room.id)
        self.assertEqual(room.status, Room.STATUS_BOOKED)

    def test_create_booking_invalid_dates(self):
        """Test creating a booking with invalid dates."""
        # Get available room
        room = Room.query.filter_by(status=Room.STATUS_AVAILABLE).first()
        customer = Customer.query.first()
        
        # Define booking data with check-out date before check-in date
        booking_data = {
            'room_id': room.id,
            'customer_id': customer.id,
            'check_in_date': (date.today() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'check_out_date': (date.today() + timedelta(days=4)).strftime('%Y-%m-%d'),  # Earlier than check-in
            'num_guests': 1,
            'special_requests': '',
            'status': 'Reserved'
        }
        
        # Submit booking form
        response = self.client.post('/customer/new-booking', data=booking_data, follow_redirects=True)
        
        # Verify error response
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Check-out date must be after check-in date', response.data)
        
        # Verify no booking was created
        booking = Booking.query.filter_by(
            room_id=room.id, 
            check_in_date=date.today() + timedelta(days=5)
        ).first()
        
        self.assertIsNone(booking)

    def test_view_bookings_list(self):
        """Test viewing the list of bookings."""
        response = self.client.get('/customer/bookings')
        self.assertEqual(response.status_code, 200)
        
        # Verify existing booking is displayed
        existing_booking = Booking.query.first()
        self.assertIn(bytes(existing_booking.confirmation_code, 'utf-8'), response.data)

    def test_view_booking_details(self):
        """Test viewing details of a booking."""
        # Get the existing booking
        existing_booking = Booking.query.first()
        
        # View booking details
        response = self.client.get(f'/customer/bookings/{existing_booking.id}/details')
        self.assertEqual(response.status_code, 200)
        
        # Verify booking details are displayed
        self.assertIn(bytes(existing_booking.confirmation_code, 'utf-8'), response.data)
        self.assertIn(bytes(str(existing_booking.num_guests), 'utf-8'), response.data)

    def test_edit_booking_page(self):
        """Test accessing the edit booking page."""
        # Get the existing booking
        existing_booking = Booking.query.first()
        
        # Access edit page
        response = self.client.get(f'/customer/bookings/{existing_booking.id}/edit')
        self.assertEqual(response.status_code, 200)
        
        # Verify edit form is displayed
        self.assertIn(b'Edit Booking', response.data)
        self.assertIn(bytes(existing_booking.confirmation_code, 'utf-8'), response.data)

    def test_edit_booking_success(self):
        """Test editing a booking successfully."""
        # Get the existing booking
        existing_booking = Booking.query.first()
        
        # New booking data
        new_check_out_date = existing_booking.check_out_date + timedelta(days=1)
        new_num_guests = 2
        
        edit_data = {
            'room_id': existing_booking.room_id,
            'check_in_date': existing_booking.check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': new_check_out_date.strftime('%Y-%m-%d'),
            'num_guests': new_num_guests,
            'special_requests': 'Updated request',
            'status': existing_booking.status  # Status should not change
        }
        
        # Submit edit form
        response = self.client.post(
            f'/customer/bookings/{existing_booking.id}/edit', 
            data=edit_data, 
            follow_redirects=True
        )
        
        # Verify success response
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Booking updated successfully', response.data)
        
        # Verify booking was updated in the database
        updated_booking = Booking.query.get(existing_booking.id)
        self.assertEqual(updated_booking.check_out_date, new_check_out_date)
        self.assertEqual(updated_booking.num_guests, new_num_guests)

    def test_edit_booking_invalid_changes(self):
        """Test editing a booking with invalid changes."""
        # Get the existing booking
        existing_booking = Booking.query.filter_by(status=Booking.STATUS_RESERVED).first()
        
        # Invalid booking data (check-out before check-in)
        edit_data = {
            'room_id': existing_booking.room_id,
            'check_in_date': existing_booking.check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': (existing_booking.check_in_date - timedelta(days=1)).strftime('%Y-%m-%d'),  # Invalid
            'num_guests': existing_booking.num_guests,
            'special_requests': existing_booking.special_requests[0] if existing_booking.special_requests else '',
            'status': existing_booking.status
        }
        
        # Submit edit form
        response = self.client.post(
            f'/customer/bookings/{existing_booking.id}/edit', 
            data=edit_data, 
            follow_redirects=True
        )
        
        # Verify error response
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Check-out date must be after check-in date', response.data)
        
        # Verify booking was not updated
        unchanged_booking = Booking.query.get(existing_booking.id)
        self.assertEqual(unchanged_booking.check_out_date, existing_booking.check_out_date)

    def test_cancel_booking(self):
        """Test cancelling a booking."""
        # Get the existing booking
        existing_booking = Booking.query.filter_by(status=Booking.STATUS_RESERVED).first()
        
        # Cancel the booking
        response = self.client.post(
            f'/customer/bookings/{existing_booking.id}/cancel',
            follow_redirects=True
        )
        
        # Verify success response
        self.assertEqual(response.status_code, 200)
        
        # Verify booking was cancelled in the database
        cancelled_booking = Booking.query.get(existing_booking.id)
        self.assertEqual(cancelled_booking.status, Booking.STATUS_CANCELLED)

    def test_room_availability_calendar(self):
        """Test viewing the room availability calendar."""
        response = self.client.get('/customer/availability-calendar')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Availability Calendar', response.data)

    def test_room_types_listing(self):
        """Test viewing the room types listing."""
        response = self.client.get('/customer/room-types')
        self.assertEqual(response.status_code, 200)
        
        # Verify room types are displayed
        room_types = RoomType.query.all()
        for room_type in room_types:
            self.assertIn(bytes(room_type.name, 'utf-8'), response.data)

    def test_staff_booking_management(self):
        """Test staff booking management functionality."""
        # Logout customer user
        self.client.get('/auth/logout')
        
        # Login as staff user
        response = self.client.post('/auth/login', data={
            'username': 'staff_user',
            'password': 'password'
        }, follow_redirects=True)
        
        # Access receptionist bookings page
        response = self.client.get('/receptionist/bookings')
        self.assertEqual(response.status_code, 200)
        
        # Verify existing booking is displayed
        existing_booking = Booking.query.first()
        self.assertIn(bytes(existing_booking.confirmation_code, 'utf-8'), response.data)
        
        # Test check-in functionality if the booking has check_in_date today or in the past
        today = date.today()
        existing_booking.check_in_date = today
        _db.session.commit()
        
        # Check in the booking
        response = self.client.post(
            f'/receptionist/bookings/{existing_booking.id}/check-in',
            follow_redirects=True
        )
        
        # Verify booking status was updated
        checked_in_booking = Booking.query.get(existing_booking.id)
        self.assertEqual(checked_in_booking.status, Booking.STATUS_CHECKED_IN)
        
        # Test check-out functionality
        response = self.client.post(
            f'/receptionist/bookings/{existing_booking.id}/check-out',
            follow_redirects=True
        )
        
        # Verify booking status was updated
        checked_out_booking = Booking.query.get(existing_booking.id)
        self.assertEqual(checked_out_booking.status, Booking.STATUS_CHECKED_OUT)


if __name__ == '__main__':
    unittest.main() 