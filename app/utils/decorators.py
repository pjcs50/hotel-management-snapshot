"""
Decorators module.

This module provides custom decorators for the application.
"""

from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def role_required(roles):
    """
    Decorator to restrict access to specific roles.
    
    Args:
        roles: A single role string or a list of roles.
        
    Returns:
        A decorator function.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Handle both single role and list of roles
            if isinstance(roles, str):
                required_roles = [roles]
            else:
                required_roles = roles
            
            if current_user.role not in required_roles:
                flash('You do not have permission to access this page.', 'danger')
                return abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorator to restrict access to admin users.
    
    Returns:
        A decorator function.
    """
    return role_required('admin')(f)


def staff_required(f):
    """
    Decorator to restrict access to staff members.
    
    Returns:
        A decorator function.
    """
    return role_required(['receptionist', 'manager', 'housekeeping', 'admin'])(f) 