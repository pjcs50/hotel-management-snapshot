"""
Room model module.

This module defines the Room model for hotel room management.
"""

from datetime import datetime
from db import db
from app.models import BaseModel


class Room(BaseModel):
    """
    Room model for hotel room management.
    
    Attributes:
        id: Primary key
        number: Room number (unique)
        room_type_id: Foreign key to the RoomType model
        status: Current room status (Available/Booked/Occupied/Needs Cleaning)
        last_cleaned: Timestamp when the room was last cleaned
        created_at: Timestamp when the room was created
        updated_at: Timestamp when the room was last updated
    """

    __tablename__ = 'rooms'

    # Room status constants
    STATUS_AVAILABLE = 'Available'
    STATUS_BOOKED = 'Booked'
    STATUS_OCCUPIED = 'Occupied'
    STATUS_CLEANING = 'Needs Cleaning'
    STATUS_MAINTENANCE = 'Under Maintenance'

    # Status choices for validation
    STATUS_CHOICES = [
        STATUS_AVAILABLE,
        STATUS_BOOKED,
        STATUS_OCCUPIED,
        STATUS_CLEANING,
        STATUS_MAINTENANCE
    ]

    number = db.Column(db.String(10), nullable=False, unique=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'), nullable=False)
    status = db.Column(
        db.String(20), 
        nullable=False, 
        default=STATUS_AVAILABLE, 
        index=True
    )
    last_cleaned = db.Column(db.DateTime, nullable=True)

    # Relationships
    room_type = db.relationship('RoomType', backref='rooms')

    def __repr__(self):
        """Provide a readable representation of a Room instance."""
        return f'<Room {self.number}, {self.status}>'
    
    def mark_as_cleaned(self):
        """Mark the room as cleaned and update last_cleaned timestamp."""
        self.status = self.STATUS_AVAILABLE
        self.last_cleaned = datetime.utcnow()
        return self
    
    def change_status(self, new_status, user_id=None):
        """
        Change the room status and log the change.
        
        Args:
            new_status: New room status
            user_id: ID of the user changing the status
            
        Returns:
            The updated room
            
        Raises:
            ValueError: If the new status is not valid
        """
        if new_status not in self.STATUS_CHOICES:
            raise ValueError(f"Invalid room status: {new_status}")
        
        old_status = self.status
        self.status = new_status
        
        # Log the status change
        if user_id is not None:
            from app.models.room_status_log import RoomStatusLog
            log = RoomStatusLog(
                room_id=self.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=user_id
            )
            db.session.add(log)
        
        return self
        
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the room
        """
        return {
            'id': self.id,
            'number': self.number,
            'room_type_id': self.room_type_id,
            'room_type': self.room_type.to_dict() if self.room_type else None,
            'status': self.status,
            'last_cleaned': self.last_cleaned.isoformat() if self.last_cleaned else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 