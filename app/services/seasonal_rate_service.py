"""
Seasonal Rate service module.

This module provides service layer functionality for managing seasonal rates.
"""

from datetime import datetime
from sqlalchemy import and_, or_
from app.models.seasonal_rate import SeasonalRate
from werkzeug.exceptions import Conflict

class SeasonalRateService:
    """Service class for managing seasonal rates."""

    def __init__(self, db_session):
        """Initialize with a database session."""
        self.db_session = db_session

    def get_all_seasonal_rates(self, page=1, per_page=10):
        """
        Get all seasonal rates with pagination.
        
        Args:
            page: Page number (starting from 1)
            per_page: Number of items per page
            
        Returns:
            Paginated seasonal rates
        """
        return SeasonalRate.query.order_by(
            SeasonalRate.start_date.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
    
    def get_seasonal_rate(self, rate_id):
        """
        Get a seasonal rate by ID.
        
        Args:
            rate_id: ID of the seasonal rate
            
        Returns:
            Seasonal rate or None if not found
        """
        return SeasonalRate.query.get(rate_id)
    
    def _check_overlap(self, room_type_id, start_date, end_date, exclude_id=None):
        """
        Check if there's an overlap with existing seasonal rates.
        
        Args:
            room_type_id: Room type ID
            start_date: Start date of the new rate
            end_date: End date of the new rate
            exclude_id: ID of rate to exclude (for updates)
            
        Returns:
            True if there's an overlap, False otherwise
        """
        query = self.db_session.query(SeasonalRate).filter(
            SeasonalRate.room_type_id == room_type_id,
            # Check for date range overlap
            or_(
                # New range starts during existing range
                and_(
                    SeasonalRate.start_date <= start_date,
                    SeasonalRate.end_date >= start_date
                ),
                # New range ends during existing range
                and_(
                    SeasonalRate.start_date <= end_date,
                    SeasonalRate.end_date >= end_date
                ),
                # New range completely contains existing range
                and_(
                    SeasonalRate.start_date >= start_date,
                    SeasonalRate.end_date <= end_date
                )
            )
        )
        
        # Exclude the current rate for updates
        if exclude_id:
            query = query.filter(SeasonalRate.id != exclude_id)
            
        return query.first() is not None
    
    def create_seasonal_rate(self, data):
        """
        Create a new seasonal rate.
        
        Args:
            data: Dictionary with seasonal rate data
            
        Returns:
            Newly created seasonal rate
            
        Raises:
            Conflict: If there's an overlap with existing rates
        """
        # Check for overlap
        if self._check_overlap(
            data['room_type_id'],
            data['start_date'],
            data['end_date']
        ):
            raise Conflict("This date range overlaps with an existing seasonal rate")
        
        # Create new seasonal rate
        seasonal_rate = SeasonalRate(
            room_type_id=data['room_type_id'],
            name=data['name'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            rate_multiplier=data['rate_multiplier']
        )
        
        # Save to database
        self.db_session.add(seasonal_rate)
        self.db_session.commit()
        
        return seasonal_rate
    
    def update_seasonal_rate(self, rate_id, data):
        """
        Update an existing seasonal rate.
        
        Args:
            rate_id: ID of the seasonal rate to update
            data: Dictionary with updated seasonal rate data
            
        Returns:
            Updated seasonal rate
            
        Raises:
            Conflict: If there's an overlap with existing rates
        """
        seasonal_rate = self.get_seasonal_rate(rate_id)
        if not seasonal_rate:
            return None
        
        # Check for overlap
        if self._check_overlap(
            data['room_type_id'],
            data['start_date'],
            data['end_date'],
            exclude_id=rate_id
        ):
            raise Conflict("This date range overlaps with an existing seasonal rate")
        
        # Update seasonal rate
        seasonal_rate.room_type_id = data['room_type_id']
        seasonal_rate.name = data['name']
        seasonal_rate.start_date = data['start_date']
        seasonal_rate.end_date = data['end_date']
        seasonal_rate.rate_multiplier = data['rate_multiplier']
        
        # Save to database
        self.db_session.commit()
        
        return seasonal_rate
    
    def delete_seasonal_rate(self, rate_id):
        """
        Delete a seasonal rate.
        
        Args:
            rate_id: ID of the seasonal rate to delete
            
        Returns:
            True if deleted, False if not found
        """
        seasonal_rate = self.get_seasonal_rate(rate_id)
        if not seasonal_rate:
            return False
        
        # Delete from database
        self.db_session.delete(seasonal_rate)
        self.db_session.commit()
        
        return True 