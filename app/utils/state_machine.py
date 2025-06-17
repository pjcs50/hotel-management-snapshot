"""
State machine utilities for validating status transitions.

This module provides state machine validation for Booking and Room status changes
to ensure data integrity and prevent invalid state transitions.
"""

from typing import Dict, List, Optional, Tuple


class InvalidTransitionError(Exception):
    """Exception raised when an invalid status transition is attempted."""
    pass


class BookingStateMachine:
    """
    State machine for booking status transitions.
    
    Defines valid transitions between booking statuses and provides
    validation methods.
    """
    
    # Valid transitions mapping: current_status -> [allowed_next_statuses]
    VALID_TRANSITIONS = {
        'Reserved': ['Checked In', 'Cancelled', 'No Show'],
        'Checked In': ['Checked Out'],
        'Checked Out': [],  # Terminal state
        'Cancelled': [],    # Terminal state
        'No Show': ['Cancelled']  # Allow cancellation of no-shows for cleanup
    }
    
    # Reasons for each transition type
    TRANSITION_REASONS = {
        ('Reserved', 'Checked In'): 'Guest arrived and checked in',
        ('Reserved', 'Cancelled'): 'Booking cancelled before arrival',
        ('Reserved', 'No Show'): 'Guest did not arrive',
        ('Checked In', 'Checked Out'): 'Guest completed stay and checked out',
        ('No Show', 'Cancelled'): 'No-show booking cancelled for cleanup'
    }
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """
        Check if a status transition is valid.
        
        Args:
            from_status: Current booking status
            to_status: Desired new status
            
        Returns:
            True if transition is valid, False otherwise
        """
        allowed_transitions = cls.VALID_TRANSITIONS.get(from_status, [])
        return to_status in allowed_transitions
    
    @classmethod
    def validate_transition(cls, from_status: str, to_status: str) -> None:
        """
        Validate a status transition and raise exception if invalid.
        
        Args:
            from_status: Current booking status
            to_status: Desired new status
            
        Raises:
            InvalidTransitionError: If transition is not valid
        """
        if not cls.can_transition(from_status, to_status):
            allowed = cls.VALID_TRANSITIONS.get(from_status, [])
            raise InvalidTransitionError(
                f"Invalid booking status transition from '{from_status}' to '{to_status}'. "
                f"Allowed transitions: {allowed}"
            )
    
    @classmethod
    def get_allowed_transitions(cls, from_status: str) -> List[str]:
        """
        Get all allowed transitions from a given status.
        
        Args:
            from_status: Current booking status
            
        Returns:
            List of allowed next statuses
        """
        return cls.VALID_TRANSITIONS.get(from_status, [])
    
    @classmethod
    def get_transition_reason(cls, from_status: str, to_status: str) -> Optional[str]:
        """
        Get the default reason for a status transition.
        
        Args:
            from_status: Current booking status
            to_status: New booking status
            
        Returns:
            Default reason string or None if no default reason
        """
        return cls.TRANSITION_REASONS.get((from_status, to_status))


