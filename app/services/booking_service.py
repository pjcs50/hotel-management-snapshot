from datetime import datetime, timedelta, timezone
import uuid
import random
import string
import json
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

    def check_room_availability(self, room_id, check_in_date, check_out_date, booking_id=None):
        """
        Check if a room is available for the given dates.

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
            # For new bookings, if room is definitively unavailable (e.g. occupied, cleaning, maintenance), return False.
            # If it's AVAILABLE or BOOKED, it might still have slots, so proceed to overlap check.
            if room.status not in [Room.STATUS_AVAILABLE, Room.STATUS_BOOKED]:
                return False
        else: # For updating an existing booking
            # If updating, the room might be Booked (by this booking) or even Occupied.
            # A room under Maintenance, however, should not be available for update.
            if room.status not in [Room.STATUS_AVAILABLE, Room.STATUS_BOOKED, Room.STATUS_OCCUPIED]:
                return False

        # Check for overlapping bookings
        # An existing booking (B) overlaps with the new/updated period (N) if:
        # B.check_in_date < N.check_out_date AND N.check_in_date < B.check_out_date
        overlapping_query = self.db_session.query(Booking).filter(
            Booking.room_id == room_id,
            Booking.check_in_date < check_out_date,  # Existing booking starts before the new period ends
            check_in_date < Booking.check_out_date,  # New period starts before the existing booking ends
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

    def calculate_booking_price(self, room_id, check_in_date, check_out_date, early_hours=0, late_hours=0):
        """
        Calculate the total price for a booking.

        Args:
            room_id: ID of the room
            check_in_date: Start date of the booking
            check_out_date: End date of the booking
            early_hours: Hours for early check-in
            late_hours: Hours for late check-out

        Returns:
            The total price for the booking
        """
        room = self.db_session.get(Room, room_id)
        if not room:
            raise ValueError(f"Room with ID {room_id} does not exist")

        room_type = room.room_type
        if not room_type:
            room_type = self.db_session.query(RoomType).get(room.room_type_id)
            if not room_type:
                 raise ValueError(f"RoomType for room ID {room_id} not found.")

        base_rate = room_type.base_rate
        total_price = 0
        current_date = check_in_date
        while current_date < check_out_date:
            seasonal_rate = self.db_session.query(SeasonalRate).filter(
                SeasonalRate.room_type_id == room_type.id,
                SeasonalRate.start_date <= current_date,
                SeasonalRate.end_date >= current_date
            ).first()
            daily_rate = base_rate * seasonal_rate.rate_multiplier if seasonal_rate else base_rate
            total_price += daily_rate
            current_date += timedelta(days=1)

        if early_hours > 0:
            total_price += (base_rate / 24) * early_hours
        if late_hours > 0:
            total_price += (base_rate / 24) * late_hours
        return total_price

    def create_booking(self, room_id, customer_id, check_in_date, check_out_date,
                       status=Booking.STATUS_RESERVED, early_hours=0, late_hours=0,
                       num_guests=1, special_requests='', source='website'):
        """
        Create a new booking.

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
        room = self.db_session.get(Room, room_id)
        if not room:
            raise ValueError(f"Room with ID {room_id} does not exist")
        customer = self.db_session.get(Customer, customer_id)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist")

        # Validate number of guests
        if num_guests > room.room_type.max_occupants:
            raise ValueError(f"Number of guests ({num_guests}) exceeds room capacity ({room.room_type.max_occupants})")

        if not self.check_room_availability(room_id, check_in_date, check_out_date):
            raise RoomNotAvailableError(f"Room {room.number} is not available for the requested dates")

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

        booking = Booking(
            room_id=room_id,
            customer_id=customer_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=status,
            early_hours=early_hours,
            late_hours=late_hours,
            num_guests=num_guests,
            special_requests_json=special_requests_json,
            confirmation_code=confirmation_code,
            source=source,
            booking_date=datetime.now(timezone.utc)
        )

        try:
            # Add booking to database
            self.db_session.add(booking)

            # We need to flush to get an ID for the booking
            self.db_session.flush()

            # Update room status
            if status in [Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN]:
                room.status = Room.STATUS_BOOKED if status == Booking.STATUS_RESERVED else Room.STATUS_OCCUPIED

                # Log room status change
                room_log = RoomStatusLog(
                    room_id=room.id,
                    old_status=Room.STATUS_AVAILABLE,
                    new_status=room.status,
                    notes=f"Status changed due to booking #{booking.id}"
                )
                self.db_session.add(room_log)

            # Log booking creation
            booking_log = BookingLog(
                booking_id=booking.id,
                action='create',
                notes=f"Booking created via {source}"
            )
            self.db_session.add(booking_log)

            # Calculate price
            print(f"Before price calculation - room_id: {booking.room_id}, customer_id: {booking.customer_id}")
            total_price = booking.calculate_price(save=True)
            print(f"Price calculation result: {total_price}")

            print("Committing transaction...")
            self.db_session.commit()
            print(f"Booking created successfully with ID: {booking.id}")
            return booking
        except IntegrityError as e:
            self.db_session.rollback()
            print(f"Database integrity error: {str(e)}")  # Log the actual error
            raise
        except Exception as e:
            self.db_session.rollback()
            import traceback
            error_details = traceback.format_exc()
            print(f"Unexpected error during booking creation: {str(e)}")
            print(f"Detailed traceback: {error_details}")
            print(f"Failed booking details - room_id: {booking.room_id}, customer_id: {booking.customer_id}, dates: {booking.check_in_date} to {booking.check_out_date}")
            raise

    def update_booking(self, booking_id, **kwargs):
        """
        Update a booking.

        Args:
            booking_id: ID of the booking to update
            **kwargs: Attributes to update

        Returns:
            The updated booking

        Raises:
            ValueError: If the booking does not exist
            RoomNotAvailableError: If trying to update dates and the room is not available
        """
        booking = self.db_session.get(Booking, booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} does not exist")

        # Ensure booking can be modified by customer (e.g., only 'Reserved' status)
        if booking.status != Booking.STATUS_RESERVED:
            raise ValueError(f"Booking cannot be modified as its status is '{booking.status}'.")

        old_room_id = booking.room_id
        old_room = self.db_session.get(Room, old_room_id)

        new_room_id = kwargs.get('room_id', old_room_id)
        new_room = self.db_session.get(Room, new_room_id)
        if not new_room:
             raise ValueError(f"Target room with ID {new_room_id} does not exist")

        # Fields that might change the price or room validity
        recalculate_price = False
        new_check_in = kwargs.get('check_in_date', booking.check_in_date)
        new_check_out = kwargs.get('check_out_date', booking.check_out_date)
        new_num_guests = kwargs.get('num_guests', booking.num_guests)

        if new_room_id != old_room_id or \
           new_check_in != booking.check_in_date or \
           new_check_out != booking.check_out_date:
            recalculate_price = True # Dates or room changed

        if new_room: # new_room is already fetched
            if new_num_guests > new_room.room_type.capacity:
                raise ValueError(f"Number of guests ({new_num_guests}) exceeds capacity ({new_room.room_type.capacity}) for room {new_room.number}.")
        else: # Should not happen if new_room_id is valid
            raise ValueError("Target room not found during update processing.")

        # Apply changes from kwargs
        for key, value in kwargs.items():
            if key == 'special_requests': # Handle special_requests via property setter
                if value and value.strip():
                    requests_list = [req.strip() for req in value.strip().split('\n') if req.strip()]
                    if requests_list:
                        booking.special_requests = requests_list
                else:
                    booking.special_requests = [] # Clear if empty
            elif hasattr(booking, key):
                setattr(booking, key, value)
                if key in ['early_hours', 'late_hours']:
                    recalculate_price = True

        if recalculate_price:
            booking.total_price = self.calculate_booking_price(
                room_id=booking.room_id, # Use the potentially updated room_id from booking object
                check_in_date=booking.check_in_date, # Use updated dates
                check_out_date=booking.check_out_date,
                early_hours=booking.early_hours or 0,
                late_hours=booking.late_hours or 0
            )

        # Update status of the new/current room for the booking
        if 'status' in kwargs: # Booking status explicitly changed
            new_booking_status = kwargs['status']
            if new_booking_status == Booking.STATUS_CHECKED_IN:
                new_room.status = Room.STATUS_OCCUPIED
            elif new_booking_status == Booking.STATUS_CHECKED_OUT:
                new_room.status = Room.STATUS_CLEANING
            elif new_booking_status == Booking.STATUS_CANCELLED:
                # Room becomes available only if no other active bookings for it
                active_bookings_on_new_room = self.db_session.query(Booking).filter(
                    Booking.room_id == new_room_id,
                    Booking.id != booking_id, # Exclude the booking being cancelled
                    Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
                ).count()
                new_room.status = Room.STATUS_BOOKED if active_bookings_on_new_room > 0 else Room.STATUS_AVAILABLE
            elif new_booking_status == Booking.STATUS_RESERVED:
                new_room.status = Room.STATUS_BOOKED
        else: # Booking status not in kwargs, infer from booking's current state (could have been set by setattr)
            if booking.status == Booking.STATUS_RESERVED:
                new_room.status = Room.STATUS_BOOKED
            elif booking.status == Booking.STATUS_CHECKED_IN:
                new_room.status = Room.STATUS_OCCUPIED
            # If booking was cancelled via kwargs but not status, this won't set room to available
            # This path assumes booking.status reflects the desired state for room status update

        # If room was changed, update the old room's status
        if new_room_id != old_room_id and old_room:
            other_active_bookings_on_old_room = self.db_session.query(Booking).filter(
                Booking.room_id == old_room_id, # Check old room
                Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
            ).count() # No need to exclude booking_id, it's no longer associated with old_room if new_room_id is different

            old_room.status = Room.STATUS_BOOKED if other_active_bookings_on_old_room > 0 else Room.STATUS_AVAILABLE

        try:
            self.db_session.commit()
            return booking
        except IntegrityError:
            self.db_session.rollback()
            raise

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
                print(f"Error updating customer stats: {e}")

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
