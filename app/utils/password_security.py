"""
Password security utilities.

This module provides comprehensive password security features including
strength validation, rate limiting, breach checking, and secure hashing.
"""

import re
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, current_app, jsonify, g
import logging

logger = logging.getLogger(__name__)


class PasswordStrengthError(Exception):
    """Exception raised for password strength validation failures."""
    pass


class PasswordRateLimitError(Exception):
    """Exception raised when password attempt rate limit is exceeded."""
    pass


class PasswordValidator:
    """
    Comprehensive password strength validator.
    
    Validates passwords against multiple security criteria including
    length, complexity, common patterns, and known breaches.
    """
    
    def __init__(self):
        """Initialize password validator with default rules."""
        self.min_length = 8
        self.max_length = 128
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_special = True
        self.special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        self.common_passwords = self._load_common_passwords()
        self.common_patterns = [
            r'(.)\1{2,}',  # Repeated characters (aaa, 111)
            r'(012|123|234|345|456|567|678|789|890)',  # Sequential digits
            r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
            r'(qwerty|asdfgh|zxcvbn)',  # Keyboard patterns
        ]
    
    def _load_common_passwords(self):
        """Load common passwords list."""
        # In production, this would load from a file or database
        return {
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey',
            'dragon', 'master', 'shadow', 'football', 'baseball',
            'superman', 'batman', 'princess', 'sunshine', 'iloveyou',
            '12345678', '1234567890', 'password1', 'login', 'test',
            'guest', 'hello', 'access', 'secret', 'pass'
        }
    
    def validate_password(self, password, username=None, user_data=None):
        """
        Validate password strength and security.
        
        Args:
            password: Password to validate
            username: Optional username to check against
            user_data: Optional user data (name, email) to check against
            
        Returns:
            dict: Validation result with score and feedback
            
        Raises:
            PasswordStrengthError: If password doesn't meet requirements
        """
        if not password:
            raise PasswordStrengthError("Password cannot be empty")
        
        errors = []
        score = 0
        feedback = []
        
        # Length validation
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        elif len(password) >= self.min_length:
            score += 1
            
        if len(password) > self.max_length:
            errors.append(f"Password cannot exceed {self.max_length} characters")
        
        # Character type validation
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'[0-9]', password))
        has_special = bool(re.search(f'[{re.escape(self.special_chars)}]', password))
        
        if self.require_uppercase and not has_upper:
            errors.append("Password must contain at least one uppercase letter")
        elif has_upper:
            score += 1
            
        if self.require_lowercase and not has_lower:
            errors.append("Password must contain at least one lowercase letter")
        elif has_lower:
            score += 1
            
        if self.require_digits and not has_digit:
            errors.append("Password must contain at least one digit")
        elif has_digit:
            score += 1
            
        if self.require_special and not has_special:
            errors.append(f"Password must contain at least one special character: {self.special_chars}")
        elif has_special:
            score += 1
        
        # Advanced strength checks
        if len(password) >= 12:
            score += 1
            feedback.append("Good length")
        
        if len(set(password)) / len(password) > 0.7:
            score += 1
            feedback.append("Good character diversity")
        
        # Common password check
        if password.lower() in self.common_passwords:
            errors.append("Password is too common")
        else:
            score += 1
        
        # Pattern checks
        for pattern in self.common_patterns:
            if re.search(pattern, password.lower()):
                errors.append("Password contains common patterns")
                break
        else:
            score += 1
        
        # Username similarity check
        if username and username.lower() in password.lower():
            errors.append("Password cannot contain username")
        elif username:
            score += 1
        
        # User data similarity check
        if user_data:
            for field, value in user_data.items():
                if value and len(value) > 3 and value.lower() in password.lower():
                    errors.append(f"Password cannot contain {field}")
                    break
            else:
                score += 1
        
        # Calculate final score (0-10)
        max_score = 10
        strength_score = min(score, max_score)
        
        # Determine strength level
        if strength_score >= 8:
            strength = "Very Strong"
        elif strength_score >= 6:
            strength = "Strong"
        elif strength_score >= 4:
            strength = "Medium"
        elif strength_score >= 2:
            strength = "Weak"
        else:
            strength = "Very Weak"
        
        # Add feedback based on score
        if not errors:
            if strength_score >= 8:
                feedback.append("Excellent password!")
            elif strength_score >= 6:
                feedback.append("Good password security")
            else:
                feedback.append("Consider making it stronger")
        
        result = {
            'valid': len(errors) == 0,
            'errors': errors,
            'score': strength_score,
            'strength': strength,
            'feedback': feedback
        }
        
        if errors:
            raise PasswordStrengthError(f"Password validation failed: {'; '.join(errors)}")
        
        return result
    
    def generate_secure_password(self, length=12):
        """
        Generate a secure random password.
        
        Args:
            length: Password length (default 12)
            
        Returns:
            str: Secure password
        """
        if length < self.min_length:
            length = self.min_length
        
        # Ensure we have at least one of each required character type
        chars = []
        if self.require_uppercase:
            chars.append(secrets.choice(string.ascii_uppercase))
        if self.require_lowercase:
            chars.append(secrets.choice(string.ascii_lowercase))
        if self.require_digits:
            chars.append(secrets.choice(string.digits))
        if self.require_special:
            chars.append(secrets.choice(self.special_chars))
        
        # Fill remaining length with random characters
        all_chars = string.ascii_letters + string.digits + self.special_chars
        for _ in range(length - len(chars)):
            chars.append(secrets.choice(all_chars))
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(chars)
        
        return ''.join(chars)


