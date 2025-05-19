"""
Authentication routes module.

This module defines the routes for user authentication operations.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from db import db
from app.models.user import User
from app.models.customer import Customer
from app.services.user_service import UserService, DuplicateEmailError, DuplicateUsernameError

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Log in a user."""
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
        
        if user and user.check_password(password):
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
        
        flash('Invalid email or password.', 'danger')
        return render_template('auth/login.html')
    
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
    """Register a new customer."""
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
        
        # Validate passwords
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        
        user_service = UserService(db.session)
        
        try:
            # Create user
            user = user_service.create_user(
                username=username,
                email=email,
                password=password,
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
    
    return render_template('auth/register.html')


@auth_bp.route('/staff-register', methods=['GET', 'POST'])
def staff_register():
    """Register a new staff member."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('customer.dashboard'))
        else:
            return redirect('/')
    
    # Define valid staff roles
    valid_roles = ['receptionist', 'housekeeping', 'manager']
    
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
        
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if role_requested not in valid_roles:
            errors.append('Please select a valid role.')
        
        # Check for errors and display them
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/staff_register.html', 
                                   roles=valid_roles,
                                   previous_data={
                                       'username': username,
                                       'email': email,
                                       'role_requested': role_requested
                                   })
        
        # Process valid form
        user_service = UserService(db.session)
        
        try:
            # Create staff user with pending approval
            user = user_service.create_staff(
                username=username,
                email=email,
                password=password,
                role_requested=role_requested
            )
            
            flash(f'Staff registration submitted for approval. You will be notified by email at {email} when your account is activated.', 'success')
            return redirect(url_for('auth.login'))
        
        except DuplicateEmailError:
            flash(f'Email {email} is already in use.', 'danger')
            return render_template('auth/staff_register.html', 
                                  roles=valid_roles,
                                  previous_data={
                                      'username': username,
                                      'email': email,
                                      'role_requested': role_requested
                                  })
        
        except DuplicateUsernameError:
            flash(f'Username {username} is already in use.', 'danger')
            return render_template('auth/staff_register.html', 
                                  roles=valid_roles,
                                  previous_data={
                                      'username': username,
                                      'email': '',
                                      'role_requested': role_requested
                                  })
        
        except Exception as e:
            flash(f'An error occurred during registration: {str(e)}', 'danger')
            return render_template('auth/staff_register.html', 
                                  roles=valid_roles,
                                  previous_data={
                                      'username': username,
                                      'email': email,
                                      'role_requested': role_requested
                                  })
    
    # Render the registration form
    return render_template('auth/staff_register.html', 
                           roles=valid_roles,
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