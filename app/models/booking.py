"""
Booking model module.

This module defines the Booking model for managing hotel reservations.
"""

import json
from datetime import datetime, timedelta
from db import db
from app.models import BaseModel


class Booking(BaseModel):
    """
    Booking model for managing hotel reservations.
    
    Attributes:
        id: Primary key
        room_id: Foreign key to the Room model
        customer_id: Foreign key to the Customer model
        check_in_date: Date when the guest will check in
        check_out_date: Date when the guest will check out
        status: Booking status (Reserved/Checked In/Checked Out/Cancelled)
        early_hours: Hours before standard check-in time
        late_hours: Hours after standard check-out time
        total_price: Total price including all adjustments
        num_guests: Number of guests for the reservation
        payment_status: Status of payment
        notes: Internal notes about the reservation
        special_requests: Guest's special requests
        room_preferences: Guest's room preferences
        confirmation_code: Unique confirmation code
        created_at: Timestamp when the booking was created
        updated_at: Timestamp when the booking was last updated
    """

    __tablename__ = 'bookings'

    # Booking status constants
    STATUS_RESERVED = 'Reserved'
    STATUS_CHECKED_IN = 'Checked In'
    STATUS_CHECKED_OUT = 'Checked Out'
    STATUS_CANCELLED = 'Cancelled'
    STATUS_NO_SHOW = 'No Show'

    # Status choices for validation
    STATUS_CHOICES = [
        STATUS_RESERVED,
        STATUS_CHECKED_IN,
        STATUS_CHECKED_OUT,
        STATUS_CANCELLED,
        STATUS_NO_SHOW
    ]
    
    # Payment status constants
    PAYMENT_NOT_PAID = 'Not Paid'
    PAYMENT_DEPOSIT = 'Deposit Paid'
    PAYMENT_FULL = 'Fully Paid'
    PAYMENT_REFUNDED = 'Refunded'
    
    # Payment status choices for validation
    PAYMENT_CHOICES = [
        PAYMENT_NOT_PAID,
        PAYMENT_DEPOSIT,
        PAYMENT_FULL,
        PAYMENT_REFUNDED
    ]

    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_RESERVED)
    early_hours = db.Column(db.Integer, nullable=False, default=0)  # Hours before standard check-in
    late_hours = db.Column(db.Integer, nullable=False, default=0)   # Hours after standard check-out
    total_price = db.Column(db.Float, nullable=True)  # Total price including all adjustments
    
    # Enhanced fields
    num_guests = db.Column(db.Integer, nullable=False, default=1)
    payment_status = db.Column(db.String(20), nullable=False, default=PAYMENT_NOT_PAID)
    notes = db.Column(db.Text, nullable=True)  # Internal staff notes
    special_requests_json = db.Column(db.Text, nullable=True)  # Guest requests (JSON)
    room_preferences_json = db.Column(db.Text, nullable=True)  # Room preferences (JSON)
    confirmation_code = db.Column(db.String(20), nullable=True, unique=True)
    payment_amount = db.Column(db.Float, default=0.0)  # Amount paid so far
    deposit_amount = db.Column(db.Float, default=0.0)  # Required deposit amount
    source = db.Column(db.String(50), nullable=True)  # Booking source (e.g., website, front desk)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)  # When the booking was made
    loyalty_points_earned = db.Column(db.Integer, default=0)  # Loyalty points earned from this booking
    guest_name = db.Column(db.String(100), nullable=True)  # Name of the guest (may differ from customer)
    
    # Cancellation details
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # User who cancelled
    cancellation_date = db.Column(db.DateTime, nullable=True)
    cancellation_fee = db.Column(db.Float, default=0.0)

    # Relationships
    room = db.relationship('Room', backref='bookings')
    customer = db.relationship('Customer', backref='bookings')
    cancelling_user = db.relationship('User', foreign_keys=[cancelled_by], backref='cancelled_bookings')

    __table_args__ = (
        # Index for efficiently querying bookings by date range
        db.Index('idx_bookings_dates', 'room_id', 'check_in_date', 'check_out_date'),
        # Index for customer lookups
        db.Index('idx_bookings_customer', 'customer_id', 'status'),
    )

    def __repr__(self):
        """Provide a readable representation of a Booking instance."""
        return f'<Booking {self.id}, Room {self.room_id}, {self.check_in_date} to {self.check_out_date}>'
    
    @property
    def nights(self):
        """Calculate the number of nights for this booking."""
        return (self.check_out_date - self.check_in_date).days
    
    @property
    def is_active(self):
        """Check if the booking is active (not cancelled or checked out)."""
        return self.status in [self.STATUS_RESERVED, self.STATUS_CHECKED_IN]
    
    @property
    def is_current(self):
        """Check if today falls within the booking dates."""
        today = datetime.now().date()
        return self.check_in_date <= today <= self.check_out_date
    
    @property
    def is_upcoming(self):
        """Check if the booking is in the future."""
        today = datetime.now().date()
        return self.check_in_date > today
    
    @property
    def arrival_time(self):
        """Calculate arrival time based on early check-in."""
        if not self.early_hours:
            return None
            
        # Assuming standard check-in is 3:00 PM (15:00)
        standard_hour = 15
        arrival_hour = max(standard_hour - self.early_hours, 0)
        
        return f"{arrival_hour:02d}:00"
    
    @property
    def departure_time(self):
        """Calculate departure time based on late check-out."""
        if not self.late_hours:
            return None
            
        # Assuming standard check-out is 11:00 AM (11:00)
        standard_hour = 11
        departure_hour = min(standard_hour + self.late_hours, 23)
        
        return f"{departure_hour:02d}:00"
    
    @property
    def special_requests(self):
        """Get special requests as a list."""
        if not self.special_requests_json:
            return []
        
        try:
            return json.loads(self.special_requests_json)
        except json.JSONDecodeError:
            return []
    
    @special_requests.setter
    def special_requests(self, requests_list):
        """Set special requests from a list."""
        self.special_requests_json = json.dumps(requests_list)
    
    @property
    def room_preferences(self):
        """Get room preferences as a dictionary."""
        if not self.room_preferences_json:
            return {}
        
        try:
            return json.loads(self.room_preferences_json)
        except json.JSONDecodeError:
            return {}
    
    @room_preferences.setter
    def room_preferences(self, prefs_dict):
        """Set room preferences from a dictionary."""
        self.room_preferences_json = json.dumps(prefs_dict)
    
    @property
    def balance_due(self):
        """Calculate the remaining balance due."""
        if self.total_price is None:
            return None
            
        return max(self.total_price - self.payment_amount, 0)
    
    @property
    def is_fully_paid(self):
        """Check if the booking is fully paid."""
        if self.total_price is None or self.payment_amount is None:
            return False
            
        return self.payment_amount >= self.total_price
    
    @property
    def discount_percent(self):
        """Calculate the discount percentage if applicable."""
        if not hasattr(self, '_base_price') or not self._base_price or not self.total_price:
            return 0
            
        discount = 1 - (self.total_price / self._base_price)
        return max(round(discount * 100), 0)  # Convert to percentage and ensure non-negative
    
    def calculate_price(self, save=True):
        """
        Calculate the total price for this booking.
        
        Args:
            save: Whether to save the calculated price to the booking
            
        Returns:
            The calculated total price
        """
        from app.models.seasonal_rate import SeasonalRate
        
        # Get the base rate for the room type
        base_rate = self.room.room_type.base_rate
        
        # Calculate price for each night considering seasonal rates
        total_price = SeasonalRate.calculate_stay_price(
            self.room.room_type_id,
            self.check_in_date,
            self.check_out_date,
            base_rate
        )
        
        # Add early check-in fee (if applicable)
        if self.early_hours:
            # Simple calculation: 10% of the daily rate per early hour
            early_fee = (base_rate * 0.1) * self.early_hours
            total_price += early_fee
        
        # Add late check-out fee (if applicable)
        if self.late_hours:
            # Simple calculation: 10% of the daily rate per late hour
            late_fee = (base_rate * 0.1) * self.late_hours
            total_price += late_fee
            
        # Store the original price for discount calculation
        self._base_price = total_price
        
        # Apply loyalty discount if applicable
        if hasattr(self, 'customer') and self.customer:
            if self.customer.loyalty_tier == self.customer.TIER_GOLD:
                total_price *= 0.95  # 5% discount
            elif self.customer.loyalty_tier == self.customer.TIER_PLATINUM:
                total_price *= 0.9   # 10% discount
        
        # Round to 2 decimal places
        total_price = round(total_price, 2)
        
        if save:
            self.total_price = total_price
            
        return total_price
    
    def generate_confirmation_code(self):
        """Generate a unique confirmation code for this booking."""
        import random
        import string
        
        if self.confirmation_code:
            return self.confirmation_code
            
        # Generate a random 8-character code
        letters = string.ascii_uppercase + string.digits
        code = ''.join(random.choice(letters) for i in range(8))
        
        # Add prefix
        self.confirmation_code = f"RES-{code}"
        
        return self.confirmation_code
    
    def record_payment(self, amount, payment_type=None, reference=None):
        """
        Record a payment for this booking.
        
        Args:
            amount: Payment amount
            payment_type: Payment type (e.g., credit card, cash)
            reference: Payment reference or transaction ID
            
        Returns:
            The updated booking
        """
        from app.models.payment import Payment
        
        # Create a payment record
        payment = Payment(
            booking_id=self.id,
            amount=amount,
            payment_type=payment_type,
            reference=reference
        )
        db.session.add(payment)
        
        # Update the booking payment amount
        self.payment_amount += amount
        
        # Update payment status
        if self.is_fully_paid:
            self.payment_status = self.PAYMENT_FULL
        elif self.payment_amount > 0:
            self.payment_status = self.PAYMENT_DEPOSIT
            
        return self
    
    def cancel(self, reason=None, cancelled_by=None, apply_fee=True):
        """
        Cancel this booking.
        
        Args:
            reason: Reason for cancellation
            cancelled_by: ID of the user who cancelled the booking
            apply_fee: Whether to apply a cancellation fee
            
        Returns:
            The updated booking
        """
        self.status = self.STATUS_CANCELLED
        self.cancellation_reason = reason
        self.cancelled_by = cancelled_by
        self.cancellation_date = datetime.utcnow()
        
        # Apply cancellation fee if applicable
        if apply_fee:
            # Calculate fee based on proximity to check-in date
            days_until_checkin = (self.check_in_date - datetime.now().date()).days
            
            if days_until_checkin <= 1:  # Last-minute cancellation
                self.cancellation_fee = self.total_price * 0.5  # 50% fee
            elif days_until_checkin <= 7:  # Within a week
                self.cancellation_fee = self.total_price * 0.2  # 20% fee
            else:
                self.cancellation_fee = 0  # No fee
                
        # Release the room
        if self.room and self.room.status == self.room.STATUS_BOOKED:
            self.room.change_status(self.room.STATUS_AVAILABLE)
            
        return self
    
    def check_in(self, staff_id=None):
        """
        Check in this booking.
        
        Args:
            staff_id: ID of the staff member checking in the guest
            
        Returns:
            The updated booking
        """
        self.status = self.STATUS_CHECKED_IN
        
        # Update room status
        if self.room:
            self.room.change_status(self.room.STATUS_OCCUPIED, staff_id)
            
        # Log the check-in
        from app.models.booking_log import BookingLog
        log = BookingLog(
            booking_id=self.id,
            action='check_in',
            user_id=staff_id,
            notes=f"Checked in at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        db.session.add(log)
            
        return self
    
    def check_out(self, staff_id=None):
        """
        Check out this booking.
        
        Args:
            staff_id: ID of the staff member checking out the guest
            
        Returns:
            The updated booking
        """
        self.status = self.STATUS_CHECKED_OUT
        
        # Update room status
        if self.room:
            self.room.change_status(self.room.STATUS_CLEANING, staff_id)
            
        # Log the check-out
        from app.models.booking_log import BookingLog
        log = BookingLog(
            booking_id=self.id,
            action='check_out',
            user_id=staff_id,
            notes=f"Checked out at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        db.session.add(log)
        
        # Update customer statistics
        if self.customer:
            self.customer.update_stats_after_stay(self)
            
        return self
    
    def mark_no_show(self, staff_id=None):
        """
        Mark this booking as no-show.
        
        Args:
            staff_id: ID of the staff member marking the no-show
            
        Returns:
            The updated booking
        """
        self.status = self.STATUS_NO_SHOW
        
        # Log the no-show
        from app.models.booking_log import BookingLog
        log = BookingLog(
            booking_id=self.id,
            action='no_show',
            user_id=staff_id,
            notes=f"Marked as no-show at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        db.session.add(log)
        
        # Release the room
        if self.room and self.room.status == self.room.STATUS_BOOKED:
            self.room.change_status(self.room.STATUS_AVAILABLE, staff_id)
            
        return self
    
    @classmethod
    def find_overlapping(cls, room_id, check_in_date, check_out_date, exclude_id=None):
        """
        Find bookings that overlap with the given date range.
        
        Args:
            room_id: ID of the room
            check_in_date: Check-in date
            check_out_date: Check-out date
            exclude_id: ID of a booking to exclude from the search
            
        Returns:
            List of overlapping bookings
        """
        query = cls.query.filter(
            cls.room_id == room_id,
            cls.status.in_([cls.STATUS_RESERVED, cls.STATUS_CHECKED_IN]),
            # Either the check-in date falls within our range
            ((cls.check_in_date >= check_in_date) & (cls.check_in_date < check_out_date)) |
            # Or the check-out date falls within our range
            ((cls.check_out_date > check_in_date) & (cls.check_out_date <= check_out_date)) |
            # Or the booking completely spans our range
            ((cls.check_in_date <= check_in_date) & (cls.check_out_date >= check_out_date))
        )
        
        if exclude_id:
            query = query.filter(cls.id != exclude_id)
            
        return query.all()
    
    @classmethod
    def get_current_occupancy_rate(cls):
        """
        Calculate the current occupancy rate.
        
        Returns:
            Current occupancy rate as a percentage
        """
        from app.models.room import Room
        from sqlalchemy import func
        
        # Count total rooms
        total_rooms = Room.query.count()
        
        if not total_rooms:
            return 0
            
        # Count occupied rooms
        occupied_rooms = Room.query.filter(
            Room.status == Room.STATUS_OCCUPIED
        ).count()
        
        return round((occupied_rooms / total_rooms) * 100, 1)
    
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the booking
        """
        return {
            'id': self.id,
            'room_id': self.room_id,
            'room': self.room.to_dict() if self.room else None,
            'customer_id': self.customer_id,
            'customer': self.customer.to_dict() if self.customer else None,
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'check_out_date': self.check_out_date.isoformat() if self.check_out_date else None,
            'status': self.status,
            'early_hours': self.early_hours,
            'late_hours': self.late_hours,
            'nights': self.nights,
            'total_price': self.total_price,
            'is_active': self.is_active,
            'is_current': self.is_current,
            'num_guests': self.num_guests,
            'payment_status': self.payment_status,
            'special_requests': self.special_requests,
            'room_preferences': self.room_preferences,
            'confirmation_code': self.confirmation_code,
            'payment_amount': self.payment_amount,
            'balance_due': self.balance_due,
            'is_fully_paid': self.is_fully_paid,
            'guest_name': self.guest_name,
            'source': self.source,
            'booking_date': self.booking_date.isoformat() if self.booking_date else None,
            'loyalty_points_earned': self.loyalty_points_earned,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }