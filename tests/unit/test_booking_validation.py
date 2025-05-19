"""
Unit tests for booking validation.

This module contains tests specifically for booking validation and double-booking prevention.
"""

import pytest
from datetime import datetime, timedelta

from app.services.booking_service import BookingService, RoomNotAvailableError
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.user import User


def test_check_room_availability_basic(app, db_session):
    """Test room availability check with no bookings."""
    with app.app_context():
        # Create room type
        room_type = RoomType(name="Standard_bv_basic", description="Standard room", base_rate=100, capacity=2)
        
        # Create room
        room = Room(number="101_basic", room_type=room_type, status=Room.STATUS_AVAILABLE)
        
        db_session.add_all([room_type, room])
        db_session.commit()
        
        # Create BookingService
        booking_service = BookingService(db_session)
        
        # Define dates
        check_in_date = datetime.now().date()
        check_out_date = check_in_date + timedelta(days=2)
        
        # Check availability (should be available)
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date
        )
        
        assert is_available is True


def test_check_room_availability_unavailable_status(app, db_session):
    """Test that a room with non-available status is not available."""
    with app.app_context():
        # Create room type
        room_type = RoomType(name="Standard_bv_unavail", description="Standard room", base_rate=100, capacity=2)
        
        # Create room with OCCUPIED status
        room = Room(number="101_unavail", room_type=room_type, status=Room.STATUS_OCCUPIED)
        
        db_session.add_all([room_type, room])
        db_session.commit()
        
        # Create BookingService
        booking_service = BookingService(db_session)
        
        # Define dates
        check_in_date = datetime.now().date()
        check_out_date = check_in_date + timedelta(days=2)
        
        # Check availability (should be unavailable)
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=check_in_date,
            check_out_date=check_out_date
        )
        
        assert is_available is False


def test_check_room_availability_existing_booking(app, db_session):
    """Test room availability check with existing booking."""
    with app.app_context():
        # Create a user and customer
        user = User(username="testuser_bv_eb", email="test_bv_eb@example.com")
        user.set_password("password_eb")
        customer = Customer(user=user, name="Test Customer EB")
        
        # Create room type
        room_type = RoomType(name="Standard_bv_eb", description="Standard room", base_rate=100, capacity=2)
        
        # Create room
        room = Room(number="101_eb", room_type=room_type, status=Room.STATUS_BOOKED)
        
        db_session.add_all([user, customer, room_type, room])
        db_session.commit()
        
        # Create a booking
        today = datetime.now().date()
        booking = Booking(
            room=room,
            customer=customer,
            check_in_date=today,
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        
        db_session.add(booking)
        db_session.commit()
        
        # Create BookingService
        booking_service = BookingService(db_session)
        
        # Test 1: Exact same dates (should not be available)
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today,
            check_out_date=today + timedelta(days=3)
        )
        assert is_available is False
        
        # Test 2: Overlapping dates (check-in during existing booking)
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=4)
        )
        assert is_available is False
        
        # Test 3: Overlapping dates (check-out during existing booking)
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today - timedelta(days=1),
            check_out_date=today + timedelta(days=1)
        )
        assert is_available is False
        
        # Test 4: New booking completely contains existing booking
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today - timedelta(days=1),
            check_out_date=today + timedelta(days=4)
        )
        assert is_available is False
        
        # Test 5: Non-overlapping dates before existing booking
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today - timedelta(days=5),
            check_out_date=today - timedelta(days=1)
        )
        assert is_available is True
        
        # Test 6: Non-overlapping dates after existing booking
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=5)
        )
        assert is_available is True
        
        # Test 7: Adjacent dates (check-out = existing check-in)
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today - timedelta(days=3),
            check_out_date=today
        )
        assert is_available is True
        
        # Test 8: Adjacent dates (check-in = existing check-out)
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=5)
        )
        assert is_available is True


