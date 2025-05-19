"""
Report service module.

This module provides services for generating reports on hotel operations.
"""

from datetime import datetime, timedelta, date
from calendar import monthrange
from sqlalchemy import func, extract, case, and_, or_, select
import numpy as np
from db import db

from app.models.user import User
from app.models.room import Room
from app.models.booking import Booking

class ReportService:
    """
    Service for generating hotel operation reports.
    
    Attributes:
        db_session: SQLAlchemy database session
    """
    
    def __init__(self, db_session):
        """Initialize the service with a database session."""
        self.db_session = db_session
    
    def get_occupancy_report(self, start_date_str, end_date_str):
        """
        Generate an occupancy report for a date range.
        
        Args:
            start_date_str: Start date string in YYYY-MM-DD format
            end_date_str: End date string in YYYY-MM-DD format
            
        Returns:
            Dictionary with occupancy report data
        """
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            total_rooms = self.db_session.execute(select(func.count(Room.id))).scalar_one_or_none() or 0
            
            daily_occupancy = self._calculate_daily_occupancy(start_date_obj, end_date_obj, total_rooms)
            
            avg_occupancy = sum(daily_occupancy.values()) / len(daily_occupancy) if daily_occupancy else 0
            
            peak_date = None
            peak_rate = 0
            for day, rate in daily_occupancy.items():
                if rate > peak_rate:
                    peak_date = day
                    peak_rate = rate
            
            total_room_nights = self._calculate_total_room_nights(start_date_obj, end_date_obj)
            
            total_bookings_query = select(func.count(Booking.id)).filter(
                or_(
                    and_(Booking.check_in_date >= start_date_obj, Booking.check_in_date <= end_date_obj),
                    and_(Booking.check_out_date >= start_date_obj, Booking.check_out_date <= end_date_obj),
                    and_(Booking.check_in_date <= start_date_obj, Booking.check_out_date >= end_date_obj)
                )
            )
            total_bookings = self.db_session.execute(total_bookings_query).scalar_one_or_none() or 0
            
            new_bookings_query = select(func.count(Booking.id)).filter(
                    Booking.created_at >= start_date_obj,
                Booking.created_at < (end_date_obj + timedelta(days=1)) # up to, but not including, the next day
            )
            new_bookings = self.db_session.execute(new_bookings_query).scalar_one_or_none() or 0
            
            cancelled_bookings_query = select(func.count(Booking.id)).filter(
                    Booking.status == Booking.STATUS_CANCELLED,
                    Booking.updated_at >= start_date_obj,
                Booking.updated_at < (end_date_obj + timedelta(days=1))
            )
            cancelled_bookings = self.db_session.execute(cancelled_bookings_query).scalar_one_or_none() or 0
            
            completed_stays_query = select(func.count(Booking.id)).filter(
                    Booking.status == Booking.STATUS_CHECKED_OUT,
                    Booking.updated_at >= start_date_obj,
                Booking.updated_at < (end_date_obj + timedelta(days=1))
            )
            completed_stays = self.db_session.execute(completed_stays_query).scalar_one_or_none() or 0
            
            return {
                'occupancy_summary': {
                    'average_occupancy_rate': avg_occupancy,
                    'peak_occupancy_date': peak_date.strftime('%Y-%m-%d') if peak_date else None,
                    'peak_occupancy_rate': peak_rate,
                    'total_room_nights': total_room_nights
                },
                'booking_summary': {
                    'total_bookings': total_bookings,
                    'new_bookings': new_bookings,
                    'cancelled_bookings': cancelled_bookings,
                    'completed_stays': completed_stays
                },
                'daily_occupancy': daily_occupancy,
                'revenue_summary': {
                    'total_revenue': 0,
                    'room_revenue': 0,
                },
                'room_type_revenue': {}
            }
        except Exception as e:
            print(f"Error generating occupancy report: {str(e)}")
            return None
    
    def get_revenue_report(self, start_date_str, end_date_str):
        """
        Generate a revenue report for a date range.
        
        Args:
            start_date_str: Start date string in YYYY-MM-DD format
            end_date_str: End date string in YYYY-MM-DD format
            
        Returns:
            Dictionary with revenue report data
        """
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            monthly_revenue = self._calculate_monthly_revenue(start_date_obj, end_date_obj)
            room_type_revenue = self._calculate_room_type_revenue(start_date_obj, end_date_obj)
            
            total_bookings_query = select(func.count(Booking.id)).filter(
                or_(
                    and_(Booking.check_in_date >= start_date_obj, Booking.check_in_date <= end_date_obj),
                    and_(Booking.check_out_date >= start_date_obj, Booking.check_out_date <= end_date_obj),
                    and_(Booking.check_in_date <= start_date_obj, Booking.check_out_date >= end_date_obj)
                )
            )
            total_bookings = self.db_session.execute(total_bookings_query).scalar_one_or_none() or 0
            
            total_rooms = self.db_session.execute(select(func.count(Room.id))).scalar_one_or_none() or 0
            daily_occupancy = self._calculate_daily_occupancy(start_date_obj, end_date_obj, total_rooms)
            avg_occupancy = sum(daily_occupancy.values()) / len(daily_occupancy) if daily_occupancy else 0
            
            return {
                'revenue_summary': {
                    'total_revenue': monthly_revenue,
                    'room_revenue': monthly_revenue, 
                },
                'room_type_revenue': room_type_revenue,
                'booking_summary': {
                    'total_bookings': total_bookings,
                    'new_bookings': 0, 
                    'cancelled_bookings': 0, 
                    'completed_stays': 0 
                },
                'occupancy_summary': {
                    'average_occupancy_rate': avg_occupancy,
                    'peak_occupancy_date': None, 
                    'peak_occupancy_rate': 0, 
                    'total_room_nights': 0 
                },
                'daily_occupancy': daily_occupancy
            }
        except Exception as e:
            print(f"Error generating revenue report: {str(e)}")
            return None
    
    def get_staff_activity_report(self, start_date_str, end_date_str):
        """
        Generate a staff activity report for a date range.
        
        Args:
            start_date_str: Start date string in YYYY-MM-DD format
            end_date_str: End date string in YYYY-MM-DD format
            
        Returns:
            Dictionary with staff activity report data
        """
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            staff_counts_query = select(User.role, func.count(User.id)).filter(
                User.role.in_(['receptionist', 'manager', 'housekeeping', 'admin'])
            ).group_by(User.role)
            staff_counts_results = self.db_session.execute(staff_counts_query).all()
            staff_by_role = {role: count for role, count in staff_counts_results}
            
            # Placeholder for actual activity data - this would involve querying logs or specific activity tables
            # Example: tasks completed, check-ins handled, etc.
            staff_activity_data = {
                'tasks_completed_by_user': {},
                'check_ins_by_receptionist': {},
                'rooms_cleaned_by_housekeeper': {}
            }

            return {
                'staff_summary': {
                    'total_staff': sum(staff_by_role.values()),
                    'staff_by_role': staff_by_role
                },
                'staff_activity': staff_activity_data, 
                'period': {
                    'start_date': start_date_str,
                    'end_date': end_date_str
                }
            }
        except Exception as e:
            print(f"Error generating staff activity report: {str(e)}")
            return None

    def get_monthly_report(self, year, month):
        """
        Generate a comprehensive monthly report.
        
        Args:
            year: Year for the report
            month: Month for the report (1-12)
            
        Returns:
            Dictionary with various report metrics
        """
        # Calculate the start and end date for the month
        _, last_day = monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)
        
        # Total number of rooms
        total_rooms = self.db_session.execute(select(func.count(Room.id))).scalar_one_or_none() or 0
        
        # Calculate daily occupancy
        daily_occupancy = self._calculate_daily_occupancy(start_date, end_date, total_rooms)
        
        # Calculate average occupancy rate
        if daily_occupancy:
            avg_occupancy = sum(daily_occupancy.values()) / len(daily_occupancy)
        else:
            avg_occupancy = 0
        
        # Find peak occupancy date
        peak_date = None
        peak_rate = 0
        for day, rate in daily_occupancy.items():
            if rate > peak_rate:
                peak_date = day
                peak_rate = rate
        
        # Calculate revenue for the month
        monthly_revenue = self._calculate_monthly_revenue(start_date, end_date)
        
        # Calculate revenue by room type
        room_type_revenue = self._calculate_room_type_revenue(start_date, end_date)
        
        # Calculate total room nights
        total_room_nights = self._calculate_total_room_nights(start_date, end_date)
        
        # Booking statistics
        total_bookings_query = select(func.count(Booking.id)).filter(
                or_(
                    and_(
                        Booking.check_in_date >= start_date,
                        Booking.check_in_date <= end_date
                    ),
                    and_(
                        Booking.check_out_date >= start_date,
                        Booking.check_out_date <= end_date
                    ),
                    and_(
                        Booking.check_in_date <= start_date,
                        Booking.check_out_date >= end_date
                    )
                )
        )
        total_bookings = self.db_session.execute(total_bookings_query).scalar_one_or_none() or 0
        
        new_bookings_query = select(func.count(Booking.id)).filter(
                extract('year', Booking.created_at) == year,
                extract('month', Booking.created_at) == month
        )
        new_bookings = self.db_session.execute(new_bookings_query).scalar_one_or_none() or 0
        
        cancelled_bookings_query = select(func.count(Booking.id)).filter(
                Booking.status == Booking.STATUS_CANCELLED,
                extract('year', Booking.updated_at) == year,
                extract('month', Booking.updated_at) == month
        )
        cancelled_bookings = self.db_session.execute(cancelled_bookings_query).scalar_one_or_none() or 0
        
        completed_stays_query = select(func.count(Booking.id)).filter(
                Booking.status == Booking.STATUS_CHECKED_OUT,
                extract('year', Booking.updated_at) == year,
                extract('month', Booking.updated_at) == month
        )
        completed_stays = self.db_session.execute(completed_stays_query).scalar_one_or_none() or 0
        
        # Compile the report
        return {
            'revenue_summary': {
                'total_revenue': monthly_revenue,
                'room_revenue': monthly_revenue,  # In a full implementation, would include other revenue sources
            },
            'occupancy_summary': {
                'average_occupancy_rate': avg_occupancy,
                'peak_occupancy_date': peak_date,
                'peak_occupancy_rate': peak_rate,
                'total_room_nights': total_room_nights
            },
            'booking_summary': {
                'total_bookings': total_bookings,
                'new_bookings': new_bookings,
                'cancelled_bookings': cancelled_bookings,
                'completed_stays': completed_stays
            },
            'room_type_revenue': room_type_revenue,
            'daily_occupancy': daily_occupancy
        }
    
    def _calculate_daily_occupancy(self, start_date, end_date, total_rooms):
        """
        Calculate daily occupancy rates for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            total_rooms: Total number of rooms in the hotel
            
        Returns:
            Dictionary with dates as keys and occupancy rates as values
        """
        from app.models.booking import Booking
        
        # Generate all dates in the range
        result = {}
        current_date = start_date
        while current_date <= end_date:
            # Count bookings for the current date
            occupied_rooms_query = select(func.count(Booking.id)).filter(
                    Booking.check_in_date <= current_date,
                    Booking.check_out_date > current_date,
                    Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
            )
            occupied_rooms = self.db_session.execute(occupied_rooms_query).scalar_one_or_none() or 0
            
            # Calculate occupancy rate
            occupancy_rate = 0
            if total_rooms > 0:
                occupancy_rate = (occupied_rooms / total_rooms) * 100
            
            # Store the result
            result[current_date.strftime('%Y-%m-%d')] = occupancy_rate
            
            # Move to the next day
            current_date += timedelta(days=1)
        
        return result
    
    def _calculate_monthly_revenue(self, start_date, end_date):
        """
        Calculate total revenue for a month.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Total revenue for the month
        """
        from app.models.booking import Booking
        from app.models.room import Room
        from app.models.room_type import RoomType
        
        # For each booking, calculate the revenue:
        # - If a booking spans outside the month, only count the days within the month
        # - Use room base_rate * number of nights
        
        # Get all bookings that overlap with the month
        bookings_query = select(Booking, Room, RoomType).join(
            Room, Booking.room_id == Room.id
        ).join(
            RoomType, Room.room_type_id == RoomType.id
        ).filter(
            or_(
                and_(
                    Booking.check_in_date >= start_date,
                    Booking.check_in_date <= end_date
                ),
                and_(
                    Booking.check_out_date >= start_date,
                    Booking.check_out_date <= end_date
                ),
                and_(
                    Booking.check_in_date <= start_date,
                    Booking.check_out_date >= end_date
                )
            ),
            Booking.status != Booking.STATUS_CANCELLED
        )
        bookings_results = self.db_session.execute(bookings_query).all() # .all() gives list of Row objects
        
        total_revenue = 0
        # Each item in bookings_results is a Row, access attributes by model name or index
        for row in bookings_results:
            booking = row.Booking
            room_type = row.RoomType
            # Calculate the number of nights within the month
            booking_start = max(booking.check_in_date, start_date)
            booking_end = min(booking.check_out_date, end_date)
            nights = (booking_end - booking_start).days
            
            # Add the revenue for this booking
            if nights > 0:
                total_revenue += float(room_type.base_rate) * nights
        
        return total_revenue
    
    def _calculate_room_type_revenue(self, start_date, end_date):
        """
        Calculate revenue by room type.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with room types as keys and revenue information as values
        """
        from app.models.booking import Booking
        from app.models.room import Room
        from app.models.room_type import RoomType
        
        # Get all room types
        room_types_query = select(RoomType)
        room_types = self.db_session.execute(room_types_query).scalars().all()
        
        result = {}
        total_revenue = 0
        
        # For each room type, calculate the revenue
        for rt in room_types:
            # Get all bookings for this room type in the month
            bookings_query = select(Booking, Room).join(
                Room, Booking.room_id == Room.id
            ).filter(
                Room.room_type_id == rt.id,
                or_(
                    and_(
                        Booking.check_in_date >= start_date,
                        Booking.check_in_date <= end_date
                    ),
                    and_(
                        Booking.check_out_date >= start_date,
                        Booking.check_out_date <= end_date
                    ),
                    and_(
                        Booking.check_in_date <= start_date,
                        Booking.check_out_date >= end_date
                    )
                ),
                Booking.status != Booking.STATUS_CANCELLED
            )
            bookings_results = self.db_session.execute(bookings_query).all() # List of Row objects
            
            rt_revenue = 0
            for row in bookings_results:
                booking = row.Booking
                # Calculate the number of nights within the month
                booking_start = max(booking.check_in_date, start_date)
                booking_end = min(booking.check_out_date, end_date)
                nights = (booking_end - booking_start).days
                
                # Add the revenue for this booking
                if nights > 0:
                    rt_revenue += float(rt.base_rate) * nights
            
            result[rt.name] = {
                'revenue': rt_revenue,
                'percentage': 0  # Will calculate after getting total
            }
            total_revenue += rt_revenue
        
        # Calculate percentages
        if total_revenue > 0:
            for rt_name in result:
                result[rt_name]['percentage'] = (result[rt_name]['revenue'] / total_revenue) * 100
        
        return result
    
    def _calculate_total_room_nights(self, start_date, end_date):
        """
        Calculate total room nights for the month.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Total room nights
        """
        from app.models.booking import Booking
        
        # Get all bookings that overlap with the month
        bookings_query = select(Booking).filter(
            or_(
                and_(
                    Booking.check_in_date >= start_date,
                    Booking.check_in_date <= end_date
                ),
                and_(
                    Booking.check_out_date >= start_date,
                    Booking.check_out_date <= end_date
                ),
                and_(
                    Booking.check_in_date <= start_date,
                    Booking.check_out_date >= end_date
                )
            ),
            Booking.status != Booking.STATUS_CANCELLED
        )
        bookings = self.db_session.execute(bookings_query).scalars().all()
        
        total_nights = 0
        for booking in bookings:
            # Calculate the number of nights within the month
            booking_start = max(booking.check_in_date, start_date)
            booking_end = min(booking.check_out_date, end_date)
            nights = (booking_end - booking_start).days
            
            # Add the nights for this booking
            if nights > 0:
                total_nights += nights
        
        return total_nights
    
    def get_available_report_periods(self):
        """
        Get a list of available year/month periods for filtering reports.
        """
        from app.models.booking import Booking # Import here if not already at top level
        
        # Query distinct year/month combinations from bookings
        # This query might need adjustment based on your specific database (e.g., SQLite, PostgreSQL)
        # For SQLite, strftime is common. For others, EXTRACT or DATE_PART might be used.
        try:
            # Attempt SQLite compatible query first
            periods_query = self.db_session.query(
                func.strftime('%Y', Booking.check_in_date).label('year'),
                func.strftime('%m', Booking.check_in_date).label('month')
            ).distinct().order_by(func.strftime('%Y', Booking.check_in_date).desc(), func.strftime('%m', Booking.check_in_date).desc())
            periods = periods_query.all()
        except Exception:
            # Fallback or alternative query for other DBs if needed, or just log error
            # For example, for PostgreSQL:
            # periods_query = self.db_session.query(
            #     extract('year', Booking.check_in_date).label('year'),
            #     extract('month', Booking.check_in_date).label('month')
            # ).distinct().order_by(extract('year', Booking.check_in_date).desc(), extract('month', Booking.check_in_date).desc())
            # periods = periods_query.all()
            periods = [] # Default to empty list on error
            print("Error querying report periods, database-specific function might be needed.")

        return [(str(int(year)), str(int(month))) for year, month in periods]

    # Add the missing export methods
    def export_to_csv(self, data, title):
        """Exports report data to CSV format."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Placeholder: Write a title and headers
        writer.writerow([title])
        if data and isinstance(data, dict) and data.get('daily_occupancy'): # Example for occupancy
            writer.writerow(['Date', 'Occupancy Rate'])
            for date_str, rate in data['daily_occupancy'].items():
                writer.writerow([date_str, rate])
        elif data and isinstance(data, list): # Generic list of dicts
            if data:
                headers = data[0].keys()
                writer.writerow(headers)
                for row in data:
                    writer.writerow(row.values())
        else:
            writer.writerow(['No data available to export.'])
        
        return output.getvalue().encode('utf-8')

    def export_to_excel(self, data, title):
        """Exports report data to Excel (XLSX) format. Placeholder."""
        # Placeholder: In a real app, use a library like openpyxl
        # For now, just return a CSV-like string indicating it's an Excel export
        csv_data = self.export_to_csv(data, title) # Leverage CSV export for content
        # Typically, you'd use a proper Excel library here.
        # This is just a stub.
        return csv_data # Returning CSV bytes for now, as actual Excel generation is complex

    def export_to_pdf(self, data, title):
        """Exports report data to PDF format. Placeholder."""
        # Placeholder: In a real app, use a library like ReportLab or WeasyPrint
        if not hasattr(self, '_check_pdf_dependencies') or not self._check_pdf_dependencies():
            raise ImportError("PDF generation libraries (e.g., WeasyPrint) not installed.")
        
        # Actual PDF generation logic would go here.
        # For now, returning a simple text message as bytes.
        message = f"PDF Export for: {title}\n\nData (simplified):\n{str(data)[:500]}..."        
        return message.encode('utf-8')

    def _check_pdf_dependencies(self):
        try:
            import weasyprint # Example dependency
            return True
        except ImportError:
            return False 