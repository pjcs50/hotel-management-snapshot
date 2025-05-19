"""
Room forms module.

This module contains forms for room management.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, ValidationError

from app.models.room import Room
from app.models.room_type import RoomType


class RoomForm(FlaskForm):
    """Form for creating and editing rooms."""
    
    number = StringField(
        'Room Number', 
        validators=[
            DataRequired(message="Room number is required"),
            Length(min=1, max=10, message="Room number must be 1-10 characters"),
        ]
    )
    
    room_type_id = SelectField(
        'Room Type',
        validators=[DataRequired(message="Room type is required")],
        coerce=int
    )
    
    status = SelectField(
        'Status',
        choices=[(status, status) for status in Room.STATUS_CHOICES],
        validators=[DataRequired(message="Status is required")]
    )
    
    submit = SubmitField('Save Room')
    
    def __init__(self, *args, **kwargs):
        """Initialize the form with room types."""
        super(RoomForm, self).__init__(*args, **kwargs)
        self.room_types = RoomType.query.all()
        self.room_type_id.choices = [
            (room_type.id, room_type.name) for room_type in self.room_types
        ]
        
    def validate_number(self, field):
        """Validate room number uniqueness."""
        # This check will be handled by the service layer
        pass


class RoomStatusForm(FlaskForm):
    """Form for changing room status."""
    
    room_id = HiddenField('Room ID', validators=[DataRequired()])
    
    status = SelectField(
        'New Status',
        choices=[(status, status) for status in Room.STATUS_CHOICES],
        validators=[DataRequired(message="Status is required")]
    )
    
    submit = SubmitField('Update Status') 