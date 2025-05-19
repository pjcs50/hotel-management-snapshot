"""
Room service module.

This module provides services for room management, including CRUD operations,
room status tracking, and housekeeping management.
"""

from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models.room import Room
from app.models.room_type import RoomType
from app.models.room_status_log import RoomStatusLog


class DuplicateRoomNumberError(Exception):
    """Exception raised when attempting to create a room with an existing number."""
    pass


class RoomService:
    """
    Service for room management.
    
    This service handles room CRUD operations, status changes, and housekeeping.
    """

    def __init__(self, db_session):
        """Initialize the service with a database session."""
        self.db_session = db_session

    def create_room(self, number, room_type_id, status=Room.STATUS_AVAILABLE):
        """
        Create a new room.
        
        Args:
            number: Room number (must be unique)
            room_type_id: ID of the room type
            status: Initial room status (default: Available)
            
        Returns:
            The newly created room
            
        Raises:
            DuplicateRoomNumberError: If a room with the given number already exists
            ValueError: If the room type does not exist
        """
        # Check if room type exists
        room_type = RoomType.query.get(room_type_id)
        if not room_type:
            raise ValueError(f"Room type with ID {room_type_id} does not exist")
        
        # Check for existing room number
        if Room.query.filter_by(number=number).first():
            raise DuplicateRoomNumberError(f"Room with number {number} already exists")
        
        # Create new room
        room = Room(
            number=number,
            room_type_id=room_type_id,
            status=status
        )
        
        try:
            self.db_session.add(room)
            self.db_session.commit()
            return room
        except IntegrityError:
            self.db_session.rollback()
            # Final check in case of race condition
            if Room.query.filter_by(number=number).first():
                raise DuplicateRoomNumberError(f"Room with number {number} already exists")
            raise  # Re-raise if it's another kind of integrity error

    def update_room(self, room_id, **kwargs):
        """
        Update a room.
        
        Args:
            room_id: ID of the room to update
            **kwargs: Attributes to update
            
        Returns:
            The updated room
            
        Raises:
            ValueError: If the room does not exist
            DuplicateRoomNumberError: If trying to update to an existing room number
        """
        room = Room.query.get(room_id)
        if not room:
            raise ValueError(f"Room with ID {room_id} does not exist")
        
        # Check if trying to update room number to an existing one
        if 'number' in kwargs and kwargs['number'] != room.number:
            existing_room = Room.query.filter_by(number=kwargs['number']).first()
            if existing_room:
                raise DuplicateRoomNumberError(f"Room with number {kwargs['number']} already exists")
        
        # Update room attributes
        for key, value in kwargs.items():
            if hasattr(room, key):
                setattr(room, key, value)
        
        try:
            self.db_session.commit()
            return room
        except IntegrityError:
            self.db_session.rollback()
            # Check if it's a duplicate room number
            if 'number' in kwargs:
                existing_room = Room.query.filter_by(number=kwargs['number']).first()
                if existing_room and existing_room.id != room_id:
                    raise DuplicateRoomNumberError(f"Room with number {kwargs['number']} already exists")
            raise  # Re-raise if it's another kind of integrity error

    def change_room_status(self, room_id, new_status, user_id):
        """
        Change a room's status.
        
        Args:
            room_id: ID of the room to update
            new_status: New room status
            user_id: ID of the user changing the status
            
        Returns:
            The updated room
            
        Raises:
            ValueError: If the room does not exist or the status is invalid
        """
        room = Room.query.get(room_id)
        if not room:
            raise ValueError(f"Room with ID {room_id} does not exist")
        
        # Change status and create log entry
        room.change_status(new_status, user_id)
        
        self.db_session.commit()
        return room

    def mark_room_cleaned(self, room_id, user_id):
        """
        Mark a room as cleaned.
        
        Args:
            room_id: ID of the room to mark as cleaned
            user_id: ID of the user marking the room as cleaned
            
        Returns:
            The updated room
            
        Raises:
            ValueError: If the room does not exist
        """
        room = Room.query.get(room_id)
        if not room:
            raise ValueError(f"Room with ID {room_id} does not exist")
        
        # Save old status for logging
        old_status = room.status
        
        # Mark as cleaned (sets status to Available)
        room.mark_as_cleaned()
        
        # Create log entry
        log = RoomStatusLog(
            room_id=room.id,
            old_status=old_status,
            new_status=room.status,
            changed_by=user_id
        )
        
        self.db_session.add(log)
        self.db_session.commit()
        
        return room

    def get_rooms_by_status(self, status):
        """
        Get all rooms with a specific status.
        
        Args:
            status: Room status to filter by
            
        Returns:
            List of rooms with the specified status
        """
        return Room.query.filter_by(status=status).all()

    def get_rooms_needing_cleaning(self):
        """
        Get all rooms that need cleaning.
        
        Returns:
            List of rooms that need cleaning
        """
        return self.get_rooms_by_status(Room.STATUS_CLEANING)

    def get_available_rooms(self):
        """
        Get all available rooms.
        
        Returns:
            List of available rooms
        """
        return self.get_rooms_by_status(Room.STATUS_AVAILABLE) 