"""
CSRF Protection utilities.

This module provides comprehensive CSRF protection for API endpoints
and form submissions to prevent cross-site request forgery attacks.
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, current_app, g
from flask_login import current_user


class CSRFError(Exception):
    """Exception raised for CSRF validation failures."""
    pass


class CSRFProtection:
    """
    Comprehensive CSRF protection system.
    
    Provides token generation, validation, and automatic protection
    for API endpoints and form submissions.
    """
    
    def __init__(self, app=None):
        """Initialize CSRF protection."""
        self.app = app
        self.secret_key = None
        self.token_lifetime = timedelta(hours=24)
        self.header_name = 'X-CSRF-Token'
        self.field_name = 'csrf_token'
        self.exempt_endpoints = set()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize CSRF protection with Flask app."""
        self.app = app
        self.secret_key = app.config.get('CSRF_SECRET_KEY', app.secret_key)
        self.token_lifetime = timedelta(
            hours=app.config.get('CSRF_TOKEN_LIFETIME_HOURS', 24)
        )
        
        # Register before_request handler
        app.before_request(self._check_csrf_protection)
        
        # Make token generator available in templates
        app.jinja_env.globals['csrf_token'] = self.generate_token
    
    def generate_token(self, user_id=None):
        """
        Generate a CSRF token for the current user/session.
        
        Args:
            user_id: Optional user ID (uses current_user if not provided)
            
        Returns:
            CSRF token string
        """
        if user_id is None and current_user.is_authenticated:
            user_id = current_user.id
        
        # Create timestamp
        timestamp = int(datetime.utcnow().timestamp())
        
        # Get session ID or create one
        session_id = session.get('csrf_session_id')
        if not session_id:
            session_id = secrets.token_urlsafe(32)
            session['csrf_session_id'] = session_id
        
        # Create token payload
        payload = f"{user_id}:{session_id}:{timestamp}"
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Combine payload and signature
        token = f"{payload}:{signature}"
        
        # Store in session for validation
        session['csrf_token'] = token
        session['csrf_token_timestamp'] = timestamp
        
        return token
    
    def validate_token(self, token, user_id=None):
        """
        Validate a CSRF token.
        
        Args:
            token: Token to validate
            user_id: Optional user ID (uses current_user if not provided)
            
        Returns:
            True if token is valid, False otherwise
            
        Raises:
            CSRFError: If token validation fails
        """
        if not token:
            raise CSRFError("CSRF token is missing")
        
        try:
            # Split token into components
            parts = token.split(':')
            if len(parts) != 4:
                raise CSRFError("Invalid CSRF token format")
            
            token_user_id, token_session_id, timestamp_str, signature = parts
            timestamp = int(timestamp_str)
            
            # Check token age
            if datetime.utcnow().timestamp() - timestamp > self.token_lifetime.total_seconds():
                raise CSRFError("CSRF token has expired")
            
            # Verify user ID
            if user_id is None and current_user.is_authenticated:
                user_id = current_user.id
            
            if str(user_id) != token_user_id:
                raise CSRFError("CSRF token user mismatch")
            
            # Verify session ID
            session_id = session.get('csrf_session_id')
            if not session_id or session_id != token_session_id:
                raise CSRFError("CSRF token session mismatch")
            
            # Verify signature
            payload = f"{token_user_id}:{token_session_id}:{timestamp_str}"
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                raise CSRFError("CSRF token signature invalid")
            
            return True
            
        except (ValueError, IndexError) as e:
            raise CSRFError(f"Invalid CSRF token: {str(e)}")
    
    def exempt(self, endpoint_or_view):
        """
        Exempt an endpoint or view from CSRF protection.
        
        Can be used as a decorator or by passing endpoint name.
        """
        if callable(endpoint_or_view):
            # Used as decorator
            endpoint_or_view._csrf_exempt = True
            return endpoint_or_view
        else:
            # Used with endpoint name
            self.exempt_endpoints.add(endpoint_or_view)
    
    def _check_csrf_protection(self):
        """Check CSRF protection for the current request."""
        # Skip for GET, HEAD, OPTIONS requests
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return
        
        # Skip for exempt endpoints
        endpoint = request.endpoint
        if endpoint in self.exempt_endpoints:
            return
        
        # Skip if view function is exempt
        view_function = current_app.view_functions.get(endpoint)
        if view_function and getattr(view_function, '_csrf_exempt', False):
            return
        
        # Skip for non-authenticated requests to certain endpoints
        if not current_user.is_authenticated and endpoint in [
            'auth.login', 'auth.register', 'auth.forgot_password'
        ]:
            return
        
        # Get token from request
        token = self._get_token_from_request()
        
        if not token:
            self._handle_csrf_error("CSRF token is missing")
            return
        
        # Validate token
        try:
            self.validate_token(token)
        except CSRFError as e:
            self._handle_csrf_error(str(e))
            return
    
    def _get_token_from_request(self):
        """Extract CSRF token from request headers or form data."""
        # Check header first
        token = request.headers.get(self.header_name)
        
        # Check form data if not in header
        if not token and request.is_json:
            data = request.get_json(silent=True)
            if data:
                token = data.get(self.field_name)
        elif not token:
            token = request.form.get(self.field_name)
        
        return token
    
    def _handle_csrf_error(self, message):
        """Handle CSRF validation errors."""
        if request.is_json or request.path.startswith('/api/'):
            # Return JSON error for API requests
            response = jsonify({
                'success': False,
                'error': 'CSRF validation failed',
                'message': message
            })
            response.status_code = 403
            return response
        else:
            # For form submissions, could redirect to error page
            # For now, return JSON error
            response = jsonify({
                'success': False,
                'error': 'CSRF validation failed',
                'message': message
            })
            response.status_code = 403
            return response


