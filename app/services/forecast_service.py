"""
Forecast service module.

This module provides service layer functionality for revenue forecasting.
"""

from datetime import datetime, timedelta
import numpy as np
from sqlalchemy import func, and_, or_, extract
from app.models.revenue_forecast import RevenueForecast, ForecastAggregation
from app.models.booking import Booking
from app.models.room import Room
from app.services.analytics_service import AnalyticsService


class ForecastService:
    """Service class for revenue forecasting."""

    def __init__(self, db_session):
        """Initialize with a database session."""
        self.db_session = db_session
        self.analytics_service = AnalyticsService(db_session)

    def generate_daily_forecasts(self, start_date=None, days=90):
        """
        Generate revenue forecasts for a specified number of days.
        
        Args:
            start_date: Start date for forecasts (defaults to tomorrow)
            days: Number of days to forecast (defaults to 90)
            
        Returns:
            List of created RevenueForecast objects
        """
        if start_date is None:
            start_date = datetime.now().date() + timedelta(days=1)
            
        # Create forecasts for each day
        forecasts = []
        for day_offset in range(days):
            forecast_date = start_date + timedelta(days=day_offset)
            
            # Calculate forecast metrics using our forecasting algorithm
            predicted_metrics = self._calculate_forecast_for_date(forecast_date)
            
            # Create or update forecast in database
            forecast = self.db_session.query(RevenueForecast).filter(
                RevenueForecast.forecast_date == forecast_date
            ).first()
            
            if forecast:
                # Update existing forecast
                forecast.predicted_occupancy_rate = predicted_metrics['occupancy_rate']
                forecast.predicted_adr = predicted_metrics['adr']
                forecast.predicted_revpar = predicted_metrics['revpar']
                forecast.predicted_room_revenue = predicted_metrics['room_revenue']
                forecast.confidence_score = predicted_metrics['confidence_score']
                forecast.forecast_type = RevenueForecast.FORECAST_AUTOMATED
            else:
                # Create new forecast
                forecast = RevenueForecast(
                    forecast_date=forecast_date,
                    predicted_occupancy_rate=predicted_metrics['occupancy_rate'],
                    predicted_adr=predicted_metrics['adr'],
                    predicted_revpar=predicted_metrics['revpar'],
                    predicted_room_revenue=predicted_metrics['room_revenue'],
                    confidence_score=predicted_metrics['confidence_score'],
                    forecast_type=RevenueForecast.FORECAST_AUTOMATED
                )
                self.db_session.add(forecast)
            
            forecasts.append(forecast)
        
        # Commit all forecasts to database
        self.db_session.commit()
        
        return forecasts
    
    def generate_aggregated_forecasts(self):
        """
        Generate aggregated forecasts for different time periods.
        
        This generates week, month, quarter, and year aggregations from daily forecasts.
        
        Returns:
            Dictionary with counts of aggregations created by period type
        """
        today = datetime.now().date()
        results = {
            'week': 0,
            'month': 0,
            'quarter': 0,
            'year': 0
        }
        
        # Generate weekly aggregations (next 12 weeks)
        for week in range(12):
            week_start = today + timedelta(days=week * 7)
            week_end = week_start + timedelta(days=6)
            if self._create_period_aggregation(ForecastAggregation.PERIOD_WEEK, week_start, week_end):
                results['week'] += 1
        
        # Generate monthly aggregations (next 12 months)
        current_month = today.month
        current_year = today.year
        for month_offset in range(12):
            month = ((current_month - 1 + month_offset) % 12) + 1
            year = current_year + ((current_month - 1 + month_offset) // 12)
            
            # Calculate month start and end
            if month == 12:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year
                
            month_start = datetime(year, month, 1).date()
            month_end = datetime(next_year, next_month, 1).date() - timedelta(days=1)
            
            if self._create_period_aggregation(ForecastAggregation.PERIOD_MONTH, month_start, month_end):
                results['month'] += 1
        
        # Generate quarterly aggregations (next 4 quarters)
        current_quarter = (today.month - 1) // 3 + 1
        for quarter_offset in range(4):
            quarter = ((current_quarter - 1 + quarter_offset) % 4) + 1
            year = current_year + ((current_quarter - 1 + quarter_offset) // 4)
            
            quarter_start = datetime(year, ((quarter - 1) * 3) + 1, 1).date()
            if quarter == 4:
                quarter_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                quarter_end = datetime(year, (quarter * 3) + 1, 1).date() - timedelta(days=1)
                
            if self._create_period_aggregation(ForecastAggregation.PERIOD_QUARTER, quarter_start, quarter_end):
                results['quarter'] += 1
        
        # Generate yearly aggregation (next year)
        year_start = datetime(current_year, 1, 1).date()
        year_end = datetime(current_year + 1, 1, 1).date() - timedelta(days=1)
        if self._create_period_aggregation(ForecastAggregation.PERIOD_YEAR, year_start, year_end):
            results['year'] += 1
            
        self.db_session.commit()
        return results
    
    def _create_period_aggregation(self, period_type, period_start, period_end):
        """
        Create or update a forecast aggregation for a specific period.
        
        Returns:
            bool: True if created or updated, False if failed
        """
        # Get daily forecasts for the period
        daily_forecasts = self.db_session.query(RevenueForecast).filter(
            RevenueForecast.forecast_date >= period_start,
            RevenueForecast.forecast_date <= period_end
        ).all()
        
        # Skip if no daily forecasts available
        if not daily_forecasts:
            return False
        
        # Calculate aggregated metrics
        num_days = (period_end - period_start).days + 1
        predicted_values = {
            'occupancy_rate': sum(f.predicted_occupancy_rate for f in daily_forecasts) / len(daily_forecasts),
            'adr': sum(f.predicted_adr for f in daily_forecasts) / len(daily_forecasts),
            'revpar': sum(f.predicted_revpar for f in daily_forecasts) / len(daily_forecasts),
            'room_revenue': sum(f.predicted_room_revenue for f in daily_forecasts)
        }
        
        # Calculate actual metrics for dates that have passed
        past_forecasts = [f for f in daily_forecasts if f.has_actuals]
        if past_forecasts:
            actual_values = {
                'occupancy_rate': sum(f.actual_occupancy_rate for f in past_forecasts) / len(past_forecasts),
                'adr': sum(f.actual_adr for f in past_forecasts) / len(past_forecasts),
                'revpar': sum(f.actual_revpar for f in past_forecasts) / len(past_forecasts),
                'room_revenue': sum(f.actual_room_revenue for f in past_forecasts)
            }
        else:
            actual_values = {
                'occupancy_rate': None,
                'adr': None,
                'revpar': None,
                'room_revenue': None
            }
        
        # Create or update the aggregation
        aggregation = self.db_session.query(ForecastAggregation).filter(
            ForecastAggregation.period_type == period_type,
            ForecastAggregation.period_start == period_start,
            ForecastAggregation.period_end == period_end
        ).first()
        
        if aggregation:
            # Update existing aggregation
            aggregation.predicted_occupancy_rate = predicted_values['occupancy_rate']
            aggregation.predicted_adr = predicted_values['adr']
            aggregation.predicted_revpar = predicted_values['revpar']
            aggregation.predicted_room_revenue = predicted_values['room_revenue']
            
            if past_forecasts:
                aggregation.actual_occupancy_rate = actual_values['occupancy_rate']
                aggregation.actual_adr = actual_values['adr']
                aggregation.actual_revpar = actual_values['revpar']
                aggregation.actual_room_revenue = actual_values['room_revenue']
        else:
            # Create new aggregation
            aggregation = ForecastAggregation(
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                predicted_occupancy_rate=predicted_values['occupancy_rate'],
                predicted_adr=predicted_values['adr'],
                predicted_revpar=predicted_values['revpar'],
                predicted_room_revenue=predicted_values['room_revenue'],
                actual_occupancy_rate=actual_values['occupancy_rate'],
                actual_adr=actual_values['adr'],
                actual_revpar=actual_values['revpar'],
                actual_room_revenue=actual_values['room_revenue']
            )
            self.db_session.add(aggregation)
        
        return True

    def _calculate_forecast_for_date(self, forecast_date):
        """
        Calculate forecast metrics for a specific date using time-series analysis.
        
        Args:
            forecast_date: The date to forecast for
            
        Returns:
            Dictionary with predicted metrics
        """
        # Get historical data for the same day of week (DoW forecasting)
        dow = forecast_date.weekday()
        historical_data = self._get_historical_data_for_dow(dow, 12)  # 12 weeks of history
        
        # Get data for same time last year if available (YoY forecasting)
        last_year_date = datetime(forecast_date.year - 1, forecast_date.month, forecast_date.day).date()
        last_year_data = self._get_historical_data_for_specific_dates([
            last_year_date - timedelta(days=1),
            last_year_date,
            last_year_date + timedelta(days=1)
        ])
        
        # Check if this date falls on any special events or holidays
        is_holiday = self._is_holiday_or_special_event(forecast_date)
        
        # Check for any existing bookings for this date (booking pace)
        existing_bookings = self._get_existing_bookings_for_date(forecast_date)
        
        # Calculate predicted metrics
        occupancy_rate = self._predict_occupancy_rate(forecast_date, historical_data, last_year_data, existing_bookings, is_holiday)
        adr = self._predict_adr(forecast_date, historical_data, last_year_data, existing_bookings, is_holiday)
        
        # Calculate RevPAR (Revenue Per Available Room)
        revpar = occupancy_rate * adr / 100
        
        # Calculate total room revenue
        total_rooms = self.db_session.query(func.count(Room.id)).scalar() or 0
        room_revenue = total_rooms * revpar
        
        # Calculate confidence score based on data quality
        confidence_score = self._calculate_confidence_score(historical_data, last_year_data, forecast_date)
        
        return {
            'occupancy_rate': round(occupancy_rate, 2),
            'adr': round(adr, 2),
            'revpar': round(revpar, 2),
            'room_revenue': round(room_revenue, 2),
            'confidence_score': confidence_score
        }
    
    def _get_historical_data_for_dow(self, day_of_week, weeks_of_history=12):
        """
        Get historical data for a specific day of week.
        
        Args:
            day_of_week: Day of week (0-6, where 0 is Monday)
            weeks_of_history: Number of weeks of history to fetch
            
        Returns:
            List of historical data points
        """
        today = datetime.now().date()
        history_start = today - timedelta(days=weeks_of_history * 7)
        
        # Query actual bookings and revenue data
        results = []
        for i in range(weeks_of_history):
            date = history_start + timedelta(days=i * 7 + day_of_week)
            if date < today:  # Only consider historical dates
                occupancy = self.analytics_service.get_daily_occupancy(date)
                adr = self.analytics_service.get_daily_adr(date)
                results.append({
                    'date': date,
                    'occupancy_rate': occupancy,
                    'adr': adr
                })
        
        return results
    
    def _get_historical_data_for_specific_dates(self, dates):
        """
        Get historical data for specific dates.
        
        Args:
            dates: List of dates to get data for
            
        Returns:
            List of historical data points
        """
        today = datetime.now().date()
        results = []
        
        for date in dates:
            if date < today:  # Only consider historical dates
                occupancy = self.analytics_service.get_daily_occupancy(date)
                adr = self.analytics_service.get_daily_adr(date)
                results.append({
                    'date': date,
                    'occupancy_rate': occupancy,
                    'adr': adr
                })
        
        return results
    
    def _is_holiday_or_special_event(self, date):
        """
        Check if a date is a holiday or special event.
        
        Args:
            date: Date to check
            
        Returns:
            bool: True if holiday or special event
        """
        # In a production system, this would check against a holiday/event calendar
        # For now, we'll use a simple approximation
        # Assume weekends and summer months have higher demand
        is_weekend = date.weekday() >= 5  # Saturday or Sunday
        is_summer = date.month in [6, 7, 8]
        
        return is_weekend or is_summer
    
    def _get_existing_bookings_for_date(self, date):
        """
        Get count of existing bookings for a specific date.
        
        Args:
            date: Date to check
            
        Returns:
            int: Number of existing bookings
        """
        booking_count = self.db_session.query(func.count(Booking.id)).filter(
            Booking.check_in_date <= date,
            Booking.check_out_date > date,
            Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
        ).scalar()
        
        return booking_count or 0
    
    def _predict_occupancy_rate(self, forecast_date, historical_data, last_year_data, existing_bookings, is_holiday):
        """
        Predict occupancy rate using historical data and booking pace.
        
        Args:
            forecast_date: Date to forecast for
            historical_data: List of historical data points
            last_year_data: List of data points from same time last year
            existing_bookings: Count of existing bookings
            is_holiday: Whether this is a holiday or special event
            
        Returns:
            float: Predicted occupancy rate (0-100)
        """
        # Start with historical average for this day of week
        if historical_data:
            base_occupancy = sum(d['occupancy_rate'] for d in historical_data) / len(historical_data)
        else:
            base_occupancy = 65  # Default occupancy if no historical data
        
        # Adjust for year-over-year trend
        if last_year_data:
            yoy_adjustment = 1.05  # Assume 5% YoY growth by default
        else:
            yoy_adjustment = 1.0
        
        # Adjust for existing bookings
        total_rooms = self.db_session.query(func.count(Room.id)).scalar() or 1
        booking_pace_factor = min(1.5, max(0.5, (existing_bookings / total_rooms) * 2))
        
        # Adjust for holidays and special events
        holiday_factor = 1.2 if is_holiday else 1.0
        
        # Calculate final prediction
        predicted_occupancy = base_occupancy * yoy_adjustment * booking_pace_factor * holiday_factor
        
        # Ensure occupancy is within valid range
        return min(100, max(0, predicted_occupancy))
    
    def _predict_adr(self, forecast_date, historical_data, last_year_data, existing_bookings, is_holiday):
        """
        Predict average daily rate using historical data and adjustments.
        
        Args:
            forecast_date: Date to forecast for
            historical_data: List of historical data points
            last_year_data: List of data points from same time last year
            existing_bookings: Count of existing bookings
            is_holiday: Whether this is a holiday or special event
            
        Returns:
            float: Predicted ADR
        """
        # Start with historical average for this day of week
        if historical_data:
            base_adr = sum(d['adr'] for d in historical_data) / len(historical_data)
        else:
            base_adr = 120  # Default ADR if no historical data
        
        # Adjust for year-over-year trend
        if last_year_data:
            yoy_adjustment = 1.03  # Assume 3% YoY growth by default
        else:
            yoy_adjustment = 1.0
        
        # Adjust for booking pace (higher occupancy typically means higher ADR)
        total_rooms = self.db_session.query(func.count(Room.id)).scalar() or 1
        occupancy_percent = (existing_bookings / total_rooms) * 100
        booking_pace_factor = 1.0
        if occupancy_percent > 70:
            booking_pace_factor = 1.1  # Higher demand can command premium rates
        elif occupancy_percent < 30:
            booking_pace_factor = 0.9  # Low demand might require discounting
        
        # Adjust for holidays and special events
        holiday_factor = 1.15 if is_holiday else 1.0
        
        # Calculate final prediction
        predicted_adr = base_adr * yoy_adjustment * booking_pace_factor * holiday_factor
        
        return max(0, predicted_adr)
    
    def _calculate_confidence_score(self, historical_data, last_year_data, forecast_date):
        """
        Calculate confidence score for a forecast based on data quality.
        
        Args:
            historical_data: List of historical data points
            last_year_data: List of data points from same time last year
            forecast_date: Date being forecast
            
        Returns:
            int: Confidence score (0-100)
        """
        # Base confidence starts at 60
        confidence = 60
        
        # Adjust based on amount of historical data
        if historical_data:
            confidence += min(20, len(historical_data) * 2)  # Up to 20 points for historical data
        
        # Adjust for year-over-year data
        if last_year_data:
            confidence += 10  # 10 points for having YoY data
        
        # Adjust for forecast horizon (closer dates are more predictable)
        days_from_now = (forecast_date - datetime.now().date()).days
        if days_from_now <= 7:
            confidence += 10  # Very near term
        elif days_from_now <= 30:
            confidence += 5  # Near term
        elif days_from_now >= 180:
            confidence -= 10  # Far future is less predictable
        
        # Ensure confidence is within valid range
        return min(100, max(0, confidence))
        
    def update_actuals(self, start_date=None, end_date=None):
        """
        Update forecasts with actual data once dates have passed.
        
        Args:
            start_date: Start date for updating actuals (defaults to 30 days ago)
            end_date: End date for updating actuals (defaults to yesterday)
            
        Returns:
            int: Number of forecasts updated
        """
        today = datetime.now().date()
        
        if start_date is None:
            start_date = today - timedelta(days=30)
            
        if end_date is None:
            end_date = today - timedelta(days=1)
            
        # Get forecasts for past dates that need actuals updated
        forecasts_to_update = self.db_session.query(RevenueForecast).filter(
            RevenueForecast.forecast_date >= start_date,
            RevenueForecast.forecast_date <= end_date,
            or_(
                RevenueForecast.actual_occupancy_rate.is_(None),
                RevenueForecast.actual_adr.is_(None),
                RevenueForecast.actual_revpar.is_(None),
                RevenueForecast.actual_room_revenue.is_(None)
            )
        ).all()
        
        count = 0
        for forecast in forecasts_to_update:
            date = forecast.forecast_date
            
            # Get actual metrics from analytics service
            occupancy_rate = self.analytics_service.get_daily_occupancy(date)
            adr = self.analytics_service.get_daily_adr(date)
            revpar = occupancy_rate * adr / 100
            
            # Calculate total room revenue
            total_rooms = self.db_session.query(func.count(Room.id)).scalar() or 0
            room_revenue = total_rooms * revpar
            
            # Update forecast with actuals
            forecast.actual_occupancy_rate = occupancy_rate
            forecast.actual_adr = adr
            forecast.actual_revpar = revpar
            forecast.actual_room_revenue = room_revenue
            
            count += 1
        
        # Commit updates
        if count > 0:
            self.db_session.commit()
            
            # Regenerate aggregations after updating actuals
            self.generate_aggregated_forecasts()
        
        return count
    
    def get_forecast_chart_data(self, start_date=None, days=90, include_actuals=True):
        """
        Get forecast data formatted for charts.
        
        Args:
            start_date: Start date for chart data (defaults to 30 days ago)
            days: Number of days to include
            include_actuals: Whether to include actual data for past dates
            
        Returns:
            Dictionary with data for charts
        """
        today = datetime.now().date()
        
        if start_date is None:
            start_date = today - timedelta(days=30)
            
        end_date = start_date + timedelta(days=days)
        
        # Get all forecasts for the period
        forecasts = self.db_session.query(RevenueForecast).filter(
            RevenueForecast.forecast_date >= start_date,
            RevenueForecast.forecast_date <= end_date
        ).order_by(RevenueForecast.forecast_date).all()
        
        # Prepare data for charts
        dates = []
        occupancy_predicted = []
        occupancy_actual = []
        adr_predicted = []
        adr_actual = []
        revpar_predicted = []
        revpar_actual = []
        revenue_predicted = []
        revenue_actual = []
        
        for forecast in forecasts:
            dates.append(forecast.forecast_date.strftime('%Y-%m-%d'))
            occupancy_predicted.append(forecast.predicted_occupancy_rate)
            adr_predicted.append(forecast.predicted_adr)
            revpar_predicted.append(forecast.predicted_revpar)
            revenue_predicted.append(forecast.predicted_room_revenue)
            
            if include_actuals and forecast.has_actuals:
                occupancy_actual.append(forecast.actual_occupancy_rate)
                adr_actual.append(forecast.actual_adr)
                revpar_actual.append(forecast.actual_revpar)
                revenue_actual.append(forecast.actual_room_revenue)
            else:
                occupancy_actual.append(None)
                adr_actual.append(None)
                revpar_actual.append(None)
                revenue_actual.append(None)
        
        return {
            'dates': dates,
            'occupancy': {
                'predicted': occupancy_predicted,
                'actual': occupancy_actual
            },
            'adr': {
                'predicted': adr_predicted,
                'actual': adr_actual
            },
            'revpar': {
                'predicted': revpar_predicted,
                'actual': revpar_actual
            },
            'revenue': {
                'predicted': revenue_predicted,
                'actual': revenue_actual
            }
        }
    
    def get_accuracy_metrics(self, period_days=30):
        """
        Get accuracy metrics for past forecasts.
        
        Args:
            period_days: Number of past days to analyze
            
        Returns:
            Dictionary with accuracy metrics
        """
        today = datetime.now().date()
        start_date = today - timedelta(days=period_days)
        
        # Get forecasts with actuals for the period
        forecasts = self.db_session.query(RevenueForecast).filter(
            RevenueForecast.forecast_date >= start_date,
            RevenueForecast.forecast_date < today,
            RevenueForecast.actual_room_revenue.isnot(None)
        ).all()
        
        if not forecasts:
            return {
                'mean_absolute_error': None,
                'mean_absolute_percentage_error': None,
                'accuracy_score': None,
                'count': 0
            }
        
        # Calculate error metrics
        absolute_errors = []
        percentage_errors = []
        accuracy_scores = []
        
        for forecast in forecasts:
            # Revenue error
            abs_error = abs(forecast.actual_room_revenue - forecast.predicted_room_revenue)
            absolute_errors.append(abs_error)
            
            # Percentage error (handle divide by zero)
            if forecast.predicted_room_revenue > 0:
                pct_error = (abs_error / forecast.predicted_room_revenue) * 100
                percentage_errors.append(pct_error)
            
            # Accuracy score
            if forecast.accuracy_score is not None:
                accuracy_scores.append(forecast.accuracy_score)
        
        # Calculate aggregate metrics
        mae = sum(absolute_errors) / len(absolute_errors) if absolute_errors else None
        mape = sum(percentage_errors) / len(percentage_errors) if percentage_errors else None
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else None
        
        return {
            'mean_absolute_error': round(mae, 2) if mae is not None else None,
            'mean_absolute_percentage_error': round(mape, 2) if mape is not None else None,
            'accuracy_score': round(avg_accuracy, 2) if avg_accuracy is not None else None,
            'count': len(forecasts)
        } 