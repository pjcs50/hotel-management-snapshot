"""
Unit tests for Room model.

Tests room creation, status changes, and related functionality.
"""

import pytest
from datetime import datetime, timedelta

from app.models.room import Room
from app.models.room_type import RoomType
from app.models.room_status_log import RoomStatusLog


class TestRoomModel:
    """Test suite for Room model functionality."""

    def test_create_room(self, db_session):
        """Test basic room creation."""
        # Create a room type first
        room_type = RoomType(
            name="Standard_create",
            description="A standard room",
            base_rate=100.00,
            capacity=2
        )
        db_session.add(room_type)
        db_session.commit()
        
        # Create a room
        room = Room(
            number="101",
            room_type_id=room_type.id,
            status=Room.STATUS_AVAILABLE
        )
        
        db_session.add(room)
        db_session.commit()
        
        saved_room = Room.query.filter_by(number="101").first()
        
        assert saved_room is not None
        assert saved_room.number == "101"
        assert saved_room.status == Room.STATUS_AVAILABLE
        assert saved_room.room_type_id == room_type.id

    def test_room_status_change(self, db_session):
        """Test changing room status."""
        # Create a room type first
        room_type = RoomType(
            name="Deluxe_status",
            description="A deluxe room",
            base_rate=150.00,
            capacity=2
        )
        db_session.add(room_type)
        db_session.commit()
        
        # Create a room
        room = Room(
            number="202",
            room_type_id=room_type.id,
            status=Room.STATUS_AVAILABLE
        )
        
        db_session.add(room)
        db_session.commit()
        
        # Change status
        room.change_status(Room.STATUS_OCCUPIED, user_id=1)
        db_session.commit()
        
        # Check the room status
        updated_room = Room.query.filter_by(number="202").first()
        assert updated_room.status == Room.STATUS_OCCUPIED
        
        # Check that a log entry was created
        log_entry = RoomStatusLog.query.filter_by(room_id=room.id).first()
        assert log_entry is not None
        assert log_entry.old_status == Room.STATUS_AVAILABLE
        assert log_entry.new_status == Room.STATUS_OCCUPIED
        assert log_entry.changed_by == 1

    def test_invalid_room_status(self, db_session):
        """Test that invalid room status raises an error."""
        # Create a room type first
        room_type = RoomType(
            name="Suite_invalid_status",
            description="A suite",
            base_rate=200.00,
            capacity=4
        )
        db_session.add(room_type)
        db_session.commit()
        
        # Create a room
        room = Room(
            number="303",
            room_type_id=room_type.id,
            status=Room.STATUS_AVAILABLE
        )
        
        db_session.add(room)
        db_session.commit()
        
        # Try to change to an invalid status
        with pytest.raises(ValueError):
            room.change_status("Invalid Status")

    def test_mark_as_cleaned(self, db_session):
        """Test marking a room as cleaned."""
        # Create a room type first
        room_type = RoomType(
            name="Standard_cleaned",
            description="A standard room",
            base_rate=100.00,
            capacity=2
        )
        db_session.add(room_type)
        db_session.commit()
        
        # Create a room that needs cleaning
        room = Room(
            number="404",
            room_type_id=room_type.id,
            status=Room.STATUS_CLEANING
        )
        
        db_session.add(room)
        db_session.commit()
        
        # Mark the room as cleaned
        before_cleaning = datetime.utcnow()
        room.mark_as_cleaned()
        db_session.commit()
        after_cleaning = datetime.utcnow()
        
        # Check the room status and last_cleaned timestamp
        updated_room = Room.query.filter_by(number="404").first()
        assert updated_room.status == Room.STATUS_AVAILABLE
        assert updated_room.last_cleaned is not None
        assert before_cleaning <= updated_room.last_cleaned <= after_cleaning 