# Global CSRF protection instance
csrf = CSRFProtection()


# Decorators for manual CSRF protection
def csrf_required(f):
    """
    Decorator to require CSRF token validation for a specific endpoint.
    
    Use this for endpoints that need extra CSRF protection.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = csrf._get_token_from_request()
        
        try:
            csrf.validate_token(token)
        except CSRFError as e:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'CSRF validation failed',
                    'message': str(e)
                }), 403
            else:
                return jsonify({
                    'success': False,
                    'error': 'CSRF validation failed',
                    'message': str(e)
                }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def csrf_exempt(f):
    """
    Decorator to exempt an endpoint from CSRF protection.
    
    Use sparingly and only for endpoints that truly don't need protection.
    """
    f._csrf_exempt = True
    return f


# Rate limiting for CSRF token generation
class CSRFRateLimiter:
    """Rate limiter for CSRF token generation to prevent abuse."""
    
    def __init__(self):
        self.token_requests = {}  # IP -> list of timestamps
        self.max_requests = 100  # Max requests per hour
        self.window = timedelta(hours=1)
    
    def is_allowed(self, client_ip):
        """Check if client is allowed to request a token."""
        now = datetime.utcnow()
        
        # Clean old entries
        if client_ip in self.token_requests:
            self.token_requests[client_ip] = [
                ts for ts in self.token_requests[client_ip]
                if now - ts < self.window
            ]
        
        # Check limit
        requests = self.token_requests.get(client_ip, [])
        if len(requests) >= self.max_requests:
            return False
        
        # Record request
        if client_ip not in self.token_requests:
            self.token_requests[client_ip] = []
        self.token_requests[client_ip].append(now)
        
        return True


# Rate limiter instance
csrf_rate_limiter = CSRFRateLimiter()


# API endpoint for token generation
def get_csrf_token():
    """
    API endpoint to get a CSRF token.
    
    Rate limited to prevent abuse.
    """
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    if not csrf_rate_limiter.is_allowed(client_ip):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded'
        }), 429
    
    token = csrf.generate_token()
    
    return jsonify({
        'success': True,
        'csrf_token': token
    })


# Helper functions for templates
def csrf_token_input():
    """Generate hidden input field with CSRF token for forms."""
    token = csrf.generate_token()
    return f'<input type="hidden" name="{csrf.field_name}" value="{token}">'


def csrf_meta_tag():
    """Generate meta tag with CSRF token for AJAX requests."""
    token = csrf.generate_token()
    return f'<meta name="csrf-token" content="{token}">' 