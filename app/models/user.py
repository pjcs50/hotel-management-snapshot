"""
User model module.

This module defines the User model for authentication and authorization.
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import desc

from db import db
from app.models import BaseModel
from app.models.notification import Notification


class User(BaseModel, UserMixin):
    """
    User model for authentication and authorization.
    
    Attributes:
        id: Primary key
        username: Unique username
        email: Unique email address
        password_hash: Hashed password
        role: User role (customer, receptionist, manager, housekeeping, admin)
        role_requested: Role requested by user during registration (for staff)
        is_active: Whether the user account is active
        created_at: Timestamp when the user was created
        updated_at: Timestamp when the user was last updated
    """

    __tablename__ = 'users'

    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer', index=True)
    role_requested = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    customer_profile = db.relationship('Customer', back_populates='user', uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan", order_by="desc(Notification.created_at)")

    def __repr__(self):
        """Provide a readable representation of a User instance."""
        return f'<User {self.username}, {self.role}>'

    def set_password(self, password):
        """Hash and store a password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if a password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_staff(self):
        """Check if the user is a staff member."""
        return self.role in ['receptionist', 'manager', 'housekeeping', 'admin']

    @property
    def is_admin(self):
        """Check if the user is an admin."""
        return self.role == 'admin'
    
    def has_role(self, role):
        """Check if the user has a specific role."""
        if isinstance(role, str):
            return self.role == role
        return self.role in role 