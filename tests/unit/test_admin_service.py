"""
Unit tests for admin service functionality.

This module contains tests for the admin operations including check-in,
check-out, and cancellation of reservations.
"""

import pytest
from datetime import datetime, timedelta
from app.services.booking_service import BookingService


def test_admin_check_in(app, db_session):
    """Test admin check-in functionality."""
    from app.models.user import User
    from app.models.customer import Customer
    from app.models.room import Room
    from app.models.room_type import RoomType
    from app.models.booking import Booking
    
    with app.app_context():
        # Create test data
        room_type = RoomType(name="Standard_admin_checkin", base_rate=100.0, capacity=2)
        db_session.add(room_type)
        db_session.flush()
        
        room = Room(number="101_admin_checkin", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        
        admin = User(username="admin_checkin", email="admin_checkin@test.com", role="admin")
        admin.set_password("password")
        db_session.add(admin)
        
        user = User(username="customer_checkin", email="customer_checkin@test.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()
        
        customer = Customer(name="Test Customer Checkin", user_id=user.id)
        db_session.add(customer)
        db_session.flush()
        
        # Create a reservation (status: 'Reserved')
        check_in_date = datetime.now().date()
        check_out_date = check_in_date + timedelta(days=2)
        
        booking = Booking(
            customer_id=customer.id,
            room_id=room.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking)
        db_session.commit()
        
        # Test check-in
        booking_service = BookingService(db_session)
        booking_service.check_in(booking.id)
        db_session.flush()
        
        # Verify booking status updated
        updated_booking = Booking.query.get(booking.id)
        assert updated_booking.status == Booking.STATUS_CHECKED_IN
        
        # Verify room status updated
        updated_room = Room.query.get(room.id)
        assert updated_room.status == Room.STATUS_OCCUPIED


def test_admin_check_out(app, db_session):
    """Test admin check-out functionality."""
    from app.models.user import User
    from app.models.customer import Customer
    from app.models.room import Room
    from app.models.room_type import RoomType
    from app.models.booking import Booking
    
    with app.app_context():
        # Create test data
        room_type = RoomType(name="Deluxe_admin_checkout", base_rate=150.0, capacity=4)
        db_session.add(room_type)
        db_session.flush()
        
        room = Room(number="202_admin_checkout", room_type_id=room_type.id, status=Room.STATUS_OCCUPIED)
        db_session.add(room)
        
        admin = User(username="admin_checkout", email="admin_checkout@test.com", role="admin")
        admin.set_password("password")
        db_session.add(admin)
        
        user = User(username="customer_checkout", email="customer_checkout@test.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()
        
        customer = Customer(name="Test Customer Checkout", user_id=user.id)
        db_session.add(customer)
        db_session.flush()
        
        # Create a reservation (status: 'Checked In')
        check_in_date = datetime.now().date() - timedelta(days=1)
        check_out_date = datetime.now().date() + timedelta(days=1)
        
        booking = Booking(
            customer_id=customer.id,
            room_id=room.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_CHECKED_IN
        )
        db_session.add(booking)
        db_session.commit()
        
        # Test check-out
        booking_service = BookingService(db_session)
        booking_service.check_out(booking.id)
        db_session.flush()
        
        # Verify booking status updated
        updated_booking = Booking.query.get(booking.id)
        assert updated_booking.status == Booking.STATUS_CHECKED_OUT
        
        # Verify room status updated
        updated_room = Room.query.get(room.id)
        assert updated_room.status == Room.STATUS_CLEANING


def test_admin_cancel_reservation(app, db_session):
    """Test admin cancellation of a reservation."""
    from app.models.user import User
    from app.models.customer import Customer
    from app.models.room import Room
    from app.models.room_type import RoomType
    from app.models.booking import Booking
    
    with app.app_context():
        # Create test data
        room_type = RoomType(name="Suite_admin_cancel", base_rate=200.0, capacity=6)
        db_session.add(room_type)
        db_session.flush()
        
        room = Room(number="303_admin_cancel", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        
        admin = User(username="admin_cancel", email="admin_cancel@test.com", role="admin")
        admin.set_password("password")
        db_session.add(admin)
        
        user = User(username="customer_cancel", email="customer_cancel@test.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()
        
        customer = Customer(name="Test Customer Cancel", user_id=user.id)
        db_session.add(customer)
        db_session.flush()
        
        # Create a future reservation (status: 'Reserved')
        check_in_date = datetime.now().date() + timedelta(days=5)
        check_out_date = check_in_date + timedelta(days=2)
        
        booking = Booking(
            customer_id=customer.id,
            room_id=room.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking)
        db_session.commit()
        
        # Test cancellation
        booking_service = BookingService(db_session)
        booking_service.cancel_booking(booking.id)
        db_session.flush()
        
        # Verify booking status updated
        updated_booking = Booking.query.get(booking.id)
        assert updated_booking.status == Booking.STATUS_CANCELLED
        
        # Verify room status is still available
        updated_room = Room.query.get(room.id)
        assert updated_room.status == Room.STATUS_AVAILABLE 