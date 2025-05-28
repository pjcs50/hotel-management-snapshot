"""
Booking forms module.

This module contains forms for booking creation and management.
"""

from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, IntegerField, SubmitField, HiddenField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Optional, NumberRange

from app.models.booking import Booking


class BookingForm(FlaskForm):
    """Form for creating and editing bookings."""
    
    room_id = SelectField(
        'Room',
        validators=[DataRequired(message="Room selection is required")],
        coerce=int
    )
    
    customer_id = HiddenField('Customer ID')
    
    check_in_date = DateField(
        'Check-in Date',
        validators=[DataRequired(message="Check-in date is required")],
        format='%Y-%m-%d'
    )
    
    check_out_date = DateField(
        'Check-out Date',
        validators=[DataRequired(message="Check-out date is required")],
        format='%Y-%m-%d'
    )
    
    num_guests = IntegerField(
        'Number of Guests',
        validators=[
            DataRequired(message="Number of guests is required."),
            NumberRange(min=1, max=10, message="Number of guests must be between 1 and 10.")
        ],
        default=1
    )

    special_requests = TextAreaField(
        'Special Requests',
        validators=[
            Optional(),
        ],
        description="E.g., extra pillows, high floor, dietary needs. We will do our best to accommodate."
    )

    status = HiddenField(
        'Status',
        validators=[DataRequired(message="Status is required")],
        default=Booking.STATUS_RESERVED
    )

    early_hours = IntegerField(
        'Early Check-in (Hours)',
        validators=[
            Optional(),
            NumberRange(min=0, max=12, message="Early check-in must be between 0 and 12 hours")
        ],
        default=0
    )
    
    late_hours = IntegerField(
        'Late Check-out (Hours)',
        validators=[
            Optional(),
            NumberRange(min=0, max=12, message="Late check-out must be between 0 and 12 hours")
        ],
        default=0
    )
    
    submit = SubmitField('Save Booking')
    
    def validate_check_out_date(self, field):
        """Validate check-out date is after check-in date."""
        if self.check_in_date.data and field.data:
            if field.data <= self.check_in_date.data:
                raise ValidationError("Check-out date must be after check-in date")

    def validate_check_in_date(self, field):
        """Validate check-in date is not in the past."""
        if field.data:
            today = datetime.now().date()
            if field.data < today:
                raise ValidationError("Check-in date cannot be in the past")


class BookingSearchForm(FlaskForm):
    """Form for searching bookings."""
    
    room_type_id = SelectField(
        'Room Type',
        validators=[Optional()],
        coerce=int
    )
    
    check_in_date = DateField(
        'Check-in Date',
        validators=[Optional()],
        format='%Y-%m-%d'
    )
    
    check_out_date = DateField(
        'Check-out Date',
        validators=[Optional()],
        format='%Y-%m-%d'
    )
    
    status = SelectField(
        'Status',
        choices=[('', 'All')] + [(status, status) for status in Booking.STATUS_CHOICES],
        validators=[Optional()]
    )
    
    submit = SubmitField('Search') 