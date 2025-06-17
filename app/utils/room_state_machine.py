"""
Room State Machine for Hotel Management System.

This module implements a robust state machine for room status management,
ensuring valid state transitions and preventing concurrent status conflicts.
"""

from enum import Enum
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from db import db


class RoomState(Enum):
    """Room state enumeration with all possible states."""
    AVAILABLE = 'Available'
    BOOKED = 'Booked'
    OCCUPIED = 'Occupied'
    CHECKOUT = 'Checkout'  # Guest checked out, needs cleaning
    CLEANING = 'Needs Cleaning'
    MAINTENANCE = 'Under Maintenance'
    OUT_OF_SERVICE = 'Out of Service'


class RoomTransitionError(Exception):
    """Exception raised for invalid room state transitions."""
    pass


class RoomStateMachine:
    """
    Room state machine with validation and concurrent access protection.
    
    Enforces business rules for room state transitions and prevents
    invalid state changes that could compromise operational integrity.
    """
    
    # Define valid state transitions
    VALID_TRANSITIONS = {
        RoomState.AVAILABLE: [
            RoomState.BOOKED,
            RoomState.MAINTENANCE,
            RoomState.OUT_OF_SERVICE
        ],
        RoomState.BOOKED: [
            RoomState.OCCUPIED,
            RoomState.AVAILABLE,  # Booking cancelled
            RoomState.MAINTENANCE,
            RoomState.OUT_OF_SERVICE
        ],
        RoomState.OCCUPIED: [
            RoomState.CHECKOUT,  # Guest checked out
            RoomState.MAINTENANCE,  # Emergency maintenance
            RoomState.OUT_OF_SERVICE
        ],
        RoomState.CHECKOUT: [
            RoomState.CLEANING,  # Start cleaning process
            RoomState.MAINTENANCE,  # Issues found during checkout
            RoomState.OUT_OF_SERVICE
        ],
        RoomState.CLEANING: [
            RoomState.AVAILABLE,  # Cleaning completed
            RoomState.MAINTENANCE,  # Issues found during cleaning
            RoomState.OUT_OF_SERVICE
        ],
        RoomState.MAINTENANCE: [
            RoomState.AVAILABLE,  # Maintenance completed
            RoomState.CLEANING,  # Needs cleaning after maintenance
            RoomState.OUT_OF_SERVICE
        ],
        RoomState.OUT_OF_SERVICE: [
            RoomState.MAINTENANCE,  # Bring back for maintenance
            RoomState.CLEANING,  # Bring back for cleaning
            RoomState.AVAILABLE  # Direct to available if no issues
        ]
    }
    
    # Business rules for state transitions
    TRANSITION_RULES = {
        (RoomState.OCCUPIED, RoomState.AVAILABLE): "Cannot go directly from Occupied to Available - must checkout and clean first",
        (RoomState.CHECKOUT, RoomState.AVAILABLE): "Cannot go directly from Checkout to Available - must clean first",
        (RoomState.BOOKED, RoomState.CLEANING): "Cannot clean a booked room - cancel booking first",
        (RoomState.OCCUPIED, RoomState.CLEANING): "Cannot clean an occupied room - checkout guest first"
    }
    
    def __init__(self, db_session):
        """Initialize state machine with database session."""
        self.db_session = db_session
    
    def validate_transition(self, current_state, new_state):
        """
        Validate if a state transition is allowed.
        
        Args:
            current_state: Current room state (string or RoomState)
            new_state: Desired new state (string or RoomState)
            
        Returns:
            bool: True if transition is valid
            
        Raises:
            RoomTransitionError: If transition is invalid
        """
        # Convert strings to RoomState enums
        if isinstance(current_state, str):
            try:
                current_state = RoomState(current_state)
            except ValueError:
                raise RoomTransitionError(f"Invalid current state: {current_state}")
        
        if isinstance(new_state, str):
            try:
                new_state = RoomState(new_state)
            except ValueError:
                raise RoomTransitionError(f"Invalid new state: {new_state}")
        
        # Check if transition is allowed
        if new_state not in self.VALID_TRANSITIONS.get(current_state, []):
            # Check for specific business rule violations
            transition_key = (current_state, new_state)
            if transition_key in self.TRANSITION_RULES:
                raise RoomTransitionError(self.TRANSITION_RULES[transition_key])
            else:
                valid_states = [state.value for state in self.VALID_TRANSITIONS.get(current_state, [])]
                raise RoomTransitionError(
                    f"Invalid transition from {current_state.value} to {new_state.value}. "
                    f"Valid transitions: {', '.join(valid_states)}"
                )
        
        return True
    
    def change_room_status(self, room_id, new_status, user_id=None, notes=None, force=False):
        """
        Change room status with state machine validation and concurrent access protection.
        
        Args:
            room_id: ID of the room to update
            new_status: New status to set
            user_id: ID of user making the change
            notes: Optional notes about the change
            force: Force the change even if validation fails (admin only)
            
        Returns:
            Updated room object
            
        Raises:
            RoomTransitionError: If transition is invalid
            ValueError: If room not found
        """
        try:
            # Lock the room for update to prevent concurrent modifications
            from app.models.room import Room
            room = self.db_session.query(Room).with_for_update().get(room_id)
            
            if not room:
                raise ValueError(f"Room with ID {room_id} not found")
            
            current_status = room.status
            
            # Skip validation if forcing (admin override)
            if not force:
                self.validate_transition(current_status, new_status)
            
            # Check for maintenance conflicts
            if new_status == RoomState.AVAILABLE.value:
                if self._has_pending_maintenance(room_id):
                    raise RoomTransitionError(
                        "Cannot mark room as Available - pending maintenance requests exist"
                    )
            
            # Update room status
            room.status = new_status
            
            # Update last_cleaned timestamp if marking as available after cleaning
            if (new_status == RoomState.AVAILABLE.value and 
                current_status in [RoomState.CLEANING.value, RoomState.CHECKOUT.value]):
                room.last_cleaned = datetime.utcnow()
            
            # Log the status change
            self._log_status_change(room_id, current_status, new_status, user_id, notes, force)
            
            # Commit the transaction
            self.db_session.commit()
            
            return room
            
        except IntegrityError as e:
            self.db_session.rollback()
            raise RoomTransitionError(f"Database error during status change: {str(e)}")
        except Exception as e:
            self.db_session.rollback()
            raise
    
    def _has_pending_maintenance(self, room_id):
        """Check if room has pending maintenance requests."""
        try:
            from app.models.maintenance_request import MaintenanceRequest
            pending_count = self.db_session.query(MaintenanceRequest).filter(
                MaintenanceRequest.room_id == room_id,
                MaintenanceRequest.status.in_(['pending', 'in_progress'])
            ).count()
            return pending_count > 0
        except Exception:
            # If maintenance model doesn't exist, assume no pending maintenance
            return False
    
    def _log_status_change(self, room_id, old_status, new_status, user_id, notes, forced):
        """Log the room status change."""
        try:
            from app.models.room_status_log import RoomStatusLog
            
            log_notes = notes or ""
            if forced:
                log_notes = f"[FORCED CHANGE] {log_notes}".strip()
            
            log = RoomStatusLog(
                room_id=room_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=user_id,
                notes=log_notes,
                created_at=datetime.utcnow()
            )
            self.db_session.add(log)
            
        except Exception as e:
            # Log the error but don't fail the status change
            print(f"Warning: Could not log status change: {str(e)}")
    
    def get_valid_transitions(self, current_state):
        """
        Get list of valid transitions from current state.
        
        Args:
            current_state: Current room state
            
        Returns:
            List of valid next states
        """
        if isinstance(current_state, str):
            try:
                current_state = RoomState(current_state)
            except ValueError:
                return []
        
        return [state.value for state in self.VALID_TRANSITIONS.get(current_state, [])]
    
    def get_state_description(self, state):
        """Get human-readable description of room state."""
        descriptions = {
            RoomState.AVAILABLE: "Ready for new guests",
            RoomState.BOOKED: "Reserved by guest",
            RoomState.OCCUPIED: "Guest currently staying",
            RoomState.CHECKOUT: "Guest checked out, awaiting cleaning",
            RoomState.CLEANING: "Being cleaned by housekeeping",
            RoomState.MAINTENANCE: "Under maintenance or repair",
            RoomState.OUT_OF_SERVICE: "Temporarily unavailable"
        }
        
        if isinstance(state, str):
            try:
                state = RoomState(state)
            except ValueError:
                return "Unknown state"
        
        return descriptions.get(state, "Unknown state")
    
    def can_transition(self, current_state, new_state):
        """
        Check if a transition is valid without raising an exception.
        
        Args:
            current_state: Current room state
            new_state: Desired new state
            
        Returns:
            bool: True if transition is valid
        """
        try:
            self.validate_transition(current_state, new_state)
            return True
        except RoomTransitionError:
            return False 