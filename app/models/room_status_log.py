"""
Room Status Log model module.

This module defines the RoomStatusLog model for tracking room status changes.
"""

from datetime import datetime
from db import db
from app.models import BaseModel


class RoomStatusLog(BaseModel):
    """
    RoomStatusLog model for tracking room status changes.
    
    Attributes:
        id: Primary key
        room_id: Foreign key to the Room model
        old_status: Previous room status
        new_status: New room status
        changed_by: Foreign key to the User model (who changed the status)
        change_time: Date and time of the status change
        booking_id: Optional foreign key to the Booking model
        notes: Additional notes about the status change
        created_at: Timestamp when the log was created
        updated_at: Timestamp when the log was last updated
    """

    __tablename__ = 'room_status_logs'

    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False, index=True)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    change_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    room = db.relationship('Room', back_populates='status_logs')
    user = db.relationship('User', back_populates='room_status_changes')
    booking = db.relationship('Booking', back_populates='room_status_changes')

    def __repr__(self):
        """Provide a readable representation of a RoomStatusLog instance."""
        return f'<RoomStatusLog {self.id}, Room {self.room_id}, {self.old_status} -> {self.new_status}>'
    
    @classmethod
    def log_status_change(cls, room_id, old_status, new_status, changed_by=None, booking_id=None, notes=None):
        """
        Log a room status change.
        
        Args:
            room_id: ID of the room
            old_status: Previous room status
            new_status: New room status
            changed_by: ID of the user changing the status
            booking_id: ID of the related booking, if applicable
            notes: Additional notes about the status change
            
        Returns:
            The created RoomStatusLog instance
        """
        log = cls(
            room_id=room_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            booking_id=booking_id,
            notes=notes
        )
        db.session.add(log)
        
        return log
    
    @classmethod
    def get_room_history(cls, room_id, limit=None):
        """
        Get the status change history for a room.
        
        Args:
            room_id: ID of the room
            limit: Maximum number of logs to return
            
        Returns:
            List of RoomStatusLog instances for the room
        """
        query = cls.query.filter_by(
            room_id=room_id
        ).order_by(cls.change_time.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    @classmethod
    def get_recent_changes(cls, limit=50):
        """
        Get recent room status changes.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of recent RoomStatusLog instances
        """
        return cls.query.order_by(
            cls.change_time.desc()
        ).limit(limit).all()
    
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the room status log
        """
        return {
            'id': self.id,
            'room_id': self.room_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'changed_by': self.changed_by,
            'change_time': self.change_time.isoformat() if self.change_time else None,
            'booking_id': self.booking_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 