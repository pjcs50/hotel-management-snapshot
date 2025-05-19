"""
Staff Performance service module.

This module contains services for tracking and retrieving staff performance metrics.
"""

import calendar
from datetime import datetime, timedelta, date
from sqlalchemy import func, select
from app.models.staff_performance import StaffPerformance
from app.models.user import User


class StaffPerformanceService:
    """Service for handling staff performance metrics."""

    def __init__(self, db_session):
        """Initialize the service with a database session."""
        self.db_session = db_session
    
    def get_staff_performance(self, user_id, period_start=None, period_end=None):
        """
        Get performance metrics for a staff member.
        
        Args:
            user_id: ID of the staff member
            period_start: Optional start date for period (defaults to 30 days ago)
            period_end: Optional end date for period (defaults to today)
            
        Returns:
            A StaffPerformance object for the given period
        """
        if not period_start:
            period_start = datetime.now().date() - timedelta(days=30)
        if not period_end:
            period_end = datetime.now().date()
            
        # Try to get existing performance record for the period
        query = select(StaffPerformance).filter_by(user_id=user_id)
        if period_start and period_end:
            query = query.filter(
                StaffPerformance.period_start == period_start,
                StaffPerformance.period_end == period_end
            )
        else: # Default to current month if no period specified
            today = date.today()
            year, month = today.year, today.month
            _, last_day = calendar.monthrange(year, month)
            current_month_start = date(year, month, 1)
            current_month_end = date(year, month, last_day)
            query = query.filter(
                StaffPerformance.period_start == current_month_start,
                StaffPerformance.period_end == current_month_end
            )
        
        existing_performance = self.db_session.execute(query).scalar_one_or_none()
        if existing_performance:
            return existing_performance
        else: # Create a new one if it doesn't exist for the period
            # Determine the period start and end if not provided
            if period_start is None or period_end is None:
                today_fallback = date.today()
                year_fallback, month_fallback = today_fallback.year, today_fallback.month
                _, last_day_fallback = calendar.monthrange(year_fallback, month_fallback)
                query_period_start = date(year_fallback, month_fallback, 1)
                query_period_end = date(year_fallback, month_fallback, last_day_fallback) # Default to full month
            else:
                query_period_start = period_start
                query_period_end = period_end

            new_performance = StaffPerformance(
                user_id=user_id,
                period_start=query_period_start,
                period_end=query_period_end,
                # Explicitly set defaults for fields that might be used before a DB flush applies them
                tasks_completed=0,
                tasks_assigned=0,
                rating_count=0,
                customer_rating=0.0,
                avg_response_time_minutes=0.0,
                avg_task_time_minutes=0.0
            )
            self.db_session.add(new_performance) # Add to session to make it managed
            # self.db_session.flush() # Optional: flush if ID or immediate persistence needed before return
            return new_performance
    
    def get_monthly_performance(self, user_id, year=None, month=None):
        """
        Get performance metrics for a staff member for a specific month.
        
        Args:
            user_id: ID of the staff member
            year: Year (defaults to current)
            month: Month (1-12, defaults to current)
            
        Returns:
            A StaffPerformance object for the given month
        """
        if not year or not month:
            today = datetime.now()
            year = year or today.year
            month = month or today.month
            
        # Calculate start and end dates for the month
        _, last_day = calendar.monthrange(year, month)
        period_start = datetime(year, month, 1).date()
        period_end = datetime(year, month, last_day).date()
        
        return self.get_staff_performance(user_id, period_start, period_end)
    
    def get_staff_performance_history(self, user_id, months=6):
        """
        Get historical performance metrics for a staff member.
        
        Args:
            user_id: ID of the staff member
            months: Number of months of history to retrieve
            
        Returns:
            List of StaffPerformance objects for the past months
        """
        today = datetime.now().date()
        
        # Get performances for the past X months
        performances = self.db_session.execute(
            select(StaffPerformance).filter(
                StaffPerformance.user_id == user_id,
                StaffPerformance.period_end <= today,
                StaffPerformance.period_end >= today - timedelta(days=30 * months)
            ).order_by(StaffPerformance.period_start)
        ).scalars().all()
        
        return performances
    
    def update_performance_metrics(self, user_id, metrics, period_start=None, period_end=None):
        """
        Update performance metrics for a staff member.
        
        Args:
            user_id: ID of the staff member
            metrics: Dictionary of metrics to update
            period_start: Optional start date for period
            period_end: Optional end date for period
            
        Returns:
            The updated StaffPerformance object
        """
        performance = self.get_staff_performance(user_id, period_start, period_end)
        
        # Update metrics
        for key, value in metrics.items():
            if hasattr(performance, key):
                setattr(performance, key, value)
                
        return performance
    
    def add_task_completion(self, user_id, task_time_minutes=None, response_time_minutes=None):
        """
        Record a completed task for a staff member.
        
        Args:
            user_id: ID of the staff member
            task_time_minutes: Time taken to complete the task
            response_time_minutes: Time taken to respond to the task
            
        Returns:
            The updated StaffPerformance object
        """
        today = datetime.now().date()
        month_start = today.replace(day=1)
        _, last_day_of_month = calendar.monthrange(today.year, today.month)
        current_month_end = date(today.year, today.month, last_day_of_month)
        
        performance = self.get_staff_performance(user_id, month_start, current_month_end)
        
        # Update task count
        performance.tasks_completed += 1
        
        # Update average times if provided
        if task_time_minutes is not None:
            # Calculate new average
            new_avg = (performance.avg_task_time_minutes * (performance.tasks_completed - 1) + task_time_minutes) / performance.tasks_completed
            performance.avg_task_time_minutes = new_avg
            
        if response_time_minutes is not None:
            # Calculate new average
            new_avg = (performance.avg_response_time_minutes * (performance.tasks_completed - 1) + response_time_minutes) / performance.tasks_completed
            performance.avg_response_time_minutes = new_avg
            
        return performance
    
    def add_customer_rating(self, user_id, rating):
        """
        Add a customer rating for a staff member.
        
        Args:
            user_id: ID of the staff member
            rating: Customer rating (1-5)
            
        Returns:
            The updated StaffPerformance object
        """
        today = datetime.now().date()
        month_start = today.replace(day=1)
        _, last_day_of_month = calendar.monthrange(today.year, today.month)
        current_month_end = date(today.year, today.month, last_day_of_month)

        performance = self.get_staff_performance(user_id, month_start, current_month_end)
        
        # Calculate new average rating
        if performance.rating_count is None: performance.rating_count = 0
        if performance.customer_rating is None: performance.customer_rating = 0.0

        current_total_score = performance.customer_rating * performance.rating_count
        new_total_score = current_total_score + rating
        performance.rating_count += 1
        performance.customer_rating = new_total_score / performance.rating_count if performance.rating_count > 0 else 0
        
        return performance
    
    def get_top_performers(self, role=None, metric='efficiency_score', limit=5):
        """
        Get the top performing staff members.
        
        Args:
            role: Optional role to filter by
            metric: Metric to sort by (efficiency_score, customer_rating, etc.)
            limit: Number of results to return
            
        Returns:
            List of staff with their performance metrics
        """
        today = datetime.now().date()
        month_start = today.replace(day=1)
        _, last_day_of_current_month = calendar.monthrange(today.year, today.month) # Get last day of current month
        current_month_end_date = date(today.year, today.month, last_day_of_current_month) # Create date object for it

        # Start with base query
        query = select(StaffPerformance, User).join(
            User, User.id == StaffPerformance.user_id
        ).filter(
            StaffPerformance.period_start == month_start, # Performance record starts at beginning of current month
            StaffPerformance.period_end == current_month_end_date, # Performance record ends at end of current month
            User.role.in_(['receptionist', 'housekeeping', 'manager'])
        )
        
        # Apply role filter if provided
        if role:
            query = query.filter(User.role == role)
            
        # Order by requested metric
        if metric == 'efficiency_score':
            # For calculated properties, we need to fetch all and sort in Python
            results = self.db_session.execute(query).all()
            sorted_results = sorted(
                results, 
                key=lambda x: getattr(x[0], 'efficiency_score', 0), 
                reverse=True
            )
            return sorted_results[:limit]
        else:
            # For database columns, we can sort in the query
            query = query.order_by(getattr(StaffPerformance, metric).desc())
            return self.db_session.execute(query.limit(limit)).all() 