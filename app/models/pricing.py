"""
Pricing model module.

This module defines the Pricing model for room rate multipliers.
"""

from db import db
from sqlalchemy import ForeignKey


class Pricing(db.Model):
    """Model representing room pricing rules.
    
    This model stores multipliers for different pricing scenarios (weekends, peak seasons, etc.)
    to be applied to the base room price.
    """
    
    __tablename__ = 'pricing'
    
    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, ForeignKey('room_types.id'), nullable=False, unique=True)
    weekend_multiplier = db.Column(db.Float, default=1.25)  # Default 25% higher on weekends
    peak_season_multiplier = db.Column(db.Float, default=1.5)  # Default 50% higher in peak season
    special_event_multiplier = db.Column(db.Float, default=1.75)  # Default 75% higher for special events
    last_minute_discount = db.Column(db.Float, default=0.85)  # Default 15% discount for last minute bookings
    extended_stay_discount = db.Column(db.Float, default=0.9)  # Default 10% discount for extended stays
    
    # Relationships
    room_type = db.relationship('RoomType', backref='pricing_rules')
    
    def __repr__(self):
        """Return a helpful representation of this instance."""
        return f"<Pricing id={self.id} room_type_id={self.room_type_id}>"
    
    def apply_multiplier(self, base_price, is_weekend=False, is_peak_season=False, is_special_event=False):
        """Apply pricing multipliers to a base price.
        
        Args:
            base_price (float): The base price to apply multipliers to
            is_weekend (bool): Whether this is a weekend booking
            is_peak_season (bool): Whether this is during peak season
            is_special_event (bool): Whether this is during a special event
            
        Returns:
            float: The adjusted price after applying multipliers
        """
        # Start with base price
        adjusted_price = base_price
        
        # Apply multipliers based on circumstances
        if is_weekend:
            adjusted_price *= self.weekend_multiplier
        
        if is_peak_season:
            adjusted_price *= self.peak_season_multiplier
        
        if is_special_event:
            adjusted_price *= self.special_event_multiplier
        
        return adjusted_price
    
    def apply_discount(self, price, is_last_minute=False, is_extended_stay=False):
        """Apply discounts to a price.
        
        Args:
            price (float): The price to apply discounts to
            is_last_minute (bool): Whether this is a last-minute booking
            is_extended_stay (bool): Whether this is an extended stay
            
        Returns:
            float: The adjusted price after applying discounts
        """
        # Start with original price
        adjusted_price = price
        
        # Apply discounts based on circumstances
        if is_last_minute:
            adjusted_price *= self.last_minute_discount
        
        if is_extended_stay:
            adjusted_price *= self.extended_stay_discount
        
        return adjusted_price 