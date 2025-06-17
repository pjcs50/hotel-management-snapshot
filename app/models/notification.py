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
    
    # Required fields based on database schema
    priority = db.Column(db.String(8), nullable=False, default='normal')  # low, normal, high, urgent
    category = db.Column(db.String(11), nullable=False, default='general')  # general, booking, system, etc.
    channels = db.Column(db.String(100), nullable=False, default='web')  # web, email, sms, push
    template_id = db.Column(db.String(50), nullable=True)
    template_data = db.Column(db.JSON, nullable=True)
    escalation_level = db.Column(db.Integer, nullable=False, default=0)
    escalated_at = db.Column(db.DateTime, nullable=True)
    escalated_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    requires_action = db.Column(db.Boolean, nullable=False, default=False)
    action_taken = db.Column(db.Boolean, nullable=False, default=False)
    action_taken_at = db.Column(db.DateTime, nullable=True)
    action_taken_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    delivery_attempts = db.Column(db.Integer, nullable=False, default=0)
    delivery_status = db.Column(db.String(20), nullable=False, default='pending')  # pending, delivered, failed
    expires_at = db.Column(db.DateTime, nullable=True)
    auto_dismiss = db.Column(db.Boolean, nullable=False, default=False)
    related_entity_type = db.Column(db.String(50), nullable=True)
    related_entity_id = db.Column(db.Integer, nullable=True)

    # The relationship in the User model should be:
    # notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan", order_by="desc(Notification.created_at)")
    # So, Notification needs a 'user' relationship that back_populates 'notifications'
    user = db.relationship("User", foreign_keys=[user_id], back_populates="notifications")
    escalated_to_user = db.relationship("User", foreign_keys=[escalated_to])
    action_taken_by_user = db.relationship("User", foreign_keys=[action_taken_by])

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
            'link_url': self.link_url,
            'priority': self.priority,
            'category': self.category,
            'channels': self.channels,
            'template_id': self.template_id,
            'template_data': self.template_data,
            'escalation_level': self.escalation_level,
            'escalated_at': self.escalated_at.isoformat() if self.escalated_at else None,
            'escalated_to': self.escalated_to,
            'requires_action': self.requires_action,
            'action_taken': self.action_taken,
            'action_taken_at': self.action_taken_at.isoformat() if self.action_taken_at else None,
            'action_taken_by': self.action_taken_by,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'delivery_attempts': self.delivery_attempts,
            'delivery_status': self.delivery_status,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'auto_dismiss': self.auto_dismiss,
            'related_entity_type': self.related_entity_type,
            'related_entity_id': self.related_entity_id
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