def test_check_room_availability_multiple_bookings(app, db_session):
    """Test room availability check with multiple bookings."""
    with app.app_context():
        # Create a user and customer
        user = User(username="testuser_bv_mb", email="test_bv_mb@example.com")
        user.set_password("password_mb")
        customer = Customer(user=user, name="Test Customer MB")
        
        # Create room type
        room_type = RoomType(name="Standard_bv_mb", description="Standard room", base_rate=100, capacity=2)
        
        # Create room
        room = Room(number="101_mb", room_type=room_type, status=Room.STATUS_BOOKED)
        
        db_session.add_all([user, customer, room_type, room])
        db_session.commit()
        
        # Create multiple bookings
        today = datetime.now().date()
        
        # Booking 1: Today to Today+3
        booking1 = Booking(
            room=room,
            customer=customer,
            check_in_date=today,
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        
        # Booking 2: Today+5 to Today+8
        booking2 = Booking(
            room=room,
            customer=customer,
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=8),
            status=Booking.STATUS_RESERVED
        )
        
        db_session.add_all([booking1, booking2])
        db_session.commit()
        
        # Create BookingService
        booking_service = BookingService(db_session)
        
        # Test 1: Between bookings (should be available)
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=5)
        )
        assert is_available is True
        
        # Test 2: Overlaps with booking 1
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4)
        )
        assert is_available is False
        
        # Test 3: Overlaps with booking 2
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today + timedelta(days=4),
            check_out_date=today + timedelta(days=6)
        )
        assert is_available is False
        
        # Test 4: Spans both bookings (should not be available)
        is_available = booking_service.check_room_availability(
            room_id=room.id,
            check_in_date=today - timedelta(days=1),
            check_out_date=today + timedelta(days=9)
        )
        assert is_available is False


def test_check_room_availability_update_booking(app, db_session):
    """Test room availability check when updating an existing booking."""
    with app.app_context():
        # Create a user and customer
        user = User(username="testuser_bv_ub", email="test_bv_ub@example.com")
        user.set_password("password_ub")
        customer = Customer(user=user, name="Test Customer UB")
        
        # Create room type
        room_type = RoomType(name="Standard_bv_ub", description="Standard room", base_rate=100, capacity=2)
        
        # Create two rooms for the test
        room1 = Room(number="101_bv_ub", room_type=room_type, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="102_bv_ub", room_type=room_type, status=Room.STATUS_AVAILABLE)
        
        db_session.add_all([user, customer, room_type, room1, room2])
        db_session.commit()
        
        # Booking for room1 (original booking)
        today = datetime.now().date()
        original_booking = Booking(
            room=room1,
            customer=customer,
            check_in_date=today,
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        room1.status = Room.STATUS_BOOKED
        db_session.add(original_booking)
        db_session.commit()
        
        booking_service = BookingService(db_session)
        
        # Scenario 1: Update existing booking (original_booking) to a new time slot that is available
        is_available_for_update = booking_service.check_room_availability(
            room_id=room1.id,
            check_in_date=today + timedelta(days=4),
            check_out_date=today + timedelta(days=7),
            booking_id=original_booking.id
        )
        assert is_available_for_update is True
        
        # Create another booking on room1 that will conflict with the update attempt for original_booking
        conflicting_booking_room1_later = Booking(
            room=room1, # Same room as original_booking
            customer=customer,
            check_in_date=today + timedelta(days=4), # days 4-6
            check_out_date=today + timedelta(days=6),
            status=Booking.STATUS_RESERVED
        )
        db_session.add(conflicting_booking_room1_later)
        db_session.commit()

        # Scenario 2: Try to update original_booking on room1 to overlap with conflicting_booking_room1_later
        # original_booking is days 0-3. Update tries to make it days 0-5.
        # conflicting_booking_room1_later is days 4-6. This will overlap.
        with pytest.raises(RoomNotAvailableError):
            booking_service.update_booking(
                booking_id=original_booking.id,
                check_out_date=today + timedelta(days=5) # Extend into days 4-5
            )
        
        # Scenario 3: Try to move original_booking to room2, but room2 has a conflict
        # First, create a conflicting booking on room2
        conflicting_booking_on_room2 = Booking(
            room=room2,
            customer=customer,
            check_in_date=today + timedelta(days=1), # Conflict: days 1-3 on room2 for original_booking's dates
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        db_session.add(conflicting_booking_on_room2)
        db_session.commit()
        
        with pytest.raises(RoomNotAvailableError):
            booking_service.update_booking(
                booking_id=original_booking.id, 
                room_id=room2.id,            
                check_in_date=today,         
                check_out_date=today + timedelta(days=3) 
            )
        
        # Scenario 4: Move original_booking to room2 with non-overlapping dates (should succeed)
        # Clear conflicting_booking_on_room2 for a clean test for this specific move
        db_session.delete(conflicting_booking_on_room2)
        db_session.commit()
        
        updated_booking = booking_service.update_booking(
            booking_id=original_booking.id,
            room_id=room2.id,
            check_in_date=today,
            check_out_date=today + timedelta(days=3)
        )
        
        assert updated_booking.room_id == room2.id
        
        # Verify room statuses
        # Fetch fresh instances from the current session to get latest status
        refreshed_room1 = db_session.get(Room, room1.id)
        assert refreshed_room1.status == Room.STATUS_BOOKED  # Previous room should be booked
        
        refreshed_room2 = db_session.get(Room, room2.id)
        assert refreshed_room2.status == Room.STATUS_BOOKED  # New room should be booked


def test_create_booking_validation(app, db_session):
    """Test that create_booking validates room availability."""
    with app.app_context():
        # Create a user and customer
        user = User(username="testuser_bv_cbv", email="test_bv_cbv@example.com")
        user.set_password("password_cbv")
        customer = Customer(user=user, name="Test Customer CBV")
        
        # Create room type and room
        room_type = RoomType(name="Standard_bv_cbv", base_rate=100, capacity=2, description="Std Room CBV")
        room = Room(number="101_cbv", room_type=room_type, status=Room.STATUS_AVAILABLE)
        db_session.add_all([user, customer, room_type, room])
        db_session.commit()
        
        booking_service = BookingService(db_session)
        
        # Create a booking (should succeed)
        today = datetime.now().date()
        booking = booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=today,
            check_out_date=today + timedelta(days=3)
        )
        
        assert booking is not None
        assert booking.room_id == room.id
        assert booking.customer_id == customer.id
        assert booking.status == Booking.STATUS_RESERVED
        
        # Verify room status was updated
        room = Room.query.get(room.id)
        assert room.status == Room.STATUS_BOOKED
        
        # Try to create an overlapping booking (should fail)
        with pytest.raises(RoomNotAvailableError):
            booking_service.create_booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=today + timedelta(days=1),
                check_out_date=today + timedelta(days=4)
            )


