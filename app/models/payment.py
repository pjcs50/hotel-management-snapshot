"""
Payment model module.

This module defines the Payment model for tracking booking payments.
"""

from datetime import datetime
from db import db
from app.models import BaseModel


class Payment(BaseModel):
    """
    Payment model for tracking booking payments.
    
    Attributes:
        id: Primary key
        booking_id: Foreign key to the Booking model
        amount: Payment amount
        payment_date: Date and time of payment
        payment_type: Type of payment (e.g., credit card, cash)
        reference: Payment reference or transaction ID
        processed_by: ID of the user who processed the payment
        notes: Additional notes about the payment
        refunded: Whether the payment has been refunded
        refund_date: Date and time of refund, if applicable
        created_at: Timestamp when the payment was created
        updated_at: Timestamp when the payment was last updated
    """

    __tablename__ = 'payments'

    # Payment type constants
    TYPE_CREDIT_CARD = 'Credit Card'
    TYPE_DEBIT_CARD = 'Debit Card'
    TYPE_CASH = 'Cash'
    TYPE_BANK_TRANSFER = 'Bank Transfer'
    TYPE_LOYALTY_POINTS = 'Loyalty Points'
    TYPE_GIFT_CARD = 'Gift Card'
    TYPE_OTHER = 'Other'
    
    # Payment type choices for validation
    TYPE_CHOICES = [
        TYPE_CREDIT_CARD,
        TYPE_DEBIT_CARD,
        TYPE_CASH,
        TYPE_BANK_TRANSFER,
        TYPE_LOYALTY_POINTS,
        TYPE_GIFT_CARD,
        TYPE_OTHER
    ]

    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payment_type = db.Column(db.String(50), nullable=True)
    reference = db.Column(db.String(100), nullable=True)  # e.g., transaction ID or receipt number
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Refund information
    refunded = db.Column(db.Boolean, default=False)
    refund_date = db.Column(db.DateTime, nullable=True)
    refund_reason = db.Column(db.Text, nullable=True)
    refund_reference = db.Column(db.String(100), nullable=True)
    refunded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    booking = db.relationship('Booking', back_populates='payments')
    processor = db.relationship('User', foreign_keys=[processed_by], back_populates='processed_payments')
    refunder = db.relationship('User', foreign_keys=[refunded_by], back_populates='refunded_payments')

    def __repr__(self):
        """Provide a readable representation of a Payment instance."""
        return f'<Payment {self.id}, Booking {self.booking_id}, {self.amount:.2f}>'
    
    @property
    def is_refunded(self):
        """Check if the payment has been refunded."""
        return self.refunded
    
    def refund(self, reason=None, reference=None, refunded_by=None):
        """
        Mark the payment as refunded.
        
        Args:
            reason: Reason for the refund
            reference: Refund reference or transaction ID
            refunded_by: ID of the user processing the refund
            
        Returns:
            The updated payment
        """
        self.refunded = True
        self.refund_date = datetime.utcnow()
        self.refund_reason = reason
        self.refund_reference = reference
        self.refunded_by = refunded_by
        
        # Update the booking payment amount
        if self.booking:
            self.booking.payment_amount -= self.amount
            
            # Update booking payment status
            if self.booking.payment_amount <= 0:
                self.booking.payment_status = self.booking.PAYMENT_NOT_PAID
            elif self.booking.is_fully_paid:
                self.booking.payment_status = self.booking.PAYMENT_FULL
            else:
                self.booking.payment_status = self.booking.PAYMENT_DEPOSIT
        
        return self
    
    @classmethod
    def get_booking_payments(cls, booking_id):
        """
        Get all payments for a booking.
        
        Args:
            booking_id: ID of the booking
            
        Returns:
            List of payments for the booking
        """
        return cls.query.filter_by(
            booking_id=booking_id
        ).order_by(cls.payment_date.desc()).all()
    
    @classmethod
    def get_booking_total_paid(cls, booking_id):
        """
        Calculate the total amount paid for a booking.
        
        Args:
            booking_id: ID of the booking
            
        Returns:
            Total amount paid
        """
        from sqlalchemy import func
        
        result = db.session.query(func.sum(cls.amount)).filter(
            cls.booking_id == booking_id,
            cls.refunded == False
        ).scalar()
        
        return result or 0.0
    
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the payment
        """
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'amount': self.amount,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_type': self.payment_type,
            'reference': self.reference,
            'processed_by': self.processed_by,
            'notes': self.notes,
            'refunded': self.refunded,
            'refund_date': self.refund_date.isoformat() if self.refund_date else None,
            'refund_reason': self.refund_reason,
            'refund_reference': self.refund_reference,
            'refunded_by': self.refunded_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 