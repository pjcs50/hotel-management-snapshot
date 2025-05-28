"""
Integration tests for the booking system.

These tests verify that the booking system works correctly end-to-end,
including interactions between the BookingService, Room, Customer, and other
models using a real database connection.
"""

import unittest
from datetime import datetime, timedelta, date
import random
import os
import tempfile

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.user import User
from app.models.seasonal_rate import SeasonalRate
from app.services.booking_service import BookingService, RoomNotAvailableError
from app.services.customer_service import CustomerService
from app.services.room_service import RoomService
from db import db as _db
from app_factory import create_app


class TestBookingIntegration(unittest.TestCase):
    """Integration tests for the booking system."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for all tests in the class."""
        # Create a temporary database for testing
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{cls.db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'WTF_CSRF_ENABLED': False
        })
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Initialize the database
        _db.init_app(cls.app)
        _db.create_all()
        
        # Create test data
        cls._create_test_data()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests in the class."""
        cls.app_context.pop()
        os.close(cls.db_fd)
        os.unlink(cls.db_path)

    def setUp(self):
        """Set up test fixtures before each test method is run."""
        # Create a session for each test
        self.session = _db.session
        
        # Create services
        self.booking_service = BookingService(self.session)
        self.customer_service = CustomerService(self.session)
        self.room_service = RoomService(self.session)
        
        # Begin a transaction
        self.session.begin_nested()

    def tearDown(self):
        """Clean up after each test method is run."""
        # Roll back the transaction
        self.session.rollback()
        self.session.close()

    @classmethod
    def _create_test_data(cls):
        """Create test data for the test suite."""
        session = _db.session
        
        # Create a test user
        user = User(
            username='test_user',
            email='test@example.com',
            role='customer',
            is_active=True
        )
        user.set_password('password')
        session.add(user)
        
        # Create room types
        standard_room_type = RoomType(
            name='Standard',
            description='Standard room with one queen bed',
            base_rate=100.0,
            capacity=2,
            max_occupants=2
        )
        deluxe_room_type = RoomType(
            name='Deluxe',
            description='Deluxe room with one king bed',
            base_rate=150.0,
            capacity=2,
            max_occupants=3
        )
        suite_room_type = RoomType(
            name='Suite',
            description='Suite with separate living area',
            base_rate=200.0,
            capacity=4,
            max_occupants=4
        )
        session.add_all([standard_room_type, deluxe_room_type, suite_room_type])
        session.flush()
        
        # Create rooms
        rooms = []
        for i in range(1, 6):  # 5 standard rooms
            room = Room(
                number=f'10{i}',
                room_type_id=standard_room_type.id,
                status=Room.STATUS_AVAILABLE
            )
            rooms.append(room)
        
        for i in range(1, 4):  # 3 deluxe rooms
            room = Room(
                number=f'20{i}',
                room_type_id=deluxe_room_type.id,
                status=Room.STATUS_AVAILABLE
            )
            rooms.append(room)
        
        for i in range(1, 3):  # 2 suite rooms
            room = Room(
                number=f'30{i}',
                room_type_id=suite_room_type.id,
                status=Room.STATUS_AVAILABLE
            )
            rooms.append(room)
        
        session.add_all(rooms)
        
        # Create a test customer
        customer = Customer(
            user_id=user.id,
            name='Test Customer',
            email='test@example.com',
            phone='123-456-7890',
            address='123 Test St'
        )
        session.add(customer)
        
        # Create seasonal rates
        today = date.today()
        summer_start = date(today.year, 6, 1)
        summer_end = date(today.year, 8, 31)
        
        summer_rate_standard = SeasonalRate(
            room_type_id=standard_room_type.id,
            start_date=summer_start,
            end_date=summer_end,
            rate_multiplier=1.25,
            name='Summer Rate'
        )
        
        summer_rate_deluxe = SeasonalRate(
            room_type_id=deluxe_room_type.id,
            start_date=summer_start,
            end_date=summer_end,
            rate_multiplier=1.2,
            name='Summer Rate'
        )
        
        summer_rate_suite = SeasonalRate(
            room_type_id=suite_room_type.id,
            start_date=summer_start,
            end_date=summer_end,
            rate_multiplier=1.15,
            name='Summer Rate'
        )
        
        session.add_all([summer_rate_standard, summer_rate_deluxe, summer_rate_suite])
        
        # Commit the changes
        session.commit()

    def test_end_to_end_booking_flow(self):
        """Test the complete booking flow from creation to checkout."""
        # Get test data
        customer = Customer.query.first()
        room = Room.query.filter_by(status=Room.STATUS_AVAILABLE).first()
        
        # Define booking dates
        check_in_date = date.today() + timedelta(days=1)
        check_out_date = check_in_date + timedelta(days=2)
        
        # Step 1: Create a booking
        booking = self.booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED,
            num_guests=1
        )
        
        # Verify booking was created with correct data
        self.assertEqual(booking.room_id, room.id)
        self.assertEqual(booking.customer_id, customer.id)
        self.assertEqual(booking.check_in_date, check_in_date)
        self.assertEqual(booking.check_out_date, check_out_date)
        self.assertEqual(booking.status, Booking.STATUS_RESERVED)
        
        # Verify room status was updated
        room = Room.query.get(room.id)
        self.assertEqual(room.status, Room.STATUS_BOOKED)
        
        # Get the booking ID for later use
        booking_id = booking.id
        
        # Step 2: Update the booking
        new_check_out_date = check_out_date + timedelta(days=1)
        updated_booking = self.booking_service.update_booking(
            booking_id=booking_id,
            check_out_date=new_check_out_date,
            num_guests=2
        )
        
        # Verify booking was updated
        self.assertEqual(updated_booking.check_out_date, new_check_out_date)
        self.assertEqual(updated_booking.num_guests, 2)
        
        # Step 3: Check in the booking
        checked_in_booking = self.booking_service.check_in(booking_id=booking_id, staff_id=None)
        
        # Verify booking status was updated
        self.assertEqual(checked_in_booking.status, Booking.STATUS_CHECKED_IN)
        
        # Verify room status was updated
        room = Room.query.get(room.id)
        self.assertEqual(room.status, Room.STATUS_OCCUPIED)
        
        # Step 4: Check out the booking
        checked_out_booking = self.booking_service.check_out(booking_id=booking_id, staff_id=None)
        
        # Verify booking status was updated
        self.assertEqual(checked_out_booking.status, Booking.STATUS_CHECKED_OUT)
        
        # Verify room status was updated
        room = Room.query.get(room.id)
        self.assertEqual(room.status, Room.STATUS_CLEANING)

    def test_concurrent_bookings_for_same_room(self):
        """Test that booking validation prevents double-booking."""
        # Get test data
        customer = Customer.query.first()
        room = Room.query.filter_by(status=Room.STATUS_AVAILABLE).first()
        
        # Define booking dates
        check_in_date = date.today() + timedelta(days=1)
        check_out_date = check_in_date + timedelta(days=2)
        
        # Create first booking
        first_booking = self.booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED,
            num_guests=1
        )
        
        # Verify first booking was created
        self.assertEqual(first_booking.status, Booking.STATUS_RESERVED)
        
        # Attempt to create a second booking for the same dates (should fail)
        with self.assertRaises(RoomNotAvailableError):
            self.booking_service.create_booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                status=Booking.STATUS_RESERVED,
                num_guests=1
            )
        
        # Attempt to create overlapping booking (starting during first booking)
        with self.assertRaises(RoomNotAvailableError):
            self.booking_service.create_booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=check_in_date + timedelta(days=1),
                check_out_date=check_out_date + timedelta(days=1),
                status=Booking.STATUS_RESERVED,
                num_guests=1
            )
        
        # Attempt to create overlapping booking (ending during first booking)
        with self.assertRaises(RoomNotAvailableError):
            self.booking_service.create_booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=check_in_date - timedelta(days=1),
                check_out_date=check_in_date + timedelta(days=1),
                status=Booking.STATUS_RESERVED,
                num_guests=1
            )
        
        # But a booking for different dates should succeed
        second_booking = self.booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_out_date,  # Starts when first booking ends
            check_out_date=check_out_date + timedelta(days=2),
            status=Booking.STATUS_RESERVED,
            num_guests=1
        )
        
        # Verify second booking was created
        self.assertEqual(second_booking.status, Booking.STATUS_RESERVED)
    
    def test_price_calculation_with_seasonal_rates(self):
        """Test booking price calculation with seasonal rates."""
        # Get test data
        customer = Customer.query.first()
        
        # Get room types
        standard_room_type = RoomType.query.filter_by(name='Standard').first()
        
        # Get a standard room
        standard_room = Room.query.filter_by(room_type_id=standard_room_type.id).first()
        
        # Define dates during summer (when seasonal rates apply)
        summer_start = date(date.today().year, 6, 1)
        check_in_date = max(summer_start, date.today())
        check_out_date = check_in_date + timedelta(days=2)
        
        # Calculate expected price
        base_rate = standard_room_type.base_rate
        seasonal_rate = SeasonalRate.query.filter_by(room_type_id=standard_room_type.id).first()
        expected_price = base_rate * seasonal_rate.rate_multiplier * 2  # 2 nights
        
        # Create a booking during summer
        booking = self.booking_service.create_booking(
            room_id=standard_room.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED,
            num_guests=1
        )
        
        # Verify booking price reflects seasonal rate
        self.assertAlmostEqual(booking.total_price, expected_price, places=2)
        
        # Now create a booking with early check-in and late check-out
        booking_with_extra = self.booking_service.create_booking(
            room_id=standard_room.id,
            customer_id=customer.id,
            check_in_date=check_out_date + timedelta(days=1),  # After previous booking
            check_out_date=check_out_date + timedelta(days=3),
            status=Booking.STATUS_RESERVED,
            num_guests=1,
            early_hours=2,
            late_hours=3
        )
        
        # Calculate expected price with early/late fees
        # Base: rate * multiplier * 2 nights
        # Early fee: (rate * multiplier / 24) * 2 hours
        # Late fee: (rate * multiplier / 24) * 3 hours
        daily_rate = base_rate * seasonal_rate.rate_multiplier
        early_fee = (daily_rate / 24) * 2
        late_fee = (daily_rate / 24) * 3
        expected_price_with_extra = (daily_rate * 2) + early_fee + late_fee
        
        # Verify booking price includes early/late fees
        self.assertAlmostEqual(booking_with_extra.total_price, expected_price_with_extra, places=2)
    
    def test_booking_cancellation_and_room_status(self):
        """Test booking cancellation and room status changes."""
        # Get test data
        customer = Customer.query.first()
        
        # Get two available rooms
        rooms = Room.query.filter_by(status=Room.STATUS_AVAILABLE).limit(2).all()
        room1 = rooms[0]
        room2 = rooms[1]
        
        # Define booking dates
        check_in_date = date.today() + timedelta(days=1)
        check_out_date = check_in_date + timedelta(days=2)
        
        # Create bookings for both rooms
        booking1 = self.booking_service.create_booking(
            room_id=room1.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED,
            num_guests=1
        )
        
        booking2 = self.booking_service.create_booking(
            room_id=room2.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED,
            num_guests=1
        )
        
        # Verify both rooms are now booked
        room1 = Room.query.get(room1.id)
        room2 = Room.query.get(room2.id)
        self.assertEqual(room1.status, Room.STATUS_BOOKED)
        self.assertEqual(room2.status, Room.STATUS_BOOKED)
        
        # Cancel the first booking
        cancelled_booking = self.booking_service.cancel_booking(
            booking_id=booking1.id,
            reason="Testing cancellation"
        )
        
        # Verify booking status is updated
        self.assertEqual(cancelled_booking.status, Booking.STATUS_CANCELLED)
        self.assertEqual(cancelled_booking.cancellation_reason, "Testing cancellation")
        
        # Verify room status is updated - room1 should be available, room2 still booked
        room1 = Room.query.get(room1.id)
        room2 = Room.query.get(room2.id)
        self.assertEqual(room1.status, Room.STATUS_AVAILABLE)
        self.assertEqual(room2.status, Room.STATUS_BOOKED)
        
        # Check in booking2
        checked_in_booking = self.booking_service.check_in(booking_id=booking2.id)
        
        # Verify booking and room status
        room2 = Room.query.get(room2.id)
        self.assertEqual(checked_in_booking.status, Booking.STATUS_CHECKED_IN)
        self.assertEqual(room2.status, Room.STATUS_OCCUPIED)
        
        # Verify we can't cancel a checked-in booking
        with self.assertRaises(ValueError):
            self.booking_service.cancel_booking(booking_id=booking2.id)
    
    def test_get_bookings_by_customer(self):
        """Test retrieving all bookings for a customer."""
        # Get test data
        customer = Customer.query.first()
        rooms = Room.query.filter_by(status=Room.STATUS_AVAILABLE).limit(3).all()
        
        # Create multiple bookings for the customer
        bookings = []
        for i, room in enumerate(rooms):
            booking = self.booking_service.create_booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=date.today() + timedelta(days=i+1),
                check_out_date=date.today() + timedelta(days=i+3),
                status=Booking.STATUS_RESERVED,
                num_guests=1
            )
            bookings.append(booking)
        
        # Retrieve bookings for the customer
        customer_bookings = self.booking_service.get_bookings_by_customer(customer.id)
        
        # Verify all bookings are returned
        self.assertEqual(len(customer_bookings), len(bookings))
        
        # Verify booking details
        for booking in bookings:
            self.assertIn(booking.id, [b.id for b in customer_bookings])


if __name__ == '__main__':
    unittest.main() 