def test_update_booking_validation(app, db_session):
    """Test that update_booking validates room availability."""
    with app.app_context():
        # Scenario: Room becomes unavailable due to another booking
        # Create users, customers
        user_orig = User(username="orig_user_bv_ubv", email="orig_bv_ubv@example.com")
        user_orig.set_password("password")
        customer_orig = Customer(user=user_orig, name="Original Customer")

        user_conflict = User(username="conflict_user_bv_ubv", email="conflict_bv_ubv@example.com")
        user_conflict.set_password("password")
        customer_conflict = Customer(user=user_conflict, name="Conflicting Customer")

        # Create room types
        room_type_standard = RoomType(name="Standard_bv_ubv", description="Standard Room", base_rate=100, capacity=2)

        # Create rooms
        room1_orig = Room(number="101_bv_ubv", room_type=room_type_standard, status=Room.STATUS_AVAILABLE)
        room2_conflict = Room(number="102_bv_ubv", room_type=room_type_standard, status=Room.STATUS_AVAILABLE)

        db_session.add_all([user_orig, customer_orig, user_conflict, customer_conflict, 
                            room_type_standard, room1_orig, room2_conflict])
        db_session.commit()
        
        booking_service = BookingService(db_session)
        
        # Create an initial booking for room1
        today = datetime.now().date()
        original_booking = booking_service.create_booking(
            room_id=room1_orig.id,
            customer_id=customer_orig.id,
            check_in_date=today,
            check_out_date=today + timedelta(days=3)
        )
        
        # Scenario 1: Update existing booking (original_booking) to a new time slot that is available
        is_available_for_update = booking_service.check_room_availability(
            room_id=room1_orig.id,
            check_in_date=today + timedelta(days=4),
            check_out_date=today + timedelta(days=7),
            booking_id=original_booking.id
        )
        assert is_available_for_update is True
        
        # Create another booking on room1 that will make the subsequent update fail
        conflicting_booking_on_room1 = Booking(
            room=room1_orig, 
            customer=customer_orig,
            check_in_date=today + timedelta(days=4), # Conflicts with the intended update below
            check_out_date=today + timedelta(days=6),
            status=Booking.STATUS_RESERVED
        )
        db_session.add(conflicting_booking_on_room1)
        db_session.commit()

        # Scenario 2: Try to update original_booking to overlap with conflicting_booking_on_room1 (should fail)
        with pytest.raises(RoomNotAvailableError):
            booking_service.update_booking(
                booking_id=original_booking.id,
                check_out_date=today + timedelta(days=5) # This extends original_booking into days 4-5, conflicting
            )
        
        # Scenario 3: Try to move original_booking to room2 with overlapping dates (should fail)
        # To ensure a clean test for scenario 3, let's remove the conflicting booking from room1 first.
        # Otherwise, if update_booking also tries to set room1 to AVAILABLE and fails due to conflicting_booking_on_room1,
        # it might mask the error we intend to test for room2.
        db_session.delete(conflicting_booking_on_room1)
        db_session.commit()

        # Now, create a conflicting booking on room2 for scenario 3
        conflicting_booking_on_room2_for_scenario3 = Booking(
            room=room2_conflict,
            customer=customer_conflict,
            check_in_date=today + timedelta(days=1), # original_booking is days 0-3. This makes room2 busy on days 1-3.
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        db_session.add(conflicting_booking_on_room2_for_scenario3)
        db_session.commit()
        # Explicitly update room2 status after adding a booking directly
        room2_from_db = db_session.get(Room, room2_conflict.id) # Get a fresh instance if needed, or assume room2 is fine
        if room2_from_db:
            room2_from_db.status = Room.STATUS_BOOKED
            db_session.commit()

        print(f"DEBUG: original_booking ID: {original_booking.id}")
        print(f"DEBUG: target room_id for update: {room2_conflict.id}")
        print(f"DEBUG: target check_in_date for update: {today}")
        print(f"DEBUG: target check_out_date for update: {today + timedelta(days=3)}")
        print(f"DEBUG: conflicting_booking_on_room2 ID: {conflicting_booking_on_room2_for_scenario3.id}")
        print(f"DEBUG: conflicting_booking_on_room2 room_id: {conflicting_booking_on_room2_for_scenario3.room_id}")
        print(f"DEBUG: conflicting_booking_on_room2 check_in: {conflicting_booking_on_room2_for_scenario3.check_in_date}")
        print(f"DEBUG: conflicting_booking_on_room2 check_out: {conflicting_booking_on_room2_for_scenario3.check_out_date}")
        print(f"DEBUG: conflicting_booking_on_room2 status: {conflicting_booking_on_room2_for_scenario3.status}")
        # Force a query to see if the conflicting booking is found by the session directly
        found_conflicting = db_session.query(Booking).filter_by(id=conflicting_booking_on_room2_for_scenario3.id).first()
        print(f"DEBUG: Conflicting booking found directly by ID in session: {found_conflicting is not None}")
        if found_conflicting:
             print(f"DEBUG: Found conflicting details: id={found_conflicting.id}, room_id={found_conflicting.room_id}, in={found_conflicting.check_in_date}, out={found_conflicting.check_out_date}")

        # Call check_room_availability directly for debugging
        is_avail_debug = booking_service.check_room_availability(
            room_id=room2_conflict.id, 
            check_in_date=today, 
            check_out_date=today + timedelta(days=3), 
            booking_id=original_booking.id
        )
        print(f"DEBUG: check_room_availability for critical scenario returned: {is_avail_debug}")

        # Try to move the booking to room2 with the EXACT same dates as the conflicting booking
        # This should raise an error since rooms can't be double-booked
        with pytest.raises(RoomNotAvailableError):
            booking_service.update_booking(
                booking_id=original_booking.id,
                room_id=room2_conflict.id,
                check_in_date=today + timedelta(days=1),  # EXACTLY matches conflicting_booking_on_room2
                check_out_date=today + timedelta(days=3)  # EXACTLY matches conflicting_booking_on_room2
            ) 