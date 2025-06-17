"""
Authentication Security Module.

This module provides comprehensive security features for authentication
including role validation, session management, and privilege escalation prevention.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, current_app, g
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)


class AuthSecurityError(Exception):
    """Exception raised for authentication security violations."""
    pass


class RoleEscalationError(AuthSecurityError):
    """Exception raised for role escalation attempts."""
    pass


class SessionSecurityError(AuthSecurityError):
    """Exception raised for session security violations."""
    pass


class AuthSecurityManager:
    """
    Comprehensive authentication security manager.
    
    Handles role validation, session security, and privilege escalation prevention.
    """
    
    # Define role hierarchy (lower number = higher privilege)
    ROLE_HIERARCHY = {
        'admin': 0,
        'manager': 1,
        'receptionist': 2,
        'housekeeping': 3,
        'customer': 4,
        'guest': 5
    }
    
    # Valid role transitions for staff registration
    ALLOWED_STAFF_ROLES = {
        'receptionist': {
            'description': 'Front desk operations',
            'requires_approval': True,
            'max_daily_registrations': 5
        },
        'housekeeping': {
            'description': 'Room cleaning and maintenance',
            'requires_approval': True,
            'max_daily_registrations': 10
        },
        'manager': {
            'description': 'Management operations',
            'requires_approval': True,
            'requires_admin_approval': True,
            'max_daily_registrations': 2
        }
    }
    
    # Restricted roles that cannot be requested through registration
    RESTRICTED_ROLES = ['admin', 'system']
    
    def __init__(self):
        """Initialize authentication security manager."""
        self.session_timeout = timedelta(hours=8)  # Default session timeout
        self.max_concurrent_sessions = 3  # Max sessions per user
        self.session_renewal_threshold = timedelta(minutes=30)  # Renew session if < 30min left
        
        # Track registration attempts
        self.daily_registrations = {}  # role -> count
        self.registration_ips = {}  # IP -> registration count
        
    def validate_role_request(self, requested_role, user_ip=None):
        """
        Validate a role request for staff registration.
        
        Args:
            requested_role: Role being requested
            user_ip: IP address of requester
            
        Returns:
            dict: Validation result
            
        Raises:
            RoleEscalationError: If role request is invalid
        """
        # Check if role is restricted
        if requested_role in self.RESTRICTED_ROLES:
            logger.warning(f"Attempt to request restricted role: {requested_role} from IP: {user_ip}")
            raise RoleEscalationError(
                f"Role '{requested_role}' cannot be requested through registration. "
                f"Contact system administrator."
            )
        
        # Check if role is valid for staff registration
        if requested_role not in self.ALLOWED_STAFF_ROLES:
            raise RoleEscalationError(
                f"Invalid role '{requested_role}'. Valid roles: {', '.join(self.ALLOWED_STAFF_ROLES.keys())}"
            )
        
        role_config = self.ALLOWED_STAFF_ROLES[requested_role]
        
        # Check daily registration limits
        today = datetime.now().date()
        daily_key = f"{requested_role}:{today}"
        current_count = self.daily_registrations.get(daily_key, 0)
        
        if current_count >= role_config['max_daily_registrations']:
            raise RoleEscalationError(
                f"Daily registration limit exceeded for role '{requested_role}'. "
                f"Please try again tomorrow or contact administrator."
            )
        
        # Check IP-based registration limits (prevent automated attacks)
        if user_ip:
            ip_key = f"ip:{user_ip}:{today}"
            ip_count = self.registration_ips.get(ip_key, 0)
            if ip_count >= 3:  # Max 3 registrations per IP per day
                raise RoleEscalationError(
                    "Too many registration attempts from this IP address. "
                    "Please try again tomorrow."
                )
        
        return {
            'valid': True,
            'role': requested_role,
            'description': role_config['description'],
            'requires_approval': role_config['requires_approval'],
            'requires_admin_approval': role_config.get('requires_admin_approval', False),
            'remaining_daily_slots': role_config['max_daily_registrations'] - current_count
        }
    
    def record_role_request(self, requested_role, user_ip=None):
        """Record a role request for tracking purposes."""
        today = datetime.now().date()
        daily_key = f"{requested_role}:{today}"
        self.daily_registrations[daily_key] = self.daily_registrations.get(daily_key, 0) + 1
        
        if user_ip:
            ip_key = f"ip:{user_ip}:{today}"
            self.registration_ips[ip_key] = self.registration_ips.get(ip_key, 0) + 1
    
    def validate_role_elevation(self, current_role, target_role, elevated_by_role=None):
        """
        Validate if a role elevation is allowed.
        
        Args:
            current_role: Current user role
            target_role: Target role to elevate to
            elevated_by_role: Role of user performing elevation
            
        Returns:
            bool: True if elevation is allowed
            
        Raises:
            RoleEscalationError: If elevation is not allowed
        """
        current_level = self.ROLE_HIERARCHY.get(current_role, 999)
        target_level = self.ROLE_HIERARCHY.get(target_role, 999)
        
        # Cannot elevate to higher privilege level
        if target_level < current_level:
            if not elevated_by_role:
                raise RoleEscalationError(
                    "Cannot elevate to higher privilege role without authorization"
                )
            
            # Check if elevating user has sufficient privileges
            elevating_level = self.ROLE_HIERARCHY.get(elevated_by_role, 999)
            if elevating_level >= target_level:
                raise RoleEscalationError(
                    f"Insufficient privileges to elevate user to '{target_role}' role"
                )
        
        return True
    
    def generate_secure_session_token(self):
        """Generate a cryptographically secure session token."""
        return secrets.token_urlsafe(32)
    
    def create_secure_session(self, user_id, role, ip_address=None):
        """
        Create a secure session with proper tracking.
        
        Args:
            user_id: User ID
            role: User role
            ip_address: Client IP address
            
        Returns:
            dict: Session information
        """
        now = datetime.utcnow()
        session_token = self.generate_secure_session_token()
        
        # Create session fingerprint
        session_fingerprint = self._create_session_fingerprint(user_id, ip_address)
        
        session_data = {
            'user_id': user_id,
            'role': role,
            'session_token': session_token,
            'created_at': now,
            'last_activity': now,
            'expires_at': now + self.session_timeout,
            'ip_address': ip_address,
            'fingerprint': session_fingerprint,
            'is_active': True
        }
        
        # Store in Flask session
        session.update({
            'user_id': user_id,
            'role': role,
            'session_token': session_token,
            'created_at': now.isoformat(),
            'expires_at': session_data['expires_at'].isoformat(),
            'fingerprint': session_fingerprint
        })
        
        # Set session security flags
        session.permanent = True
        
        return session_data
    
    def validate_session_security(self, user_id=None):
        """
        Validate current session security.
        
        Args:
            user_id: Expected user ID (optional)
            
        Returns:
            bool: True if session is valid
            
        Raises:
            SessionSecurityError: If session is invalid
        """
        if not session.get('user_id'):
            raise SessionSecurityError("No active session")
        
        # Check user ID match
        if user_id and session.get('user_id') != user_id:
            raise SessionSecurityError("Session user ID mismatch")
        
        # Check session expiration
        expires_at_str = session.get('expires_at')
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.utcnow() > expires_at:
                raise SessionSecurityError("Session expired")
        
        # Check session fingerprint
        current_fingerprint = self._create_session_fingerprint(
            session.get('user_id'), 
            request.environ.get('REMOTE_ADDR')
        )
        stored_fingerprint = session.get('fingerprint')
        
        if stored_fingerprint and current_fingerprint != stored_fingerprint:
            logger.warning(f"Session fingerprint mismatch for user {session.get('user_id')}")
            raise SessionSecurityError("Session security violation detected")
        
        return True
    
    def renew_session_if_needed(self):
        """Renew session if it's close to expiring."""
        expires_at_str = session.get('expires_at')
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            time_remaining = expires_at - datetime.utcnow()
            
            if time_remaining < self.session_renewal_threshold:
                # Renew session
                new_expires_at = datetime.utcnow() + self.session_timeout
                session['expires_at'] = new_expires_at.isoformat()
                
                logger.info(f"Session renewed for user {session.get('user_id')}")
    
    def invalidate_session(self, reason="logout"):
        """
        Invalidate current session.
        
        Args:
            reason: Reason for invalidation
        """
        user_id = session.get('user_id')
        if user_id:
            logger.info(f"Session invalidated for user {user_id}: {reason}")
        
        session.clear()
    
    def _create_session_fingerprint(self, user_id, ip_address):
        """Create a session fingerprint for security validation."""
        fingerprint_data = [
            str(user_id),
            ip_address or 'unknown',
            request.environ.get('HTTP_USER_AGENT', ''),
            request.environ.get('HTTP_ACCEPT_LANGUAGE', ''),
        ]
        
        fingerprint_string = '|'.join(fingerprint_data)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
    
    def check_role_permission(self, required_role, user_role=None):
        """
        Check if user has required role permission.
        
        Args:
            required_role: Required role for access
            user_role: User's current role (optional, will use current_user if not provided)
            
        Returns:
            bool: True if user has permission
        """
        if not user_role:
            if current_user.is_authenticated:
                user_role = current_user.role
            else:
                return False
        
        user_level = self.ROLE_HIERARCHY.get(user_role, 999)
        required_level = self.ROLE_HIERARCHY.get(required_role, 0)
        
        return user_level <= required_level


# Global instance
auth_security = AuthSecurityManager()


def secure_role_required(required_role):
    """
    Enhanced role requirement decorator with security validation.
    
    Args:
        required_role: Required role for access
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Validate session security
            try:
                auth_security.validate_session_security()
                auth_security.renew_session_if_needed()
            except SessionSecurityError as e:
                logger.warning(f"Session security error: {str(e)}")
                auth_security.invalidate_session("security_violation")
                return redirect(url_for('auth.login'))
            
            # Check role permission
            if not auth_security.check_role_permission(required_role):
                logger.warning(
                    f"Access denied: User {current_user.id if current_user.is_authenticated else 'anonymous'} "
                    f"attempted to access {required_role} resource"
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_staff_registration(requested_role, user_ip=None):
    """
    Validate staff registration request.
    
    Args:
        requested_role: Role being requested
        user_ip: IP address of requester
        
    Returns:
        dict: Validation result
        
    Raises:
        RoleEscalationError: If request is invalid
    """
    return auth_security.validate_role_request(requested_role, user_ip) 