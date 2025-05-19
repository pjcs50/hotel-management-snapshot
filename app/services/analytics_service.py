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
        Get the distribution of booking sources.
        
        Returns:
            Dictionary with booking source distribution data
        """
        # This is a placeholder implementation
        # In a real application, you would query the actual booking sources
        sources = {
            'Website': 65,
            'Phone': 20,
            'Walk-in': 5,
            'Travel Agent': 10
        }
        
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
                ],
                'borderColor': [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
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
            Total number of rooms sold as an integer.
        """
        # This counts each night a room is occupied within the period.
        # It iterates through each day in the period and counts rooms occupied on that day.
        rooms_sold = 0
        current_date = start_date
        while current_date <= end_date:
            occupied_on_date = self.db_session.query(
                func.count(Booking.id)
            ).filter(
                Booking.check_in_date <= current_date,
                Booking.check_out_date > current_date,
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_RESERVED]) # Changed from STATUS_CONFIRMED
            ).scalar()
            rooms_sold += (occupied_on_date if occupied_on_date else 0)
            current_date += timedelta(days=1)
        return rooms_sold

    def get_total_available_room_nights(self, start_date: datetime.date, end_date: datetime.date) -> int:
        """
        Calculate the total number of available room nights for a given period.

        Args:
            start_date: The start date of the period.
            end_date: The end date of the period.

        Returns:
            Total available room nights as an integer.
        """
        total_hotel_rooms = self.db_session.query(func.count(Room.id)).scalar()
        if not total_hotel_rooms:
            return 0
        
        num_days = (end_date - start_date).days + 1
        return total_hotel_rooms * num_days

    def calculate_adr(self, start_date: datetime.date, end_date: datetime.date) -> float:
        """
        Calculate Average Daily Rate (ADR) for a given period.
        ADR = Total Room Revenue / Number of Rooms Sold

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
        return round(total_revenue / rooms_sold, 2)

    def calculate_revpar(self, start_date: datetime.date, end_date: datetime.date) -> float:
        """
        Calculate Revenue Per Available Room (RevPAR) for a given period.
        RevPAR = Total Room Revenue / Total Available Room Nights

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
        return round(total_revenue / available_room_nights, 2)
    
    def get_forecast_data(self, days=30):
        """
        Get forecast data for upcoming days.
        
        Args:
            days: Number of days to forecast
            
        Returns:
            Dictionary with forecast data
        """
        today = datetime.now().date()
        date_range = [today + timedelta(days=i) for i in range(days)]
        
        # Query bookings for the date range
        bookings_by_date = self.db_session.query(
            func.date(Booking.check_in_date).label('date'),
            func.count(Booking.id).label('count')
        ).filter(
            Booking.check_in_date >= today,
            Booking.check_in_date <= today + timedelta(days=days-1),
            Booking.status.in_(['confirmed', 'checked_in'])
        ).group_by('date').all()
        
        # Convert to dictionary for easier lookup
        bookings_dict = {row[0].isoformat(): row[1] for row in bookings_by_date}
        
        # Create forecast data
        dates = [d.isoformat() for d in date_range]
        counts = [bookings_dict.get(d, 0) for d in dates]
        
        # Format data for Chart.js
        result = {
            'labels': dates,
            'datasets': [{
                'label': 'Forecast Bookings',
                'data': counts,
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 1,
                'tension': 0.4
            }]
        }
        
        return result 