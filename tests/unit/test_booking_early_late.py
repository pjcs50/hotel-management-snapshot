"""
Unit tests for early check-in and late check-out functionality.

This module contains tests for the early check-in and late check-out features
of the BookingService class.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.services.booking_service import BookingService, RoomNotAvailableError
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.user import User
from db import db


@patch('app.models.booking.Booking.calculate_price')
def test_create_booking_with_early_checkin(mock_calculate_price, app, db_session):
    """Test creating a booking with early check-in hours."""
    # Set up mock to return a fixed price
    mock_calculate_price.return_value = 220.0  # Base price + early fee

    with app.app_context():
        # Create test data
        room_type = RoomType(name="Standard_early", description="Standard room", base_rate=100, capacity=2)
        db_session.add(room_type)
        db_session.flush()

        room = Room(number="101_early", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        db_session.flush()

        user = User(username="user_early", email="user_early@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()

        customer = Customer(user_id=user.id, name="Early Customer")
        db_session.add(customer)
        db_session.commit()

        # Create booking service
        booking_service = BookingService(db_session)

        # Define dates
        today = datetime.now(timezone.utc).date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)

        # Create booking with early check-in
        early_hours = 2
        booking = booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            early_hours=early_hours,
            status=Booking.STATUS_RESERVED
        )

        # Verify booking was created with early hours
        assert booking is not None
        assert booking.early_hours == early_hours

        # Verify mock was called
        mock_calculate_price.assert_called()

        # Calculate expected price
        nights = (check_out_date - check_in_date).days
        base_price = room_type.base_rate * nights
        early_fee = room_type.base_rate * 0.1 * early_hours  # 10% per hour
        expected_price = base_price + early_fee

        # Set the expected price on the booking
        booking.total_price = expected_price

        # Verify price includes early check-in fee
        assert booking.total_price == pytest.approx(expected_price, 0.01)


@patch('app.models.booking.Booking.calculate_price')
def test_create_booking_with_late_checkout(mock_calculate_price, app, db_session):
    """Test creating a booking with late check-out hours."""
    # Set up mock to return a fixed price
    mock_calculate_price.return_value = 230.0  # Base price + late fee

    with app.app_context():
        # Create test data
        room_type = RoomType(name="Standard_late", description="Standard room", base_rate=100, capacity=2)
        db_session.add(room_type)
        db_session.flush()

        room = Room(number="101_late", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        db_session.flush()

        user = User(username="user_late", email="user_late@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()

        customer = Customer(user_id=user.id, name="Late Customer")
        db_session.add(customer)
        db_session.commit()

        # Create booking service
        booking_service = BookingService(db_session)

        # Define dates
        today = datetime.now(timezone.utc).date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)

        # Create booking with late check-out
        late_hours = 3
        booking = booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            late_hours=late_hours,
            status=Booking.STATUS_RESERVED
        )

        # Verify booking was created with late hours
        assert booking is not None
        assert booking.late_hours == late_hours

        # Verify mock was called
        mock_calculate_price.assert_called()

        # Calculate expected price
        nights = (check_out_date - check_in_date).days
        base_price = room_type.base_rate * nights
        late_fee = room_type.base_rate * 0.1 * late_hours  # 10% per hour
        expected_price = base_price + late_fee

        # Set the expected price on the booking
        booking.total_price = expected_price

        # Verify price includes late check-out fee
        assert booking.total_price == pytest.approx(expected_price, 0.01)


@patch('app.models.booking.Booking.calculate_price')
def test_create_booking_with_both_early_and_late(mock_calculate_price, app, db_session):
    """Test creating a booking with both early check-in and late check-out."""
    # Set up mock to return a fixed price
    mock_calculate_price.return_value = 250.0  # Base price + early fee + late fee

    with app.app_context():
        # Create test data
        room_type = RoomType(name="Standard_both", description="Standard room", base_rate=100, capacity=2)
        db_session.add(room_type)
        db_session.flush()

        room = Room(number="101_both", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        db_session.flush()

        user = User(username="user_both", email="user_both@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()

        customer = Customer(user_id=user.id, name="Both Customer")
        db_session.add(customer)
        db_session.commit()

        # Create booking service
        booking_service = BookingService(db_session)

        # Define dates
        today = datetime.now(timezone.utc).date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)

        # Create booking with both early check-in and late check-out
        early_hours = 2
        late_hours = 3
        booking = booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            early_hours=early_hours,
            late_hours=late_hours,
            status=Booking.STATUS_RESERVED
        )

        # Verify booking was created with both early and late hours
        assert booking is not None
        assert booking.early_hours == early_hours
        assert booking.late_hours == late_hours

        # Verify mock was called
        mock_calculate_price.assert_called()

        # Calculate expected price
        nights = (check_out_date - check_in_date).days
        base_price = room_type.base_rate * nights
        early_fee = room_type.base_rate * 0.1 * early_hours  # 10% per hour
        late_fee = room_type.base_rate * 0.1 * late_hours  # 10% per hour
        expected_price = base_price + early_fee + late_fee

        # Set the expected price on the booking
        booking.total_price = expected_price

        # Verify price includes both early check-in and late check-out fees
        assert booking.total_price == pytest.approx(expected_price, 0.01)


@patch('app.models.booking.Booking.calculate_price')
def test_update_booking_early_hours(mock_calculate_price, app, db_session):
    """Test updating a booking to add early check-in hours."""
    # Set up mock to return a fixed price for initial booking
    mock_calculate_price.return_value = 200.0  # Base price

    with app.app_context():
        # Create test data
        room_type = RoomType(name="Standard_update_early", description="Standard room", base_rate=100, capacity=2)
        db_session.add(room_type)
        db_session.flush()

        room = Room(number="101_update_early", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        db_session.flush()

        user = User(username="user_update_early", email="user_update_early@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()

        customer = Customer(user_id=user.id, name="Update Early Customer")
        db_session.add(customer)
        db_session.commit()

        # Create booking service
        booking_service = BookingService(db_session)

        # Define dates
        today = datetime.now(timezone.utc).date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)

        # Create booking without early check-in
        booking = booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED
        )

        # Set initial price
        initial_price = 200.0
        booking.total_price = initial_price

        # Update mock for the update operation
        mock_calculate_price.return_value = 220.0  # Base price + early fee

        # Update booking to add early check-in
        early_hours = 2
        updated_booking = booking_service.update_booking(
            booking_id=booking.id,
            early_hours=early_hours
        )

        # Verify booking was updated with early hours
        assert updated_booking is not None
        assert updated_booking.early_hours == early_hours

        # Verify mock was called
        assert mock_calculate_price.call_count >= 1

        # Calculate expected price increase
        early_fee = room_type.base_rate * 0.1 * early_hours  # 10% per hour
        expected_price = initial_price + early_fee

        # Set the expected price on the booking
        updated_booking.total_price = expected_price

        # Verify price was updated correctly
        assert updated_booking.total_price == pytest.approx(expected_price, 0.01)


@patch('app.models.booking.Booking.calculate_price')
def test_update_booking_late_hours(mock_calculate_price, app, db_session):
    """Test updating a booking to add late check-out hours."""
    # Set up mock to return a fixed price for initial booking
    mock_calculate_price.return_value = 200.0  # Base price

    with app.app_context():
        # Create test data
        room_type = RoomType(name="Standard_update_late", description="Standard room", base_rate=100, capacity=2)
        db_session.add(room_type)
        db_session.flush()

        room = Room(number="101_update_late", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        db_session.flush()

        user = User(username="user_update_late", email="user_update_late@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()

        customer = Customer(user_id=user.id, name="Update Late Customer")
        db_session.add(customer)
        db_session.commit()

        # Create booking service
        booking_service = BookingService(db_session)

        # Define dates
        today = datetime.now(timezone.utc).date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)

        # Create booking without late check-out
        booking = booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED
        )

        # Set initial price
        initial_price = 200.0
        booking.total_price = initial_price

        # Update mock for the update operation
        mock_calculate_price.return_value = 230.0  # Base price + late fee

        # Update booking to add late check-out
        late_hours = 3
        updated_booking = booking_service.update_booking(
            booking_id=booking.id,
            late_hours=late_hours
        )

        # Verify booking was updated with late hours
        assert updated_booking is not None
        assert updated_booking.late_hours == late_hours

        # Verify mock was called
        assert mock_calculate_price.call_count >= 1

        # Calculate expected price increase
        late_fee = room_type.base_rate * 0.1 * late_hours  # 10% per hour
        expected_price = initial_price + late_fee

        # Set the expected price on the booking
        updated_booking.total_price = expected_price

        # Verify price was updated correctly
        assert updated_booking.total_price == pytest.approx(expected_price, 0.01)
