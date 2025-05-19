"""
Loyalty Ledger model module.

This module defines the LoyaltyLedger model for tracking loyalty points transactions.
"""

from datetime import datetime
from db import db
from app.models import BaseModel


class LoyaltyLedger(BaseModel):
    """
    LoyaltyLedger model for tracking loyalty points transactions.
    
    Attributes:
        id: Primary key
        customer_id: Foreign key to the Customer model
        points: Number of points (positive for earned, negative for redeemed)
        reason: Reason for the points transaction
        booking_id: Optional booking ID associated with the transaction
        txn_dt: Transaction date and time
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """

    __tablename__ = 'loyalty_ledger'

    # Transaction type constants
    TYPE_EARN = 'earn'
    TYPE_REDEEM = 'redeem'
    TYPE_ADJUST = 'adjust'
    TYPE_EXPIRE = 'expire'
    
    TYPE_CHOICES = [
        TYPE_EARN,
        TYPE_REDEEM,
        TYPE_ADJUST,
        TYPE_EXPIRE
    ]

    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    points = db.Column(db.Integer, nullable=False)  # Positive for earned, negative for redeemed
    reason = db.Column(db.String(255), nullable=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    txn_dt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    txn_type = db.Column(db.String(20), nullable=False, default=TYPE_EARN)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # For manual adjustments

    # Relationships
    customer = db.relationship('Customer', backref='loyalty_transactions')
    booking = db.relationship('Booking', backref='loyalty_transactions')
    staff = db.relationship('User', backref='loyalty_adjustments')

    def __repr__(self):
        """Provide a readable representation of a LoyaltyLedger instance."""
        points_str = f"+{self.points}" if self.points >= 0 else f"{self.points}"
        return f'<LoyaltyLedger {self.id}, Customer {self.customer_id}, {points_str} points>'

    @classmethod
    def get_customer_transactions(cls, customer_id, limit=None):
        """
        Get a customer's loyalty transactions.
        
        Args:
            customer_id: ID of the customer
            limit: Maximum number of transactions to return
            
        Returns:
            List of loyalty transactions
        """
        query = cls.query.filter(
            cls.customer_id == customer_id
        ).order_by(cls.txn_dt.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    @classmethod
    def get_customer_balance(cls, customer_id):
        """
        Calculate a customer's loyalty points balance.
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            Loyalty points balance
        """
        from sqlalchemy import func
        
        result = db.session.query(func.sum(cls.points)).filter(
            cls.customer_id == customer_id
        ).scalar()
        
        return result or 0
    
    @classmethod
    def earn_points(cls, customer_id, points, reason=None, booking_id=None, staff_id=None):
        """
        Record earned loyalty points.
        
        Args:
            customer_id: ID of the customer
            points: Number of points earned
            reason: Reason for earning points
            booking_id: Optional ID of the associated booking
            staff_id: Optional ID of the staff member recording the transaction
            
        Returns:
            The created LoyaltyLedger instance
        """
        ledger = cls(
            customer_id=customer_id,
            points=abs(points),  # Ensure positive
            reason=reason,
            booking_id=booking_id,
            txn_type=cls.TYPE_EARN,
            staff_id=staff_id
        )
        db.session.add(ledger)
        
        # Update the customer's loyalty points balance
        from app.models.customer import Customer
        customer = Customer.query.get(customer_id)
        if customer:
            customer.loyalty_points += abs(points)
            customer.update_loyalty_tier()
            
        return ledger
    
    @classmethod
    def redeem_points(cls, customer_id, points, reason=None, booking_id=None, staff_id=None):
        """
        Record redeemed loyalty points.
        
        Args:
            customer_id: ID of the customer
            points: Number of points redeemed
            reason: Reason for redeeming points
            booking_id: Optional ID of the associated booking
            staff_id: Optional ID of the staff member recording the transaction
            
        Returns:
            The created LoyaltyLedger instance, or None if insufficient points
        """
        # Verify the customer has enough points
        from app.models.customer import Customer
        customer = Customer.query.get(customer_id)
        if not customer or customer.loyalty_points < abs(points):
            return None
            
        ledger = cls(
            customer_id=customer_id,
            points=-abs(points),  # Ensure negative
            reason=reason,
            booking_id=booking_id,
            txn_type=cls.TYPE_REDEEM,
            staff_id=staff_id
        )
        db.session.add(ledger)
        
        # Update the customer's loyalty points balance
        customer.loyalty_points -= abs(points)
            
        return ledger
    
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the loyalty transaction
        """
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'points': self.points,
            'reason': self.reason,
            'booking_id': self.booking_id,
            'txn_type': self.txn_type,
            'txn_dt': self.txn_dt.isoformat() if self.txn_dt else None,
            'staff_id': self.staff_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 