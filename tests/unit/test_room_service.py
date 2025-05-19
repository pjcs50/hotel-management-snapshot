"""
Unit tests for the room service.

This module contains tests for the RoomService class.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.room_service import RoomService, DuplicateRoomNumberError
from app.models.room import Room
from app.models.room_type import RoomType


class TestRoomService:
    """Tests for the RoomService class."""
    
    def test_create_room_success(self, db_session):
        """Test creating a room successfully."""
        # Arrange
        mock_db_session = MagicMock()
        room_service = RoomService(mock_db_session)
        
        # Mock room type
        room_type = MagicMock(spec=RoomType)
        room_type.id = 1
        
        # Mock db queries
        with patch('app.models.room_type.RoomType.query') as mock_room_type_query:
            mock_room_type_query.get.return_value = room_type
            with patch('app.models.room.Room.query') as mock_room_query:
                mock_room_query.filter_by.return_value.first.return_value = None
                
                # Act
                result = room_service.create_room(
                    number="101",
                    room_type_id=1,
                    status=Room.STATUS_AVAILABLE
                )
                
                # Assert
                assert result is not None
                assert result.number == "101"
                assert result.room_type_id == 1
                assert result.status == Room.STATUS_AVAILABLE
                mock_db_session.add.assert_called_once()
                mock_db_session.commit.assert_called_once()
    
    def test_create_room_duplicate_number(self, db_session):
        """Test that creating a room with a duplicate number raises an error."""
        # Arrange
        room_service = RoomService(db_session)
        
        # Mock room type
        room_type = MagicMock(spec=RoomType)
        room_type.id = 1
        
        # Mock existing room
        existing_room = MagicMock(spec=Room)
        existing_room.number = "101"
        
        # Mock db queries
        with patch('app.models.room_type.RoomType.query') as mock_room_type_query:
            mock_room_type_query.get.return_value = room_type
            with patch('app.models.room.Room.query') as mock_room_query:
                mock_room_query.filter_by.return_value.first.return_value = existing_room
                
                # Act & Assert
                with pytest.raises(DuplicateRoomNumberError):
                    room_service.create_room(
                        number="101",
                        room_type_id=1,
                        status=Room.STATUS_AVAILABLE
                    )
    
    def test_create_room_invalid_room_type(self, db_session):
        """Test that creating a room with an invalid room type raises an error."""
        # Arrange
        room_service = RoomService(db_session)
        
        # Mock db queries - room type not found
        with patch('app.models.room_type.RoomType.query') as mock_room_type_query:
            mock_room_type_query.get.return_value = None
            
            # Act & Assert
            with pytest.raises(ValueError):
                room_service.create_room(
                    number="101",
                    room_type_id=999,  # Invalid ID
                    status=Room.STATUS_AVAILABLE
                )
    
    def test_update_room_success(self, db_session):
        """Test updating a room successfully."""
        # Arrange
        mock_db_session = MagicMock()
        room_service = RoomService(mock_db_session)
        
        # Mock room
        room = MagicMock(spec=Room)
        room.id = 1
        room.number = "101"
        
        # Mock db queries
        with patch('app.models.room.Room.query') as mock_room_query:
            mock_room_query.get.return_value = room
            mock_room_query.filter_by.return_value.first.return_value = None
            
            # Act
            result = room_service.update_room(
                room_id=1,
                number="102",
                status=Room.STATUS_MAINTENANCE
            )
            
            # Assert
            assert result is not None
            assert result.number == "102"
            assert result.status == Room.STATUS_MAINTENANCE
            mock_db_session.commit.assert_called_once()
    
    def test_update_room_not_found(self, db_session):
        """Test that updating a non-existent room raises an error."""
        # Arrange
        room_service = RoomService(db_session)
        
        # Mock db queries - room not found
        with patch('app.models.room.Room.query') as mock_room_query:
            mock_room_query.get.return_value = None
            
            # Act & Assert
            with pytest.raises(ValueError):
                room_service.update_room(
                    room_id=999,  # Invalid ID
                    number="102",
                    status=Room.STATUS_AVAILABLE
                )
    
    def test_change_room_status(self, db_session):
        """Test changing a room's status."""
        # Arrange
        mock_db_session = MagicMock()
        room_service = RoomService(mock_db_session)
        
        # Mock room
        room = MagicMock(spec=Room)
        room.id = 1
        room.status = Room.STATUS_AVAILABLE
        
        # Mock db queries
        with patch('app.models.room.Room.query') as mock_room_query:
            mock_room_query.get.return_value = room
            
            # Act
            result = room_service.change_room_status(
                room_id=1,
                new_status=Room.STATUS_OCCUPIED,
                user_id=1
            )
            
            # Assert
            assert result is not None
            room.change_status.assert_called_with(Room.STATUS_OCCUPIED, 1)
            mock_db_session.commit.assert_called_once()
    
    def test_mark_room_cleaned(self, db_session):
        """Test marking a room as cleaned."""
        # Arrange
        mock_db_session = MagicMock()
        room_service = RoomService(mock_db_session)
        
        # Mock room
        room = MagicMock(spec=Room)
        room.id = 1
        room.status = Room.STATUS_CLEANING
        
        # Mock db queries
        with patch('app.models.room.Room.query') as mock_room_query:
            mock_room_query.get.return_value = room
            
            # Act
            result = room_service.mark_room_cleaned(
                room_id=1,
                user_id=1
            )
            
            # Assert
            assert result is not None
            assert room.mark_as_cleaned.called
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once() 