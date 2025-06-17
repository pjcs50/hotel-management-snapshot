"""
Dashboard service module.

This module provides services for dashboard data and metrics.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, select, text, distinct

from app.models.booking import Booking
from app.models.room import Room
from app.models.room_status_log import RoomStatusLog
from app.models.customer import Customer
from app.models.user import User
from app.models.room_type import RoomType
from app.services.analytics_service import AnalyticsService
from app.services.notification_service import NotificationService
from app.models.booking_log import BookingLog
from app.models.payment import Payment


class DashboardService:
    """
    Service for dashboard data and metrics.
    
    This service provides methods for retrieving dashboard data for different user roles.
    """

    def __init__(self, db_session):
        """Initialize the service with a database session."""
        self.db_session = db_session
    
    def get_customer_metrics(self, user_id):
        """
        Get dashboard metrics for a customer.
        
        Args:
            user_id: ID of the customer user
            
        Returns:
            Dictionary of dashboard metrics
        """
        # Get the customer associated with the user
        customer = self.db_session.execute(
            select(Customer).filter_by(user_id=user_id)
        ).scalar_one_or_none()
        
        if not customer:
            return {
                "error": "Customer profile not found"
            }
        
        # Get upcoming bookings with eager loading to prevent N+1 queries
        today = datetime.now().date()
        from sqlalchemy.orm import joinedload
        
        upcoming_bookings = self.db_session.execute(
            select(Booking)
            .options(
                joinedload(Booking.room).joinedload(Room.room_type),
                joinedload(Booking.customer)
            )
            .filter(
                Booking.customer_id == customer.id,
                Booking.check_in_date >= today,
                Booking.status == Booking.STATUS_RESERVED
            ).order_by(Booking.check_in_date)
        ).scalars().all()
        
        # Get active booking (currently checked in) with eager loading
        active_booking = self.db_session.execute(
            select(Booking)
            .options(
                joinedload(Booking.room).joinedload(Room.room_type),
                joinedload(Booking.customer)
            )
            .filter(
                Booking.customer_id == customer.id,
                Booking.status == Booking.STATUS_CHECKED_IN,
                Booking.check_in_date <= today,
                Booking.check_out_date >= today
            )
        ).scalar_one_or_none()
        
        # Get past bookings (checked out or cancelled) with eager loading
        past_bookings = self.db_session.execute(
            select(Booking)
            .options(
                joinedload(Booking.room).joinedload(Room.room_type),
                joinedload(Booking.customer)
            )
            .filter(
                Booking.customer_id == customer.id,
                Booking.status.in_([Booking.STATUS_CHECKED_OUT, Booking.STATUS_CANCELLED, Booking.STATUS_NO_SHOW])
            ).order_by(Booking.check_out_date.desc()).limit(5)
        ).scalars().all()
        
        # Format booking data for the dashboard
        upcoming_bookings_data = [{
            "id": booking.id,
            "room_number": booking.room.number,
            "room_type": booking.room.room_type.name,
            "check_in_date": booking.check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": booking.check_out_date.strftime("%Y-%m-%d"),
            "nights": booking.nights,
            "status": booking.status
        } for booking in upcoming_bookings]
        
        past_bookings_data = [{
            "id": booking.id,
            "room_number": booking.room.number,
            "room_type": booking.room.room_type.name,
            "check_in_date": booking.check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": booking.check_out_date.strftime("%Y-%m-%d"),
            "nights": booking.nights,
            "status": booking.status
        } for booking in past_bookings]
        
        active_booking_data = None
        if active_booking:
            active_booking_data = {
                "id": active_booking.id,
                "room_number": active_booking.room.number,
                "room_type": active_booking.room.room_type.name,
                "check_in_date": active_booking.check_in_date.strftime("%Y-%m-%d"),
                "check_out_date": active_booking.check_out_date.strftime("%Y-%m-%d"),
                "nights": active_booking.nights,
                "status": active_booking.status
            }
        
        # Get customer's profile completeness
        profile_completeness = "Complete" if customer.profile_complete else "Incomplete"
        
        # Get unread notification count
        notification_service = NotificationService(self.db_session) # Assuming NotificationService is available
        unread_notification_count = notification_service.get_unread_notification_count(user_id)

        # Existing logic to build metrics dict
        metrics = {
            "customer_name": customer.name,
            "profile_status": profile_completeness,
            "active_booking": active_booking_data,
            "upcoming_bookings": upcoming_bookings_data,
            "past_bookings": past_bookings_data,
            "booking_count": len(upcoming_bookings_data) + len(past_bookings_data) + (1 if active_booking_data else 0),
            "loyalty_points": customer.loyalty_points or 0,
            "loyalty_tier": customer.loyalty_tier or "None",
            "unread_notification_count": unread_notification_count
        }
        # Guarantee all required keys are present
        required_keys = [
            "customer_name", "profile_status", "active_booking", "upcoming_bookings",
            "past_bookings", "booking_count", "loyalty_points", "loyalty_tier", "unread_notification_count"
        ]
        for key in required_keys:
            if key not in metrics:
                if key in ["upcoming_bookings", "past_bookings"]:
                    metrics[key] = []
                elif key == "active_booking":
                    metrics[key] = None
                elif key in ["booking_count", "loyalty_points", "unread_notification_count"]:
                    metrics[key] = 0
                elif key == "profile_status":
                    metrics[key] = "Unknown"
                elif key == "loyalty_tier":
                    metrics[key] = "N/A"
                else:
                    metrics[key] = "N/A"
        return metrics
    
    def get_receptionist_metrics(self):
        """
        Get dashboard metrics for receptionists.
        
        Returns:
            Dictionary of dashboard metrics
        """
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Today's check-ins
        todays_checkins = self.db_session.execute(
            select(func.count(Booking.id)).filter(
                Booking.check_in_date == today,
                Booking.status == Booking.STATUS_RESERVED
            )
        ).scalar_one()
        
        # Today's check-outs
        todays_checkouts = self.db_session.execute(
            select(func.count(Booking.id)).filter(
                Booking.check_out_date == today,
                Booking.status == Booking.STATUS_CHECKED_IN
            )
        ).scalar_one()
        
        # Tomorrow's check-ins
        tomorrows_checkins = self.db_session.execute(
            select(func.count(Booking.id)).filter(
                Booking.check_in_date == tomorrow,
                Booking.status == Booking.STATUS_RESERVED
            )
        ).scalar_one()
        
        # Currently occupied rooms
        occupied_rooms = self.db_session.execute(
            select(func.count(Room.id)).filter(Room.status == Room.STATUS_OCCUPIED)
        ).scalar_one()
        
        # Available rooms
        available_rooms = self.db_session.execute(
            select(func.count(Room.id)).filter(Room.status == Room.STATUS_AVAILABLE)
        ).scalar_one()
        
        # Rooms needing cleaning
        cleaning_rooms = self.db_session.execute(
            select(func.count(Room.id)).filter(Room.status == Room.STATUS_CLEANING)
        ).scalar_one()
        
        # Recent bookings (last 10)
        recent_bookings = self.db_session.execute(
            select(Booking).order_by(Booking.created_at.desc()).limit(10)
        ).scalars().all()
        
        recent_bookings_data = [{
            "id": booking.id,
            "customer_name": booking.customer.name,
            "room_number": booking.room.number,
            "check_in_date": booking.check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": booking.check_out_date.strftime("%Y-%m-%d"),
            "status": booking.status
        } for booking in recent_bookings]
        
        # Get room status breakdown for chart
        room_status_counts = self.db_session.execute(
            select(Room.status, func.count(Room.id)).group_by(Room.status)
        ).all()
        
        room_status_data = {status: count for status, count in room_status_counts}
        
        # Get today's check-ins for table display with enhanced details
        todays_checkin_bookings = self.db_session.execute(
            select(Booking).filter(
                Booking.check_in_date == today,
                Booking.status == Booking.STATUS_RESERVED
            ).order_by(Booking.check_in_date)
        ).scalars().all()
        
        todays_checkin_data = [{
            "id": booking.id,
            "customer_name": booking.customer.name,
            "customer_phone": booking.customer.phone or "Not provided",
            "customer_id": booking.customer_id,
            "room_number": booking.room.number,
            "room_id": booking.room_id,
            "room_type": booking.room.room_type.name,
            "nights": booking.nights,
            "check_in_date": booking.check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": booking.check_out_date.strftime("%Y-%m-%d"),
            "special_requests": booking.special_requests,
            "total_price": booking.total_price,
            "payment_status": booking.payment_status,
            "balance_due": booking.balance_due,
            "is_vip": hasattr(booking.customer, "loyalty_tier") and 
                     booking.customer.loyalty_tier in [booking.customer.TIER_GOLD, booking.customer.TIER_PLATINUM],
            "num_guests": booking.num_guests,
            "notes": booking.notes
        } for booking in todays_checkin_bookings]
        
        # Get today's check-outs for table display with enhanced details
        todays_checkout_bookings = self.db_session.execute(
            select(Booking).filter(
                Booking.check_out_date == today,
                Booking.status == Booking.STATUS_CHECKED_IN
            ).order_by(Booking.check_out_date)
        ).scalars().all()
        
        todays_checkout_data = [{
            "id": booking.id,
            "customer_name": booking.customer.name,
            "customer_phone": booking.customer.phone or "Not provided",
            "customer_id": booking.customer_id,
            "room_number": booking.room.number,
            "room_id": booking.room_id,
            "room_type": booking.room.room_type.name,
            "check_in_date": booking.check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": booking.check_out_date.strftime("%Y-%m-%d"),
            "nights": booking.nights,
            "total_price": booking.total_price,
            "payment_status": booking.payment_status,
            "balance_due": booking.balance_due,
            "late_hours": booking.late_hours,
            "notes": booking.notes
        } for booking in todays_checkout_bookings]
        
        # Get in-house guests (currently checked in)
        in_house_bookings = self.db_session.execute(
            select(Booking).filter(
                Booking.status == Booking.STATUS_CHECKED_IN,
                Booking.check_out_date > today
            ).order_by(Booking.check_out_date)
        ).scalars().all()
        
        in_house_data = [{
            "id": booking.id,
            "customer_name": booking.customer.name,
            "customer_id": booking.customer_id,
            "room_number": booking.room.number,
            "room_id": booking.room_id,
            "room_type": booking.room.room_type.name,
            "check_in_date": booking.check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": booking.check_out_date.strftime("%Y-%m-%d"),
            "nights_remaining": (booking.check_out_date - today).days,
            "total_price": booking.total_price,
            "payment_status": booking.payment_status,
            "is_vip": hasattr(booking.customer, "loyalty_tier") and 
                     booking.customer.loyalty_tier in [booking.customer.TIER_GOLD, booking.customer.TIER_PLATINUM]
        } for booking in in_house_bookings]
        
        # Detailed room status information by room type
        room_type_status = {}
        room_types = self.db_session.execute(select(RoomType)).scalars().all()
        
        for room_type in room_types:
            # Count rooms of this type by status
            room_counts = self.db_session.execute(
                select(Room.status, func.count(Room.id))
                .filter(Room.room_type_id == room_type.id)
                .group_by(Room.status)
            ).all()
            
            status_counts = {status: count for status, count in room_counts}
            
            # Calculate total rooms of this type
            total_type_rooms = sum(status_counts.values())
            
            # Get available count
            available_count = status_counts.get(Room.STATUS_AVAILABLE, 0)
            
            room_type_status[room_type.id] = {
                "id": room_type.id,
                "name": room_type.name,
                "total_rooms": total_type_rooms,
                "available_rooms": available_count,
                "occupied_rooms": status_counts.get(Room.STATUS_OCCUPIED, 0),
                "cleaning_rooms": status_counts.get(Room.STATUS_CLEANING, 0),
                "maintenance_rooms": status_counts.get(Room.STATUS_MAINTENANCE, 0),
                "booked_rooms": status_counts.get(Room.STATUS_BOOKED, 0),
                "occupancy_rate": round((status_counts.get(Room.STATUS_OCCUPIED, 0) / total_type_rooms) * 100, 1) if total_type_rooms > 0 else 0
            }
        
        # Total rooms count
        total_rooms = self.db_session.execute(select(func.count(Room.id))).scalar_one()
        
        # Calculate overall occupancy rate
        occupancy_rate = round((occupied_rooms / total_rooms) * 100, 1) if total_rooms > 0 else 0
        
        return {
            "todays_checkins": todays_checkins,
            "todays_checkouts": todays_checkouts,
            "tomorrows_checkins": tomorrows_checkins,
            "occupied_rooms": occupied_rooms,
            "available_rooms": available_rooms,
            "cleaning_rooms": cleaning_rooms,
            "maintenance_rooms": self.db_session.execute(
                select(func.count(Room.id)).filter(Room.status == Room.STATUS_MAINTENANCE)
            ).scalar_one() or 0,
            "total_rooms": total_rooms,
            "occupancy_rate": occupancy_rate,
            "current_time": datetime.now(),
            "recent_bookings": recent_bookings_data,
            "room_status": room_status_data,
            "todays_checkin_list": todays_checkin_data,
            "todays_checkout_list": todays_checkout_data,
            "in_house_guests": in_house_data,
            "room_type_status": room_type_status
        }
    
    def get_manager_metrics(self):
        """
        Get dashboard metrics for managers.
        
        Returns:
            Dictionary of dashboard metrics
        """
        today = datetime.now().date()
        start_of_month = datetime(today.year, today.month, 1).date()
        # Define period for ADR/RevPAR - e.g., last 30 days
        period_end_date = today
        period_start_date = today - timedelta(days=29) # for a 30 day period

        analytics_service = AnalyticsService(self.db_session) # Instantiate AnalyticsService
        
        # Room occupancy rate - currently occupied rooms / total rooms
        total_rooms = self.db_session.execute(select(func.count(Room.id))).scalar_one()
        occupied_rooms = self.db_session.execute(
            select(func.count(Room.id)).filter(Room.status == Room.STATUS_OCCUPIED)
        ).scalar_one()
        occupancy_rate = round((occupied_rooms / total_rooms * 100), 2) if total_rooms > 0 else 0
        
        # Get customer count
        customer_count = self.db_session.execute(
            select(func.count(Customer.id))
        ).scalar_one()
        
        # Get room status breakdown
        room_status_counts = self.db_session.execute(
            select(Room.status, func.count(Room.id)).group_by(Room.status)
        ).all()
        
        room_status_data = {}
        for status, count in room_status_counts:
            room_status_data[status.capitalize()] = count
            
        # Get monthly bookings
        monthly_bookings = self.db_session.execute(
            select(func.count(Booking.id)).filter(
                Booking.check_in_date >= start_of_month,
                Booking.check_in_date <= today
            )
        ).scalar_one()
        
        # Get staff counts by role
        staff_role_counts = self.db_session.execute(
            select(User.role, func.count(User.id))
            .filter(User.role != 'customer')
            .group_by(User.role)
        ).all()
        
        staff_counts = {role: count for role, count in staff_role_counts}
        
        # Get historical occupancy
        occupancy_history = self.get_historical_occupancy(days=14)
        
        # Get top-performing staff
        top_performers = self._get_top_staff_performers()
        
        # Add actionable alerts
        alerts = self._get_actionable_alerts()
        
        # Add booking forecast for next 7 days
        booking_forecast = self._get_booking_forecast(7)
        
        # Add maintenance and housekeeping status
        maintenance_status = self._get_maintenance_status()
        housekeeping_status = self._get_housekeeping_status()

        # Calculate ADR and RevPAR for the defined period
        adr_value = analytics_service.calculate_adr(period_start_date, period_end_date)
        revpar_value = analytics_service.calculate_revpar(period_start_date, period_end_date)
        
        # Get real revenue data
        revenue_data = self._get_revenue_analytics()
        
        # Get recent activity timeline
        recent_activities = self._get_recent_activities()
        
        # Calculate guest satisfaction score from recent bookings
        guest_satisfaction = self._calculate_guest_satisfaction()
        
        return {
            "occupancy_rate": occupancy_rate,
            "customer_count": customer_count,
            "room_status": room_status_data,
            "total_rooms": total_rooms,
            "monthly_bookings": monthly_bookings,
            "staff_counts": staff_counts,
            "historical_occupancy": occupancy_history,
            "top_performers": top_performers,
            "alerts": alerts,
            "booking_forecast": booking_forecast,
            "maintenance_status": maintenance_status,
            "housekeeping_status": housekeeping_status,
            "adr": adr_value if adr_value is not None else 0.0,
            "revpar": revpar_value if revpar_value is not None else 0.0,
            "revenue_data": revenue_data,
            "recent_activities": recent_activities,
            "guest_satisfaction": guest_satisfaction
        }
    
    def _get_top_staff_performers(self, limit=5):
        """Get top-performing staff based on real task completion, booking activities, and performance metrics."""
        from sqlalchemy import func, case, distinct
        from app.models.booking_log import BookingLog
        from app.models.room_status_log import RoomStatusLog
        from app.models.payment import Payment
        import datetime
        
        # Get the last 30 days for performance calculation
        start_date = datetime.datetime.now() - datetime.timedelta(days=30)
        
        # Query staff users with their activity counts
        staff_performance = self.db_session.execute(
            select(
                User.id,
                User.username,
                User.role,
                # Count booking-related activities
                func.count(distinct(BookingLog.id)).label('booking_activities'),
                # Count room status changes they made
                func.count(distinct(RoomStatusLog.id)).label('room_activities'),
                # Count payments they processed
                func.count(distinct(Payment.id)).label('payment_activities'),
                # Calculate total activities
                (func.count(distinct(BookingLog.id)) + 
                 func.count(distinct(RoomStatusLog.id)) + 
                 func.count(distinct(Payment.id))).label('total_activities')
            )
            .outerjoin(BookingLog, and_(
                BookingLog.user_id == User.id,
                BookingLog.action_time >= start_date
            ))
            .outerjoin(RoomStatusLog, and_(
                RoomStatusLog.changed_by == User.id,
                RoomStatusLog.change_time >= start_date
            ))
            .outerjoin(Payment, and_(
                Payment.processed_by == User.id,
                Payment.payment_date >= start_date
            ))
            .filter(User.role.in_(['receptionist', 'housekeeping', 'manager']))
            .group_by(User.id, User.username, User.role)
            .order_by(text('total_activities DESC'))
            .limit(limit)
        ).all()
        
        performers = []
        for row in staff_performance:
            user_id, username, role, booking_activities, room_activities, payment_activities, total_activities = row
            
            # Calculate efficiency score based on activities (normalize to 100 scale)
            max_possible_activities = 50  # Reasonable max for 30 days
            efficiency_score = min(95, (total_activities / max_possible_activities) * 100) if total_activities > 0 else 0
            efficiency_score = max(50, efficiency_score)  # Minimum score of 50 for active staff
            
            # Calculate customer rating based on successful completions
            # This is a simplified calculation - in real system would use actual customer feedback
            successful_operations = booking_activities + room_activities + payment_activities
            if successful_operations > 0:
                # Higher activity = better assumed performance
                customer_rating = min(5.0, 3.5 + (successful_operations / 20))
            else:
                customer_rating = 3.5  # Default rating
            
            performers.append({
                'id': user_id,
                'username': username,
                'role': role,
                'tasks_completed': total_activities,
                'efficiency_score': round(efficiency_score, 1),
                'customer_rating': round(customer_rating, 1),
                'booking_activities': booking_activities,
                'room_activities': room_activities,
                'payment_activities': payment_activities
            })
        
        return performers
        
    def _get_actionable_alerts(self):
        """Get actionable alerts for the manager's attention."""
        today = datetime.now().date()
        alerts = []
        
        # Check for rooms needing maintenance
        maintenance_count = self.db_session.execute(
            select(func.count())
            .select_from(Room)
            .filter(Room.status == 'maintenance')
        ).scalar_one()
        
        if maintenance_count > 0:
            alerts.append({
                'type': 'maintenance',
                'level': 'warning',
                'message': f'{maintenance_count} rooms currently under maintenance',
                'action_url': '/manager/maintenance'
            })
            
        # Check for high occupancy days (over 90%)
        # In a real system, this would look at bookings in the next few weeks
        # This is simplified for demonstration
        from sqlalchemy import cast, Date
        from datetime import timedelta
        
        next_week = today + timedelta(days=7)
        
        # Get daily occupancy for the next 7 days
        daily_bookings = self.db_session.execute(
            select(
                cast(Booking.check_in_date, Date).label('date'),
                func.count().label('count')
            )
            .filter(
                Booking.check_in_date.between(today, next_week),
                Booking.status.in_(['reserved', 'confirmed'])
            )
            .group_by('date')
        ).all()
        
        # Check for days with high occupancy
        total_rooms = self.db_session.execute(select(func.count(Room.id))).scalar_one()
        threshold = 0.9  # 90% occupancy
        
        for date, count in daily_bookings:
            occupancy_rate = count / total_rooms
            if occupancy_rate >= threshold:
                date_str = date.strftime('%Y-%m-%d')
                alerts.append({
                    'type': 'occupancy',
                    'level': 'info',
                    'message': f'High occupancy ({int(occupancy_rate * 100)}%) on {date_str}',
                    'action_url': f'/manager/reports?date={date_str}'
                })
                
        return alerts
        
    def _get_booking_forecast(self, days=7):
        """Get booking forecast for the upcoming days."""
        today = datetime.now().date()
        forecast = {}
        
        for i in range(days):
            date = today + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            # Count bookings for this day
            bookings_count = self.db_session.execute(
                select(func.count())
                .select_from(Booking)
                .filter(
                    Booking.check_in_date == date,
                    Booking.status.in_(['reserved', 'confirmed'])
                )
            ).scalar_one()
            
            forecast[date_str] = bookings_count
            
        return forecast
        
    def _get_maintenance_status(self):
        """Get maintenance request status summary."""
        # Count maintenance requests by status
        maintenance_status = {}
        
        try:
            from app.models.maintenance_request import MaintenanceRequest
            
            status_counts = self.db_session.execute(
                select(MaintenanceRequest.status, func.count())
                .group_by(MaintenanceRequest.status)
            ).all()
            
            for status, count in status_counts:
                maintenance_status[status] = count
                
        except Exception:
            # If MaintenanceRequest model is not available
            maintenance_status = {
                'pending': 0,
                'in_progress': 0,
                'completed': 0
            }
            
        return maintenance_status
        
    def _get_housekeeping_status(self):
        """Get housekeeping task status summary."""
        # Count housekeeping tasks by status
        housekeeping_status = {}
        
        try:
            from app.models.housekeeping_task import HousekeepingTask
            
            status_counts = self.db_session.execute(
                select(HousekeepingTask.status, func.count())
                .group_by(HousekeepingTask.status)
            ).all()
            
            for status, count in status_counts:
                housekeeping_status[status] = count
                
        except Exception:
            # If HousekeepingTask model is not available
            housekeeping_status = {
                'pending': 0,
                'in_progress': 0,
                'completed': 0
            }
            
        return housekeeping_status
    
    def get_housekeeping_metrics(self):
        """
        Get dashboard metrics for housekeeping staff.
        
        Returns:
            Dictionary of dashboard metrics
        """
        today = datetime.now().date()
        
        # Rooms that need cleaning
        rooms_to_clean = self.db_session.execute(
            select(Room).filter(
                Room.status == Room.STATUS_CLEANING
            ).order_by(Room.number)
        ).scalars().all()
        
        rooms_to_clean_data = [{
            "id": room.id,
            "number": room.number,
            "type": room.room_type.name,
            "last_cleaned": room.last_cleaned.strftime("%Y-%m-%d %H:%M") if room.last_cleaned else "Never"
        } for room in rooms_to_clean]
        
        # Rooms with checkout today (will need cleaning soon)
        checkout_rooms = self.db_session.execute(
            select(Room).join(Booking, Booking.room_id == Room.id).filter(
                Booking.check_out_date == today,
                Booking.status == Booking.STATUS_CHECKED_IN
            )
        ).scalars().all()
        
        checkout_rooms_data = [{
            "id": room.id,
            "number": room.number,
            "type": room.room_type.name
        } for room in checkout_rooms]
        
        # Recently cleaned rooms (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recently_cleaned_query = select(RoomStatusLog).join(Room, Room.id == RoomStatusLog.room_id).filter(
            RoomStatusLog.new_status == Room.STATUS_AVAILABLE,
            RoomStatusLog.change_time >= yesterday
        ).order_by(RoomStatusLog.change_time.desc())
        recently_cleaned_logs = self.db_session.execute(recently_cleaned_query).scalars().all()
        
        # Cleaning schedule (upcoming check-outs today)
        upcoming_checkouts_query = select(Booking).join(Room, Room.id == Booking.room_id).filter(
            Booking.check_out_date == today,
            Booking.status == Booking.STATUS_CHECKED_IN
        ).order_by(Room.number)
        
        upcoming_checkouts = self.db_session.execute(upcoming_checkouts_query).scalars().all()
        
        # Cleaning statistics
        cleaning_count_today = self.db_session.execute(
            select(func.count(Room.id)).filter(
                Room.last_cleaned >= datetime.combine(today, datetime.min.time())
            )
        ).scalar_one()
        
        # Get cleaning history by day for the past week
        cleaning_history = self.get_cleaning_history(days=7)
        
        return {
            "rooms_to_clean": rooms_to_clean_data,
            "checkout_rooms": checkout_rooms_data,
            "recently_cleaned": recently_cleaned_logs,
            "cleaning_count_today": cleaning_count_today,
            "total_to_clean": len(rooms_to_clean_data),
            "total_checkout_today": len(checkout_rooms_data),
            "cleaning_history": cleaning_history
        }
    
    def get_admin_metrics(self):
        """
        Get dashboard metrics for admin users.
        
        Returns:
            Dictionary of dashboard metrics
        """
        # User counts by role (exclude 'pending' and 'Rejected')
        user_counts = self.db_session.execute(
            select(User.role, func.count(User.id)).where(~User.role.in_(["pending", "Rejected"])).group_by(User.role)
        ).all()
        
        user_data = {}
        for row in user_counts:
            if len(row) == 2:  # Make sure we have exactly role and count
                role, count = row
                user_data[role] = count
        
        # Total users (exclude 'pending' and 'Rejected')
        total_users = sum(user_data.values())
        
        # Recent user registrations
        recent_users = self.db_session.execute(
            select(User).order_by(User.created_at.desc()).limit(10)
        ).scalars().all()
        
        recent_users_data = [{
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M")
        } for user in recent_users]
        
        # Users with pending role requests
        pending_role_requests = self.db_session.execute(
            select(User).filter(User.role_requested.isnot(None))
        ).scalars().all()
        
        pending_requests_data = [{
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "current_role": user.role,
            "requested_role": user.role_requested
        } for user in pending_role_requests]
        
        # Total rooms by type
        room_type_counts = self.db_session.execute(
            select(RoomType.name, func.count(Room.id)).join(Room, Room.room_type_id == RoomType.id).group_by(RoomType.name)
        ).all()
        
        room_type_data = {}
        for row in room_type_counts:
            if len(row) == 2:  # Make sure we have exactly name and count
                name, count = row
                room_type_data[name] = count
        
        # System statistics
        total_bookings = self.db_session.execute(select(func.count(Booking.id))).scalar_one()
        active_bookings = self.db_session.execute(
            select(func.count(Booking.id)).filter(
                Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
            )
        ).scalar_one()
        
        # Get user registration history
        user_registration_history = self.get_user_registration_history(days=30)
        
        # Get real revenue analytics for admin dashboard
        revenue_analytics = self._get_admin_revenue_analytics()
        
        # Get system health metrics
        system_health = self._get_system_health_metrics()
        
        # Get performance statistics
        performance_stats = self._get_admin_performance_stats()
        
        # Get recent booking analytics
        booking_analytics = self._get_admin_booking_analytics()
        
        return {
            "user_counts": user_data,
            "total_users": total_users,
            "recent_users": recent_users_data,
            "pending_role_requests": pending_requests_data,
            "room_type_counts": room_type_data,
            "total_bookings": total_bookings,
            "active_bookings": active_bookings,
            "user_registration_history": user_registration_history,
            "revenue_analytics": revenue_analytics,
            "system_health": system_health,
            "performance_stats": performance_stats,
            "booking_analytics": booking_analytics
        }
    
    def _get_admin_revenue_analytics(self):
        """Get comprehensive revenue analytics for admin dashboard."""
        today = datetime.now().date()
        start_of_month = datetime(today.year, today.month, 1).date()
        start_of_year = datetime(today.year, 1, 1).date()
        
        # Monthly revenue
        monthly_revenue = self.db_session.execute(
            select(func.sum(Booking.total_price))
            .filter(
                Booking.check_in_date >= start_of_month,
                Booking.check_in_date <= today,
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
            )
        ).scalar_one() or 0
        
        # Yearly revenue
        yearly_revenue = self.db_session.execute(
            select(func.sum(Booking.total_price))
            .filter(
                Booking.check_in_date >= start_of_year,
                Booking.check_in_date <= today,
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
            )
        ).scalar_one() or 0
        
        # Revenue by room type for current month
        revenue_by_room_type = self.db_session.execute(
            select(RoomType.name, func.sum(Booking.total_price))
            .join(Room, Booking.room_id == Room.id)
            .join(RoomType, Room.room_type_id == RoomType.id)
            .filter(
                Booking.check_in_date >= start_of_month,
                Booking.check_in_date <= today,
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
            )
            .group_by(RoomType.name)
        ).all()
        
        # Daily revenue trend for last 7 days
        daily_revenue_trend = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            day_revenue = self.db_session.execute(
                select(func.sum(Booking.total_price))
                .filter(
                    Booking.check_in_date == date,
                    Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
                )
            ).scalar_one() or 0
            daily_revenue_trend.append({
                'date': date.strftime('%Y-%m-%d'),
                'revenue': float(day_revenue)
            })
        
        return {
            'monthly_revenue': float(monthly_revenue),
            'yearly_revenue': float(yearly_revenue),
            'revenue_by_room_type': {name: float(revenue) for name, revenue in revenue_by_room_type},
            'daily_revenue_trend': daily_revenue_trend
        }
    
    def _get_system_health_metrics(self):
        """Get system health and performance metrics."""
        # Room utilization rate
        total_rooms = self.db_session.execute(select(func.count(Room.id))).scalar_one()
        occupied_rooms = self.db_session.execute(
            select(func.count(Room.id)).filter(Room.status == Room.STATUS_OCCUPIED)
        ).scalar_one()
        
        room_utilization = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        
        # Staff utilization (active vs total staff)
        total_staff = self.db_session.execute(
            select(func.count(User.id)).filter(User.role.in_(['receptionist', 'housekeeping', 'manager']))
        ).scalar_one()
        
        active_staff = self.db_session.execute(
            select(func.count(User.id)).filter(
                User.role.in_(['receptionist', 'housekeeping', 'manager']),
                User.is_active == True
            )
        ).scalar_one()
        
        staff_utilization = (active_staff / total_staff * 100) if total_staff > 0 else 0
        
        # Payment processing health (successful vs failed)
        successful_payments = self.db_session.execute(
            select(func.count(Payment.id)).filter(Payment.status == 'completed')
        ).scalar_one() or 0
        
        total_payments = self.db_session.execute(select(func.count(Payment.id))).scalar_one() or 1
        payment_success_rate = (successful_payments / total_payments * 100)
        
        # Booking completion rate
        completed_bookings = self.db_session.execute(
            select(func.count(Booking.id)).filter(Booking.status == Booking.STATUS_CHECKED_OUT)
        ).scalar_one() or 0
        
        total_resolved_bookings = self.db_session.execute(
            select(func.count(Booking.id)).filter(
                Booking.status.in_([Booking.STATUS_CHECKED_OUT, Booking.STATUS_CANCELLED])
            )
        ).scalar_one() or 1
        
        booking_completion_rate = (completed_bookings / total_resolved_bookings * 100)
        
        return {
            'room_utilization': round(room_utilization, 1),
            'staff_utilization': round(staff_utilization, 1),
            'payment_success_rate': round(payment_success_rate, 1),
            'booking_completion_rate': round(booking_completion_rate, 1)
        }
    
    def _get_admin_performance_stats(self):
        """Get performance statistics for admin dashboard."""
        today = datetime.now().date()
        last_30_days = today - timedelta(days=30)
        
        # Average stay duration
        avg_stay_duration = self.db_session.execute(
            select(func.avg(
                func.julianday(Booking.check_out_date) - func.julianday(Booking.check_in_date)
            ))
            .filter(
                Booking.check_in_date >= last_30_days,
                Booking.status == Booking.STATUS_CHECKED_OUT
            )
        ).scalar_one() or 0
        
        # Average booking value
        avg_booking_value = self.db_session.execute(
            select(func.avg(Booking.total_price))
            .filter(
                Booking.check_in_date >= last_30_days,
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
            )
        ).scalar_one() or 0
        
        # Repeat customer rate
        total_customers = self.db_session.execute(
            select(func.count(distinct(Booking.customer_id)))
            .filter(
                Booking.check_in_date >= last_30_days,
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
            )
        ).scalar_one() or 1
        
        # Count customers with more than one booking
        repeat_customers_subquery = self.db_session.execute(
            select(Booking.customer_id)
            .filter(
                Booking.check_in_date >= last_30_days,
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
            )
            .group_by(Booking.customer_id)
            .having(func.count(Booking.id) > 1)
        ).all()
        
        repeat_customers = len(repeat_customers_subquery)
        
        repeat_customer_rate = (repeat_customers / total_customers * 100)
        
        # Cancellation rate
        total_bookings = self.db_session.execute(
            select(func.count(Booking.id))
            .filter(Booking.check_in_date >= last_30_days)
        ).scalar_one() or 1
        
        cancelled_bookings = self.db_session.execute(
            select(func.count(Booking.id))
            .filter(
                Booking.check_in_date >= last_30_days,
                Booking.status.in_([Booking.STATUS_CANCELLED, Booking.STATUS_NO_SHOW])
            )
        ).scalar_one() or 0
        
        cancellation_rate = (cancelled_bookings / total_bookings * 100)
        
        return {
            'avg_stay_duration': round(avg_stay_duration, 1),
            'avg_booking_value': round(float(avg_booking_value), 2),
            'repeat_customer_rate': round(repeat_customer_rate, 1),
            'cancellation_rate': round(cancellation_rate, 1)
        }
    
    def _get_admin_booking_analytics(self):
        """Get booking analytics and forecasts for admin dashboard."""
        today = datetime.now().date()
        
        # Upcoming arrivals (next 7 days)
        upcoming_arrivals = []
        for i in range(7):
            date = today + timedelta(days=i)
            arrivals = self.db_session.execute(
                select(func.count(Booking.id))
                .filter(
                    Booking.check_in_date == date,
                    Booking.status == Booking.STATUS_RESERVED
                )
            ).scalar_one()
            upcoming_arrivals.append({
                'date': date.strftime('%Y-%m-%d'),
                'arrivals': arrivals
            })
        
        # Upcoming departures (next 7 days)
        upcoming_departures = []
        for i in range(7):
            date = today + timedelta(days=i)
            departures = self.db_session.execute(
                select(func.count(Booking.id))
                .filter(
                    Booking.check_out_date == date,
                    Booking.status == Booking.STATUS_CHECKED_IN
                )
            ).scalar_one()
            upcoming_departures.append({
                'date': date.strftime('%Y-%m-%d'),
                'departures': departures
            })
        
        # Occupancy forecast (next 14 days)
        total_rooms = self.db_session.execute(select(func.count(Room.id))).scalar_one()
        occupancy_forecast = []
        for i in range(14):
            date = today + timedelta(days=i)
            occupied = self.db_session.execute(
                select(func.count(distinct(Booking.room_id)))
                .filter(
                    Booking.check_in_date <= date,
                    Booking.check_out_date > date,
                    Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN])
                )
            ).scalar_one()
            
            occupancy_rate = (occupied / total_rooms * 100) if total_rooms > 0 else 0
            occupancy_forecast.append({
                'date': date.strftime('%Y-%m-%d'),
                'occupancy_rate': round(occupancy_rate, 1)
            })
        
        return {
            'upcoming_arrivals': upcoming_arrivals,
            'upcoming_departures': upcoming_departures,
            'occupancy_forecast': occupancy_forecast
        }
    
    def get_historical_occupancy(self, days=14):
        """
        Get historical occupancy data for the past N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with dates as keys and occupancy rates as values
        """
        today = datetime.now().date()
        
        # Initialize result dictionary with all zeros
        result = {}
        for i in range(days, 0, -1):
            date = today - timedelta(days=i)
            result[date.strftime("%Y-%m-%d")] = 0
        
        # Total number of rooms
        total_rooms = self.db_session.execute(select(func.count(Room.id))).scalar_one()
        if total_rooms == 0:
            return result
        
        # For each day, calculate occupancy
        for i in range(days, 0, -1):
            date = today - timedelta(days=i)
            # Count bookings active on that day
            occupied_count = self.db_session.execute(
                select(func.count(func.distinct(Booking.room_id))).filter(
                    Booking.check_in_date <= date,
                    Booking.check_out_date > date,
                    Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_RESERVED])
                )
            ).scalar_one()
            
            # Calculate occupancy rate
            occupancy_rate = round((occupied_count / total_rooms * 100), 2)
            result[date.strftime("%Y-%m-%d")] = occupancy_rate
        
        return result
    
    def get_cleaning_history(self, days=7):
        """
        Get room cleaning history for the past N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with dates as keys and cleaning counts as values
        """
        today = datetime.now().date()
        
        # Initialize result dictionary with all zeros
        result = {}
        for i in range(days, 0, -1):
            date = today - timedelta(days=i)
            result[date.strftime("%Y-%m-%d")] = 0
        
        # Add today
        result[today.strftime("%Y-%m-%d")] = 0
        
        # For each day in range, count rooms cleaned
        for i in range(days, -1, -1):
            date = today - timedelta(days=i)
            
            # Count room status changes to "Available" on that day
            day_start = datetime.combine(date, datetime.min.time())
            day_end = datetime.combine(date, datetime.max.time())
            
            cleaned_count = self.db_session.execute(
                select(func.count(RoomStatusLog.id)).filter(
                    RoomStatusLog.new_status == Room.STATUS_AVAILABLE,
                    RoomStatusLog.old_status == Room.STATUS_CLEANING,
                    RoomStatusLog.change_time.between(day_start, day_end)
                )
            ).scalar_one()
            
            result[date.strftime("%Y-%m-%d")] = cleaned_count
        
        return result
    
    def get_user_registration_history(self, days=30):
        """
        Get user registration history for the past N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with dates as keys and registration counts as values
        """
        today = datetime.now().date()
        
        # Initialize result dictionary with all zeros
        result = {}
        for i in range(days, 0, -1):
            date = today - timedelta(days=i)
            result[date.strftime("%Y-%m-%d")] = 0
        
        # Add today
        result[today.strftime("%Y-%m-%d")] = 0
        
        # For each day in range, count new user registrations
        for i in range(days, -1, -1):
            date = today - timedelta(days=i)
            
            # Count user registrations on that day
            day_start = datetime.combine(date, datetime.min.time())
            day_end = datetime.combine(date, datetime.max.time())
            
            registration_count = self.db_session.execute(
                select(func.count(User.id)).filter(
                    User.created_at.between(day_start, day_end)
                )
            ).scalar_one()
            
            result[date.strftime("%Y-%m-%d")] = registration_count
        
        return result
    
    def _get_revenue_analytics(self):
        """Get real revenue analytics data for the manager dashboard."""
        today = datetime.now().date()
        start_of_month = datetime(today.year, today.month, 1).date()
        
        # Monthly revenue calculation
        monthly_revenue = self.db_session.execute(
            select(func.sum(Booking.total_price))
            .filter(
                Booking.check_in_date >= start_of_month,
                Booking.check_in_date <= today,
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
            )
        ).scalar_one() or 0
        
        # Previous month for comparison
        prev_month_start = (start_of_month.replace(day=1) - timedelta(days=1)).replace(day=1)
        prev_month_end = start_of_month - timedelta(days=1)
        
        prev_monthly_revenue = self.db_session.execute(
            select(func.sum(Booking.total_price))
            .filter(
                Booking.check_in_date >= prev_month_start,
                Booking.check_in_date <= prev_month_end,
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
            )
        ).scalar_one() or 0
        
        # Calculate growth percentage
        if prev_monthly_revenue > 0:
            growth_percentage = ((monthly_revenue - prev_monthly_revenue) / prev_monthly_revenue) * 100
        else:
            growth_percentage = 0 if monthly_revenue == 0 else 100
            
        # Daily average this month
        days_in_month = (today - start_of_month).days + 1
        daily_average = monthly_revenue / days_in_month if days_in_month > 0 else 0
        
        # Revenue by day for the last 7 days
        daily_revenue = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            day_revenue = self.db_session.execute(
                select(func.sum(Booking.total_price))
                .filter(
                    Booking.check_in_date == date,
                    Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_CHECKED_OUT, Booking.STATUS_RESERVED])
                )
            ).scalar_one() or 0
            daily_revenue.append({
                'date': date.strftime('%Y-%m-%d'),
                'revenue': float(day_revenue)
            })
        
        return {
            'total_revenue': float(monthly_revenue),
            'growth_percentage': round(growth_percentage, 1),
            'daily_average': round(float(daily_average), 2),
            'daily_revenue': daily_revenue
        }
    
    def _get_recent_activities(self, limit=10):
        """Get recent activities across the hotel for the activity timeline."""
        activities = []
        
        # Recent booking activities
        recent_bookings = self.db_session.execute(
            select(BookingLog, Booking, User)
            .join(Booking, BookingLog.booking_id == Booking.id)
            .outerjoin(User, BookingLog.user_id == User.id)
            .order_by(BookingLog.action_time.desc())
            .limit(limit)
        ).all()
        
        for log, booking, user in recent_bookings:
            activities.append({
                'type': 'booking',
                'action': log.action,
                'description': f"Booking {booking.id} {log.action.replace('_', ' ')}",
                'time': log.action_time,
                'user': user.username if user else 'System',
                'details': f"Room {booking.room.number}" if booking.room else ""
            })
        
        # Recent room status changes
        recent_room_changes = self.db_session.execute(
            select(RoomStatusLog, Room, User)
            .join(Room, RoomStatusLog.room_id == Room.id)
            .outerjoin(User, RoomStatusLog.changed_by == User.id)
            .order_by(RoomStatusLog.change_time.desc())
            .limit(limit)
        ).all()
        
        for log, room, user in recent_room_changes:
            activities.append({
                'type': 'room',
                'action': 'status_change',
                'description': f"Room {room.number} status changed to {log.new_status}",
                'time': log.change_time,
                'user': user.username if user else 'System',
                'details': f"From {log.old_status}" if log.old_status else ""
            })
        
        # Recent payments
        recent_payments = self.db_session.execute(
            select(Payment, Booking, User)
            .join(Booking, Payment.booking_id == Booking.id)
            .outerjoin(User, Payment.processed_by == User.id)
            .order_by(Payment.payment_date.desc())
            .limit(limit)
        ).all()
        
        for payment, booking, user in recent_payments:
            activities.append({
                'type': 'payment',
                'action': 'payment_processed',
                'description': f"Payment of ${payment.amount} processed for booking {booking.id}",
                'time': payment.payment_date,
                'user': user.username if user else 'System',
                'details': f"Method: {payment.payment_type}"
            })
        
        # Sort all activities by time and return the most recent
        activities.sort(key=lambda x: x['time'], reverse=True)
        return activities[:limit]
    
    def _calculate_guest_satisfaction(self):
        """Calculate guest satisfaction score based on completed stays and ratings."""
        # This is a simplified calculation - in a real system you'd have actual guest feedback
        # For now, we'll use successful bookings vs cancellations as a proxy
        
        # Get bookings from the last 30 days
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        
        total_bookings = self.db_session.execute(
            select(func.count(Booking.id))
            .filter(
                Booking.check_in_date >= thirty_days_ago,
                Booking.status.in_([
                    Booking.STATUS_CHECKED_OUT, 
                    Booking.STATUS_CANCELLED, 
                    Booking.STATUS_NO_SHOW
                ])
            )
        ).scalar_one() or 0
        
        successful_bookings = self.db_session.execute(
            select(func.count(Booking.id))
            .filter(
                Booking.check_in_date >= thirty_days_ago,
                Booking.status == Booking.STATUS_CHECKED_OUT
            )
        ).scalar_one() or 0
        
        if total_bookings > 0:
            # Calculate satisfaction as percentage of successful vs total bookings
            # Scale to a 1-5 rating system
            success_rate = successful_bookings / total_bookings
            satisfaction_score = 3.0 + (success_rate * 2.0)  # Range: 3.0 to 5.0
        else:
            satisfaction_score = 4.5  # Default good rating
        
        return round(satisfaction_score, 1) 