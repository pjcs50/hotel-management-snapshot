"""
Unit tests for booking price calculation.

This module contains tests for the price calculation features of the Booking model,
including early check-in and late check-out fees.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.user import User


@pytest.fixture
def setup_price_test_data(app, db_session):
    """Set up test data for price calculation tests."""
    with app.app_context():
        # Create room types with different rates
        standard = RoomType(name="Standard_Price", description="Standard room", base_rate=100, capacity=2)
        deluxe = RoomType(name="Deluxe_Price", description="Deluxe room", base_rate=200, capacity=4)
        suite = RoomType(name="Suite_Price", description="Suite", base_rate=300, capacity=6)
        
        # Create rooms
        room1 = Room(number="101_Price", room_type=standard, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="201_Price", room_type=deluxe, status=Room.STATUS_AVAILABLE)
        room3 = Room(number="301_Price", room_type=suite, status=Room.STATUS_AVAILABLE)
        
        # Create user and customer
        user = User(username="user_price", email="user_price@example.com", role="customer")
        user.set_password("password")
        customer = Customer(user=user, name="Price Test Customer")
        
        db_session.add_all([standard, deluxe, suite, room1, room2, room3, user, customer])
        db_session.commit()
        
        return {
            'standard': standard,
            'deluxe': deluxe,
            'suite': suite,
            'room1': room1,
            'room2': room2,
            'room3': room3,
            'customer': customer
        }


def test_base_price_calculation(setup_price_test_data, app, db_session):
    """Test basic price calculation without early check-in or late check-out."""
    with app.app_context():
        # Create booking for standard room for 2 nights
        today = datetime.now().date()
        booking = Booking(
            room_id=setup_price_test_data['room1'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking)
        db_session.commit()
        
        # Calculate price
        booking.calculate_price()
        db_session.commit()
        
        # Verify price (2 nights * $100/night = $200)
        assert booking.total_price == 200.0
        
        # Create booking for deluxe room for 3 nights
        booking2 = Booking(
            room_id=setup_price_test_data['room2'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=8),
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking2)
        db_session.commit()
        
        # Calculate price
        booking2.calculate_price()
        db_session.commit()
        
        # Verify price (3 nights * $200/night = $600)
        assert booking2.total_price == 600.0


def test_early_checkin_fee_calculation(setup_price_test_data, app, db_session):
    """Test price calculation with early check-in fees."""
    with app.app_context():
        # Create booking for standard room with early check-in
        today = datetime.now().date()
        booking = Booking(
            room_id=setup_price_test_data['room1'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            early_hours=2,  # 2 hours early
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking)
        db_session.commit()
        
        # Calculate price
        booking.calculate_price()
        db_session.commit()
        
        # Verify price (2 nights * $100/night + 2 hours * 10% of $100 = $220)
        assert booking.total_price == 220.0
        
        # Create booking for deluxe room with early check-in
        booking2 = Booking(
            room_id=setup_price_test_data['room2'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=8),
            early_hours=3,  # 3 hours early
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking2)
        db_session.commit()
        
        # Calculate price
        booking2.calculate_price()
        db_session.commit()
        
        # Verify price (3 nights * $200/night + 3 hours * 10% of $200 = $660)
        assert booking2.total_price == 660.0


def test_late_checkout_fee_calculation(setup_price_test_data, app, db_session):
    """Test price calculation with late check-out fees."""
    with app.app_context():
        # Create booking for standard room with late check-out
        today = datetime.now().date()
        booking = Booking(
            room_id=setup_price_test_data['room1'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            late_hours=3,  # 3 hours late
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking)
        db_session.commit()
        
        # Calculate price
        booking.calculate_price()
        db_session.commit()
        
        # Verify price (2 nights * $100/night + 3 hours * 10% of $100 = $230)
        assert booking.total_price == 230.0
        
        # Create booking for suite with late check-out
        booking2 = Booking(
            room_id=setup_price_test_data['room3'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            late_hours=4,  # 4 hours late
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking2)
        db_session.commit()
        
        # Calculate price
        booking2.calculate_price()
        db_session.commit()
        
        # Verify price (2 nights * $300/night + 4 hours * 10% of $300 = $720)
        assert booking2.total_price == 720.0


def test_both_early_and_late_fee_calculation(setup_price_test_data, app, db_session):
    """Test price calculation with both early check-in and late check-out fees."""
    with app.app_context():
        # Create booking for standard room with both early check-in and late check-out
        today = datetime.now().date()
        booking = Booking(
            room_id=setup_price_test_data['room1'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            early_hours=2,  # 2 hours early
            late_hours=3,   # 3 hours late
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking)
        db_session.commit()
        
        # Calculate price
        booking.calculate_price()
        db_session.commit()
        
        # Verify price (2 nights * $100/night + 2 hours * 10% of $100 + 3 hours * 10% of $100 = $250)
        assert booking.total_price == 250.0
        
        # Create booking for deluxe room with both early check-in and late check-out
        booking2 = Booking(
            room_id=setup_price_test_data['room2'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=8),
            early_hours=1,  # 1 hour early
            late_hours=2,   # 2 hours late
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking2)
        db_session.commit()
        
        # Calculate price
        booking2.calculate_price()
        db_session.commit()
        
        # Verify price (3 nights * $200/night + 1 hour * 10% of $200 + 2 hours * 10% of $200 = $660)
        assert booking2.total_price == 660.0


def test_max_early_late_hours_calculation(setup_price_test_data, app, db_session):
    """Test price calculation with maximum early check-in and late check-out hours."""
    with app.app_context():
        # Create booking for standard room with maximum early check-in and late check-out
        today = datetime.now().date()
        booking = Booking(
            room_id=setup_price_test_data['room1'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            early_hours=12,  # 12 hours early (maximum)
            late_hours=12,   # 12 hours late (maximum)
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking)
        db_session.commit()
        
        # Calculate price
        booking.calculate_price()
        db_session.commit()
        
        # Verify price (2 nights * $100/night + 12 hours * 10% of $100 + 12 hours * 10% of $100 = $440)
        assert booking.total_price == 440.0


def test_price_calculation_with_zero_early_late_hours(setup_price_test_data, app, db_session):
    """Test price calculation with zero early check-in and late check-out hours."""
    with app.app_context():
        # Create booking for standard room with zero early check-in and late check-out
        today = datetime.now().date()
        booking = Booking(
            room_id=setup_price_test_data['room1'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            early_hours=0,  # 0 hours early
            late_hours=0,   # 0 hours late
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking)
        db_session.commit()
        
        # Calculate price
        booking.calculate_price()
        db_session.commit()
        
        # Verify price (2 nights * $100/night = $200)
        assert booking.total_price == 200.0


def test_price_calculation_with_null_early_late_hours(setup_price_test_data, app, db_session):
    """Test price calculation with null early check-in and late check-out hours."""
    with app.app_context():
        # Create booking for standard room with null early check-in and late check-out
        today = datetime.now().date()
        booking = Booking(
            room_id=setup_price_test_data['room1'].id,
            customer_id=setup_price_test_data['customer'].id,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            early_hours=None,  # null hours early
            late_hours=None,   # null hours late
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking)
        db_session.commit()
        
        # Calculate price
        booking.calculate_price()
        db_session.commit()
        
        # Verify price (2 nights * $100/night = $200)
        assert booking.total_price == 200.0
