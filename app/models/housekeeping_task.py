"""
Housekeeping task model module.

This module defines the HousekeepingTask model for managing housekeeping tasks.
"""

from datetime import datetime
from sqlalchemy import ForeignKey, Index
from db import db
from app.models import BaseModel


class HousekeepingTask(BaseModel):
    """
    HousekeepingTask model for tracking housekeeping tasks.
    
    Attributes:
        id: Primary key
        room_id: Foreign key to the Room model
        assigned_to: Foreign key to the User model assigned to the task
        task_type: Type of housekeeping task
        description: Additional description of the task
        status: Status of the task
        priority: Priority level of the task
        due_date: When the task should be completed
        completed_at: When the task was completed
        notes: Additional notes about the task
        created_at: Timestamp when the task was created
        updated_at: Timestamp when the task was last updated
    """

    __tablename__ = 'housekeeping_tasks'

    room_id = db.Column(db.Integer, ForeignKey('rooms.id'), nullable=False)
    assigned_to = db.Column(db.Integer, ForeignKey('users.id'), nullable=True)
    task_type = db.Column(db.String(50), nullable=False)  # regular_cleaning, deep_cleaning, turnover, etc.
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, verified
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    due_date = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.Integer, ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    room = db.relationship('Room', backref='housekeeping_tasks')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tasks')
    verifier = db.relationship('User', foreign_keys=[verified_by], backref='verified_tasks')
    
    # Add indexes for efficient querying
    __table_args__ = (
        Index('idx_housekeeping_room', 'room_id'),
        Index('idx_housekeeping_status', 'status'),
        Index('idx_housekeeping_assigned', 'assigned_to'),
        Index('idx_housekeeping_due_date', 'due_date'),
    )

    def __repr__(self):
        """Provide a readable representation of a HousekeepingTask instance."""
        return f'<HousekeepingTask id={self.id}, room_id={self.room_id}, status={self.status}>' 