"""
Comprehensive tests for the BookingService class.

These tests verify the full functionality of the booking system, which is the core of
the hotel management system. Tests cover the creation, modification, and cancellation
of bookings, as well as availability checking, price calculation, and integration with
the room and customer models.
"""

import unittest
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock, Mock

from sqlalchemy.exc import IntegrityError

from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.seasonal_rate import SeasonalRate
from app.models.booking_log import BookingLog
from app.models.room_status_log import RoomStatusLog
from app.services.booking_service import BookingService, RoomNotAvailableError


class TestBookingServiceComprehensive(unittest.TestCase):
    """Comprehensive tests for the BookingService class."""

    def setUp(self):
        """Set up test fixtures before each test method is run."""
        # Mock the db session
        self.mock_session = Mock()
        
        # Create the booking service with the mock session
        self.booking_service = BookingService(self.mock_session)
        
        # Create mock models
        self.mock_room = Mock(spec=Room)
        self.mock_room.id = 1
        self.mock_room.number = "101"
        self.mock_room.status = Room.STATUS_AVAILABLE
        
        self.mock_room_type = Mock(spec=RoomType)
        self.mock_room_type.id = 1
        self.mock_room_type.name = "Standard"
        self.mock_room_type.base_rate = 100.0
        self.mock_room_type.max_occupants = 2
        
        self.mock_room.room_type = self.mock_room_type
        self.mock_room.room_type_id = self.mock_room_type.id
        
        self.mock_customer = Mock(spec=Customer)
        self.mock_customer.id = 1
        self.mock_customer.name = "Test Customer"
        self.mock_customer.loyalty_tier = Customer.TIER_STANDARD
        
        # Mock get method on session to return our mock objects
        self.mock_session.get.side_effect = lambda model, id: {
            Room: self.mock_room if id == 1 else None,
            Customer: self.mock_customer if id == 1 else None,
            RoomType: self.mock_room_type if id == 1 else None
        }.get(model)
        
        # Define common test dates
        self.today = date.today()
        self.tomorrow = self.today + timedelta(days=1)
        self.day_after_tomorrow = self.today + timedelta(days=2)

    def test_create_booking_success(self):
        """Test creating a booking successfully."""
        # Mock the query for check_room_availability
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        self.mock_session.query.return_value = mock_query
        
        # Create a booking
        booking = self.booking_service.create_booking(
            room_id=1,
            customer_id=1,
            check_in_date=self.today,
            check_out_date=self.tomorrow,
            status=Booking.STATUS_RESERVED,
            num_guests=1
        )
        
        # Verify the booking was added to the session
        self.mock_session.add.assert_called()
        
        # Verify the session was committed
        self.mock_session.commit.assert_called_once()
        
        # Verify the booking has the correct data
        self.assertEqual(booking.room_id, 1)
        self.assertEqual(booking.customer_id, 1)
        self.assertEqual(booking.check_in_date, self.today)
        self.assertEqual(booking.check_out_date, self.tomorrow)
        self.assertEqual(booking.status, Booking.STATUS_RESERVED)

    def test_create_booking_room_not_available(self):
        """Test creating a booking when the room is not available."""
        # Mock check_room_availability to return False
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1  # Indicates room is already booked
        self.mock_session.query.return_value = mock_query
        
        # Attempt to create a booking for an unavailable room
        with self.assertRaises(RoomNotAvailableError):
            self.booking_service.create_booking(
                room_id=1,
                customer_id=1,
                check_in_date=self.today,
                check_out_date=self.tomorrow,
                status=Booking.STATUS_RESERVED,
                num_guests=1
            )
        
        # Verify no booking was added to the session
        self.mock_session.add.assert_not_called()
        
        # Verify the session was not committed
        self.mock_session.commit.assert_not_called()

    def test_create_booking_invalid_room(self):
        """Test creating a booking with an invalid room ID."""
        # Set up the session to return None for an invalid room ID
        self.mock_session.get.side_effect = lambda model, id: None if model == Room and id == 999 else {
            Room: self.mock_room if id == 1 else None,
            Customer: self.mock_customer if id == 1 else None
        }.get(model)
        
        # Attempt to create a booking with an invalid room ID
        with self.assertRaises(ValueError):
            self.booking_service.create_booking(
                room_id=999,  # Invalid room ID
                customer_id=1,
                check_in_date=self.today,
                check_out_date=self.tomorrow,
                status=Booking.STATUS_RESERVED,
                num_guests=1
            )

    def test_create_booking_invalid_customer(self):
        """Test creating a booking with an invalid customer ID."""
        # Set up the session to return None for an invalid customer ID
        self.mock_session.get.side_effect = lambda model, id: None if model == Customer and id == 999 else {
            Room: self.mock_room if id == 1 else None,
            Customer: self.mock_customer if id == 1 else None
        }.get(model)
        
        # Attempt to create a booking with an invalid customer ID
        with self.assertRaises(ValueError):
            self.booking_service.create_booking(
                room_id=1,
                customer_id=999,  # Invalid customer ID
                check_in_date=self.today,
                check_out_date=self.tomorrow,
                status=Booking.STATUS_RESERVED,
                num_guests=1
            )

    def test_create_booking_too_many_guests(self):
        """Test creating a booking with too many guests for the room."""
        # Mock the room type to have a max_occupants of 2
        self.mock_room_type.max_occupants = 2
        
        # Attempt to create a booking with too many guests
        with self.assertRaises(ValueError):
            self.booking_service.create_booking(
                room_id=1,
                customer_id=1,
                check_in_date=self.today,
                check_out_date=self.tomorrow,
                status=Booking.STATUS_RESERVED,
                num_guests=3  # Too many guests
            )

    def test_calculate_booking_price_standard(self):
        """Test calculating the price for a standard booking."""
        # Mock a seasonal rate query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No seasonal rate applies
        self.mock_session.query.return_value = mock_query
        
        # Calculate the price for a 1-night stay
        price = self.booking_service.calculate_booking_price(
            room_id=1,
            check_in_date=self.today,
            check_out_date=self.tomorrow
        )
        
        # Verify the price is the base rate for 1 night
        self.assertEqual(price, 100.0)

    def test_calculate_booking_price_with_seasonal_rate(self):
        """Test calculating the price with a seasonal rate applied."""
        # Create a mock seasonal rate
        mock_seasonal_rate = Mock(spec=SeasonalRate)
        mock_seasonal_rate.rate_multiplier = 1.5  # 50% increase
        
        # Mock a seasonal rate query to return our mock rate
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_seasonal_rate
        self.mock_session.query.return_value = mock_query
        
        # Calculate the price for a 1-night stay with seasonal rate
        price = self.booking_service.calculate_booking_price(
            room_id=1,
            check_in_date=self.today,
            check_out_date=self.tomorrow
        )
        
        # Verify the price is the base rate times the seasonal multiplier
        self.assertEqual(price, 150.0)  # 100 * 1.5 = 150

    def test_calculate_booking_price_multi_night(self):
        """Test calculating the price for a multi-night booking."""
        # Mock a seasonal rate query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No seasonal rate applies
        self.mock_session.query.return_value = mock_query
        
        # Calculate the price for a 2-night stay
        price = self.booking_service.calculate_booking_price(
            room_id=1,
            check_in_date=self.today,
            check_out_date=self.day_after_tomorrow
        )
        
        # Verify the price is the base rate times the number of nights
        self.assertEqual(price, 200.0)  # 100 * 2 = 200

    def test_calculate_booking_price_with_early_late_fees(self):
        """Test calculating the price with early check-in and late check-out fees."""
        # Mock a seasonal rate query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No seasonal rate applies
        self.mock_session.query.return_value = mock_query
        
        # Calculate the price with early and late fees
        price = self.booking_service.calculate_booking_price(
            room_id=1,
            check_in_date=self.today,
            check_out_date=self.tomorrow,
            early_hours=2,
            late_hours=3
        )
        
        # Verify the price includes the base rate plus hourly fees
        # Base: 100, Early fee: (100/24) * 2, Late fee: (100/24) * 3
        expected_early_fee = (100.0 / 24) * 2
        expected_late_fee = (100.0 / 24) * 3
        expected_price = 100.0 + expected_early_fee + expected_late_fee
        self.assertAlmostEqual(price, expected_price, places=2)

    def test_update_booking_success(self):
        """Test updating a booking successfully."""
        # Create a mock booking
        mock_booking = Mock(spec=Booking)
        mock_booking.id = 1
        mock_booking.room_id = 1
        mock_booking.status = Booking.STATUS_RESERVED
        
        # Set up the session to return our mock booking
        self.mock_session.get.side_effect = lambda model, id: mock_booking if model == Booking and id == 1 else {
            Room: self.mock_room if id == 1 else None,
            Customer: self.mock_customer if id == 1 else None
        }.get(model)
        
        # Update the booking
        updated_booking = self.booking_service.update_booking(
            booking_id=1,
            check_in_date=self.tomorrow,
            check_out_date=self.day_after_tomorrow,
            num_guests=2
        )
        
        # Verify the booking was updated
        self.assertEqual(updated_booking.check_in_date, self.tomorrow)
        self.assertEqual(updated_booking.check_out_date, self.day_after_tomorrow)
        self.assertEqual(updated_booking.num_guests, 2)
        
        # Verify the session was committed
        self.mock_session.commit.assert_called_once()

    def test_cancel_booking_success(self):
        """Test cancelling a booking successfully."""
        # Create a mock booking
        mock_booking = Mock(spec=Booking)
        mock_booking.id = 1
        mock_booking.room_id = 1
        mock_booking.status = Booking.STATUS_RESERVED
        mock_booking.room = self.mock_room
        
        # Set up the session to return our mock booking
        self.mock_session.get.side_effect = lambda model, id: mock_booking if model == Booking and id == 1 else {
            Room: self.mock_room if id == 1 else None
        }.get(model)
        
        # Cancel the booking
        cancelled_booking = self.booking_service.cancel_booking(booking_id=1, reason="Test cancellation")
        
        # Verify the booking was cancelled
        self.assertEqual(cancelled_booking.status, Booking.STATUS_CANCELLED)
        self.assertEqual(cancelled_booking.cancellation_reason, "Test cancellation")
        
        # Verify the room status was updated
        self.assertEqual(self.mock_room.status, Room.STATUS_AVAILABLE)
        
        # Verify the session was committed
        self.mock_session.commit.assert_called_once()

    def test_cancel_booking_already_checked_in(self):
        """Test attempting to cancel a booking that's already checked in."""
        # Create a mock booking that's already checked in
        mock_booking = Mock(spec=Booking)
        mock_booking.id = 1
        mock_booking.status = Booking.STATUS_CHECKED_IN
        
        # Set up the session to return our mock booking
        self.mock_session.get.side_effect = lambda model, id: mock_booking if model == Booking and id == 1 else None
        
        # Attempt to cancel the booking
        with self.assertRaises(ValueError):
            self.booking_service.cancel_booking(booking_id=1)

    def test_check_in_booking_success(self):
        """Test checking in a booking successfully."""
        # Create a mock booking
        mock_booking = Mock(spec=Booking)
        mock_booking.id = 1
        mock_booking.room_id = 1
        mock_booking.status = Booking.STATUS_RESERVED
        mock_booking.room = self.mock_room
        
        # Set up the session to return our mock booking
        self.mock_session.get.side_effect = lambda model, id: mock_booking if model == Booking and id == 1 else {
            Room: self.mock_room if id == 1 else None
        }.get(model)
        
        # Check in the booking
        checked_in_booking = self.booking_service.check_in(booking_id=1, staff_id=1)
        
        # Verify the booking was checked in
        self.assertEqual(checked_in_booking.status, Booking.STATUS_CHECKED_IN)
        
        # Verify the room status was updated
        self.assertEqual(self.mock_room.status, Room.STATUS_OCCUPIED)
        
        # Verify a booking log was created
        self.mock_session.add.assert_called()
        
        # Verify the session was committed
        self.mock_session.commit.assert_called_once()

    def test_check_in_booking_invalid_status(self):
        """Test attempting to check in a booking with an invalid status."""
        # Create a mock booking that's already checked in
        mock_booking = Mock(spec=Booking)
        mock_booking.id = 1
        mock_booking.status = Booking.STATUS_CHECKED_IN
        
        # Set up the session to return our mock booking
        self.mock_session.get.side_effect = lambda model, id: mock_booking if model == Booking and id == 1 else None
        
        # Attempt to check in the booking
        with self.assertRaises(ValueError):
            self.booking_service.check_in(booking_id=1)

    def test_check_out_booking_success(self):
        """Test checking out a booking successfully."""
        # Create a mock booking
        mock_booking = Mock(spec=Booking)
        mock_booking.id = 1
        mock_booking.room_id = 1
        mock_booking.status = Booking.STATUS_CHECKED_IN
        mock_booking.room = self.mock_room
        mock_booking.customer = self.mock_customer
        
        # Mock the customer's update_stats_after_stay method
        self.mock_customer.update_stats_after_stay = Mock()
        
        # Set up the session to return our mock booking
        self.mock_session.get.side_effect = lambda model, id: mock_booking if model == Booking and id == 1 else {
            Room: self.mock_room if id == 1 else None
        }.get(model)
        
        # Check out the booking
        checked_out_booking = self.booking_service.check_out(booking_id=1, staff_id=1)
        
        # Verify the booking was checked out
        self.assertEqual(checked_out_booking.status, Booking.STATUS_CHECKED_OUT)
        
        # Verify the room status was updated
        self.assertEqual(self.mock_room.status, Room.STATUS_CLEANING)
        
        # Verify the customer stats were updated
        self.mock_customer.update_stats_after_stay.assert_called_once_with(mock_booking)
        
        # Verify a booking log was created
        self.mock_session.add.assert_called()
        
        # Verify the session was committed
        self.mock_session.commit.assert_called_once()

    def test_check_out_booking_invalid_status(self):
        """Test attempting to check out a booking with an invalid status."""
        # Create a mock booking that's not checked in
        mock_booking = Mock(spec=Booking)
        mock_booking.id = 1
        mock_booking.status = Booking.STATUS_RESERVED
        
        # Set up the session to return our mock booking
        self.mock_session.get.side_effect = lambda model, id: mock_booking if model == Booking and id == 1 else None
        
        # Attempt to check out the booking
        with self.assertRaises(ValueError):
            self.booking_service.check_out(booking_id=1)

    def test_get_available_rooms(self):
        """Test getting available rooms for a date range."""
        # Create mock rooms
        mock_room1 = Mock(spec=Room)
        mock_room1.id = 1
        mock_room1.status = Room.STATUS_AVAILABLE
        
        mock_room2 = Mock(spec=Room)
        mock_room2.id = 2
        mock_room2.status = Room.STATUS_AVAILABLE
        
        # Mock the query for available rooms
        mock_room_query = MagicMock()
        mock_room_query.filter.return_value = mock_room_query
        mock_room_query.all.return_value = [mock_room1, mock_room2]
        
        # Mock the query for unavailable room IDs
        mock_booking_query = MagicMock()
        mock_booking_query.filter.return_value = mock_booking_query
        mock_booking_query.all.return_value = []  # No unavailable rooms
        
        # Set up the session to return our mock queries
        self.mock_session.query.side_effect = lambda model: mock_room_query if model == Room else mock_booking_query
        
        # Get available rooms
        available_rooms = self.booking_service.get_available_rooms(
            check_in_date=self.today,
            check_out_date=self.tomorrow
        )
        
        # Verify the correct rooms were returned
        self.assertEqual(len(available_rooms), 2)
        self.assertIn(mock_room1, available_rooms)
        self.assertIn(mock_room2, available_rooms)

    def test_get_availability_calendar_data(self):
        """Test getting availability calendar data."""
        # Create mock room types
        mock_room_type = Mock(spec=RoomType)
        mock_room_type.id = 1
        mock_room_type.to_dict.return_value = {'id': 1, 'name': 'Standard'}
        
        # Mock the query for room types
        mock_room_type_query = MagicMock()
        mock_room_type_query.filter_by.return_value = mock_room_type_query
        mock_room_type_query.all.return_value = [mock_room_type]
        
        # Mock the query for room count
        mock_room_count_query = MagicMock()
        mock_room_count_query.filter_by.return_value = mock_room_count_query
        mock_room_count_query.count.return_value = 10  # 10 rooms of this type
        
        # Mock the query for booked rooms count
        mock_booking_count_query = MagicMock()
        mock_booking_count_query.join.return_value = mock_booking_count_query
        mock_booking_count_query.filter.return_value = mock_booking_count_query
        mock_booking_count_query.scalar.return_value = 5  # 5 rooms booked
        
        # Set up the session to return our mock queries
        self.mock_session.query.side_effect = lambda *args: {
            RoomType: mock_room_type_query,
            Room: mock_room_count_query
        }.get(args[0], mock_booking_count_query)
        
        # Get availability calendar data
        calendar_data = self.booking_service.get_availability_calendar_data(
            start_date=self.today,
            end_date=self.tomorrow
        )
        
        # Verify the calendar data
        self.assertIn(self.today.strftime('%Y-%m-%d'), calendar_data['dates'])
        self.assertEqual(len(calendar_data['room_types']), 1)
        self.assertEqual(calendar_data['room_types'][0]['id'], 1)
        
        # Verify availability data
        date_str = self.today.strftime('%Y-%m-%d')
        self.assertEqual(calendar_data['availability']['1'][date_str]['available'], 5)  # 10 total - 5 booked = 5 available
        self.assertEqual(calendar_data['availability']['1'][date_str]['total'], 10)

    def test_database_error_handling(self):
        """Test handling of database errors during booking creation."""
        # Mock query to pass availability check
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        self.mock_session.query.return_value = mock_query
        
        # Set up the session to raise an IntegrityError on commit
        self.mock_session.commit.side_effect = IntegrityError("Mock integrity error", None, None)
        
        # Attempt to create a booking that will cause a database error
        with self.assertRaises(IntegrityError):
            self.booking_service.create_booking(
                room_id=1,
                customer_id=1,
                check_in_date=self.today,
                check_out_date=self.tomorrow,
                status=Booking.STATUS_RESERVED,
                num_guests=1
            )
        
        # Verify the session was rolled back
        self.mock_session.rollback.assert_called_once()


if __name__ == '__main__':
    unittest.main() 