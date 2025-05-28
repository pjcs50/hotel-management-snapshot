"""
Comprehensive unit tests for the BookingService class.

This module contains thorough tests for all methods in the BookingService class,
ensuring that the core booking functionality works correctly.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.services.booking_service import BookingService, RoomNotAvailableError
from app.models.room import Room
from app.models.booking import Booking
from app.models.customer import Customer
from app.models.room_type import RoomType
from app.models.seasonal_rate import SeasonalRate


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = MagicMock()
    mock_session.query.return_value = mock_session
    mock_session.filter.return_value = mock_session
    mock_session.filter_by.return_value = mock_session
    mock_session.first.return_value = None
    mock_session.all.return_value = []
    return mock_session


@pytest.fixture
def mock_room():
    """Create a mock Room object."""
    mock = MagicMock(spec=Room)
    mock.id = 1
    mock.number = "101"
    mock.status = Room.STATUS_AVAILABLE
    mock.room_type_id = 1

    # Create a mock room_type
    mock_room_type = MagicMock(spec=RoomType)
    mock_room_type.id = 1
    mock_room_type.name = "Standard"
    mock_room_type.base_rate = 100.0
    mock_room_type.max_occupants = 2

    mock.room_type = mock_room_type
    return mock


@pytest.fixture
def mock_customer():
    """Create a mock Customer object."""
    mock = MagicMock(spec=Customer)
    mock.id = 1
    mock.name = "Test Customer"
    mock.user_id = 1
    return mock


@pytest.fixture
def booking_service(mock_db_session):
    """Create a BookingService instance with a mock db session."""
    return BookingService(mock_db_session)


class TestBookingServiceComprehensive:
    """Comprehensive test suite for BookingService."""

    def test_check_room_availability_available(self, booking_service, mock_db_session, mock_room):
        """Test check_room_availability when room is available."""
        # Setup
        mock_db_session.get.return_value = mock_room
        mock_db_session.query.return_value.filter.return_value.filter.return_value.count.return_value = 0

        # Execute
        result = booking_service.check_room_availability(
            room_id=1,
            check_in_date=datetime.now(timezone.utc).date(),
            check_out_date=datetime.now(timezone.utc).date() + timedelta(days=2)
        )

        # Assert
        assert result is True

    def test_check_room_availability_unavailable(self, booking_service, mock_db_session, mock_room):
        """Test check_room_availability when room is unavailable."""
        # Setup
        mock_db_session.get.return_value = mock_room
        mock_db_session.query.return_value.filter.return_value.filter.return_value.count.return_value = 1

        # Execute
        result = booking_service.check_room_availability(
            room_id=1,
            check_in_date=datetime.now(timezone.utc).date(),
            check_out_date=datetime.now(timezone.utc).date() + timedelta(days=2)
        )

        # Assert
        assert result is False

    def test_check_room_availability_room_not_found(self, booking_service, mock_db_session):
        """Test check_room_availability when room doesn't exist."""
        # Setup
        mock_db_session.get.return_value = None

        # Execute and Assert
        with pytest.raises(ValueError, match="Room with ID 1 does not exist"):
            booking_service.check_room_availability(
                room_id=1,
                check_in_date=datetime.now(timezone.utc).date(),
                check_out_date=datetime.now(timezone.utc).date() + timedelta(days=2)
            )

    def test_get_available_rooms(self, booking_service, mock_db_session, mock_room):
        """Test get_available_rooms."""
        # Setup
        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_room]
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        # Execute
        result = booking_service.get_available_rooms(
            check_in_date=datetime.now(timezone.utc).date(),
            check_out_date=datetime.now(timezone.utc).date() + timedelta(days=2)
        )

        # Assert
        assert isinstance(result, list)
        assert mock_db_session.query.call_count >= 1

    def test_calculate_booking_price(self, booking_service, mock_db_session, mock_room):
        """Test calculate_booking_price."""
        # Setup
        mock_db_session.get.return_value = mock_room

        # No seasonal rates
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Execute
        check_in_date = datetime.now(timezone.utc).date()
        check_out_date = check_in_date + timedelta(days=2)
        price = booking_service.calculate_booking_price(
            room_id=1,
            check_in_date=check_in_date,
            check_out_date=check_out_date
        )

        # Assert
        # Base rate is 100 per night for 2 nights = 200
        assert price == 200.0

    def test_calculate_booking_price_with_early_late_hours(self, booking_service, mock_db_session, mock_room):
        """Test calculate_booking_price with early check-in and late check-out."""
        # Setup
        mock_db_session.get.return_value = mock_room

        # No seasonal rates
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Execute
        check_in_date = datetime.now(timezone.utc).date()
        check_out_date = check_in_date + timedelta(days=2)
        price = booking_service.calculate_booking_price(
            room_id=1,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            early_hours=2,
            late_hours=3
        )

        # Assert
        # Base rate is 100 per night for 2 nights = 200
        # Early fee: 2 hours * (100 / 24) = 8.33
        # Late fee: 3 hours * (100 / 24) = 12.5
        # Total should be approximately 220.83
        assert abs(price - 220.83) < 0.1

    def test_create_booking_success(self, booking_service, mock_db_session, mock_room, mock_customer):
        """Test create_booking when successful."""
        # Setup
        mock_db_session.get.side_effect = lambda model, id: mock_room if model == Room else mock_customer
        booking_service.check_room_availability = MagicMock(return_value=True)
        booking_service._generate_confirmation_code = MagicMock(return_value='TEST123')

        # Execute
        check_in_date = datetime.now(timezone.utc).date()
        check_out_date = check_in_date + timedelta(days=2)
        booking = booking_service.create_booking(
            room_id=1,
            customer_id=1,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            num_guests=2,
            special_requests='Test request'
        )

        # Assert
        assert mock_db_session.add.call_count >= 1
        assert mock_db_session.commit.call_count == 1
        assert mock_room.status == Room.STATUS_BOOKED

    def test_create_booking_room_unavailable(self, booking_service, mock_db_session, mock_room, mock_customer):
        """Test create_booking when room is unavailable."""
        # Setup
        mock_db_session.get.side_effect = lambda model, id: mock_room if model == Room else mock_customer
        booking_service.check_room_availability = MagicMock(return_value=False)

        # Execute and Assert
        with pytest.raises(RoomNotAvailableError):
            booking_service.create_booking(
                room_id=1,
                customer_id=1,
                check_in_date=datetime.now(timezone.utc).date(),
                check_out_date=datetime.now(timezone.utc).date() + timedelta(days=2)
            )

    def test_create_booking_too_many_guests(self, booking_service, mock_db_session, mock_room, mock_customer):
        """Test create_booking with too many guests."""
        # Setup
        mock_db_session.get.side_effect = lambda model, id: mock_room if model == Room else mock_customer
        booking_service.check_room_availability = MagicMock(return_value=True)

        # Execute and Assert
        with pytest.raises(ValueError, match="Number of guests .* exceeds room capacity"):
            booking_service.create_booking(
                room_id=1,
                customer_id=1,
                check_in_date=datetime.now(timezone.utc).date(),
                check_out_date=datetime.now(timezone.utc).date() + timedelta(days=2),
                num_guests=5  # Max is 2 for our mock room
            )

    def test_update_booking_success(self, booking_service, mock_db_session):
        """Test update_booking when successful."""
        # Setup
        mock_booking = MagicMock(spec=Booking)
        mock_booking.id = 1
        mock_booking.room_id = 1
        mock_booking.status = Booking.STATUS_RESERVED

        mock_room = MagicMock(spec=Room)
        mock_room.id = 2  # New room
        mock_room.status = Room.STATUS_AVAILABLE
        mock_room.room_type_id = 1

        mock_room_type = MagicMock(spec=RoomType)
        mock_room_type.id = 1
        mock_room_type.max_occupants = 4
        mock_room.room_type = mock_room_type

        mock_db_session.get.side_effect = lambda model, id: mock_booking if model == Booking else mock_room
        booking_service.check_room_availability = MagicMock(return_value=True)

        # Execute
        today = datetime.now(timezone.utc).date()
        new_check_in = today + timedelta(days=5)
        new_check_out = today + timedelta(days=7)

        result = booking_service.update_booking(
            booking_id=1,
            room_id=2,  # Change room
            check_in_date=new_check_in,
            check_out_date=new_check_out,
            num_guests=3,
            special_requests='Updated request'
        )

        # Assert
        assert mock_db_session.add.call_count >= 1
        assert mock_db_session.commit.call_count == 1
        assert result.room_id == 2
        assert result.check_in_date == new_check_in
        assert result.check_out_date == new_check_out

    def test_update_booking_room_unavailable(self, booking_service, mock_db_session):
        """Test update_booking when new room is unavailable."""
        # Setup
        mock_booking = MagicMock(spec=Booking)
        mock_booking.id = 1
        mock_booking.room_id = 1
        mock_booking.status = Booking.STATUS_RESERVED

        mock_room = MagicMock(spec=Room)
        mock_room.id = 2  # New room

        mock_db_session.get.side_effect = lambda model, id: mock_booking if model == Booking else mock_room
        booking_service.check_room_availability = MagicMock(return_value=False)

        # Execute and Assert
        with pytest.raises(RoomNotAvailableError):
            booking_service.update_booking(
                booking_id=1,
                room_id=2,
                check_in_date=datetime.now(timezone.utc).date(),
                check_out_date=datetime.now(timezone.utc).date() + timedelta(days=2)
            )

    def test_cancel_booking_success(self, booking_service, mock_db_session):
        """Test cancel_booking when successful."""
        # Setup
        mock_booking = MagicMock(spec=Booking)
        mock_booking.id = 1
        mock_booking.room_id = 1
        mock_booking.status = Booking.STATUS_RESERVED

        mock_room = MagicMock(spec=Room)
        mock_room.id = 1
        mock_room.status = Room.STATUS_BOOKED

        mock_booking.room = mock_room

        mock_db_session.get.return_value = mock_booking
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0  # No other bookings

        # Execute
        result = booking_service.cancel_booking(booking_id=1)

        # Assert
        assert result.status == Booking.STATUS_CANCELLED
        assert mock_room.status == Room.STATUS_AVAILABLE
        assert mock_db_session.add.call_count >= 1
        assert mock_db_session.commit.call_count == 1

    def test_cancel_booking_already_checked_in(self, booking_service, mock_db_session):
        """Test cancel_booking when booking is already checked in."""
        # Setup
        mock_booking = MagicMock(spec=Booking)
        mock_booking.id = 1
        mock_booking.status = Booking.STATUS_CHECKED_IN

        mock_db_session.get.return_value = mock_booking

        # Execute and Assert
        with pytest.raises(ValueError, match="Cannot cancel a booking that is already checked in"):
            booking_service.cancel_booking(booking_id=1)

    def test_check_in_success(self, booking_service, mock_db_session):
        """Test check_in when successful."""
        # Setup
        mock_booking = MagicMock(spec=Booking)
        mock_booking.id = 1
        mock_booking.status = Booking.STATUS_RESERVED
        mock_booking.room_id = 1

        mock_room = MagicMock(spec=Room)
        mock_room.id = 1
        mock_room.status = Room.STATUS_BOOKED

        mock_booking.room = mock_room

        mock_db_session.get.return_value = mock_booking

        # Execute
        result = booking_service.check_in(booking_id=1, staff_id=1)

        # Assert
        assert result.status == Booking.STATUS_CHECKED_IN
        assert mock_room.status == Room.STATUS_OCCUPIED
        assert mock_db_session.add.call_count >= 1
        assert mock_db_session.commit.call_count == 1

    def test_check_in_invalid_status(self, booking_service, mock_db_session):
        """Test check_in when booking has invalid status."""
        # Setup
        mock_booking = MagicMock(spec=Booking)
        mock_booking.id = 1
        mock_booking.status = Booking.STATUS_CANCELLED  # Invalid status for check-in

        mock_db_session.get.return_value = mock_booking

        # Execute and Assert
        with pytest.raises(ValueError, match="Cannot check in booking with status"):
            booking_service.check_in(booking_id=1)

    def test_check_out_success(self, booking_service, mock_db_session):
        """Test check_out when successful."""
        # Setup
        mock_booking = MagicMock(spec=Booking)
        mock_booking.id = 1
        mock_booking.status = Booking.STATUS_CHECKED_IN
        mock_booking.room_id = 1
        mock_booking.customer = None  # No customer for simplicity

        mock_room = MagicMock(spec=Room)
        mock_room.id = 1
        mock_room.status = Room.STATUS_OCCUPIED

        mock_booking.room = mock_room

        mock_db_session.get.return_value = mock_booking

        # Execute
        result = booking_service.check_out(booking_id=1, staff_id=1)

        # Assert
        assert result.status == Booking.STATUS_CHECKED_OUT
        assert mock_room.status == Room.STATUS_CLEANING
        assert mock_db_session.add.call_count >= 1
        assert mock_db_session.commit.call_count == 1

    def test_check_out_invalid_status(self, booking_service, mock_db_session):
        """Test check_out when booking has invalid status."""
        # Setup
        mock_booking = MagicMock(spec=Booking)
        mock_booking.id = 1
        mock_booking.status = Booking.STATUS_RESERVED  # Invalid status for check-out

        mock_db_session.get.return_value = mock_booking

        # Execute and Assert
        with pytest.raises(ValueError, match="Cannot check out booking with status"):
            booking_service.check_out(booking_id=1)

    def test_get_bookings_by_customer(self, booking_service, mock_db_session):
        """Test get_bookings_by_customer."""
        # Setup
        mock_bookings = [MagicMock(spec=Booking) for _ in range(3)]
        mock_db_session.query.return_value.filter_by.return_value.all.return_value = mock_bookings

        # Execute
        result = booking_service.get_bookings_by_customer(customer_id=1)

        # Assert
        assert result == mock_bookings
        mock_db_session.query.assert_called_once()
        mock_db_session.query.return_value.filter_by.assert_called_once_with(customer_id=1)

    def test_get_booking_by_id_and_customer(self, booking_service, mock_db_session):
        """Test get_booking_by_id_and_customer."""
        # Setup
        mock_booking = MagicMock(spec=Booking)
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_booking

        # Execute
        result = booking_service.get_booking_by_id_and_customer(booking_id=1, customer_id=1)

        # Assert
        assert result == mock_booking
        mock_db_session.query.assert_called_once()
        mock_db_session.query.return_value.filter_by.assert_called_once_with(id=1, customer_id=1)

    def test_get_availability_calendar_data(self, booking_service, mock_db_session):
        """Test get_availability_calendar_data."""
        # Setup
        mock_room_types = [MagicMock(spec=RoomType) for _ in range(2)]
        for i, rt in enumerate(mock_room_types):
            rt.id = i + 1

        mock_db_session.query.return_value.all.return_value = mock_room_types
        mock_db_session.query.return_value.filter_by.return_value.count.return_value = 5  # Total rooms
        mock_db_session.query.return_value.join.return_value.filter.return_value.scalar.return_value = 2  # Booked rooms

        # Execute
        today = datetime.now(timezone.utc).date()
        result = booking_service.get_availability_calendar_data(
            start_date=today,
            end_date=today + timedelta(days=3)
        )

        # Assert
        assert isinstance(result, dict)
        assert 'dates' in result
        assert 'availability' in result
        assert len(result['dates']) == 4  # 4 days
        assert len(result['availability']) == 2  # 2 room types
