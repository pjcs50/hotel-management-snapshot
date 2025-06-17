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
        Change a user's password with enhanced security validation.

        Args:
            user_id: The ID of the user.
            current_password: The user's current password.
            new_password: The new password to set.

        Returns:
            True if the password was changed successfully, False otherwise.

        Raises:
            ValueError: If the user is not found or current password does not match.
            PasswordStrengthError: If the new password doesn't meet security requirements.
            PasswordRateLimitError: If too many password change attempts.
        """
        from app.utils.password_security import PasswordStrengthError, PasswordRateLimitError
        
        user = self.db_session.get(User, user_id)
        if not user:
            raise ValueError("User not found.")

        try:
            # Check current password with rate limiting
            if not user.check_password(current_password):
                raise ValueError("Current password does not match.")

            # Set new password (will validate strength automatically)
            user.set_password(new_password)
            self.db_session.commit()
            return True
            
        except PasswordRateLimitError:
            # Re-raise rate limit errors
            raise
            
        except PasswordStrengthError:
            # Re-raise password strength errors
            raise
            
        except IntegrityError:
            self.db_session.rollback()
            raise # Re-raise for further handling if necessary
        
        except Exception as e:
            self.db_session.rollback()
            raise ValueError(f"Password change failed: {str(e)}")
    
    def create_user(self, username, email, password=None, password_hash=None, role="customer"):
        """
        Create a new user.
        
        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password to hash (deprecated, use password_hash)
            password_hash: Pre-hashed password (preferred for security)
            role: User role (default: customer)
            
        Returns:
            The newly created user
            
        Raises:
            DuplicateEmailError: If a user with the given email already exists
            DuplicateUsernameError: If a user with the given username already exists
            ValueError: If neither password nor password_hash is provided
        """
        if not password and not password_hash:
            raise ValueError("Either password or password_hash must be provided")
        
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
        
        # Set password - prefer pre-hashed for security
        if password_hash:
            user.password_hash = password_hash
        else:
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
    
    def create_staff(self, username, email, password=None, password_hash=None, role_requested=None, requires_admin_approval=False):
        """
        Create a staff user with enhanced security and optional admin approval.
        
        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password to hash (deprecated, use password_hash)
            password_hash: Pre-hashed password (preferred for security)
            role_requested: Role requested by the user
            requires_admin_approval: Whether the user requires admin approval
            
        Returns:
            The newly created user
            
        Raises:
            DuplicateEmailError: If a user with the given email already exists
            DuplicateUsernameError: If a user with the given username already exists
        """
        # Start a transaction
        transaction = self.db_session.begin_nested()
        
        try:
            # Create user with enhanced security
            if requires_admin_approval:
                # Create inactive user with temporary role
                user = self.create_user(
                    username=username,
                    email=email,
                    password=password,
                    password_hash=password_hash,
                    role="pending"  # Temporary role
                )
            
                # Set user as inactive and record requested role
                user.is_active = False
                user.role_requested = role_requested
            
                # Create staff request
                staff_request = StaffRequest(
                    user_id=user.id,
                    role_requested=role_requested,
                    status="pending",
                    notes="Staff registration request"
                )
            
                self.db_session.add(staff_request)
            else:
                # Create active user with requested role (for low-privilege roles)
                user = self.create_user(
                    username=username,
                    email=email,
                    password=password,
                    password_hash=password_hash,
                    role=role_requested or "receptionist"
                )
                user.is_active = True
        
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