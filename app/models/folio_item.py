"""
Folio Item model module.

This module defines the FolioItem model for tracking guest charges.
"""

from datetime import datetime
from db import db
from app.models import BaseModel


class FolioItem(BaseModel):
    """
    FolioItem model for tracking guest charges.

    Attributes:
        id: Primary key
        booking_id: Foreign key to the Booking model
        date: Date of the charge
        description: Description of the charge
        charge_amount: Amount of the charge
        charge_type: Type of charge (e.g., room, service, minibar)
        status: Status of the charge (e.g., pending, paid, refunded)
        staff_id: ID of the staff member who added the charge
        created_at: Timestamp when the charge was created
        updated_at: Timestamp when the charge was last updated
    """

    __tablename__ = 'folio_items'

    # Charge type constants
    TYPE_ROOM = 'Room'
    TYPE_SERVICE = 'Service'
    TYPE_ROOM_SERVICE = 'Room Service'  # Added for test compatibility
    TYPE_MINIBAR = 'Minibar'
    TYPE_RESTAURANT = 'Restaurant'
    TYPE_SPA = 'Spa'
    TYPE_LAUNDRY = 'Laundry'
    TYPE_TELEPHONE = 'Telephone'
    TYPE_DAMAGE = 'Damage'
    TYPE_LATE_CHECKOUT = 'Late Checkout'
    TYPE_EARLY_CHECKIN = 'Early Checkin'
    TYPE_OTHER = 'Other'

    # Charge type choices for validation
    TYPE_CHOICES = [
        TYPE_ROOM,
        TYPE_SERVICE,
        TYPE_ROOM_SERVICE,  # Added for test compatibility
        TYPE_MINIBAR,
        TYPE_RESTAURANT,
        TYPE_SPA,
        TYPE_LAUNDRY,
        TYPE_TELEPHONE,
        TYPE_DAMAGE,
        TYPE_LATE_CHECKOUT,
        TYPE_EARLY_CHECKIN,
        TYPE_OTHER
    ]

    # Status constants
    STATUS_PENDING = 'Pending'
    STATUS_PAID = 'Paid'
    STATUS_REFUNDED = 'Refunded'
    STATUS_VOIDED = 'Voided'

    # Status choices for validation
    STATUS_CHOICES = [
        STATUS_PENDING,
        STATUS_PAID,
        STATUS_REFUNDED,
        STATUS_VOIDED
    ]

    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    description = db.Column(db.Text, nullable=False)
    charge_amount = db.Column(db.Float, nullable=False)
    charge_type = db.Column(db.String(20), nullable=False, default=TYPE_OTHER)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reference = db.Column(db.String(50), nullable=True)  # Reference number for the charge

    # Relationships
    booking = db.relationship('Booking', back_populates='folio_items')
    staff = db.relationship('User', backref='posted_charges')

    def __repr__(self):
        """Provide a readable representation of a FolioItem instance."""
        return f'<FolioItem {self.id}, Booking {self.booking_id}, {self.charge_amount:.2f}>'

    @classmethod
    def get_booking_charges(cls, booking_id):
        """
        Get all charges for a booking.

        Args:
            booking_id: ID of the booking

        Returns:
            List of charges for the booking
        """
        return cls.query.filter_by(
            booking_id=booking_id
        ).order_by(cls.date.desc()).all()

    @classmethod
    def get_booking_total_charges(cls, booking_id):
        """
        Calculate the total charges for a booking.

        Args:
            booking_id: ID of the booking

        Returns:
            Total charges for the booking
        """
        from sqlalchemy import func

        result = db.session.query(func.sum(cls.charge_amount)).filter(
            cls.booking_id == booking_id,
            cls.status != cls.STATUS_VOIDED,
            cls.status != cls.STATUS_REFUNDED
        ).scalar()

        return result or 0.0

    def void(self, staff_id=None, reason=None):
        """
        Void this charge.

        Args:
            staff_id: ID of the staff member voiding the charge
            reason: Reason for voiding the charge

        Returns:
            The updated charge
        """
        self.status = self.STATUS_VOIDED

        # Update description to include void information
        void_info = f" [VOIDED: {datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        if reason:
            void_info += f" Reason: {reason}"
        self.description += void_info

        return self

    def refund(self, staff_id=None, reason=None):
        """
        Mark this charge as refunded.

        Args:
            staff_id: ID of the staff member processing the refund
            reason: Reason for the refund

        Returns:
            The updated charge
        """
        self.status = self.STATUS_REFUNDED

        # Update description to include refund information
        refund_info = f" [REFUNDED: {datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        if reason:
            refund_info += f" Reason: {reason}"
        self.description += refund_info

        return self

    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.

        Returns:
            Dict representation of the charge
        """
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'charge_amount': self.charge_amount,
            'charge_type': self.charge_type,
            'status': self.status,
            'staff_id': self.staff_id,
            'reference': self.reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }