"""
Notification model module.

This module defines the Notification model for storing user notifications.
"""
from datetime import datetime
from sqlalchemy import Text # For db.Text
from db import db # Import the SQLAlchemy instance
from app.models import BaseModel # Import BaseModel

# Ensure User is imported for relationship, handle potential circularity if User also imports Notification
# from app.models.user import User # This might be tricky if User also imports Notification directly or via app.models

class Notification(BaseModel):
    __tablename__ = 'notifications'

    # 'id', 'created_at', 'updated_at' are inherited from BaseModel

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False) # Using db.Text for longer messages
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    type = db.Column(db.String(50), nullable=True)  # e.g., 'booking_update', 'profile_alert', 'system'
    link_url = db.Column(db.String(255), nullable=True) # Optional URL for the notification to link to

    # The relationship in the User model should be:
    # notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan", order_by="desc(Notification.created_at)")
    # So, Notification needs a 'user' relationship that back_populates 'notifications'
    user = db.relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, message='{self.message[:20]}...', is_read={self.is_read})>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'type': self.type,
            'link_url': self.link_url
        }

# Reminder for User model (app/models/user.py):
# Ensure 'from sqlalchemy import desc'
# Ensure 'from app.models.notification import Notification' (or handle potential circularity)
# notifications = db.relationship(
#     "Notification",
#     back_populates="user",
#     cascade="all, delete-orphan",
#     order_by="desc(Notification.created_at)" # or desc(Notification.created_at) if imported directly
# ) 