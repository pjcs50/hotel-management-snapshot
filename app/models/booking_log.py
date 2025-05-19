"""
Booking Log model module.

This module defines the BookingLog model for tracking booking-related activities.
"""

from datetime import datetime
from db import db
from app.models import BaseModel


class BookingLog(BaseModel):
    """
    BookingLog model for tracking booking-related activities.
    
    Attributes:
        id: Primary key
        booking_id: Foreign key to the Booking model
        action: Type of action (e.g., create, check_in, check_out, cancel)
        action_time: Date and time of the action
        user_id: Foreign key to the User model (who performed the action)
        notes: Additional notes about the action
        created_at: Timestamp when the log was created
        updated_at: Timestamp when the log was last updated
    """

    __tablename__ = 'booking_logs'

    # Action type constants
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_CHECK_IN = 'check_in'
    ACTION_CHECK_OUT = 'check_out'
    ACTION_CANCEL = 'cancel'
    ACTION_PAYMENT = 'payment'
    ACTION_REFUND = 'refund'
    ACTION_NO_SHOW = 'no_show'
    ACTION_ROOM_CHANGE = 'room_change'
    ACTION_NOTE = 'note'
    
    # Action type choices for validation
    ACTION_CHOICES = [
        ACTION_CREATE,
        ACTION_UPDATE,
        ACTION_CHECK_IN,
        ACTION_CHECK_OUT,
        ACTION_CANCEL,
        ACTION_PAYMENT,
        ACTION_REFUND,
        ACTION_NO_SHOW,
        ACTION_ROOM_CHANGE,
        ACTION_NOTE
    ]

    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False)
    action_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Additional context
    prev_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=True)
    prev_room_id = db.Column(db.Integer, nullable=True)
    new_room_id = db.Column(db.Integer, nullable=True)
    amount = db.Column(db.Float, nullable=True)  # For payment/refund actions
    reference = db.Column(db.String(100), nullable=True)  # For payment/refund actions

    # Relationships
    booking = db.relationship('Booking', backref='logs')
    user = db.relationship('User', backref='booking_logs')

    def __repr__(self):
        """Provide a readable representation of a BookingLog instance."""
        return f'<BookingLog {self.id}, Booking {self.booking_id}, {self.action}>'
    
    @classmethod
    def log_booking_action(cls, booking_id, action, user_id=None, notes=None, **kwargs):
        """
        Log a booking action.
        
        Args:
            booking_id: ID of the booking
            action: Type of action
            user_id: ID of the user performing the action
            notes: Additional notes about the action
            **kwargs: Additional fields to include in the log
            
        Returns:
            The created BookingLog instance
        """
        log = cls(
            booking_id=booking_id,
            action=action,
            action_time=datetime.utcnow(),
            user_id=user_id,
            notes=notes,
            **kwargs
        )
        db.session.add(log)
        
        return log
    
    @classmethod
    def get_booking_history(cls, booking_id):
        """
        Get the activity history for a booking.
        
        Args:
            booking_id: ID of the booking
            
        Returns:
            List of BookingLog instances for the booking
        """
        return cls.query.filter_by(
            booking_id=booking_id
        ).order_by(cls.action_time.desc()).all()
    
    @classmethod
    def get_recent_activity(cls, limit=50):
        """
        Get recent booking activity.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of recent BookingLog instances
        """
        return cls.query.order_by(
            cls.action_time.desc()
        ).limit(limit).all()
    
    @classmethod
    def get_user_activity(cls, user_id, limit=50):
        """
        Get booking activity for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of logs to return
            
        Returns:
            List of BookingLog instances for the user
        """
        return cls.query.filter_by(
            user_id=user_id
        ).order_by(cls.action_time.desc()).limit(limit).all()
    
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the booking log
        """
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'action': self.action,
            'action_time': self.action_time.isoformat() if self.action_time else None,
            'user_id': self.user_id,
            'notes': self.notes,
            'prev_status': self.prev_status,
            'new_status': self.new_status,
            'prev_room_id': self.prev_room_id,
            'new_room_id': self.new_room_id,
            'amount': self.amount,
            'reference': self.reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 