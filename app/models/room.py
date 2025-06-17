"""
Room model module.

This module defines the Room model for hotel room management.
"""

from datetime import datetime
from db import db
from app.models import BaseModel


class Room(BaseModel):
    """
    Room model for hotel room management.
    
    Attributes:
        id: Primary key
        number: Room number (unique)
        room_type_id: Foreign key to the RoomType model
        status: Current room status (Available/Booked/Occupied/Needs Cleaning)
        last_cleaned: Timestamp when the room was last cleaned
        created_at: Timestamp when the room was created
        updated_at: Timestamp when the room was last updated
    """

    __tablename__ = 'rooms'

    # Room status constants - Updated to match state machine
    STATUS_AVAILABLE = 'Available'
    STATUS_BOOKED = 'Booked'
    STATUS_OCCUPIED = 'Occupied'
    STATUS_CHECKOUT = 'Checkout'
    STATUS_CLEANING = 'Needs Cleaning'
    STATUS_MAINTENANCE = 'Under Maintenance'
    STATUS_OUT_OF_SERVICE = 'Out of Service'

    # Status choices for validation
    STATUS_CHOICES = [
        STATUS_AVAILABLE,
        STATUS_BOOKED,
        STATUS_OCCUPIED,
        STATUS_CHECKOUT,
        STATUS_CLEANING,
        STATUS_MAINTENANCE,
        STATUS_OUT_OF_SERVICE
    ]

    number = db.Column(db.String(10), nullable=False, unique=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id', ondelete='RESTRICT'), nullable=False)
    status = db.Column(
        db.String(20), 
        nullable=False, 
        default=STATUS_AVAILABLE, 
        index=True
    )
    last_cleaned = db.Column(db.DateTime, nullable=True)
    # floor = db.Column(db.Integer, nullable=True)  # Temporarily commented out - will add via migration

    # Relationships with proper cascade settings
    room_type = db.relationship(
        'RoomType', 
        back_populates='rooms',
        passive_deletes=True
    )
    
    # Bookings should be restricted from deletion if they exist
    bookings = db.relationship(
        'Booking',
        back_populates='room',
        cascade="save-update, merge",
        passive_deletes=True
    )
    
    # Related records that should be deleted with room
    housekeeping_tasks = db.relationship(
        'HousekeepingTask',
        foreign_keys='HousekeepingTask.room_id',
        back_populates='room',
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    maintenance_requests = db.relationship(
        'MaintenanceRequest',
        foreign_keys='MaintenanceRequest.room_id',
        back_populates='room',
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    status_logs = db.relationship(
        'RoomStatusLog',
        foreign_keys='RoomStatusLog.room_id',
        back_populates='room',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
        """Provide a readable representation of a Room instance."""
        return f'<Room {self.number}, {self.status}>'
    
    def mark_as_cleaned(self):
        """
        Mark the room as cleaned and update last_cleaned timestamp.
        Uses state machine for proper validation.
        """
        from app.utils.room_state_machine import RoomStateMachine
        
        state_machine = RoomStateMachine(db.session)
        return state_machine.change_room_status(
            self.id, 
            self.STATUS_AVAILABLE, 
            notes="Marked as cleaned"
        )
    
    def change_status(self, new_status, user_id=None, notes=None, force=False):
        """
        Change the room status using state machine validation and proper locking.
        
        Args:
            new_status: New room status
            user_id: ID of the user changing the status
            notes: Optional notes about the change
            force: Force the change (admin override)
            
        Returns:
            The updated room
            
        Raises:
            RoomTransitionError: If the transition is invalid
            ValueError: If the new status is not valid
        """
        from app.utils.room_state_machine import RoomStateMachine, RoomTransitionError
        
        if new_status not in self.STATUS_CHOICES:
            raise ValueError(f"Invalid room status: {new_status}")
        
        # Use state machine for validation and concurrent access protection
        state_machine = RoomStateMachine(db.session)
        return state_machine.change_room_status(
            self.id, 
            new_status, 
            user_id=user_id, 
            notes=notes, 
            force=force
        )
    
    def get_valid_transitions(self):
        """
        Get list of valid status transitions from current state.
        
        Returns:
            List of valid next statuses
        """
        from app.utils.room_state_machine import RoomStateMachine
        
        state_machine = RoomStateMachine(db.session)
        return state_machine.get_valid_transitions(self.status)
    
    def can_transition_to(self, new_status):
        """
        Check if room can transition to new status.
        
        Args:
            new_status: Status to check
            
        Returns:
            bool: True if transition is valid
        """
        from app.utils.room_state_machine import RoomStateMachine
        
        state_machine = RoomStateMachine(db.session)
        return state_machine.can_transition(self.status, new_status)
    
    def get_status_description(self):
        """Get human-readable description of current status."""
        from app.utils.room_state_machine import RoomStateMachine
        
        state_machine = RoomStateMachine(db.session)
        return state_machine.get_state_description(self.status)
    
    @property
    def is_available_for_booking(self):
        """Check if room is available for new bookings."""
        return self.status == self.STATUS_AVAILABLE
    
    @property
    def needs_attention(self):
        """Check if room needs staff attention."""
        return self.status in [
            self.STATUS_CHECKOUT,
            self.STATUS_CLEANING,
            self.STATUS_MAINTENANCE
        ]
    
    @property
    def is_out_of_order(self):
        """Check if room is out of order."""
        return self.status in [
            self.STATUS_MAINTENANCE,
            self.STATUS_OUT_OF_SERVICE
        ]
        
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the room
        """
        return {
            'id': self.id,
            'number': self.number,
            'room_type_id': self.room_type_id,
            'room_type': self.room_type.to_dict() if self.room_type else None,
            'status': self.status,
            'status_description': self.get_status_description(),
            'valid_transitions': self.get_valid_transitions(),
            'last_cleaned': self.last_cleaned.isoformat() if self.last_cleaned else None,
            'floor': self.floor,
            'is_available_for_booking': self.is_available_for_booking,
            'needs_attention': self.needs_attention,
            'is_out_of_order': self.is_out_of_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 