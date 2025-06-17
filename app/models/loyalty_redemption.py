"""
Loyalty Redemption model module.

This module defines the LoyaltyRedemption model for tracking reward redemptions.
"""

from datetime import datetime
from db import db
from app.models import BaseModel


class LoyaltyRedemption(BaseModel):
    """
    LoyaltyRedemption model for tracking reward redemptions by customers.
    
    Attributes:
        id: Primary key
        customer_id: Foreign key to the Customer model
        reward_id: Foreign key to the LoyaltyReward model
        points_spent: Number of points spent on this redemption
        status: Status of the redemption (pending, approved, cancelled, etc.)
        redemption_date: Date when the redemption was made
        fulfillment_date: Date when the reward was fulfilled
        booking_id: Optional booking ID associated with the redemption
        notes: Additional notes about the redemption
        staff_id: ID of the staff member who processed the redemption
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """

    __tablename__ = 'loyalty_redemptions'

    # Status constants
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_FULFILLED = 'fulfilled'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        STATUS_PENDING,
        STATUS_APPROVED,
        STATUS_FULFILLED,
        STATUS_CANCELLED,
        STATUS_REJECTED
    ]

    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    reward_id = db.Column(db.Integer, db.ForeignKey('loyalty_rewards.id'), nullable=False)
    points_spent = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    redemption_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fulfillment_date = db.Column(db.DateTime, nullable=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    customer = db.relationship('Customer', back_populates='loyalty_redemptions')
    reward = db.relationship('LoyaltyReward', backref='redemptions')
    booking = db.relationship('Booking', back_populates='loyalty_redemptions')
    staff = db.relationship('User', backref='processed_redemptions')

    def __repr__(self):
        """Provide a readable representation of a LoyaltyRedemption instance."""
        return f'<LoyaltyRedemption {self.id}, Customer {self.customer_id}, Reward {self.reward_id}, Status: {self.status}>'
    
    def approve(self, staff_id):
        """
        Approve a redemption request.
        
        Args:
            staff_id: ID of the staff member approving the request
            
        Returns:
            The updated redemption instance
        
        Raises:
            ValueError: If the redemption is not in a state that can be approved
        """
        if self.status != self.STATUS_PENDING:
            raise ValueError(f"Cannot approve redemption with status {self.status}")
            
        self.status = self.STATUS_APPROVED
        self.staff_id = staff_id
        
        return self
    
    def fulfill(self, staff_id=None):
        """
        Mark a redemption as fulfilled.
        
        Args:
            staff_id: Optional ID of the staff member fulfilling the redemption
            
        Returns:
            The updated redemption instance
            
        Raises:
            ValueError: If the redemption is not in a state that can be fulfilled
        """
        if self.status not in [self.STATUS_PENDING, self.STATUS_APPROVED]:
            raise ValueError(f"Cannot fulfill redemption with status {self.status}")
            
        self.status = self.STATUS_FULFILLED
        self.fulfillment_date = datetime.utcnow()
        
        if staff_id:
            self.staff_id = staff_id
            
        return self
    
    def cancel(self, reason=None):
        """
        Cancel a redemption.
        
        Args:
            reason: Reason for cancellation
            
        Returns:
            The updated redemption instance
            
        Raises:
            ValueError: If the redemption is not in a state that can be cancelled
        """
        if self.status not in [self.STATUS_PENDING, self.STATUS_APPROVED]:
            raise ValueError(f"Cannot cancel redemption with status {self.status}")
            
        self.status = self.STATUS_CANCELLED
        
        if reason:
            self.notes = reason
            
        # Refund points through loyalty ledger
        from app.models.loyalty_ledger import LoyaltyLedger
        
        refund = LoyaltyLedger(
            customer_id=self.customer_id,
            points=self.points_spent,  # Positive for refund
            reason=f"Refund: Cancelled redemption #{self.id}",
            txn_type=LoyaltyLedger.TYPE_ADJUST
        )
        db.session.add(refund)
        
        # Update the customer's loyalty points balance
        from app.models.customer import Customer
        customer = Customer.query.get(self.customer_id)
        if customer:
            customer.loyalty_points += self.points_spent
            
        return self
    
    def reject(self, staff_id, reason=None):
        """
        Reject a redemption request.
        
        Args:
            staff_id: ID of the staff member rejecting the request
            reason: Reason for rejection
            
        Returns:
            The updated redemption instance
            
        Raises:
            ValueError: If the redemption is not in a state that can be rejected
        """
        if self.status != self.STATUS_PENDING:
            raise ValueError(f"Cannot reject redemption with status {self.status}")
            
        self.status = self.STATUS_REJECTED
        self.staff_id = staff_id
        
        if reason:
            self.notes = reason
            
        # Refund points through loyalty ledger
        from app.models.loyalty_ledger import LoyaltyLedger
        
        refund = LoyaltyLedger(
            customer_id=self.customer_id,
            points=self.points_spent,  # Positive for refund
            reason=f"Refund: Rejected redemption #{self.id}",
            txn_type=LoyaltyLedger.TYPE_ADJUST,
            staff_id=staff_id
        )
        db.session.add(refund)
        
        # Update the customer's loyalty points balance
        from app.models.customer import Customer
        customer = Customer.query.get(self.customer_id)
        if customer:
            customer.loyalty_points += self.points_spent
            
        return self
    
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the loyalty redemption
        """
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'reward_id': self.reward_id,
            'points_spent': self.points_spent,
            'status': self.status,
            'redemption_date': self.redemption_date.isoformat() if self.redemption_date else None,
            'fulfillment_date': self.fulfillment_date.isoformat() if self.fulfillment_date else None,
            'booking_id': self.booking_id,
            'notes': self.notes,
            'staff_id': self.staff_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 