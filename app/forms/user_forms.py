"""
User account related forms with enhanced password security.
"""

from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError
import re


class PasswordStrengthValidator:
    """Custom validator for password strength."""
    
    def __init__(self, message=None):
        self.message = message or (
            "Password must be at least 8 characters long and contain: "
            "uppercase letter, lowercase letter, digit, and special character"
        )
    
    def __call__(self, form, field):
        password = field.data
        if not password:
            return
        
        errors = []
        
        if len(password) < 8:
            errors.append("at least 8 characters")
        
        if not re.search(r'[A-Z]', password):
            errors.append("one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("one lowercase letter")
        
        if not re.search(r'[0-9]', password):
            errors.append("one digit")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            errors.append("one special character")
        
        # Check for common patterns
        if re.search(r'(.)\1{2,}', password):
            errors.append("no repeated characters (aaa, 111)")
        
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            errors.append("no sequential digits")
        
        if re.search(r'(qwerty|asdfgh|zxcvbn)', password.lower()):
            errors.append("no keyboard patterns (qwerty, etc.)")
        
        # Common passwords check
        common_passwords = {
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome'
        }
        if password.lower() in common_passwords:
            errors.append("a stronger, less common password")
        
        if errors:
            raise ValidationError(f"Password must contain {', '.join(errors[:-1])} and {errors[-1]}." if len(errors) > 1 else f"Password must contain {errors[0]}.")


class ChangePasswordForm(FlaskForm):
    """Enhanced form for users to change their password."""
    current_password = PasswordField(
        'Current Password',
        validators=[DataRequired(message="Current password is required.")],
        render_kw={
            'placeholder': 'Enter your current password',
            'class': 'form-control'
        }
    )
    new_password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message="New password is required."),
            Length(min=8, max=128, message="Password must be between 8 and 128 characters."),
            PasswordStrengthValidator()
        ],
        render_kw={
            'placeholder': 'Enter your new password',
            'class': 'form-control',
            'data-toggle': 'password-strength'
        }
    )
    confirm_new_password = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(message="Please confirm your new password."),
            EqualTo('new_password', message="New passwords must match.")
        ],
        render_kw={
            'placeholder': 'Confirm your new password',
            'class': 'form-control'
        }
    )
    submit = SubmitField(
        'Change Password',
        render_kw={'class': 'btn btn-primary'}
    )
    
    def validate_new_password(self, field):
        """Additional validation to ensure new password is different from current."""
        if hasattr(self, 'current_password') and field.data == self.current_password.data:
            raise ValidationError("New password must be different from current password.")


class RegisterForm(FlaskForm):
    """Enhanced registration form with strong password validation."""
    username = StringField(
        'Username',
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=64, message="Username must be between 3 and 64 characters.")
        ],
        render_kw={
            'placeholder': 'Choose a username',
            'class': 'form-control'
        }
    )
    email = StringField(
        'Email',
        validators=[DataRequired(message="Email is required.")],
        render_kw={
            'placeholder': 'Enter your email address',
            'class': 'form-control',
            'type': 'email'
        }
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, max=128, message="Password must be between 8 and 128 characters."),
            PasswordStrengthValidator()
        ],
        render_kw={
            'placeholder': 'Create a strong password',
            'class': 'form-control',
            'data-toggle': 'password-strength'
        }
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo('password', message="Passwords must match.")
        ],
        render_kw={
            'placeholder': 'Confirm your password',
            'class': 'form-control'
        }
    )
    name = StringField(
        'Full Name',
        validators=[
            DataRequired(message="Full name is required."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
        ],
        render_kw={
            'placeholder': 'Enter your full name',
            'class': 'form-control'
        }
    )
    submit = SubmitField(
        'Register',
        render_kw={'class': 'btn btn-primary'}
    )