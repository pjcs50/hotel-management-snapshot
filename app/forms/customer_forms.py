"""
Customer forms module.

This module contains forms for customer profile management.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Optional


class CustomerProfileForm(FlaskForm):
    """Form for creating and editing customer profiles."""
    
    name = StringField(
        'Full Name', 
        validators=[
            DataRequired(message="Full name is required"),
            Length(min=3, max=100, message="Name must be 3-100 characters")
        ]
    )
    
    phone = StringField(
        'Phone Number',
        validators=[
            DataRequired(message="Phone number is required"),
            Length(min=5, max=20, message="Phone number must be 5-20 characters")
        ]
    )
    
    address = TextAreaField(
        'Address',
        validators=[
            Optional(),
            Length(max=255, message="Address must be less than 255 characters")
        ]
    )
    
    emergency_contact = TextAreaField(
        'Emergency Contact',
        validators=[
            Optional(),
            Length(max=255, message="Emergency contact must be less than 255 characters")
        ]
    )
    
    submit = SubmitField('Save Profile') 