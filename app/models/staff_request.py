"""
Staff Request model.

This module contains the model definition for staff appointment requests.
"""

from datetime import datetime
from sqlalchemy import ForeignKey, Text
from db import db


class StaffRequest(db.Model):
    """Model representing a request to become staff."""

    __tablename__ = 'staff_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    role_requested = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, denied
    notes = db.Column(Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    handled_at = db.Column(db.DateTime, nullable=True)
    handled_by = db.Column(db.Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='staff_requests')
    processor = db.relationship('User', foreign_keys=[handled_by], backref='processed_requests')

    def __repr__(self):
        """Return a helpful representation of this instance."""
        return f"<StaffRequest id={self.id} user_id={self.user_id} role={self.role_requested} status={self.status}>" 