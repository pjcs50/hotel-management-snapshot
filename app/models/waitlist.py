"""
Waitlist model module.

This module defines the Waitlist model for managing room waitlists.
"""

from datetime import datetime
from sqlalchemy import ForeignKey, Index
from db import db
from app.models import BaseModel


class Waitlist(BaseModel):
    """
    Waitlist model for managing room waitlists.
    
    Attributes:
        id: Primary key
        customer_id: Foreign key to the User model
        room_type_id: Foreign key to the RoomType model
        requested_date_start: Requested check-in date
        requested_date_end: Requested check-out date
        status: Status of the waitlist entry (waiting, promoted, expired)
        notes: Additional notes
        created_at: Timestamp when the waitlist entry was created
        updated_at: Timestamp when the waitlist entry was last updated
    """

    __tablename__ = 'waitlist'

    customer_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    room_type_id = db.Column(db.Integer, ForeignKey('room_types.id'), nullable=False)
    requested_date_start = db.Column(db.Date, nullable=False)
    requested_date_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='waiting')  # waiting, promoted, expired
    notification_sent = db.Column(db.Boolean, default=False)
    notification_sent_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    customer = db.relationship('User', backref='waitlist_entries')
    room_type = db.relationship('RoomType', backref='waitlist_entries')
    
    # Add indexes for efficient querying
    __table_args__ = (
        Index('idx_waitlist_dates', 'room_type_id', 'requested_date_start', 'requested_date_end'),
        Index('idx_waitlist_customer', 'customer_id'),
        Index('idx_waitlist_status', 'status'),
    )

    def __repr__(self):
        """Provide a readable representation of a Waitlist instance."""
        return f'<Waitlist id={self.id}, customer_id={self.customer_id}, room_type={self.room_type_id}, status={self.status}>' 