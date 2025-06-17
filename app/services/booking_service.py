from datetime import datetime, timedelta, timezone
import uuid
import random
import string
import json
import traceback
from sqlalchemy import or_, and_, func
from sqlalchemy.exc import IntegrityError
from app.models.room import Room
from app.models.booking import Booking
from app.models.customer import Customer
from app.models.room_type import RoomType
from app.models.seasonal_rate import SeasonalRate
from app.models.booking_log import BookingLog
from app.models.room_status_log import RoomStatusLog
from db import db
from decimal import Decimal
from app.utils.error_handling import (
    error_handler, ErrorContext, ErrorSeverity, ErrorCategory,
    DatabaseError, ValidationError, BusinessLogicError
)
import logging

logger = logging.getLogger(__name__)

class RoomNotAvailableError(Exception):
    """Exception raised when a room is not available for the requested dates."""
    pass

class BookingService:
    def __init__(self, db_session):
        self.db_session = db_session

    def _generate_confirmation_code(self, length=8):
        """
        Generate a unique confirmation code for a booking.

        Args:
            length: Length of the confirmation code

        Returns:
            A unique confirmation code
        """
        # Generate a random string of uppercase letters and digits
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choice(chars) for _ in range(length))

        # Check if the code already exists
        while self.db_session.query(Booking).filter_by(confirmation_code=code).first():
            code = ''.join(random.choice(chars) for _ in range(length))

        return code

    def get_booking_by_id(self, booking_id):
        """
        Get a booking by ID.

        Args:
            booking_id: ID of the booking

        Returns:
            The booking or None if not found
        """
        return self.db_session.get(Booking, booking_id)

    def get_booking_by_id_and_customer(self, booking_id, customer_id):
        """
        Get a booking by ID that belongs to a specific customer.

        Args:
            booking_id: ID of the booking
            customer_id: ID of the customer

        Returns:
            The booking or None if not found or doesn't belong to customer
        """
        return self.db_session.query(Booking).filter(
            Booking.id == booking_id,
            Booking.customer_id == customer_id
        ).first()

    def is_booking_owned_by_customer(self, booking_id, customer_id):
        """
        Check if a booking is owned by a customer.

        Args:
            booking_id: ID of the booking
            customer_id: ID of the customer

        Returns:
            True if the booking is owned by the customer, False otherwise
        """
        booking = self.get_booking_by_id(booking_id)
        return booking is not None and booking.customer_id == customer_id

    def check_room_availability_with_lock(self, room_id, check_in_date, check_out_date, booking_id=None):
        """
        Check if a room is available for the given dates with database-level locking.
        This method must be called within a transaction to prevent race conditions.

        Args:
            room_id: ID of the room to check
            check_in_date: Start date of the booking
            check_out_date: End date of the booking
            booking_id: ID of the current booking (for updates)

        Returns:
            True if the room is available, False otherwise
        """
        # Lock the room row for update to prevent concurrent modifications
        room = self.db_session.query(Room).with_for_update().get(room_id)
        if not room:
            return False

        # Preliminary room status check
        if booking_id is None:  # For a new booking
            # For new bookings, room must be available or booked (with no overlapping reservations)
            if room.status not in [Room.STATUS_AVAILABLE, Room.STATUS_BOOKED]:
                return False
        else:  # For updating an existing booking
            # If updating, the room might be Booked or Occupied
            if room.status not in [Room.STATUS_AVAILABLE, Room.STATUS_BOOKED, Room.STATUS_OCCUPIED]:
                return False

        # Check for overlapping bookings with row-level locking to prevent race conditions
        overlapping_query = self.db_session.query(Booking).with_for_update().filter(
            Booking.room_id == room_id,
            Booking.check_in_date < check_out_date,
            check_in_date < Booking.check_out_date,
            Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
        )

        if booking_id:  # If updating, exclude the booking being updated
            overlapping_query = overlapping_query.filter(Booking.id != booking_id)

        return overlapping_query.count() == 0

    def check_room_availability(self, room_id, check_in_date, check_out_date, booking_id=None):
        """
        Check if a room is available for the given dates.
        This is a non-locking version for read-only checks only.
        WARNING: DO NOT USE THIS METHOD FOR BOOKING CREATION - Use check_room_availability_with_lock instead.

        Args:
            room_id: ID of the room to check
            check_in_date: Start date of the booking
            check_out_date: End date of the booking
            booking_id: ID of the current booking (for updates)

        Returns:
            True if the room is available, False otherwise
        """
        room = self.db_session.get(Room, room_id)
        if not room:
            return False

        # Preliminary room status check
        if booking_id is None: # For a new booking
            if room.status not in [Room.STATUS_AVAILABLE, Room.STATUS_BOOKED]:
                return False
        else: # For updating an existing booking
            if room.status not in [Room.STATUS_AVAILABLE, Room.STATUS_BOOKED, Room.STATUS_OCCUPIED]:
                return False

        # Check for overlapping bookings
        overlapping_query = self.db_session.query(Booking).filter(
            Booking.room_id == room_id,
            Booking.check_in_date < check_out_date,
            check_in_date < Booking.check_out_date,
            Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
        )

        if booking_id: # If updating, exclude the booking being updated from the overlap check
            overlapping_query = overlapping_query.filter(Booking.id != booking_id)

        return overlapping_query.count() == 0

    def get_available_rooms(self, room_type_id=None, check_in_date=None, check_out_date=None):
        """
        Get all available rooms for the given dates and room type.

        Args:
            room_type_id: Optional ID of the room type to filter by
            check_in_date: Start date of the booking
            check_out_date: End date of the booking

        Returns:
            List of available rooms
        """
        if not check_in_date or not check_out_date:
            check_in_date = datetime.now().date()
            check_out_date = check_in_date + timedelta(days=1)

        query = self.db_session.query(Room).filter(Room.status == Room.STATUS_AVAILABLE)

        if room_type_id:
            query = query.filter(Room.room_type_id == room_type_id)

        potential_rooms = query.all()

        unavailable_room_ids_query = self.db_session.query(Booking.room_id).filter(
            Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN]),
            or_(
                and_(Booking.check_in_date <= check_in_date, check_in_date < Booking.check_out_date),
                and_(Booking.check_in_date < check_out_date, check_out_date <= Booking.check_out_date),
                and_(check_in_date <= Booking.check_in_date, Booking.check_out_date <= check_out_date)
            )
        )
        unavailable_room_ids = [room_id for (room_id,) in unavailable_room_ids_query.all()]
        return [room for room in potential_rooms if room.id not in unavailable_room_ids]

    def calculate_booking_price_atomic(self, room_id, check_in_date, check_out_date, early_hours=0, late_hours=0):
        """
        Calculate the total price for a booking atomically within a transaction.
        This is the single source of truth for price calculations.
        This method locks the seasonal rate data to prevent race conditions.

        Args:
            room_id: ID of the room
            check_in_date: Start date of the booking
            check_out_date: End date of the booking
            early_hours: Hours for early check-in
            late_hours: Hours for late check-out

        Returns:
            The total price for the booking as Decimal
        """
        # Get room and room type with locking
        room = self.db_session.query(Room).with_for_update().get(room_id)
        if not room:
            raise ValueError(f"Room with ID {room_id} does not exist")

        room_type = room.room_type
        if not room_type:
            room_type = self.db_session.query(RoomType).with_for_update().get(room.room_type_id)
            if not room_type:
                raise ValueError(f"RoomType for room ID {room_id} not found.")

        base_rate = Decimal(str(room_type.base_rate))
        total_price = Decimal('0')
        current_date = check_in_date
        
        while current_date < check_out_date:
            # Lock seasonal rates to prevent changes during calculation
            seasonal_rate = self.db_session.query(SeasonalRate).with_for_update().filter(
                SeasonalRate.room_type_id == room_type.id,
                SeasonalRate.start_date <= current_date,
                SeasonalRate.end_date >= current_date,
                SeasonalRate.active == True
            ).order_by(SeasonalRate.priority.desc()).first()
            
            if seasonal_rate:
                # Use day-specific multiplier if available
                day_multiplier = seasonal_rate.get_day_rate_multiplier(current_date)
                daily_rate = base_rate * Decimal(str(day_multiplier))
            else:
                # Check for weekend rates
                if current_date.weekday() >= 5:  # Weekend (Saturday=5, Sunday=6)
                    weekend_rate = self.db_session.query(SeasonalRate).with_for_update().filter(
                        SeasonalRate.room_type_id == room_type.id,
                        SeasonalRate.rate_type == SeasonalRate.TYPE_WEEKEND,
                        SeasonalRate.active == True
                    ).order_by(SeasonalRate.priority.desc()).first()
                    
                    if weekend_rate:
                        daily_rate = base_rate * Decimal(str(weekend_rate.rate_multiplier))
                    else:
                        daily_rate = base_rate
                else:
                    daily_rate = base_rate
            
            total_price += daily_rate
            current_date += timedelta(days=1)

        # Add early check-in fee
        if early_hours > 0:
            early_fee = (base_rate / 24) * Decimal(str(early_hours))
            total_price += early_fee

        # Add late check-out fee
        if late_hours > 0:
            late_fee = (base_rate / 24) * Decimal(str(late_hours))
            total_price += late_fee
            
        return total_price

    def calculate_booking_price(self, room_id, check_in_date, check_out_date, early_hours=0, late_hours=0):
        """
        DEPRECATED: Use calculate_booking_price_atomic instead.
        This method is kept for backward compatibility but delegates to the atomic version.
        """
        return self.calculate_booking_price_atomic(room_id, check_in_date, check_out_date, early_hours, late_hours)

    def create_booking(self, room_id, customer_id, check_in_date, check_out_date,
                       status=Booking.STATUS_RESERVED, early_hours=0, late_hours=0,
                       num_guests=1, special_requests='', source='website'):
        """
        Create a new booking with database-level locking to prevent race conditions.
        All operations are performed atomically within a single transaction.

        Args:
            room_id: ID of the room to book
            customer_id: ID of the customer making the booking
            check_in_date: Start date of the booking
            check_out_date: End date of the booking
            status: Initial booking status (default: Reserved)
            early_hours: Hours for early check-in
            late_hours: Hours for late check-out
            num_guests: Number of guests for the reservation
            special_requests: Special requests for the booking
            source: Source of the booking (e.g., website, front desk)

        Returns:
            The newly created booking

        Raises:
            RoomNotAvailableError: If the room is not available for the requested dates
            ValueError: If the room or customer does not exist
        """
        # Start a transaction with proper error handling
        try:
            # Lock the room and customer records to prevent concurrent modifications
            room = self.db_session.query(Room).with_for_update().get(room_id)
            if not room:
                raise ValueError(f"Room with ID {room_id} does not exist")

            customer = self.db_session.query(Customer).with_for_update().get(customer_id)
            if not customer:
                raise ValueError(f"Customer with ID {customer_id} does not exist")

            # Validate number of guests
            if num_guests > room.room_type.max_occupants:
                raise ValueError(f"Number of guests ({num_guests}) exceeds room capacity ({room.room_type.max_occupants})")

            # Check room availability with locking (prevents double booking)
            if not self.check_room_availability_with_lock(room_id, check_in_date, check_out_date):
                raise RoomNotAvailableError(f"Room {room.number} is not available for the requested dates")

            # Calculate price atomically (within the same transaction)
            total_price = self.calculate_booking_price_atomic(room_id, check_in_date, check_out_date, early_hours, late_hours)

            # Generate confirmation code
            confirmation_code = self._generate_confirmation_code()

            # Process special requests
            special_requests_json = None
            if special_requests:
                if isinstance(special_requests, list):
                    special_requests_json = json.dumps(special_requests)
                else:
                    # Convert string to list of requests
                    requests_list = [req.strip() for req in special_requests.strip().split('\n') if req.strip()]
                    special_requests_json = json.dumps(requests_list) if requests_list else None

            # Create booking with calculated price
            booking = Booking(
                room_id=room_id,
                customer_id=customer_id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                status=status,
                early_hours=early_hours,
                late_hours=late_hours,
                total_price=float(total_price),  # Store as float but calculated as Decimal for precision
                num_guests=num_guests,
                special_requests_json=special_requests_json,
                confirmation_code=confirmation_code,
                source=source,
                booking_date=datetime.now(timezone.utc)
            )

            # Add booking to database
            self.db_session.add(booking)

            # We need to flush to get an ID for the booking
            self.db_session.flush()

            # Update room status atomically
            old_room_status = room.status
            if status in [Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN]:
                new_room_status = Room.STATUS_BOOKED if status == Booking.STATUS_RESERVED else Room.STATUS_OCCUPIED
                room.status = new_room_status

                # Log room status change
                room_log = RoomStatusLog(
                    room_id=room.id,
                    old_status=old_room_status,
                    new_status=new_room_status,
                    notes=f"Status changed due to booking #{booking.id}"
                )
                self.db_session.add(room_log)

            # Log booking creation
            booking_log = BookingLog(
                booking_id=booking.id,
                action='create',
                notes=f"Booking created via {source} with total price ${total_price}"
            )
            self.db_session.add(booking_log)

            # Commit the entire transaction atomically
            self.db_session.commit()
            logger.info(f"Booking created successfully with ID: {booking.id}, Price: ${total_price}")
            return booking

        except (RoomNotAvailableError, ValueError):
            self.db_session.rollback()
            raise
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to create booking: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Enhanced error handling with specific error types
            context = ErrorContext(
                operation="create_booking",
                additional_data={
                    'room_id': room_id,
                    'customer_id': customer_id,
                    'check_in_date': str(check_in_date),
                    'check_out_date': str(check_out_date)
                }
            )
            
            # Classify and handle the error appropriately
            if isinstance(e, IntegrityError):
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.DATABASE
                )
                raise DatabaseError(f"Database integrity error during booking creation: {error_result['user_message']}")
            
            elif "room not available" in str(e).lower() or "overlapping" in str(e).lower():
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.BUSINESS_LOGIC
                )
                raise BusinessLogicError(f"Room availability conflict: {str(e)}")
            
            elif "validation" in str(e).lower() or "invalid" in str(e).lower():
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.VALIDATION
                )
                raise ValidationError(f"Booking validation failed: {str(e)}")
            
            else:
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.SYSTEM
                )
                raise DatabaseError(f"Unexpected error during booking creation: {error_result['user_message']}")

    def update_booking(self, booking_id, **kwargs):
        """
        Update a booking with atomic operations and proper locking.

        Args:
            booking_id: ID of the booking to update
            **kwargs: Attributes to update

        Returns:
            The updated booking

        Raises:
            ValueError: If the booking does not exist
            RoomNotAvailableError: If trying to update dates and the room is not available
        """
        try:
            # Lock the booking for update
            booking = self.db_session.query(Booking).with_for_update().get(booking_id)
            if not booking:
                raise ValueError(f"Booking with ID {booking_id} does not exist")

            # Ensure booking can be modified
            if booking.status not in [Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN]:
                raise ValueError(f"Booking cannot be modified as its status is '{booking.status}'.")

            old_room_id = booking.room_id
            old_room = self.db_session.query(Room).with_for_update().get(old_room_id)

            new_room_id = kwargs.get('room_id', old_room_id)
            new_room = self.db_session.query(Room).with_for_update().get(new_room_id)
            if not new_room:
                raise ValueError(f"Target room with ID {new_room_id} does not exist")

            # Fields that might change the price or room validity
            recalculate_price = False
            new_check_in = kwargs.get('check_in_date', booking.check_in_date)
            new_check_out = kwargs.get('check_out_date', booking.check_out_date)
            new_num_guests = kwargs.get('num_guests', booking.num_guests)
            new_early_hours = kwargs.get('early_hours', booking.early_hours)
            new_late_hours = kwargs.get('late_hours', booking.late_hours)

            # Check if we need to recalculate price or validate room availability
            if (new_room_id != old_room_id or 
                new_check_in != booking.check_in_date or 
                new_check_out != booking.check_out_date or
                new_early_hours != booking.early_hours or
                new_late_hours != booking.late_hours):
                
                recalculate_price = True
                
                # Check new room availability with locking
                if not self.check_room_availability_with_lock(new_room_id, new_check_in, new_check_out, booking_id):
                    raise RoomNotAvailableError(f"Room {new_room.number} is not available for the requested dates")

            # Validate number of guests
            if new_num_guests > new_room.room_type.max_occupants:
                raise ValueError(f"Number of guests ({new_num_guests}) exceeds room capacity ({new_room.room_type.max_occupants})")

            # Update booking fields
            for key, value in kwargs.items():
                if hasattr(booking, key):
                    setattr(booking, key, value)

            # Recalculate price if necessary
            if recalculate_price:
                new_total_price = self.calculate_booking_price_atomic(
                    new_room_id, new_check_in, new_check_out, new_early_hours, new_late_hours
                )
                booking.total_price = float(new_total_price)

            # Handle room status changes atomically
            if new_room_id != old_room_id:
                # Release old room if it was booked by this booking
                if old_room.status == Room.STATUS_BOOKED:
                    # Check if there are other active bookings for this room
                    other_bookings = self.db_session.query(Booking).filter(
                        Booking.room_id == old_room_id,
                        Booking.id != booking_id,
                        Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
                    ).count()
                    
                    if other_bookings == 0:
                        old_room.status = Room.STATUS_AVAILABLE
                        
                        # Log room status change
                        room_log = RoomStatusLog(
                            room_id=old_room.id,
                            old_status=Room.STATUS_BOOKED,
                            new_status=Room.STATUS_AVAILABLE,
                            notes=f"Room released due to booking #{booking.id} room change"
                        )
                        self.db_session.add(room_log)

                # Book new room
                if booking.status in [Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN]:
                    new_room_status = Room.STATUS_BOOKED if booking.status == Booking.STATUS_RESERVED else Room.STATUS_OCCUPIED
                    old_new_room_status = new_room.status
                    new_room.status = new_room_status
                    
                    # Log room status change
                    room_log = RoomStatusLog(
                        room_id=new_room.id,
                        old_status=old_new_room_status,
                        new_status=new_room_status,
                        notes=f"Status changed due to booking #{booking.id} room change"
                    )
                    self.db_session.add(room_log)

            # Log booking update
            booking_log = BookingLog(
                booking_id=booking.id,
                action='update',
                notes=f"Booking updated with changes: {', '.join(kwargs.keys())}"
            )
            self.db_session.add(booking_log)

            # Commit all changes atomically
            self.db_session.commit()
            return booking

        except (RoomNotAvailableError, ValueError):
            self.db_session.rollback()
            raise
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Unexpected error during booking update: {str(e)}")
            logger.error(f"Detailed traceback: {traceback.format_exc()}")
            raise e

    def cancel_booking(self, booking_id, reason='', cancelled_by=None):
        """
        Cancel a booking.

        Args:
            booking_id: ID of the booking to cancel
            reason: Reason for cancellation
            cancelled_by: ID of the user who cancelled the booking

        Returns:
            The cancelled booking

        Raises:
            ValueError: If the booking does not exist or is already checked in
        """
        try:
            booking = self.db_session.get(Booking, booking_id)
            if not booking:
                raise ValueError(f"Booking with ID {booking_id} does not exist")

            if booking.status == Booking.STATUS_CHECKED_IN:
                raise ValueError("Cannot cancel a booking that is already checked in")

            # Update booking status
            booking.status = Booking.STATUS_CANCELLED
            booking.cancellation_reason = reason
            booking.cancelled_by = cancelled_by
            booking.cancellation_date = datetime.now(timezone.utc)

            # Calculate cancellation fee based on how close to check-in date
            days_until_checkin = (booking.check_in_date - datetime.now(timezone.utc).date()).days
            if days_until_checkin <= 1:  # Less than 24 hours
                booking.cancellation_fee = booking.total_price * 0.5  # 50% fee
            elif days_until_checkin <= 3:  # Less than 72 hours
                booking.cancellation_fee = booking.total_price * 0.25  # 25% fee
            else:
                booking.cancellation_fee = 0  # No fee

            # Update room status
            room = booking.room
            if not room:
                room = self.db_session.get(Room, booking.room_id)

            if room:
                old_status = room.status

                # Check if there are other active bookings for this room
                other_active_bookings = self.db_session.query(Booking).filter(
                    Booking.room_id == room.id,
                    Booking.id != booking_id,
                    Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
                ).count()

                # Update room status
                new_status = Room.STATUS_BOOKED if other_active_bookings > 0 else Room.STATUS_AVAILABLE
                room.status = new_status

                # Log room status change
                if old_status != new_status:
                    room_log = RoomStatusLog(
                        room_id=room.id,
                        old_status=old_status,
                        new_status=new_status,
                        changed_by=cancelled_by,
                        notes=f"Status changed due to booking #{booking.id} cancellation"
                    )
                    self.db_session.add(room_log)

            # Log booking cancellation
            booking_log = BookingLog(
                booking_id=booking.id,
                action='cancel',
                user_id=cancelled_by,
                notes=f"Booking cancelled. Reason: {reason}"
            )
            self.db_session.add(booking_log)

            self.db_session.commit()
            return booking
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to cancel booking {booking_id}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Enhanced error handling
            context = ErrorContext(
                operation="cancel_booking",
                additional_data={
                    'booking_id': booking_id,
                    'reason': reason,
                    'cancelled_by': cancelled_by
                }
            )
            
            # Classify and handle the error appropriately
            if isinstance(e, IntegrityError):
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.DATABASE
                )
                raise DatabaseError(f"Database error during booking cancellation: {error_result['user_message']}")
            
            elif "not found" in str(e).lower() or "does not exist" in str(e).lower():
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.VALIDATION
                )
                raise ValidationError(f"Booking not found: {booking_id}")
            
            elif "cannot cancel" in str(e).lower() or "already" in str(e).lower():
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.BUSINESS_LOGIC
                )
                raise BusinessLogicError(f"Booking cancellation not allowed: {str(e)}")
            
            else:
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.SYSTEM
                )
                raise DatabaseError(f"Unexpected error during booking cancellation: {error_result['user_message']}")

    def check_in(self, booking_id, staff_id=None):
        """
        Check in a booking.

        Args:
            booking_id: ID of the booking to check in
            staff_id: ID of the staff member checking in the guest

        Returns:
            The checked-in booking

        Raises:
            ValueError: If the booking does not exist or is not in a valid state for check-in
        """
        booking = self.db_session.get(Booking, booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} does not exist")

        if booking.status != Booking.STATUS_RESERVED:
            raise ValueError(f"Cannot check in booking with status {booking.status}")

        # Update booking status
        booking.status = Booking.STATUS_CHECKED_IN

        # Update room status
        room = booking.room
        if not room:
            room = self.db_session.get(Room, booking.room_id)

        if room:
            old_status = room.status
            room.status = Room.STATUS_OCCUPIED

            # Log room status change
            room_log = RoomStatusLog(
                room_id=room.id,
                old_status=old_status,
                new_status=Room.STATUS_OCCUPIED,
                changed_by=staff_id,
                notes=f"Status changed due to check-in of booking #{booking.id}"
            )
            self.db_session.add(room_log)

        # Log booking check-in
        booking_log = BookingLog(
            booking_id=booking.id,
            action='check_in',
            user_id=staff_id,
            notes=f"Guest checked in at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        )
        self.db_session.add(booking_log)

        self.db_session.commit()
        return booking

    def check_out(self, booking_id, staff_id=None):
        """
        Check out a booking.

        Args:
            booking_id: ID of the booking to check out
            staff_id: ID of the staff member checking out the guest

        Returns:
            The checked-out booking

        Raises:
            ValueError: If the booking does not exist or is not in a valid state for check-out
        """
        booking = self.db_session.get(Booking, booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} does not exist")

        if booking.status != Booking.STATUS_CHECKED_IN:
            raise ValueError(f"Cannot check out booking with status {booking.status}")

        # Update booking status
        booking.status = Booking.STATUS_CHECKED_OUT

        # Update room status
        room = booking.room
        if not room:
            room = self.db_session.get(Room, booking.room_id)

        if room:
            old_status = room.status
            room.status = Room.STATUS_CLEANING

            # Log room status change
            room_log = RoomStatusLog(
                room_id=room.id,
                old_status=old_status,
                new_status=Room.STATUS_CLEANING,
                changed_by=staff_id,
                notes=f"Status changed due to check-out of booking #{booking.id}"
            )
            self.db_session.add(room_log)

        # Log booking check-out
        booking_log = BookingLog(
            booking_id=booking.id,
            action='check_out',
            user_id=staff_id,
            notes=f"Guest checked out at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        )
        self.db_session.add(booking_log)

        # Update customer statistics if applicable
        if booking.customer:
            try:
                booking.customer.update_stats_after_stay(booking)
            except Exception as e:
                # Log the error but continue with check-out
                logger.error(f"Error updating customer stats: {e}")

        self.db_session.commit()
        return booking

    def get_bookings_by_customer(self, customer_id):
        """
        Get all bookings for a customer.

        Args:
            customer_id: ID of the customer

        Returns:
            List of bookings for the customer
        """
        return self.db_session.query(Booking).filter_by(customer_id=customer_id).all()

    def get_bookings_by_room(self, room_id):
        """
        Get all bookings for a room.

        Args:
            room_id: ID of the room

        Returns:
            List of bookings for the room
        """
        return self.db_session.query(Booking).filter_by(room_id=room_id).all()

    def get_bookings_by_date_range(self, start_date, end_date):
        """
        Get all bookings for a date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range

        Returns:
            List of bookings that overlap with the date range
        """
        return self.db_session.query(Booking).filter(
            or_(
                and_(Booking.check_in_date <= start_date, start_date < Booking.check_out_date),
                and_(Booking.check_in_date < end_date, end_date <= Booking.check_out_date),
                and_(start_date <= Booking.check_in_date, Booking.check_out_date <= end_date)
            )
        ).all()

    def get_bookings_by_status(self, status):
        """
        Get all bookings with a specific status.

        Args:
            status: Booking status to filter by

        Returns:
            List of bookings with the specified status
        """
        return self.db_session.query(Booking).filter_by(status=status).all()

    def get_availability_calendar_data(self, start_date, end_date, room_type_id=None):
        """
        Get availability data for calendar display.

        Args:
            start_date: Start date of the calendar range
            end_date: End date of the calendar range
            room_type_id: Optional room type ID to filter by

        Returns:
            A dictionary containing availability data for the date range:
            {
                'dates': ['2024-05-27', '2024-05-28', ...],
                'room_types': [{'id': 1, 'name': 'Standard', ...}, ...],
                'availability': {
                    'room_type_id_1': {
                        '2024-05-27': {'available': 5, 'total': 10},
                        '2024-05-28': {'available': 8, 'total': 10},
                        ...
                    },
                    ...
                }
            }
        """
        date_range_str = []
        current_date = start_date
        while current_date <= end_date:
            date_range_str.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

        room_types_query = self.db_session.query(RoomType)
        if room_type_id:
            room_types_query = room_types_query.filter_by(id=room_type_id)
        room_types = room_types_query.all()

        result = {'dates': date_range_str, 'room_types': [rt.to_dict() for rt in room_types], 'availability': {}}

        for rt_obj in room_types:
            rt_id_str = str(rt_obj.id)
            result['availability'][rt_id_str] = {}
            total_rooms = self.db_session.query(Room).filter_by(room_type_id=rt_obj.id).count()

            for date_str_val in date_range_str:
                date_obj_val = datetime.strptime(date_str_val, '%Y-%m-%d').date()
                booked_rooms_count = self.db_session.query(func.count(Booking.id)).join(Room).filter(
                    Room.room_type_id == rt_obj.id,
                    Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN]),
                    Booking.check_in_date <= date_obj_val,
                    Booking.check_out_date > date_obj_val
                ).scalar()
                available_rooms = max(0, total_rooms - booked_rooms_count)
                result['availability'][rt_id_str][date_str_val] = {'available': available_rooms, 'total': total_rooms}
        return result
