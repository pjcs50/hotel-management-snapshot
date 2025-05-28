"""
User service module.

This module provides services for user management, including registration,
authentication, and authorization.
"""

from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from sqlalchemy import select

from app.models.user import User
from app.models.staff_request import StaffRequest


class DuplicateEmailError(Exception):
    """Exception raised when attempting to register with an existing email."""
    pass


class DuplicateUsernameError(Exception):
    """Exception raised when attempting to register with an existing username."""
    pass


class UserService:
    """
    Service for user management.
    
    This service handles user registration, authentication, and authorization.
    """

    def __init__(self, db_session):
        """Initialize the service with a database session."""
        self.db_session = db_session

    def change_password(self, user_id, current_password, new_password):
        """
        Change a user's password.

        Args:
            user_id: The ID of the user.
            current_password: The user's current password.
            new_password: The new password to set.

        Returns:
            True if the password was changed successfully, False otherwise.

        Raises:
            ValueError: If the user is not found or current password does not match.
        """
        user = self.db_session.get(User, user_id)
        if not user:
            raise ValueError("User not found.")

        if not user.check_password(current_password):
            raise ValueError("Current password does not match.")

        user.set_password(new_password)
        try:
            self.db_session.commit()
            return True
        except IntegrityError:
            self.db_session.rollback()
            raise # Re-raise for further handling if necessary
            
    def create_user(self, username, email, password, role="customer"):
        """
        Create a new user.
        
        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password to hash
            role: User role (default: customer)
            
        Returns:
            The newly created user
            
        Raises:
            DuplicateEmailError: If a user with the given email already exists
            DuplicateUsernameError: If a user with the given username already exists
        """
        # Check for existing email or username
        if self.db_session.execute(select(User).filter_by(email=email)).scalar_one_or_none():
            raise DuplicateEmailError(f"User with email {email} already exists")
        
        if self.db_session.execute(select(User).filter_by(username=username)).scalar_one_or_none():
            raise DuplicateUsernameError(f"User with username {username} already exists")
        
        # Create new user
        user = User(
            username=username,
            email=email,
            role=role
        )
        user.set_password(password)
        
        try:
            self.db_session.add(user)
            self.db_session.commit()
            return user
        except IntegrityError:
            self.db_session.rollback()
            # Final check in case of race condition
            if self.db_session.execute(select(User).filter_by(email=email)).scalar_one_or_none():
                raise DuplicateEmailError(f"User with email {email} already exists")
            if self.db_session.execute(select(User).filter_by(username=username)).scalar_one_or_none():
                raise DuplicateUsernameError(f"User with username {username} already exists")
            raise  # Re-raise if it's another kind of integrity error
    
    def create_staff(self, username, email, password, role_requested):
        """
        Create a staff user with pending status.
        
        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password to hash
            role_requested: Role requested by the user
            
        Returns:
            The newly created user
            
        Raises:
            DuplicateEmailError: If a user with the given email already exists
            DuplicateUsernameError: If a user with the given username already exists
        """
        # Start a transaction
        transaction = self.db_session.begin_nested()
        
        try:
            # Create inactive user with temporary role
            user = self.create_user(
                username=username,
                email=email,
                password=password,
                role="pending"  # Temporary role
            )
        
            # Set user as inactive and record requested role
            user.is_active = False
            user.role_requested = role_requested
        
            # Create staff request - don't set create_at as it has a default value
            staff_request = StaffRequest(
                user_id=user.id,
                role_requested=role_requested,
                status="pending",
                notes="Staff registration request"
            )
        
            self.db_session.add(staff_request)
            self.db_session.commit()
        
            return user
            
        except Exception as e:
            self.db_session.rollback()
            
            # Re-raise specific exceptions for the calling code to handle
            if isinstance(e, (DuplicateEmailError, DuplicateUsernameError)):
                raise
            
            # Log the error and raise a user-friendly exception
            print(f"Error creating staff account: {str(e)}")
            raise Exception(f"Failed to create staff account: {str(e)}")
    
    def approve_staff_request(self, request_id, admin_user_id, notes=None):
        """
        Approve a staff request.
        
        Args:
            request_id: ID of the staff request
            admin_user_id: ID of the admin user approving the request
            notes: Optional notes about the approval
            
        Returns:
            The updated staff request
        """
        try:
            # Start a transaction
            self.db_session.begin_nested()
            
            request = self.db_session.get(StaffRequest, request_id)
            if not request:
                raise ValueError(f"Staff request with ID {request_id} not found")
            
            request.status = "approved"
            request.handled_at = datetime.now(timezone.utc)
            request.handled_by = admin_user_id
            if notes:
                request.notes = notes
            
            user = self.db_session.get(User, request.user_id)
            if not user:
                raise ValueError(f"User with ID {request.user_id} not found")
                
            user.role = request.role_requested
            user.role_requested = None
            user.is_active = True
            
            self.db_session.commit()
            return request
        
        except Exception as e:
            self.db_session.rollback()
            raise Exception(f"Failed to approve staff request: {str(e)}")
    
    def deny_staff_request(self, request_id, admin_user_id, notes=None):
        """
        Deny a staff request.
        
        Args:
            request_id: ID of the staff request
            admin_user_id: ID of the admin user denying the request
            notes: Optional notes about the denial
            
        Returns:
            The updated staff request
        """
        try:
            # Start a transaction
            self.db_session.begin_nested()
            
            request = self.db_session.get(StaffRequest, request_id)
            if not request:
                raise ValueError(f"Staff request with ID {request_id} not found")
            
            request.status = "denied"
            request.handled_at = datetime.now(timezone.utc)
            request.handled_by = admin_user_id
            if notes:
                request.notes = notes
            
            user = self.db_session.get(User, request.user_id)
            if user:
                user.role_requested = None
                if user.role == "pending":
                    user.role = "Rejected"
                # Keep the user account but with limited access
                # Optionally could deactivate: user.is_active = False
            
            self.db_session.commit()
            return request
        
        except Exception as e:
            self.db_session.rollback()
            raise Exception(f"Failed to deny staff request: {str(e)}") 