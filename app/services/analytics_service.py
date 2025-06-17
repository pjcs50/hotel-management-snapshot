"""
Analytics service module.

This module provides service layer functionality for analytics data.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, extract, and_, text
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.user import User


class AnalyticsService:
    """Service class for analytics data."""

    def __init__(self, db_session):
        """Initialize with a database session."""
        self.db_session = db_session

    def get_monthly_occupancy(self, year=None):
        """
        Get monthly occupancy rates for a given year.
        
        Args:
            year: Year to get data for (defaults to current year)
            
        Returns:
            Dictionary with monthly occupancy rates
        """
        if year is None:
            year = datetime.now().year
            
        # Calculate total rooms available per month
        total_rooms_query = self.db_session.query(func.count(Room.id)).scalar()
        total_rooms = total_rooms_query or 0
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Adjust for leap year
        if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
            days_in_month[1] = 29
            
        # Calculate room-nights per month
        room_nights = [days * total_rooms for days in days_in_month]
        
        # Query bookings by month
        bookings_by_month = self.db_session.query(
            extract('month', Booking.check_in_date).label('month'),
            func.sum(
                func.julianday(func.min(Booking.check_out_date, func.date(f"{year}-12-31"))) - 
                func.julianday(func.max(Booking.check_in_date, func.date(f"{year}-01-01")))
            ).label('booked_days')
        ).filter(
            Booking.check_in_date <= func.date(f"{year}-12-31"),
            Booking.check_out_date >= func.date(f"{year}-01-01")
        ).group_by('month').all()
        
        # Initialize results with zeros
        occupancy_rates = [0] * 12
        
        # Fill in actual data
        for month, booked_days in bookings_by_month:
            if month >= 1 and month <= 12 and room_nights[month-1] > 0:
                occupancy_rates[month-1] = round((booked_days / room_nights[month-1]) * 100, 2)
        
        # Format data for Chart.js
        result = {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'datasets': [{
                'label': 'Occupancy Rate (%)',
                'data': occupancy_rates,
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 1
            }]
        }
        
        return result
    
    def get_daily_occupancy(self, date):
        """
        Get occupancy rate for a specific date.
        
        Args:
            date: Date to get occupancy for
            
        Returns:
            float: Occupancy rate as a percentage
        """
        # Get total number of rooms
        total_rooms = self.db_session.query(func.count(Room.id)).scalar() or 0
        
        if total_rooms == 0:
            return 0.0
            
        # Get count of occupied rooms for the date
        occupied_rooms = self.db_session.query(func.count(Booking.id)).filter(
            Booking.check_in_date <= date,
            Booking.check_out_date > date,
            Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
        ).scalar() or 0
        
        # Calculate occupancy rate
        occupancy_rate = (occupied_rooms / total_rooms) * 100
        
        return round(occupancy_rate, 2)
    
    def get_daily_adr(self, date):
        """
        Get average daily rate for a specific date.
        
        Args:
            date: Date to get ADR for
            
        Returns:
            float: Average daily rate
        """
        # Query bookings for this date
        bookings = self.db_session.query(Booking).filter(
            Booking.check_in_date <= date,
            Booking.check_out_date > date,
            Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT])
        ).all()
        
        if not bookings:
            # If no bookings for this date, return average from similar dates
            # This is a fallback to provide sensible data
            day_of_week = date.weekday()
            month = date.month
            
            # Look for bookings on same day of week in same month
            similar_bookings = self.db_session.query(Booking).filter(
                extract('dow', Booking.check_in_date) == day_of_week,
                extract('month', Booking.check_in_date) == month,
                Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT])
            ).all()
            
            if not similar_bookings:
                return 100.0  # Default value if no reference data
                
            # Calculate average rate
            total_price = sum(booking.total_price / booking.nights for booking in similar_bookings if booking.nights > 0)
            return round(total_price / len(similar_bookings), 2)
        
        # Calculate ADR from bookings
        total_price = sum(booking.total_price / booking.nights for booking in bookings if booking.nights > 0)
        adr = total_price / len(bookings)
        
        return round(adr, 2)
    
    def get_revenue_by_room_type(self, year=None, month=None):
        """
        Get revenue data grouped by room type.
        
        Args:
            year: Year to get data for (defaults to current year)
            month: Month to get data for (defaults to all months)
            
        Returns:
            Dictionary with revenue by room type
        """
        if year is None:
            year = datetime.now().year
            
        # Build query filters
        filters = [
            extract('year', Booking.check_in_date) == year,
            Booking.status.in_(['confirmed', 'checked_in', 'checked_out'])
        ]
        
        if month is not None:
            filters.append(extract('month', Booking.check_in_date) == month)
            
        # Query revenue by room type
        revenue_by_type = self.db_session.query(
            RoomType.name,
            func.sum(
                Booking.total_price
            ).label('revenue')
        ).join(
            Room, Booking.room_id == Room.id
        ).join(
            RoomType, Room.room_type_id == RoomType.id
        ).filter(
            *filters
        ).group_by(
            RoomType.name
        ).all()
        
        # Format data for Chart.js
        result = {
            'labels': [row[0] for row in revenue_by_type],
            'datasets': [{
                'label': 'Revenue ($)',
                'data': [float(row[1]) for row in revenue_by_type],
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                ],
                'borderColor': [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                ],
                'borderWidth': 1
            }]
        }
        
        return result
    
    def get_top_customers(self, limit=5):
        """
        Get the top customers by booking amount.
        
        Args:
            limit: Number of customers to return
            
        Returns:
            List of top customers with their total spend
        """
        # Query top customers
        top_customers = self.db_session.query(
            User.id,
            User.username,
            User.email,
            func.sum(Booking.total_price).label('total_spend'),
            func.count(Booking.id).label('booking_count')
        ).join(
            Booking, User.id == Booking.customer_id
        ).filter(
            Booking.status.in_(['confirmed', 'checked_in', 'checked_out'])
        ).group_by(
            User.id
        ).order_by(
            text('total_spend DESC')
        ).limit(limit).all()
        
        # Format results
        result = []
        for customer in top_customers:
            result.append({
                'id': customer[0],
                'username': customer[1],
                'email': customer[2],
                'total_spend': float(customer[3]),
                'booking_count': customer[4]
            })
            
        return result
    
    def get_booking_source_distribution(self):
        """
        Get the distribution of booking sources from real database data.
        
        Returns:
            Dictionary with booking source distribution data
        """
        # Query actual booking sources from the database
        source_counts = self.db_session.query(
            Booking.source,
            func.count(Booking.id)
        ).filter(
            Booking.source.isnot(None),
            Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
        ).group_by(Booking.source).all()
        
        # If no data, provide reasonable defaults
        if not source_counts:
            sources = {
                'Website': 0,
                'Phone': 0,
                'Walk-in': 0,
                'Front Desk': 0
            }
        else:
            sources = {}
            for source, count in source_counts:
                # Clean up source names and provide fallback
                clean_source = source if source else 'Unknown'
                sources[clean_source] = count
        
        # Format data for Chart.js
        result = {
            'labels': list(sources.keys()),
            'datasets': [{
                'data': list(sources.values()),
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)'
                ],
                'borderColor': [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                'borderWidth': 1
            }]
        }
        
        return result
    
    def get_total_room_revenue(self, start_date: datetime.date, end_date: datetime.date) -> float:
        """
        Calculate total room revenue for a given period.

        Args:
            start_date: The start date of the period.
            end_date: The end date of the period.

        Returns:
            Total room revenue as a float.
        """
        total_revenue = self.db_session.query(
            func.sum(Booking.total_price)
        ).filter(
            Booking.check_in_date <= end_date,
            Booking.check_out_date > start_date, # Capture bookings that overlap the start_date
            Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED]) # Changed from STATUS_CONFIRMED
        ).scalar()
        
        return float(total_revenue) if total_revenue else 0.0

    def get_number_of_rooms_sold(self, start_date: datetime.date, end_date: datetime.date) -> int:
        """
        Calculate the number of rooms sold (occupied room nights) for a given period.

        Args:
            start_date: The start date of the period.
            end_date: The end date of the period.

        Returns:
            Number of rooms sold (occupied room nights).
        """
        # Approach: For each booking that overlaps with the period, count the days it overlaps
        overlapping_bookings = self.db_session.query(Booking).filter(
            Booking.check_in_date <= end_date,
            Booking.check_out_date > start_date,
            Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
        ).all()
        
        room_nights = 0
        for booking in overlapping_bookings:
            # Calculate the overlap between the booking and the period
            overlap_start = max(booking.check_in_date, start_date)
            overlap_end = min(booking.check_out_date, end_date)
            days_overlapping = (overlap_end - overlap_start).days
            room_nights += days_overlapping
            
        return room_nights

    def get_total_available_room_nights(self, start_date: datetime.date, end_date: datetime.date) -> int:
        """
        Calculate the total available room nights for a given period.

        Args:
            start_date: The start date of the period.
            end_date: The end date of the period.

        Returns:
            Total available room nights.
        """
        total_rooms = self.db_session.query(func.count(Room.id)).scalar() or 0
        days_in_period = (end_date - start_date).days
        
        return total_rooms * days_in_period

    def calculate_adr(self, start_date: datetime.date, end_date: datetime.date) -> float:
        """
        Calculate the Average Daily Rate (ADR) for a given period.

        Args:
            start_date: The start date of the period.
            end_date: The end date of the period.

        Returns:
            ADR as a float.
        """
        total_revenue = self.get_total_room_revenue(start_date, end_date)
        rooms_sold = self.get_number_of_rooms_sold(start_date, end_date)
        
        if rooms_sold == 0:
            return 0.0
            
        return total_revenue / rooms_sold

    def calculate_revpar(self, start_date: datetime.date, end_date: datetime.date) -> float:
        """
        Calculate the Revenue Per Available Room (RevPAR) for a given period.

        Args:
            start_date: The start date of the period.
            end_date: The end date of the period.

        Returns:
            RevPAR as a float.
        """
        total_revenue = self.get_total_room_revenue(start_date, end_date)
        available_room_nights = self.get_total_available_room_nights(start_date, end_date)
        
        if available_room_nights == 0:
            return 0.0
            
        return total_revenue / available_room_nights
    
    def get_forecast_data(self, days=30):
        """
        Get booking forecast data for upcoming days.
        
        Args:
            days: Number of days to include in forecast
            
        Returns:
            Dictionary with forecast data
        """
        today = datetime.now().date()
        end_date = today + timedelta(days=days)
        
        # Get daily counts for next 'days' days
        daily_counts = []
        labels = []
        
        for day in range(days):
            date = today + timedelta(days=day)
            labels.append(date.strftime('%b %d'))
        
            # Count bookings for this day
            count = self.db_session.query(func.count(Booking.id)).filter(
                Booking.check_in_date <= date,
                Booking.check_out_date > date,
                Booking.status == Booking.STATUS_RESERVED
            ).scalar() or 0
            
            daily_counts.append(count)
        
        # Format for Chart.js
        result = {
            'labels': labels,
            'datasets': [{
                'label': 'Expected Occupancy',
                'data': daily_counts,
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 1,
                'tension': 0.4
            }]
        }
        
        return result 