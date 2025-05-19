"""
Staff Performance model module.

This module defines the StaffPerformance model for tracking staff metrics.
"""

from datetime import datetime
from sqlalchemy import ForeignKey
from db import db


class StaffPerformance(db.Model):
    """Model representing staff performance metrics.
    
    This model stores metrics related to staff performance, including tasks completed,
    average response time, and customer ratings.
    """
    
    __tablename__ = 'staff_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    tasks_completed = db.Column(db.Integer, default=0)
    tasks_assigned = db.Column(db.Integer, default=0)
    avg_response_time_minutes = db.Column(db.Float, default=0.0)
    avg_task_time_minutes = db.Column(db.Float, default=0.0)
    customer_rating = db.Column(db.Float, default=0.0)  # 1-5 scale
    rating_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref='performance_metrics')
    
    def __repr__(self):
        """Return a helpful representation of this instance."""
        return f"<StaffPerformance id={self.id} user_id={self.user_id} period={self.period_start} to {self.period_end}>"
    
    @property
    def completion_rate(self):
        """Calculate the task completion rate."""
        if self.tasks_assigned == 0:
            return 0.0
        return (self.tasks_completed / self.tasks_assigned) * 100
    
    @property
    def efficiency_score(self):
        """Calculate an overall efficiency score based on multiple metrics."""
        # A simple weighted score combining completion rate, response time, and customer rating
        if self.rating_count == 0:
            return 0.0
            
        # Normalize response time (lower is better) - assume 60 min is maximum expected
        response_time_score = max(0, 100 - (self.avg_response_time_minutes / 60 * 100))
        
        # Weight the components
        completion_weight = 0.4
        response_weight = 0.3
        rating_weight = 0.3
        
        # Calculate weighted score
        return (
            self.completion_rate * completion_weight +
            response_time_score * response_weight +
            (self.customer_rating / 5 * 100) * rating_weight
        ) 