"""
SeasonalRate model module.

This module defines the SeasonalRate model for managing seasonal pricing.
"""

from datetime import datetime, timedelta
from db import db
from app.models import BaseModel


class SeasonalRate(BaseModel):
    """
    SeasonalRate model for managing seasonal pricing.
    
    Attributes:
        id: Primary key
        room_type_id: Foreign key to the RoomType model
        start_date: Start date of the seasonal rate period
        end_date: End date of the seasonal rate period
        rate_multiplier: Multiplier to apply to the base rate
        name: Name of the seasonal rate period (e.g., "Summer", "Holiday")
        day_of_week_adjustments: JSON string of day-specific adjustments
        is_special_event: Whether this is a special event rate
        description: Description of the seasonal rate
        created_at: Timestamp when the seasonal rate was created
        updated_at: Timestamp when the seasonal rate was last updated
    """

    __tablename__ = 'seasonal_rates'

    # Rate types
    TYPE_SEASONAL = 'seasonal'
    TYPE_WEEKEND = 'weekend'
    TYPE_HOLIDAY = 'holiday'
    TYPE_EVENT = 'event'
    TYPE_PROMOTION = 'promotion'
    
    TYPE_CHOICES = [
        TYPE_SEASONAL,
        TYPE_WEEKEND,
        TYPE_HOLIDAY,
        TYPE_EVENT,
        TYPE_PROMOTION
    ]

    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    rate_multiplier = db.Column(db.Numeric(5, 2), nullable=False)  # e.g., 1.25 for +25%
    name = db.Column(db.String(50), nullable=False)
    
    # New fields for enhanced pricing
    rate_type = db.Column(db.String(20), nullable=False, default=TYPE_SEASONAL)
    day_of_week_adjustments = db.Column(db.Text, nullable=True)  # JSON of day-specific rates
    is_special_event = db.Column(db.Boolean, default=False)  # For premium events
    min_stay_nights = db.Column(db.Integer, default=1)  # Minimum nights required
    description = db.Column(db.Text, nullable=True)  # Details about the rate
    priority = db.Column(db.Integer, default=100)  # Higher number = higher priority
    active = db.Column(db.Boolean, default=True)  # Whether the rate is active

    # Relationships
    room_type = db.relationship('RoomType', backref='seasonal_rates')

    __table_args__ = (
        # Index for efficiently querying rates by date range
        db.Index('idx_seasonal_rates_dates', 'room_type_id', 'start_date', 'end_date'),
    )

    def __repr__(self):
        """Provide a readable representation of a SeasonalRate instance."""
        return f'<SeasonalRate {self.name}, {self.start_date} to {self.end_date}, x{self.rate_multiplier}>'
    
    @property
    def day_adjustments(self):
        """Get day-of-week rate adjustments as a dictionary.
        
        Returns:
            Dict of day names to rate multipliers
        """
        import json
        if not self.day_of_week_adjustments:
            return {}
        
        try:
            return json.loads(self.day_of_week_adjustments)
        except json.JSONDecodeError:
            return {}
    
    @day_adjustments.setter
    def day_adjustments(self, adjustments_dict):
        """Set day-of-week rate adjustments from a dictionary.
        
        Args:
            adjustments_dict: Dict of day names to rate multipliers
        """
        import json
        self.day_of_week_adjustments = json.dumps(adjustments_dict)
    
    def get_day_rate_multiplier(self, date):
        """Get the rate multiplier specific to a day of the week.
        
        Args:
            date: Date to check
            
        Returns:
            Rate multiplier as a float
        """
        day_name = date.strftime('%A').lower()  # e.g., 'monday'
        adjustments = self.day_adjustments
        
        # If we have a specific multiplier for this day, use it
        if day_name in adjustments:
            return float(adjustments[day_name])
        
        # Otherwise, use the default rate multiplier
        return float(self.rate_multiplier)
    
    @classmethod
    def get_applicable_rates(cls, room_type_id, date):
        """
        Get all applicable seasonal rates for a room type on a specific date.
        
        Args:
            room_type_id: ID of the room type
            date: Date to check
            
        Returns:
            List of applicable seasonal rates, sorted by priority
        """
        return cls.query.filter(
            cls.room_type_id == room_type_id,
            cls.start_date <= date,
            cls.end_date >= date,
            cls.active == True
        ).order_by(cls.priority.desc()).all()
    
    @classmethod
    def get_rate_for_date(cls, room_type_id, date):
        """
        Get the highest priority applicable seasonal rate for a room type on a specific date.
        
        Args:
            room_type_id: ID of the room type
            date: Date to check
            
        Returns:
            The applicable seasonal rate, or None if no seasonal rate applies
        """
        return cls.query.filter(
            cls.room_type_id == room_type_id,
            cls.start_date <= date,
            cls.end_date >= date,
            cls.active == True
        ).order_by(cls.priority.desc()).first()
    
    @classmethod
    def calculate_adjusted_rate(cls, base_rate, room_type_id, date):
        """
        Calculate the adjusted rate for a room type on a specific date.
        
        Args:
            base_rate: Base rate to adjust
            room_type_id: ID of the room type
            date: Date to check
            
        Returns:
            The adjusted rate
        """
        seasonal_rate = cls.get_rate_for_date(room_type_id, date)
        if seasonal_rate:
            day_multiplier = seasonal_rate.get_day_rate_multiplier(date)
            return base_rate * day_multiplier
        
        # Check if it's a weekend (Saturday or Sunday)
        if date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            # Look for a weekend rate
            weekend_rate = cls.query.filter(
                cls.room_type_id == room_type_id,
                cls.rate_type == cls.TYPE_WEEKEND,
                cls.active == True
            ).order_by(cls.priority.desc()).first()
            
            if weekend_rate:
                return base_rate * float(weekend_rate.rate_multiplier)
        
        return base_rate
    
    @classmethod
    def calculate_stay_price(cls, room_type_id, check_in_date, check_out_date, base_rate):
        """
        Calculate the total price for a stay, considering seasonal rates for each night.
        
        Args:
            room_type_id: ID of the room type
            check_in_date: Check-in date
            check_out_date: Check-out date
            base_rate: Base rate for the room type
            
        Returns:
            Total price for the stay
        """
        total_price = 0
        current_date = check_in_date
        
        # Add the rate for each night
        while current_date < check_out_date:
            daily_rate = cls.calculate_adjusted_rate(base_rate, room_type_id, current_date)
            total_price += daily_rate
            current_date += timedelta(days=1)
            
        return total_price

    @classmethod
    def find_overlapping(cls, room_type_id, start_date, end_date, exclude_id=None):
        """
        Find seasonal rates that overlap with the given date range.
        
        Args:
            room_type_id: ID of the room type
            start_date: Start date
            end_date: End date
            exclude_id: ID of a seasonal rate to exclude
            
        Returns:
            List of overlapping seasonal rates
        """
        query = cls.query.filter(
            cls.room_type_id == room_type_id,
            cls.rate_type == cls.TYPE_SEASONAL,
            # Start date falls within our range
            ((cls.start_date >= start_date) & (cls.start_date <= end_date)) |
            # End date falls within our range
            ((cls.end_date >= start_date) & (cls.end_date <= end_date)) |
            # Rate completely spans our range
            ((cls.start_date <= start_date) & (cls.end_date >= end_date))
        )
        
        if exclude_id:
            query = query.filter(cls.id != exclude_id)
            
        return query.all() 