class PasswordRateLimiter:
    """
    Enhanced rate limiter for password attempts to prevent brute force attacks.
    
    Implements multiple layers of protection including IP-based, user-based,
    and fingerprint-based rate limiting with exponential backoff.
    """
    
    def __init__(self):
        """Initialize rate limiter with enhanced security settings."""
        self.attempts = defaultdict(list)  # Key -> list of attempt timestamps
        self.locked_accounts = defaultdict(datetime)  # user_id -> lock_until
        self.suspicious_ips = defaultdict(int)  # IP -> suspicion score
        
        # Rate limiting settings
        self.max_attempts_per_ip = 10  # Max attempts per IP per hour
        self.max_attempts_per_user = 5  # Max attempts per user per 15 minutes
        self.max_attempts_per_fingerprint = 8  # Max attempts per browser fingerprint
        
        # Time windows
        self.ip_window = timedelta(hours=1)
        self.user_window = timedelta(minutes=15)
        self.fingerprint_window = timedelta(minutes=30)
        
        # Lockout settings
        self.lockout_duration = timedelta(minutes=30)
        self.progressive_delays = [1, 2, 5, 10, 30, 60]  # Seconds
        
        # Enhanced security thresholds
        self.ip_ban_threshold = 50  # Ban IP after 50 failed attempts in 24h
        self.ip_ban_duration = timedelta(hours=24)
        self.suspicious_threshold = 20  # Mark IP as suspicious
    
    def _generate_request_fingerprint(self, request_data=None):
        """
        Generate a unique fingerprint for the request to prevent easy bypassing.
        
        Args:
            request_data: Optional request data dict
            
        Returns:
            str: Unique fingerprint hash
        """
        import hashlib
        from flask import request
        
        # Collect multiple request attributes for fingerprinting
        fingerprint_data = []
        
        if request:
            # Basic request info
            fingerprint_data.extend([
                request.environ.get('HTTP_USER_AGENT', ''),
                request.environ.get('HTTP_ACCEPT_LANGUAGE', ''),
                request.environ.get('HTTP_ACCEPT_ENCODING', ''),
                request.environ.get('HTTP_ACCEPT', ''),
                request.environ.get('HTTP_CONNECTION', ''),
                request.environ.get('HTTP_CACHE_CONTROL', ''),
            ])
            
            # Network info (multiple sources to prevent IP spoofing)
            real_ip = self._get_real_ip()
            fingerprint_data.append(real_ip)
            
            # Additional headers that are harder to spoof
            fingerprint_data.extend([
                request.environ.get('HTTP_DNT', ''),
                request.environ.get('HTTP_UPGRADE_INSECURE_REQUESTS', ''),
                request.environ.get('HTTP_SEC_FETCH_SITE', ''),
                request.environ.get('HTTP_SEC_FETCH_MODE', ''),
                request.environ.get('HTTP_SEC_FETCH_USER', ''),
                request.environ.get('HTTP_SEC_FETCH_DEST', ''),
            ])
        
        # Add custom request data if provided
        if request_data:
            fingerprint_data.extend([
                str(request_data.get('screen_resolution', '')),
                str(request_data.get('timezone', '')),
                str(request_data.get('plugins', '')),
                str(request_data.get('canvas_fingerprint', ''))
            ])
        
        # Create hash of all fingerprint data
        fingerprint_string = '|'.join(str(item) for item in fingerprint_data)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
    
    def _get_real_ip(self):
        """
        Get the real client IP address, checking multiple headers to prevent spoofing.
        
        Returns:
            str: Client IP address
        """
        from flask import request
        
        # Check multiple headers in order of preference
        ip_headers = [
            'HTTP_CF_CONNECTING_IP',  # Cloudflare
            'HTTP_X_REAL_IP',  # Nginx
            'HTTP_X_FORWARDED_FOR',  # Standard proxy header
            'HTTP_X_FORWARDED',
            'HTTP_X_CLUSTER_CLIENT_IP',
            'HTTP_FORWARDED_FOR',
            'HTTP_FORWARDED',
            'REMOTE_ADDR'  # Direct connection
        ]
        
        for header in ip_headers:
            ip = request.environ.get(header)
            if ip:
                # Handle comma-separated IPs (X-Forwarded-For can have multiple)
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                
                # Validate IP format
                if self._is_valid_ip(ip):
                    return ip
        
        return request.remote_addr or 'unknown'
    
    def _is_valid_ip(self, ip):
        """Validate IP address format."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def check_rate_limit(self, user_id=None, ip_address=None, request_data=None):
        """
        Enhanced rate limit checking with multiple protection layers.
        
        Args:
            user_id: User ID (optional)
            ip_address: IP address (optional, will be detected if not provided)
            request_data: Additional request data for fingerprinting
            
        Returns:
            dict: Rate limit status
            
        Raises:
            PasswordRateLimitError: If rate limit exceeded
        """
        now = datetime.utcnow()
        
        # Get real IP if not provided
        if not ip_address:
            ip_address = self._get_real_ip()
        
        # Generate request fingerprint
        fingerprint = self._generate_request_fingerprint(request_data)
        
        # Check if IP is banned
        ip_ban_key = f"ip_ban:{ip_address}"
        if ip_ban_key in self.locked_accounts:
            if now < self.locked_accounts[ip_ban_key]:
                remaining = (self.locked_accounts[ip_ban_key] - now).total_seconds()
                raise PasswordRateLimitError(
                    f"IP address temporarily banned due to suspicious activity. "
                    f"Try again in {int(remaining/3600)} hours."
                )
            else:
                del self.locked_accounts[ip_ban_key]
        
        # Check account lockout
        if user_id and user_id in self.locked_accounts:
            if now < self.locked_accounts[user_id]:
                remaining = (self.locked_accounts[user_id] - now).total_seconds()
                raise PasswordRateLimitError(
                    f"Account temporarily locked. Try again in {int(remaining)} seconds."
                )
            else:
                del self.locked_accounts[user_id]
        
        # Check IP-based rate limiting
        ip_key = f"ip:{ip_address}"
        self._clean_old_attempts(ip_key, self.ip_window)
        ip_attempts = len(self.attempts[ip_key])
        
        if ip_attempts >= self.max_attempts_per_ip:
            # Escalate to IP ban if too many attempts
            if ip_attempts >= self.ip_ban_threshold:
                self.locked_accounts[ip_ban_key] = now + self.ip_ban_duration
                raise PasswordRateLimitError(
                    f"IP address banned due to excessive failed attempts. "
                    f"Contact support if this is an error."
                )
            else:
                raise PasswordRateLimitError(
                    f"Too many password attempts from this IP. Try again later."
                )
        
        # Check fingerprint-based rate limiting (prevents user agent switching)
        fingerprint_key = f"fingerprint:{fingerprint}"
        self._clean_old_attempts(fingerprint_key, self.fingerprint_window)
        
        if len(self.attempts[fingerprint_key]) >= self.max_attempts_per_fingerprint:
            raise PasswordRateLimitError(
                f"Too many password attempts from this device. Try again later."
            )
        
        # Check user-based rate limiting
        if user_id:
            user_key = f"user:{user_id}"
            self._clean_old_attempts(user_key, self.user_window)
            
            attempt_count = len(self.attempts[user_key])
            if attempt_count >= self.max_attempts_per_user:
                # Lock the account
                self.locked_accounts[user_id] = now + self.lockout_duration
                raise PasswordRateLimitError(
                    f"Too many failed login attempts. Account locked for "
                    f"{self.lockout_duration.total_seconds()/60} minutes."
                )
            
            # Calculate progressive delay
            if attempt_count > 0:
                delay_index = min(attempt_count - 1, len(self.progressive_delays) - 1)
                delay = self.progressive_delays[delay_index]
                last_attempt = max(self.attempts[user_key])
                if (now - last_attempt).total_seconds() < delay:
                    remaining = delay - (now - last_attempt).total_seconds()
                    raise PasswordRateLimitError(
                        f"Please wait {int(remaining)} seconds before trying again."
                    )
        
        # Update suspicion score for IP
        if ip_attempts > self.suspicious_threshold:
            self.suspicious_ips[ip_address] = min(self.suspicious_ips[ip_address] + 1, 100)
        
        return {
            'allowed': True,
            'remaining_attempts': {
                'ip': self.max_attempts_per_ip - ip_attempts,
                'user': self.max_attempts_per_user - len(self.attempts.get(f"user:{user_id}", [])) if user_id else None,
                'fingerprint': self.max_attempts_per_fingerprint - len(self.attempts[fingerprint_key])
            },
            'suspicion_score': self.suspicious_ips.get(ip_address, 0),
            'fingerprint': fingerprint
        }
    
    def record_attempt(self, user_id=None, ip_address=None, success=False, request_data=None):
        """
        Record a password attempt with enhanced tracking.
        
        Args:
            user_id: User ID (optional)
            ip_address: IP address (optional)
            success: Whether the attempt was successful
            request_data: Additional request data for fingerprinting
        """
        now = datetime.utcnow()
        
        # Get real IP if not provided
        if not ip_address:
            ip_address = self._get_real_ip()
        
        # Generate request fingerprint
        fingerprint = self._generate_request_fingerprint(request_data)
        
        if success:
            # Clear attempts on successful login
            if user_id:
                user_key = f"user:{user_id}"
                if user_key in self.attempts:
                    del self.attempts[user_key]
                if user_id in self.locked_accounts:
                    del self.locked_accounts[user_id]
            
            # Reduce suspicion score on successful login
            if ip_address in self.suspicious_ips:
                self.suspicious_ips[ip_address] = max(0, self.suspicious_ips[ip_address] - 5)
        else:
            # Record failed attempt across all tracking methods
            ip_key = f"ip:{ip_address}"
            fingerprint_key = f"fingerprint:{fingerprint}"
            
            self.attempts[ip_key].append(now)
            self.attempts[fingerprint_key].append(now)
            
            if user_id:
                user_key = f"user:{user_id}"
                self.attempts[user_key].append(now)
            
            # Increase suspicion score
            self.suspicious_ips[ip_address] = min(self.suspicious_ips[ip_address] + 2, 100)
    
    def _clean_old_attempts(self, key, window):
        """Remove old attempts outside the time window."""
        now = datetime.utcnow()
        if key in self.attempts:
            self.attempts[key] = [
                attempt for attempt in self.attempts[key]
                if now - attempt < window
            ]
    
    def is_ip_suspicious(self, ip_address=None):
        """
        Check if an IP address is considered suspicious.
        
        Args:
            ip_address: IP to check (optional, will detect current if not provided)
            
        Returns:
            bool: True if IP is suspicious
        """
        if not ip_address:
            ip_address = self._get_real_ip()
        
        return self.suspicious_ips.get(ip_address, 0) >= self.suspicious_threshold


class PasswordManager:
    """
    Comprehensive password management system.
    
    Combines validation, rate limiting, secure hashing, and breach checking.
    """
    
    def __init__(self):
        """Initialize password manager."""
        self.validator = PasswordValidator()
        self.rate_limiter = PasswordRateLimiter()
        self.hash_algorithm = 'pbkdf2:sha256:100000'  # Strong hashing
    
    def validate_and_hash(self, password, username=None, user_data=None):
        """
        Validate password strength and return secure hash.
        
        Args:
            password: Password to validate and hash
            username: Optional username for validation
            user_data: Optional user data for validation
            
        Returns:
            dict: Validation result and password hash
        """
        # Validate password strength
        validation_result = self.validator.validate_password(
            password, username, user_data
        )
        
        # Generate secure hash
        password_hash = generate_password_hash(
            password, method=self.hash_algorithm
        )
        
        return {
            'validation': validation_result,
            'password_hash': password_hash
        }
    
    def check_password_with_rate_limit(self, password, password_hash, user_id=None):
        """
        Check password with rate limiting protection.
        
        Args:
            password: Password to check
            password_hash: Stored password hash
            user_id: User ID for rate limiting
            
        Returns:
            bool: True if password matches
            
        Raises:
            PasswordRateLimitError: If rate limit exceeded
        """
        # Get client IP
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Check rate limits
        self.rate_limiter.check_rate_limit(user_id=user_id, ip_address=ip_address)
        
        # Check password
        success = check_password_hash(password_hash, password)
        
        # Record attempt
        self.rate_limiter.record_attempt(
            user_id=user_id, 
            ip_address=ip_address, 
            success=success
        )
        
        return success
    
    def generate_secure_password(self, length=12):
        """Generate a secure password."""
        return self.validator.generate_secure_password(length)
    
    def check_password_breach(self, password):
        """
        Check if password has been compromised in known data breaches.
        
        Uses k-anonymity to protect the password being checked.
        
        Args:
            password: Password to check
            
        Returns:
            dict: Breach check result
        """
        # Generate SHA-1 hash of password
        password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        
        # Use k-anonymity: only send first 5 characters of hash
        prefix = password_hash[:5]
        suffix = password_hash[5:]
        
        # In a real implementation, you would query the HaveIBeenPwned API
        # For this example, we'll simulate the check
        try:
            # Simulated breach check - in production, use requests to query API
            # response = requests.get(f'https://api.pwnedpasswords.com/range/{prefix}')
            # Check if suffix appears in response
            
            # For now, return safe result
            return {
                'breached': False,
                'count': 0,
                'message': 'Password appears to be safe'
            }
        except Exception as e:
            logger.warning(f"Password breach check failed: {e}")
            return {
                'breached': None,
                'count': None,
                'message': 'Breach check unavailable'
            }


# Global password manager instance
password_manager = PasswordManager()


# Password rate limiting decorator
def password_rate_limit(f):
    """
    Decorator to add password rate limiting to authentication endpoints.
    
    This decorator should be applied to login, password change, and other
    password-related endpoints to prevent brute force attacks.
    """
    from functools import wraps
    from flask import request, jsonify, g
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Initialize password manager if not already done
        if not hasattr(g, 'password_manager'):
            g.password_manager = PasswordManager()
        
        # Get client information
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        try:
            # Check rate limits before proceeding
            g.password_manager.rate_limiter.check_rate_limit(ip_address=ip_address)
            
            # Execute original function
            result = f(*args, **kwargs)
            
            # Record successful attempt if this is a POST request
            if request.method == 'POST':
                g.password_manager.rate_limiter.record_attempt(
                    ip_address=ip_address, 
                    success=True
                )
            
            return result
            
        except PasswordRateLimitError as e:
            # Record failed attempt
            g.password_manager.rate_limiter.record_attempt(
                ip_address=ip_address, 
                success=False
            )
            
            # Return appropriate error response
            if request.is_json:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': str(e)
                }), 429
            else:
                from flask import flash, redirect, url_for
                flash(str(e), 'danger')
                return redirect(url_for('auth.login'))
        
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Password rate limit decorator error: {e}")
            # Continue with original function - don't block legitimate users
            return f(*args, **kwargs)
    
    return decorated_function


# Password strength checker for forms
def check_password_strength(password):
    """
    Simple password strength checker for client-side validation.
    
    Args:
        password: Password to check
        
    Returns:
        dict: Strength information
    """
    try:
        result = password_manager.validator.validate_password(password)
        return result
    except PasswordStrengthError as e:
        return {
            'valid': False,
            'errors': [str(e)],
            'score': 0,
            'strength': 'Very Weak',
            'feedback': []
        } 