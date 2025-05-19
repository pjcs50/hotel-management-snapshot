"""
Maintenance request model module.

This module defines the MaintenanceRequest model for managing room maintenance.
"""

from datetime import datetime
from sqlalchemy import ForeignKey, Index
from db import db
from app.models import BaseModel


class MaintenanceRequest(BaseModel):
    """
    MaintenanceRequest model for tracking room maintenance issues.
    
    Attributes:
        id: Primary key
        room_id: Foreign key to the Room model
        reported_by: Foreign key to the User model who reported the issue
        assigned_to: Foreign key to the User model assigned to fix the issue
        issue_type: Type of maintenance issue
        description: Detailed description of the issue
        status: Status of the maintenance request
        priority: Priority level of the request
        resolved_at: When the issue was resolved
        notes: Additional notes about the maintenance
        created_at: Timestamp when the request was created
        updated_at: Timestamp when the request was last updated
    """

    __tablename__ = 'maintenance_requests'

    room_id = db.Column(db.Integer, ForeignKey('rooms.id'), nullable=False)
    reported_by = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, ForeignKey('users.id'), nullable=True)
    issue_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, assigned, in_progress, resolved, closed
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    resolved_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    room = db.relationship('Room', backref='maintenance_requests')
    reporter = db.relationship('User', foreign_keys=[reported_by], backref='reported_maintenance')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_maintenance')
    
    # Add indexes for efficient querying
    __table_args__ = (
        Index('idx_maintenance_room', 'room_id'),
        Index('idx_maintenance_status', 'status'),
        Index('idx_maintenance_assigned', 'assigned_to'),
    )

    def __repr__(self):
        """Provide a readable representation of a MaintenanceRequest instance."""
        return f'<MaintenanceRequest id={self.id}, room_id={self.room_id}, status={self.status}>' 