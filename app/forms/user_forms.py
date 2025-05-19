"""
User account related forms.
"""

from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length

class ChangePasswordForm(FlaskForm):
    """Form for users to change their password."""
    current_password = PasswordField(
        'Current Password',
        validators=[DataRequired(message="Current password is required.")]
    )
    new_password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message="New password is required."),
            Length(min=8, message="New password must be at least 8 characters long.")
        ]
    )
    confirm_new_password = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(message="Please confirm your new password."),
            EqualTo('new_password', message="New passwords must match.")
        ]
    )
    submit = SubmitField('Change Password') 