"""
Loyalty Reward model module.

This module defines the LoyaltyReward model for managing loyalty program rewards.
"""

from db import db
from app.models import BaseModel


class LoyaltyReward(BaseModel):
    """
    LoyaltyReward model for defining rewards that customers can redeem with loyalty points.
    
    Attributes:
        id: Primary key
        name: Name of the reward
        description: Detailed description of the reward
        points_cost: Number of points required to redeem this reward
        category: Category of the reward (e.g., 'room_upgrade', 'dining', 'spa')
        is_active: Whether the reward is currently available
        min_tier: Minimum loyalty tier required to access this reward
        limited_quantity: Whether there's a limited quantity of this reward
        quantity_remaining: Number of rewards remaining if limited
        image_url: URL to an image representing the reward
        expiry_date: Date when this reward expires (if applicable)
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """

    __tablename__ = 'loyalty_rewards'

    # Category constants
    CATEGORY_ROOM = 'room_upgrade'
    CATEGORY_DINING = 'dining'
    CATEGORY_SPA = 'spa'
    CATEGORY_AMENITY = 'amenity'
    CATEGORY_SERVICE = 'service'
    CATEGORY_OTHER = 'other'
    
    CATEGORY_CHOICES = [
        CATEGORY_ROOM,
        CATEGORY_DINING,
        CATEGORY_SPA,
        CATEGORY_AMENITY,
        CATEGORY_SERVICE,
        CATEGORY_OTHER
    ]

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    points_cost = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(20), nullable=False, default=CATEGORY_OTHER)
    is_active = db.Column(db.Boolean, default=True)
    min_tier = db.Column(db.String(20), nullable=False, default='Standard')
    limited_quantity = db.Column(db.Boolean, default=False)
    quantity_remaining = db.Column(db.Integer, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_rewards_active_tier', 'is_active', 'min_tier'),
        db.Index('idx_rewards_category', 'category'),
    )

    def __repr__(self):
        """Provide a readable representation of a LoyaltyReward instance."""
        return f'<LoyaltyReward {self.id}, {self.name}, {self.points_cost} points>'
    
    @classmethod
    def get_available_rewards(cls, tier='Standard', category=None):
        """
        Get available rewards for a specific loyalty tier.
        
        Args:
            tier: Customer's loyalty tier
            category: Optional category filter
            
        Returns:
            List of available rewards
        """
        from app.models.customer import Customer
        
        # Map tier to numerical value for comparison
        tier_values = {
            Customer.TIER_STANDARD: 0,
            Customer.TIER_SILVER: 1,
            Customer.TIER_GOLD: 2,
            Customer.TIER_PLATINUM: 3
        }
        
        # Get customer tier value
        customer_tier_value = tier_values.get(tier, 0)
        
        # Build filter conditions
        filters = [
            cls.is_active == True,
        ]
        
        # Add category filter if specified
        if category:
            filters.append(cls.category == category)
        
        # Get all rewards
        rewards = cls.query.filter(*filters).all()
        
        # Filter based on tier
        return [
            reward for reward in rewards
            if tier_values.get(reward.min_tier, 0) <= customer_tier_value
        ]
    
    def is_available_for_customer(self, customer):
        """
        Check if a reward is available for a specific customer.
        
        Args:
            customer: Customer model instance
            
        Returns:
            Boolean indicating if the reward is available
        """
        from app.models.customer import Customer
        
        # Check if reward is active
        if not self.is_active:
            return False
            
        # Check quantity remaining if limited
        if self.limited_quantity and (self.quantity_remaining is None or self.quantity_remaining <= 0):
            return False
            
        # Check expiry date
        if self.expiry_date and self.expiry_date < datetime.date.today():
            return False
            
        # Map tier to numerical value for comparison
        tier_values = {
            Customer.TIER_STANDARD: 0,
            Customer.TIER_SILVER: 1,
            Customer.TIER_GOLD: 2,
            Customer.TIER_PLATINUM: 3
        }
        
        # Compare customer tier with required tier
        customer_tier_value = tier_values.get(customer.loyalty_tier, 0)
        reward_tier_value = tier_values.get(self.min_tier, 0)
        
        return customer_tier_value >= reward_tier_value
    
    def to_dict(self):
        """
        Convert the model to a dictionary for JSON serialization.
        
        Returns:
            Dict representation of the loyalty reward
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'points_cost': self.points_cost,
            'category': self.category,
            'is_active': self.is_active,
            'min_tier': self.min_tier,
            'limited_quantity': self.limited_quantity,
            'quantity_remaining': self.quantity_remaining,
            'image_url': self.image_url,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 