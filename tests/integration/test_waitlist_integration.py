"""
Integration tests for the waitlist feature.

This module provides integration tests for the waitlist feature, testing
the interaction between models, services, and routes.
"""

import pytest
from datetime import datetime, timedelta
from app.services.waitlist_service import WaitlistService
from app.models.waitlist import Waitlist
from app.models.room_type import RoomType
from app.models.booking import Booking
from app.models.room import Room


@pytest.fixture
def room_type(db_session):
    """Create a room type for testing."""
    room_type = RoomType(
        name="Standard",
        description="Standard room",
        base_rate=100.00,
        capacity=2
    )
    db_session.add(room_type)
    db_session.commit()
    return room_type


@pytest.fixture
def room(db_session, room_type):
    """Create a room for testing."""
    room = Room(
        number="101",
        room_type_id=room_type.id,
        status="clean"
    )
    db_session.add(room)
    db_session.commit()
    return room


def test_waitlist_to_booking_flow(db_session, customer_user, room_type, room):
    """Test the full flow from waitlist to booking."""
    # Create waitlist service
    waitlist_service = WaitlistService(db_session)
    
    # 1. Add customer to waitlist
    start_date = datetime.now().date() + timedelta(days=7)
    end_date = start_date + timedelta(days=3)
    
    waitlist_entry = waitlist_service.add_to_waitlist(
        customer_id=customer_user.id,
        room_type_id=room_type.id,
        start_date=start_date,
        end_date=end_date,
        notes="Test waitlist to booking flow"
    )
    
    assert waitlist_entry.status == 'waiting'
    
    # 2. Create a booking with dates that match the waitlist request
    booking = Booking(
        customer_id=customer_user.id,
        room_id=room.id,
        check_in_date=start_date,
        check_out_date=end_date,
        status="confirmed",
        total_price=room_type.base_rate * 3  # 3 nights
    )
    db_session.add(booking)
    db_session.commit()
    
    # 3. Promote waitlist entry
    promoted_entry, _ = waitlist_service.promote_waitlist_entry(waitlist_entry.id)
    
    assert promoted_entry.status == 'promoted'
    assert "Promoted to booking" in promoted_entry.notes
    
    # In a real implementation, verify the booking is created correctly


def test_cancellation_notification_workflow(db_session, customer_user, room_type, room):
    """Test the workflow of cancelling a booking and notifying waitlisted customers."""
    # Create waitlist service
    waitlist_service = WaitlistService(db_session)
    
    # 1. Add customer to waitlist
    start_date = datetime.now().date() + timedelta(days=5)
    end_date = start_date + timedelta(days=2)
    
    waitlist_entry = waitlist_service.add_to_waitlist(
        customer_id=customer_user.id,
        room_type_id=room_type.id,
        start_date=start_date,
        end_date=end_date
    )
    
    # 2. Create a booking that overlaps with the waitlist request
    booking = Booking(
        customer_id=customer_user.id,  # Using same customer for simplicity
        room_id=room.id,
        check_in_date=start_date - timedelta(days=1),  # Starts 1 day earlier
        check_out_date=end_date + timedelta(days=1),   # Ends 1 day later
        status="confirmed",
        total_price=room_type.base_rate * 4  # 4 nights
    )
    db_session.add(booking)
    db_session.commit()
    
    # 3. Process cancellation
    notified_entries = waitlist_service.process_cancellation(booking.id)
    
    assert len(notified_entries) == 1
    assert notified_entries[0].id == waitlist_entry.id
    assert notified_entries[0].notification_sent is True
    
    # Verify the waitlist entry was updated with notification info
    updated_entry = waitlist_service.get_waitlist_entry(waitlist_entry.id)
    assert updated_entry.notification_sent is True
    assert updated_entry.notification_sent_at is not None


def test_expire_waitlist_entries(db_session, customer_user, room_type):
    """Test expiring waitlist entries."""
    # Create waitlist service
    waitlist_service = WaitlistService(db_session)
    
    # 1. Add customer to waitlist with dates in the past
    past_start_date = datetime.now().date() - timedelta(days=10)
    past_end_date = past_start_date + timedelta(days=3)
    
    past_entry = waitlist_service.add_to_waitlist(
        customer_id=customer_user.id,
        room_type_id=room_type.id,
        start_date=past_start_date,
        end_date=past_end_date,
        notes="Past dates entry"
    )
    
    # 2. Add another entry with future dates
    future_start_date = datetime.now().date() + timedelta(days=10)
    future_end_date = future_start_date + timedelta(days=3)
    
    future_entry = waitlist_service.add_to_waitlist(
        customer_id=customer_user.id,
        room_type_id=room_type.id,
        start_date=future_start_date,
        end_date=future_end_date,
        notes="Future dates entry"
    )
    
    # 3. Expire past entry
    updated_entry = waitlist_service.expire_waitlist_entry(
        past_entry.id, 
        "Dates have passed"
    )
    
    assert updated_entry.status == 'expired'
    assert "Dates have passed" in updated_entry.notes
    
    # 4. Verify only past entry is expired
    entries = waitlist_service.get_all_waitlist_entries()
    waiting_entries = [e for e in entries.items if e.status == 'waiting']
    expired_entries = [e for e in entries.items if e.status == 'expired']
    
    assert len(waiting_entries) == 1
    assert waiting_entries[0].id == future_entry.id
    
    assert len(expired_entries) == 1
    assert expired_entries[0].id == past_entry.id 