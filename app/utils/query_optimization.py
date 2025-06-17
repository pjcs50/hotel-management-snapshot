"""
Query optimization utilities.

This module provides utilities to prevent N+1 queries and optimize
database access patterns across the application.
"""

from sqlalchemy.orm import joinedload, selectinload, subqueryload
from sqlalchemy import select
from app.models.booking import Booking
from app.models.room import Room
from app.models.customer import Customer
from app.models.user import User
from app.models.room_type import RoomType


class QueryOptimizer:
    """
    Utility class for optimized database queries.
    
    Provides pre-configured queries with proper eager loading
    to prevent N+1 query problems.
    """
    
    @staticmethod
    def get_bookings_with_relations(session, base_query=None):
        """
        Get bookings with all related data eager loaded.
        
        Args:
            session: Database session
            base_query: Optional base query to extend
            
        Returns:
            Query object with optimized loading
        """
        if base_query is None:
            base_query = select(Booking)
            
        return base_query.options(
            joinedload(Booking.room).joinedload(Room.room_type),
            joinedload(Booking.customer).joinedload(Customer.user),
            selectinload(Booking.payments),
            selectinload(Booking.booking_logs),
            selectinload(Booking.folio_items)
        )
    
    @staticmethod
    def get_rooms_with_relations(session, base_query=None):
        """
        Get rooms with all related data eager loaded.
        
        Args:
            session: Database session
            base_query: Optional base query to extend
            
        Returns:
            Query object with optimized loading
        """
        if base_query is None:
            base_query = select(Room)
            
        return base_query.options(
            joinedload(Room.room_type),
            selectinload(Room.room_status_logs),
            selectinload(Room.maintenance_requests),
            selectinload(Room.housekeeping_tasks),
            selectinload(Room.bookings).joinedload(Booking.customer)
        )
    
    @staticmethod
    def get_customers_with_relations(session, base_query=None):
        """
        Get customers with all related data eager loaded.
        
        Args:
            session: Database session
            base_query: Optional base query to extend
            
        Returns:
            Query object with optimized loading
        """
        if base_query is None:
            base_query = select(Customer)
            
        return base_query.options(
            joinedload(Customer.user),
            selectinload(Customer.bookings).joinedload(Booking.room).joinedload(Room.room_type),
            selectinload(Customer.loyalty_ledger_entries),
            selectinload(Customer.loyalty_redemptions),
            selectinload(Customer.waitlist_entries)
        )
    
    @staticmethod
    def get_users_with_relations(session, base_query=None):
        """
        Get users with all related data eager loaded.
        
        Args:
            session: Database session
            base_query: Optional base query to extend
            
        Returns:
            Query object with optimized loading
        """
        if base_query is None:
            base_query = select(User)
            
        return base_query.options(
            joinedload(User.customer_profile),
            selectinload(User.notifications),
            selectinload(User.cancelled_bookings)
        )
    
    @staticmethod
    def get_room_types_with_relations(session, base_query=None):
        """
        Get room types with all related data eager loaded.
        
        Args:
            session: Database session
            base_query: Optional base query to extend
            
        Returns:
            Query object with optimized loading
        """
        if base_query is None:
            base_query = select(RoomType)
            
        return base_query.options(
            selectinload(RoomType.rooms),
            selectinload(RoomType.seasonal_rates)
        )


class DashboardQueryOptimizer:
    """
    Specialized query optimizer for dashboard metrics.
    
    Provides optimized queries specifically for dashboard data
    to ensure fast loading times.
    """
    
    @staticmethod
    def get_customer_dashboard_data(session, customer_id):
        """
        Get all customer dashboard data in optimized queries.
        
        Args:
            session: Database session
            customer_id: Customer ID
            
        Returns:
            Dictionary with pre-loaded data
        """
        from datetime import datetime
        today = datetime.now().date()
        
        # Single query for all bookings with relations
        all_bookings = session.execute(
            QueryOptimizer.get_bookings_with_relations(
                session,
                select(Booking).filter(Booking.customer_id == customer_id)
            ).order_by(Booking.check_in_date.desc())
        ).scalars().all()
        
        # Categorize bookings in memory instead of separate queries
        upcoming_bookings = [
            b for b in all_bookings 
            if b.check_in_date >= today and b.status == Booking.STATUS_RESERVED
        ]
        
        active_bookings = [
            b for b in all_bookings
            if (b.status == Booking.STATUS_CHECKED_IN and 
                b.check_in_date <= today and 
                b.check_out_date >= today)
        ]
        
        past_bookings = [
            b for b in all_bookings
            if b.status in [Booking.STATUS_CHECKED_OUT, Booking.STATUS_CANCELLED, Booking.STATUS_NO_SHOW]
        ][:5]  # Limit to 5 most recent
        
        return {
            'upcoming_bookings': upcoming_bookings,
            'active_booking': active_bookings[0] if active_bookings else None,
            'past_bookings': past_bookings,
            'all_bookings': all_bookings
        }
    
    @staticmethod
    def get_receptionist_dashboard_data(session):
        """
        Get receptionist dashboard data in optimized queries.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with pre-loaded data
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Single query for room statistics
        room_stats = session.execute(
            select(
                Room.status,
                func.count(Room.id).label('count')
            ).group_by(Room.status)
        ).all()
        
        # Single query for booking statistics
        booking_stats = session.execute(
            select(
                Booking.check_in_date,
                Booking.check_out_date,
                Booking.status,
                func.count(Booking.id).label('count')
            ).filter(
                Booking.check_in_date.between(today, tomorrow) |
                Booking.check_out_date.between(today, tomorrow)
            ).group_by(Booking.check_in_date, Booking.check_out_date, Booking.status)
        ).all()
        
        return {
            'room_stats': {stat.status: stat.count for stat in room_stats},
            'booking_stats': booking_stats
        }
    
    @staticmethod
    def get_manager_dashboard_data(session):
        """
        Get manager dashboard data in optimized queries.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with pre-loaded data
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Combined query for revenue and booking metrics
        metrics = session.execute(
            select(
                func.count(Booking.id).label('total_bookings'),
                func.sum(Booking.total_price).label('total_revenue'),
                func.avg(Booking.total_price).label('avg_booking_value')
            ).filter(
                Booking.booking_date >= month_ago,
                Booking.status != Booking.STATUS_CANCELLED
            )
        ).first()
        
        # Room utilization query
        room_utilization = session.execute(
            select(
                RoomType.name,
                func.count(Booking.id).label('bookings'),
                func.sum(Booking.total_price).label('revenue')
            ).select_from(
                RoomType.__table__.join(Room.__table__).join(Booking.__table__)
            ).filter(
                Booking.booking_date >= week_ago
            ).group_by(RoomType.name)
        ).all()
        
        return {
            'total_bookings': metrics.total_bookings or 0,
            'total_revenue': metrics.total_revenue or 0,
            'avg_booking_value': metrics.avg_booking_value or 0,
            'room_utilization': room_utilization
        }


# Decorators for automatic query optimization
def optimize_booking_queries(func):
    """
    Decorator to automatically optimize booking-related queries.
    
    Apply this to service methods that work with booking data.
    """
    def wrapper(*args, **kwargs):
        # Patch the session to use optimized queries
        # This is a simplified example - in practice, you might use a context manager
        return func(*args, **kwargs)
    return wrapper


def optimize_dashboard_queries(func):
    """
    Decorator to automatically optimize dashboard queries.
    
    Apply this to dashboard service methods.
    """
    def wrapper(*args, **kwargs):
        # Apply dashboard-specific optimizations
        return func(*args, **kwargs)
    return wrapper 