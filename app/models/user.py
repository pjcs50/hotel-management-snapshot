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

    # Relationships with proper cascade settings
    customer_profile = db.relationship(
        'Customer', 
        back_populates='user', 
        uselist=False, 
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    notifications = db.relationship(
        "Notification", 
        back_populates="user", 
        cascade="all, delete-orphan", 
        order_by="desc(Notification.created_at)",
        passive_deletes=True
    )
    
    # Staff-related relationships
    staff_requests = db.relationship(
        'StaffRequest',
        foreign_keys='StaffRequest.user_id',
        back_populates='user',
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    processed_requests = db.relationship(
        'StaffRequest',
        foreign_keys='StaffRequest.handled_by',
        back_populates='processor',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    # Booking-related relationships
    cancelled_bookings = db.relationship(
        'Booking',
        foreign_keys='Booking.cancelled_by',
        back_populates='cancelling_user',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    # Payment-related relationships
    processed_payments = db.relationship(
        'Payment',
        foreign_keys='Payment.processed_by',
        back_populates='processor',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    refunded_payments = db.relationship(
        'Payment',
        foreign_keys='Payment.refunded_by',
        back_populates='refunder',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    # Room and housekeeping relationships
    room_status_changes = db.relationship(
        'RoomStatusLog',
        foreign_keys='RoomStatusLog.changed_by',
        back_populates='user',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    assigned_tasks = db.relationship(
        'HousekeepingTask',
        foreign_keys='HousekeepingTask.assigned_to',
        back_populates='assignee',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    verified_tasks = db.relationship(
        'HousekeepingTask',
        foreign_keys='HousekeepingTask.verified_by',
        back_populates='verifier',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    # Maintenance relationships
    reported_maintenance = db.relationship(
        'MaintenanceRequest',
        foreign_keys='MaintenanceRequest.reported_by',
        back_populates='reporter',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    assigned_maintenance = db.relationship(
        'MaintenanceRequest',
        foreign_keys='MaintenanceRequest.assigned_to',
        back_populates='assignee',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    # Loyalty relationships
    loyalty_adjustments = db.relationship(
        'LoyaltyLedger',
        foreign_keys='LoyaltyLedger.staff_id',
        back_populates='staff',
        cascade="save-update, merge",
        passive_deletes=True
    )

    def __repr__(self):
        """Provide a readable representation of a User instance."""
        return f'<User {self.username}, {self.role}>'

    def set_password(self, password):
        """Hash and store a password with enhanced security validation."""
        from app.utils.password_security import PasswordManager, PasswordStrengthError
        
        password_manager = PasswordManager()
        
        try:
            # Validate and hash password with enhanced security
            result = password_manager.validate_and_hash(
                password, 
                username=self.username,
                user_data={'email': self.email}
            )
            self.password_hash = result['password_hash']
        except PasswordStrengthError as e:
            raise ValueError(f"Password validation failed: {str(e)}")
        except Exception as e:
            raise ValueError(f"Password security error: {str(e)}")

    def check_password(self, password):
        """Check if a password matches the stored hash with rate limiting."""
        from app.utils.password_security import PasswordManager, PasswordRateLimitError
        
        password_manager = PasswordManager()
        
        try:
            # Check password with rate limiting protection
            return password_manager.check_password_with_rate_limit(
                password, 
                self.password_hash, 
                user_id=self.id
            )
        except PasswordRateLimitError:
            # Re-raise rate limit errors for proper handling
            raise
        except Exception as e:
            # Log other errors but don't reveal details
            from flask import current_app
            if current_app:
                current_app.logger.error(f"Password check error for user {self.id}: {e}")
            return False

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