"""
Test module for WaitlistService.

This module provides unit tests for the waitlist service.
"""

import pytest
from datetime import datetime, timedelta
from app.services.waitlist_service import WaitlistService
from app.models.waitlist import Waitlist
from app.models.room_type import RoomType
from app.models.user import User
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


@pytest.fixture
def waitlist_service(db_session):
    """Create a waitlist service instance for testing."""
    return WaitlistService(db_session)


@pytest.fixture
def customer(db_session):
    """Create a customer user for testing."""
    user = User(
        username="waitlist_customer",
        email="waitlist_customer@example.com",
        role="customer",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def waitlist_entry(db_session, customer, room_type):
    """Create a waitlist entry for testing."""
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=3)
    entry = Waitlist(
        customer_id=customer.id,
        room_type_id=room_type.id,
        requested_date_start=start_date,
        requested_date_end=end_date,
        status='waiting',
        notes="Test waitlist entry"
    )
    db_session.add(entry)
    db_session.commit()
    return entry


class TestWaitlistService:
    """Test class for WaitlistService."""

    def test_get_all_waitlist_entries(self, waitlist_service, waitlist_entry):
        """Test getting all waitlist entries."""
        # Test without filters
        result = waitlist_service.get_all_waitlist_entries()
        assert result.total == 1
        assert result.items[0].id == waitlist_entry.id

        # Test with status filter
        result = waitlist_service.get_all_waitlist_entries(status='waiting')
        assert result.total == 1
        assert result.items[0].id == waitlist_entry.id

        # Test with non-matching status filter
        result = waitlist_service.get_all_waitlist_entries(status='expired')
        assert result.total == 0

    def test_get_waitlist_entry(self, waitlist_service, waitlist_entry):
        """Test getting a waitlist entry by ID."""
        entry = waitlist_service.get_waitlist_entry(waitlist_entry.id)
        assert entry is not None
        assert entry.id == waitlist_entry.id
        assert entry.customer_id == waitlist_entry.customer_id
        assert entry.room_type_id == waitlist_entry.room_type_id

        # Test with non-existing ID
        entry = waitlist_service.get_waitlist_entry(9999)
        assert entry is None

    def test_add_to_waitlist(self, waitlist_service, customer, room_type):
        """Test adding a customer to the waitlist."""
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=2)
        
        # Add to waitlist
        entry = waitlist_service.add_to_waitlist(
            customer_id=customer.id,
            room_type_id=room_type.id,
            start_date=start_date,
            end_date=end_date,
            notes="New waitlist entry"
        )
        
        assert entry is not None
        assert entry.customer_id == customer.id
        assert entry.room_type_id == room_type.id
        assert entry.requested_date_start == start_date
        assert entry.requested_date_end == end_date
        assert entry.status == 'waiting'
        assert entry.notes == "New waitlist entry"

        # Test adding duplicate entry (should raise ValueError)
        with pytest.raises(ValueError):
            waitlist_service.add_to_waitlist(
                customer_id=customer.id,
                room_type_id=room_type.id,
                start_date=start_date,
                end_date=end_date
            )

    def test_update_waitlist_entry(self, waitlist_service, waitlist_entry):
        """Test updating a waitlist entry."""
        # Update status
        updated_entry = waitlist_service.update_waitlist_entry(
            waitlist_entry.id, 
            {'status': 'expired', 'notes': 'Expired by test'}
        )
        
        assert updated_entry is not None
        assert updated_entry.status == 'expired'
        assert updated_entry.notes == 'Expired by test'

        # Test with non-existing ID
        updated_entry = waitlist_service.update_waitlist_entry(9999, {'status': 'expired'})
        assert updated_entry is None

    def test_delete_waitlist_entry(self, waitlist_service, waitlist_entry):
        """Test deleting a waitlist entry."""
        # Delete entry
        result = waitlist_service.delete_waitlist_entry(waitlist_entry.id)
        assert result is True
        
        # Verify it's deleted
        entry = waitlist_service.get_waitlist_entry(waitlist_entry.id)
        assert entry is None

        # Test deleting non-existing entry
        result = waitlist_service.delete_waitlist_entry(9999)
        assert result is False

    def test_find_matching_waitlist_entries(self, waitlist_service, waitlist_entry, room_type):
        """Test finding waitlist entries matching available dates."""
        available_start = waitlist_entry.requested_date_start - timedelta(days=1)
        available_end = waitlist_entry.requested_date_end + timedelta(days=1)
        
        # Find matching entries
        matches = waitlist_service.find_matching_waitlist_entries(
            room_type_id=room_type.id,
            available_date_start=available_start,
            available_date_end=available_end
        )
        
        assert len(matches) == 1
        assert matches[0].id == waitlist_entry.id

        # Test with non-matching dates
        non_matching_start = waitlist_entry.requested_date_end + timedelta(days=1)
        non_matching_end = non_matching_start + timedelta(days=3)
        
        matches = waitlist_service.find_matching_waitlist_entries(
            room_type_id=room_type.id,
            available_date_start=non_matching_start,
            available_date_end=non_matching_end
        )
        
        assert len(matches) == 0

    def test_process_cancellation(self, waitlist_service, waitlist_entry, db_session, room, customer):
        """Test processing a cancellation and notifying waitlisted customers."""
        # Create a booking that matches the waitlist entry
        booking = Booking(
            customer_id=customer.id,
            room_id=room.id,
            check_in_date=waitlist_entry.requested_date_start,
            check_out_date=waitlist_entry.requested_date_end,
            status="confirmed"
        )
        db_session.add(booking)
        db_session.commit()
        
        # Process cancellation
        notified_entries = waitlist_service.process_cancellation(booking.id)
        
        assert len(notified_entries) == 1
        assert notified_entries[0].id == waitlist_entry.id
        assert notified_entries[0].notification_sent is True

    def test_promote_waitlist_entry(self, waitlist_service, waitlist_entry):
        """Test promoting a waitlist entry to a booking."""
        # Promote entry
        entry, booking = waitlist_service.promote_waitlist_entry(waitlist_entry.id)
        
        assert entry is not None
        assert entry.status == 'promoted'
        assert "Promoted to booking" in entry.notes
        
        # Note: In this implementation, booking is None since we don't actually create a booking
        # In a real implementation, we would verify the booking was created correctly

    def test_expire_waitlist_entry(self, waitlist_service, waitlist_entry):
        """Test marking a waitlist entry as expired."""
        # Expire entry
        reason = "No longer needed"
        entry = waitlist_service.expire_waitlist_entry(waitlist_entry.id, reason)
        
        assert entry is not None
        assert entry.status == 'expired'
        assert reason in entry.notes

    def test_get_waitlist_counts_by_room_type(self, waitlist_service, waitlist_entry, room_type):
        """Test getting counts of waiting entries grouped by room type."""
        # Get counts
        counts = waitlist_service.get_waitlist_counts_by_room_type()
        
        assert room_type.name in counts
        assert counts[room_type.name] == 1 