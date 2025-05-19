"""
Seasonal rate form module.

This module defines the form for managing seasonal rates.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, SelectField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange
from datetime import date


class SeasonalRateForm(FlaskForm):
    """Form for creating and editing seasonal rates."""
    
    name = StringField('Season Name', validators=[
        DataRequired(),
        Length(min=2, max=50)
    ])
    
    room_type_id = SelectField('Room Type', coerce=int, validators=[
        DataRequired()
    ])
    
    start_date = DateField('Start Date', validators=[
        DataRequired()
    ], default=date.today)
    
    end_date = DateField('End Date', validators=[
        DataRequired()
    ], default=date.today)
    
    rate_multiplier = DecimalField('Rate Multiplier', validators=[
        DataRequired(),
        NumberRange(min=0.1, max=5.0, message="Multiplier must be between 0.1 and 5.0")
    ], default=1.0)
    
    id = HiddenField() 