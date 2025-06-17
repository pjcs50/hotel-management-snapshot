"""
Authentication routes module.

This module defines the routes for user authentication operations.
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from db import db
from app.models.user import User
from app.models.customer import Customer
from app.services.user_service import UserService, DuplicateEmailError, DuplicateUsernameError
from app.utils.auth_security import validate_staff_registration, RoleEscalationError, auth_security
from app.utils.password_security import PasswordManager, PasswordStrengthError, PasswordRateLimitError

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Setup logger
logger = logging.getLogger(__name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Log in a user with enhanced security protection."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('customer.dashboard'))
        elif current_user.role == 'receptionist':
            return redirect(url_for('receptionist.dashboard'))
        elif current_user.role == 'manager':
            return redirect(url_for('manager.dashboard'))
        elif current_user.role == 'housekeeping':
            return redirect(url_for('housekeeping.dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            # Default fallback to main page
            return redirect('/')
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            try:
                password_valid = user.check_password(password)
                
                if password_valid:
                    # Check if the user is active
                    if not user.is_active:
                        flash('Your account is inactive. Please contact an administrator.', 'danger')
                        return render_template('auth/login.html')
                    
                    login_user(user, remember=remember)
                    
                    # Get next URL from query string
                    next_page = request.args.get('next')
                    
                    if not next_page or not next_page.startswith('/'):
                        if user.role == 'customer':
                            next_page = url_for('customer.dashboard')
                        elif user.role == 'receptionist':
                            next_page = url_for('receptionist.dashboard')
                        elif user.role == 'manager':
                            next_page = url_for('manager.dashboard')
                        elif user.role == 'housekeeping':
                            next_page = url_for('housekeeping.dashboard')
                        elif user.role == 'admin':
                            next_page = url_for('admin.dashboard')
                        else:
                            # Default fallback
                            next_page = '/'
                    
                    flash('Logged in successfully.', 'success')
                    return redirect(next_page)
                else:
                    flash('Invalid email or password.', 'danger')
            
            except PasswordRateLimitError as e:
                flash(str(e), 'danger')
                return render_template('auth/login.html')
                
            except Exception as e:
                # Log security-related errors
                from flask import current_app
                current_app.logger.warning(f"Login security error for email {email}: {e}")
                flash('Login failed due to security restrictions. Please try again later.', 'danger')
                return render_template('auth/login.html')
        else:
            # Still show generic error to prevent email enumeration
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out a user."""
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new customer with enhanced password security."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('customer.dashboard'))
        else:
            return redirect('/')
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        
        # Basic validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters long.')
        
        # Validate passwords
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        # Enhanced password validation
        if password:
            password_manager = PasswordManager()
            try:
                # Check rate limiting for registration attempts
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                password_manager.rate_limiter.check_rate_limit(ip_address=client_ip)
                
                # Validate password strength
                password_result = password_manager.validate_and_hash(
                    password, 
                    username=username,
                    user_data={'email': email, 'name': name}
                )
                
            except PasswordStrengthError as e:
                errors.append(str(e))
            except PasswordRateLimitError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append('Password validation failed. Please try again.')
        
        # Display errors if any
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html')
        
        user_service = UserService(db.session)
        
        try:
            # Create user with validated password hash
            user = user_service.create_user(
                username=username,
                email=email,
                password_hash=password_result['password_hash'],
                role='customer'
            )
            
            # Create customer profile
            customer = Customer(
                user_id=user.id,
                name=name
            )
            
            db.session.add(customer)
            db.session.commit()
            
            flash('Registration successful. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        
        except DuplicateEmailError:
            flash(f'Email {email} is already in use.', 'danger')
        
        except DuplicateUsernameError:
            flash(f'Username {username} is already in use.', 'danger')
        
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('auth/register.html')


@auth_bp.route('/staff-register', methods=['GET', 'POST'])
def staff_register():
    """Register a new staff member with enhanced security validation."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('customer.dashboard'))
        else:
            return redirect('/')
    
    # Get client IP for security tracking
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    # Initialize password manager for enhanced security
    password_manager = PasswordManager()
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role_requested = request.form.get('role_requested', '')
        
        # Validate form data
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        # Enhanced role validation with security checks
        try:
            role_validation = validate_staff_registration(role_requested, client_ip)
            if not role_validation['valid']:
                errors.append('Invalid role selection.')
        except RoleEscalationError as e:
            errors.append(str(e))
            # Log security violation
            logger.warning(f"Role escalation attempt: {role_requested} from IP {client_ip}")
            role_validation = None
        
        # Enhanced password validation
        try:
            if password:
                password_result = password_manager.validate_and_hash(
                    password, 
                    username=username,
                    user_data={'email': email}
                )
        except PasswordStrengthError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append('Password validation failed. Please try again.')
        
        # Check for errors and display them
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/staff_register.html', 
                                   roles=list(auth_security.ALLOWED_STAFF_ROLES.keys()),
                                   role_descriptions=auth_security.ALLOWED_STAFF_ROLES,
                                   previous_data={
                                       'username': username,
                                       'email': email,
                                       'role_requested': role_requested
                                   })
        
        # Process valid form with enhanced security
        user_service = UserService(db.session)
        
        try:
            # Check rate limiting for registration attempts
            try:
                password_manager.rate_limiter.check_rate_limit(ip_address=client_ip)
            except PasswordRateLimitError as e:
                flash(str(e), 'danger')
                return render_template('auth/staff_register.html', 
                                      roles=list(auth_security.ALLOWED_STAFF_ROLES.keys()),
                                      role_descriptions=auth_security.ALLOWED_STAFF_ROLES,
                                      previous_data={})
            
            # Create staff user with pending approval and enhanced security
            user = user_service.create_staff(
                username=username,
                email=email,
                password_hash=password_result['password_hash'],
                role_requested=role_requested,
                requires_admin_approval=role_validation.get('requires_admin_approval', False),
                client_ip=client_ip
            )
            
            # Record the role request for tracking
            auth_security.record_role_request(role_requested, client_ip)
            
            # Record successful registration attempt
            password_manager.rate_limiter.record_attempt(
                ip_address=client_ip, 
                success=True
            )
            
            approval_message = "admin approval" if role_validation.get('requires_admin_approval') else "approval"
            flash(
                f'Staff registration submitted for {approval_message}. '
                f'You will be notified by email at {email} when your account is activated.',
                'success'
            )
            return redirect(url_for('auth.login'))
        
        except DuplicateEmailError:
            password_manager.rate_limiter.record_attempt(ip_address=client_ip, success=False)
            flash(f'Email {email} is already in use.', 'danger')
            return render_template('auth/staff_register.html', 
                                  roles=list(auth_security.ALLOWED_STAFF_ROLES.keys()),
                                  role_descriptions=auth_security.ALLOWED_STAFF_ROLES,
                                  previous_data={
                                      'username': username,
                                      'email': email,
                                      'role_requested': role_requested
                                  })
        
        except DuplicateUsernameError:
            password_manager.rate_limiter.record_attempt(ip_address=client_ip, success=False)
            flash(f'Username {username} is already in use.', 'danger')
            return render_template('auth/staff_register.html', 
                                  roles=list(auth_security.ALLOWED_STAFF_ROLES.keys()),
                                  role_descriptions=auth_security.ALLOWED_STAFF_ROLES,
                                  previous_data={
                                      'username': username,
                                      'email': '',
                                      'role_requested': role_requested
                                  })
        
        except Exception as e:
            password_manager.rate_limiter.record_attempt(ip_address=client_ip, success=False)
            logger.error(f"Staff registration error: {str(e)}")
            flash(f'An error occurred during registration. Please try again.', 'danger')
            return render_template('auth/staff_register.html', 
                                  roles=list(auth_security.ALLOWED_STAFF_ROLES.keys()),
                                  role_descriptions=auth_security.ALLOWED_STAFF_ROLES,
                                  previous_data={
                                      'username': username,
                                      'email': email,
                                      'role_requested': role_requested
                                  })
    
    # Render the registration form with enhanced security info
    return render_template('auth/staff_register.html', 
                           roles=list(auth_security.ALLOWED_STAFF_ROLES.keys()),
                           role_descriptions=auth_security.ALLOWED_STAFF_ROLES,
                           previous_data={})


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password requests."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('customer.dashboard'))
        else:
            return redirect('/')
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # TODO: Generate password reset token and send email
            # For now, just show a success message
            flash('If an account with that email exists, a password reset link has been sent.', 'info')
            return redirect(url_for('auth.login'))
        
        # Still show success to prevent email enumeration
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html') 