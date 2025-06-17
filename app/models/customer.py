"""
Customer model module.

This module defines the Customer model for storing customer information.
"""

import json
from datetime import datetime
from db import db
from app.models import BaseModel


class Customer(BaseModel):
    """
    Customer model for storing customer information.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to the User model
        name: Customer's full name
        phone: Customer's phone number
        address: Customer's address
        email: Customer's email address
        emergency_contact: Customer's emergency contact information
        preferences: JSON string of customer preferences
        documents: JSON string of customer document information
        notes: Staff notes about the customer
        loyalty_points: Customer's loyalty points balance
        loyalty_tier: Customer's loyalty tier
        profile_complete: Whether the customer's profile is complete
        created_at: Timestamp when the customer was created
        updated_at: Timestamp when the customer was last updated
    """

    __tablename__ = 'customers'

    # Loyalty tier constants
    TIER_STANDARD = 'Standard'
    TIER_SILVER = 'Silver'
    TIER_GOLD = 'Gold'
    TIER_PLATINUM = 'Platinum'
    
    TIER_CHOICES = [
        TIER_STANDARD,
        TIER_SILVER,
        TIER_GOLD,
        TIER_PLATINUM
    ]

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    emergency_contact = db.Column(db.Text, nullable=True)
    profile_complete = db.Column(db.Boolean, default=False)
    
    # Enhanced fields
    preferences_json = db.Column(db.Text, nullable=True)  # JSON string of preferences
    documents_json = db.Column(db.Text, nullable=True)  # JSON string of document info
    notes = db.Column(db.Text, nullable=True)  # Staff notes
    loyalty_points = db.Column(db.Integer, default=0)  # Loyalty points balance
    loyalty_tier = db.Column(db.String(20), default=TIER_STANDARD)  # Loyalty tier
    date_of_birth = db.Column(db.Date, nullable=True)  # For birthday offers
    nationality = db.Column(db.String(50), nullable=True)  # For reporting
    vip = db.Column(db.Boolean, default=False)  # VIP status
    stay_count = db.Column(db.Integer, default=0)  # Number of completed stays
    total_spent = db.Column(db.Float, default=0.0)  # Lifetime spend

    # Relationships with proper cascade settings
    user = db.relationship(
        'User', 
        back_populates='customer_profile',
        passive_deletes=True
    )
    
    bookings = db.relationship(
        'Booking', 
        back_populates='customer',
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    loyalty_transactions = db.relationship(
        'LoyaltyLedger',
        foreign_keys='LoyaltyLedger.customer_id',
        back_populates='customer',
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    loyalty_redemptions = db.relationship(
        'LoyaltyRedemption',
        foreign_keys='LoyaltyRedemption.customer_id',
        back_populates='customer',
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    waitlist_entries = db.relationship(
        'Waitlist',
        foreign_keys='Waitlist.customer_id',
        back_populates='customer',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    __table_args__ = (
        db.Index('idx_customers_loyalty', 'loyalty_tier', 'loyalty_points'),
    )

    def __repr__(self):
        """Provide a readable representation of a Customer instance."""
        return f'<Customer {self.id}, {self.name}>'
    
    @property
    def email(self):
        """Get email from the associated User model."""
        return self.user.email if self.user else None
    
    @property
    def is_profile_complete(self):
        """Check if the customer profile is complete."""
        return all([
            self.name,
            self.phone,
            self.address,
            self.email
        ])
    
    def update_profile_completeness(self):
        """Update the profile_complete flag based on required fields."""
        self.profile_complete = self.is_profile_complete
        return self.profile_complete
    
    @property
    def preferences(self):
        """Get customer preferences as a dictionary."""
        if not self.preferences_json:
            return {}
        
        try:
            return json.loads(self.preferences_json)
        except json.JSONDecodeError:
            return {}
    
    @preferences.setter
    def preferences(self, prefs_dict):
        """Set customer preferences from a dictionary."""
        self.preferences_json = json.dumps(prefs_dict)
    
    @property
    def documents(self):
        """Get customer document information as a dictionary."""
        if not self.documents_json:
            return {}
        
        try:
            return json.loads(self.documents_json)
        except json.JSONDecodeError:
            return {}
    
    @documents.setter
    def documents(self, docs_dict):
        """Set customer document information from a dictionary."""
        self.documents_json = json.dumps(docs_dict)
    
    def add_loyalty_points(self, points, reason=None, booking_id=None, staff_id=None):
        """
        Add loyalty points through the ledger system.
        
        Args:
            points: Number of points to add
            reason: Reason for adding points
            booking_id: Optional booking ID associated with the transaction
            staff_id: Optional staff ID for manual adjustments
            
        Returns:
            The created ledger transaction or None
        """
        from app.models.loyalty_ledger import LoyaltyLedger
        return LoyaltyLedger.earn_points(
            customer_id=self.id,
            points=points,
            reason=reason,
            booking_id=booking_id,
            staff_id=staff_id
        )
    
    def update_loyalty_tier(self):
        """
        Update the customer's loyalty tier based on points and stay count.
        
        Returns:
            New loyalty tier
        """
        if self.loyalty_points >= 10000 or self.stay_count >= 50:
            self.loyalty_tier = self.TIER_PLATINUM
        elif self.loyalty_points >= 5000 or self.stay_count >= 25:
            self.loyalty_tier = self.TIER_GOLD
        elif self.loyalty_points >= 1000 or self.stay_count >= 10:
            self.loyalty_tier = self.TIER_SILVER
        else:
            self.loyalty_tier = self.TIER_STANDARD
            
        return self.loyalty_tier
    
    def update_stats_after_stay(self, booking):
        """
        Update customer statistics after a stay.
        
        Args:
            booking: The completed booking
            
        Returns:
            Updated customer
        """
        self.stay_count += 1
        
        # Add total spent
        if booking.total_price:
            self.total_spent += booking.total_price
            
        # Add loyalty points (10 points per dollar spent)
        if booking.total_price:
            points_earned = int(booking.total_price * 10)
            from app.models.loyalty_ledger import LoyaltyLedger
            LoyaltyLedger.earn_points(
                customer_id=self.id,
                points=points_earned,
                reason=f"Stay #{self.stay_count}",
                booking_id=booking.id
            )
            
        return self
    
    def get_upcoming_bookings(self):
        """
        Get customer's upcoming bookings.
        
        Returns:
            List of upcoming bookings
        """
        from app.models.booking import Booking
        from datetime import date
        
        return Booking.query.filter(
            Booking.customer_id == self.id,
            Booking.check_in_date >= date.today(),
            Booking.status == Booking.STATUS_RESERVED
        ).order_by(Booking.check_in_date).all()
    
    def get_stay_history(self, limit=None):
        """
        Get customer's stay history.
        
        Args:
            limit: Maximum number of bookings to return
            
        Returns:
            List of past bookings
        """
        from app.models.booking import Booking
        
        query = Booking.query.filter(
            Booking.customer_id == self.id,
            Booking.status.in_([Booking.STATUS_CHECKED_OUT, Booking.STATUS_CANCELLED])
        ).order_by(Booking.check_out_date.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the customer
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'phone': self.phone,
            'address': self.address,
            'email': self.email,
            'emergency_contact': self.emergency_contact,
            'loyalty_points': self.loyalty_points,
            'loyalty_tier': self.loyalty_tier,
            'preferences': self.preferences,
            'vip': self.vip,
            'stay_count': self.stay_count,
            'total_spent': self.total_spent,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'nationality': self.nationality,
            'profile_complete': self.profile_complete,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
