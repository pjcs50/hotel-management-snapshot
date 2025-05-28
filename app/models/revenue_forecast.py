"""
Revenue Forecast model module.

This module defines the RevenueForecast model for storing predicted occupancy and revenue data.
"""

from datetime import datetime
from db import db
from app.models import BaseModel
from sqlalchemy import UniqueConstraint


class RevenueForecast(BaseModel):
    """
    Model for storing revenue forecasting data.
    
    This model captures predicted revenue and occupancy metrics for specific dates,
    allowing for historical tracking of forecast accuracy and time-series trend analysis.
    
    Attributes:
        id: Primary key
        forecast_date: The date the forecast is for
        created_at: When the forecast was generated
        predicted_occupancy_rate: Forecasted occupancy rate (percentage)
        predicted_adr: Forecasted average daily rate
        predicted_revpar: Forecasted revenue per available room
        predicted_room_revenue: Total predicted room revenue for the date
        confidence_score: Score from 0-100 indicating confidence in prediction
        forecast_type: Type of forecast (e.g., 'automated', 'manager_adjusted')
        actual_occupancy_rate: Actual occupancy rate once date has passed
        actual_adr: Actual ADR once date has passed
        actual_revpar: Actual RevPAR once date has passed
        actual_room_revenue: Actual room revenue once date has passed
    """

    __tablename__ = 'revenue_forecasts'

    # Forecast type constants
    FORECAST_AUTOMATED = 'automated'
    FORECAST_MANAGER_ADJUSTED = 'manager_adjusted'
    
    # Forecast type choices
    FORECAST_TYPES = [
        FORECAST_AUTOMATED,
        FORECAST_MANAGER_ADJUSTED
    ]

    forecast_date = db.Column(db.Date, nullable=False, index=True)
    
    # Predicted metrics
    predicted_occupancy_rate = db.Column(db.Float, nullable=False)
    predicted_adr = db.Column(db.Float, nullable=False)
    predicted_revpar = db.Column(db.Float, nullable=False)
    predicted_room_revenue = db.Column(db.Float, nullable=False)
    
    # Forecast metadata
    confidence_score = db.Column(db.Integer, nullable=False)  # 0-100
    forecast_type = db.Column(db.String(50), nullable=False, default=FORECAST_AUTOMATED)
    forecast_notes = db.Column(db.Text, nullable=True)
    
    # Actual metrics (to be filled after the date has passed)
    actual_occupancy_rate = db.Column(db.Float, nullable=True)
    actual_adr = db.Column(db.Float, nullable=True)
    actual_revpar = db.Column(db.Float, nullable=True)
    actual_room_revenue = db.Column(db.Float, nullable=True)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('forecast_date', name='uix_forecast_date'),
    )

    def __repr__(self):
        """Provide a readable representation of a RevenueForecast instance."""
        return f'<RevenueForecast for {self.forecast_date}, predicted revenue: ${self.predicted_room_revenue}>'
    
    @property
    def accuracy_score(self):
        """Calculate the accuracy of this forecast if actuals are available."""
        if None in (self.actual_room_revenue, self.predicted_room_revenue):
            return None
            
        if self.predicted_room_revenue == 0:
            return 0
            
        # Calculate accuracy as percentage (100 - absolute percentage error)
        error_percentage = abs((self.actual_room_revenue - self.predicted_room_revenue) / self.predicted_room_revenue) * 100
        accuracy = max(0, 100 - error_percentage)
        
        return round(accuracy, 2)
    
    @property
    def variance_percentage(self):
        """Calculate variance between predicted and actual revenue as a percentage."""
        if None in (self.actual_room_revenue, self.predicted_room_revenue):
            return None
            
        if self.predicted_room_revenue == 0:
            return 0
            
        variance = ((self.actual_room_revenue - self.predicted_room_revenue) / self.predicted_room_revenue) * 100
        
        return round(variance, 2)
    
    @property
    def has_actuals(self):
        """Check if this forecast has actual data recorded."""
        return self.actual_room_revenue is not None


class ForecastAggregation(BaseModel):
    """
    Model for storing aggregated forecast data over periods.
    
    This model stores forecast data aggregated over periods like weeks, months, or quarters,
    which is useful for trend analysis and longer-term forecasting.
    
    Attributes:
        id: Primary key
        period_type: Type of period (day, week, month, quarter, year)
        period_start: Start date of the period
        period_end: End date of the period
        predicted_occupancy_rate: Average forecasted occupancy rate for the period
        predicted_adr: Average forecasted ADR for the period
        predicted_revpar: Average forecasted RevPAR for the period
        predicted_room_revenue: Total forecasted room revenue for the period
        actual_occupancy_rate: Actual average occupancy rate for the period
        actual_adr: Actual average ADR for the period
        actual_revpar: Actual average RevPAR for the period
        actual_room_revenue: Actual total room revenue for the period
    """

    __tablename__ = 'forecast_aggregations'

    # Period type constants
    PERIOD_DAY = 'day'
    PERIOD_WEEK = 'week'
    PERIOD_MONTH = 'month'
    PERIOD_QUARTER = 'quarter'
    PERIOD_YEAR = 'year'
    
    # Period type choices
    PERIOD_TYPES = [
        PERIOD_DAY,
        PERIOD_WEEK,
        PERIOD_MONTH,
        PERIOD_QUARTER,
        PERIOD_YEAR
    ]

    period_type = db.Column(db.String(10), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    # Predicted metrics
    predicted_occupancy_rate = db.Column(db.Float, nullable=False)  # Average for period
    predicted_adr = db.Column(db.Float, nullable=False)  # Average for period
    predicted_revpar = db.Column(db.Float, nullable=False)  # Average for period
    predicted_room_revenue = db.Column(db.Float, nullable=False)  # Total for period
    
    # Actual metrics
    actual_occupancy_rate = db.Column(db.Float, nullable=True)
    actual_adr = db.Column(db.Float, nullable=True)
    actual_revpar = db.Column(db.Float, nullable=True)
    actual_room_revenue = db.Column(db.Float, nullable=True)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('period_type', 'period_start', 'period_end', name='uix_period'),
    )

    def __repr__(self):
        """Provide a readable representation of a ForecastAggregation instance."""
        return f'<ForecastAggregation {self.period_type} from {self.period_start} to {self.period_end}>' 