class RoomStateMachine:
    """
    State machine for room status transitions.
    
    Defines valid transitions between room statuses and provides
    validation methods with business logic rules.
    """
    
    # Valid transitions mapping: current_status -> [allowed_next_statuses]
    VALID_TRANSITIONS = {
        'Available': ['Booked', 'Under Maintenance', 'Needs Cleaning'],
        'Booked': ['Occupied', 'Available', 'Needs Cleaning'],  # Available if booking cancelled
        'Occupied': ['Needs Cleaning', 'Under Maintenance'],  # Must clean after occupancy
        'Needs Cleaning': ['Available', 'Under Maintenance'],
        'Under Maintenance': ['Needs Cleaning']  # Must clean after maintenance
    }
    
    # Transitions that require special business logic validation
    RESTRICTED_TRANSITIONS = {
        ('Occupied', 'Available'): 'Cannot go directly from Occupied to Available - must clean first',
        ('Under Maintenance', 'Available'): 'Cannot go directly from Maintenance to Available - must clean first',
        ('Booked', 'Under Maintenance'): 'Cannot put booked room under maintenance without cancelling booking'
    }
    
    # Reasons for each transition type
    TRANSITION_REASONS = {
        ('Available', 'Booked'): 'Room reserved by guest',
        ('Available', 'Under Maintenance'): 'Room scheduled for maintenance',
        ('Available', 'Needs Cleaning'): 'Room requires cleaning',
        ('Booked', 'Occupied'): 'Guest checked in',
        ('Booked', 'Available'): 'Booking cancelled',
        ('Booked', 'Needs Cleaning'): 'Booking cancelled, room needs cleaning',
        ('Occupied', 'Needs Cleaning'): 'Guest checked out',
        ('Occupied', 'Under Maintenance'): 'Maintenance required during occupancy',
        ('Needs Cleaning', 'Available'): 'Room cleaned and ready',
        ('Needs Cleaning', 'Under Maintenance'): 'Maintenance required',
        ('Under Maintenance', 'Needs Cleaning'): 'Maintenance completed'
    }
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str, 
                      has_active_booking: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Check if a room status transition is valid with business logic.
        
        Args:
            from_status: Current room status
            to_status: Desired new status
            has_active_booking: Whether room has active booking
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check basic transition validity
        allowed_transitions = cls.VALID_TRANSITIONS.get(from_status, [])
        if to_status not in allowed_transitions:
            return False, f"Invalid transition from '{from_status}' to '{to_status}'"
        
        # Check restricted transitions
        transition_key = (from_status, to_status)
        if transition_key in cls.RESTRICTED_TRANSITIONS:
            return False, cls.RESTRICTED_TRANSITIONS[transition_key]
        
        # Business logic validation
        if has_active_booking and to_status == 'Under Maintenance':
            return False, "Cannot put room under maintenance while it has active bookings"
        
        if from_status == 'Occupied' and to_status == 'Available':
            return False, "Room must be cleaned after occupancy before becoming available"
        
        return True, None
    
    @classmethod
    def validate_transition(cls, from_status: str, to_status: str, 
                           has_active_booking: bool = False) -> None:
        """
        Validate a room status transition and raise exception if invalid.
        
        Args:
            from_status: Current room status
            to_status: Desired new status
            has_active_booking: Whether room has active booking
            
        Raises:
            InvalidTransitionError: If transition is not valid
        """
        is_valid, error_message = cls.can_transition(from_status, to_status, has_active_booking)
        if not is_valid:
            raise InvalidTransitionError(error_message)
    
    @classmethod
    def get_allowed_transitions(cls, from_status: str, 
                               has_active_booking: bool = False) -> List[str]:
        """
        Get all allowed transitions from a given status with business logic.
        
        Args:
            from_status: Current room status
            has_active_booking: Whether room has active booking
            
        Returns:
            List of allowed next statuses
        """
        base_transitions = cls.VALID_TRANSITIONS.get(from_status, [])
        
        # Filter out transitions that would fail business logic validation
        valid_transitions = []
        for to_status in base_transitions:
            is_valid, _ = cls.can_transition(from_status, to_status, has_active_booking)
            if is_valid:
                valid_transitions.append(to_status)
        
        return valid_transitions
    
    @classmethod
    def get_transition_reason(cls, from_status: str, to_status: str) -> Optional[str]:
        """
        Get the default reason for a status transition.
        
        Args:
            from_status: Current room status
            to_status: New room status
            
        Returns:
            Default reason string or None if no default reason
        """
        return cls.TRANSITION_REASONS.get((from_status, to_status))


# Convenience functions for easy integration
def validate_booking_transition(from_status: str, to_status: str) -> None:
    """Validate a booking status transition."""
    BookingStateMachine.validate_transition(from_status, to_status)


def validate_room_transition(from_status: str, to_status: str, 
                           has_active_booking: bool = False) -> None:
    """Validate a room status transition."""
    RoomStateMachine.validate_transition(from_status, to_status, has_active_booking) 