"""
Dashboard service module.

This module provides services for dashboard data and metrics.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, select

from app.models.booking import Booking
from app.models.room import Room
from app.models.room_status_log import RoomStatusLog
from app.models.customer import Customer
from app.models.user import User
from app.models.room_type import RoomType
from app.services.analytics_service import AnalyticsService
from app.services.notification_service import NotificationService


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
        
        # Get upcoming bookings
        today = datetime.now().date()
        upcoming_bookings = self.db_session.execute(
            select(Booking).filter(
                Booking.customer_id == customer.id,
                Booking.check_in_date >= today,
                Booking.status == Booking.STATUS_RESERVED
            ).order_by(Booking.check_in_date)
        ).scalars().all()
        
        # Get active booking (currently checked in)
        active_booking = self.db_session.execute(
            select(Booking).filter(
                Booking.customer_id == customer.id,
                Booking.status == Booking.STATUS_CHECKED_IN,
                Booking.check_in_date <= today,
                Booking.check_out_date >= today
            )
        ).scalar_one_or_none()
        
        # Get past bookings (checked out or cancelled)
        past_bookings = self.db_session.execute(
            select(Booking).filter(
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
            "total_rooms": total_rooms,
            "occupancy_rate": occupancy_rate,
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
            "adr": adr_value if adr_value is not None else 0.0,  # Ensure key exists and is float
            "revpar": revpar_value if revpar_value is not None else 0.0 # Ensure key exists and is float
        }
    
    def _get_top_staff_performers(self, limit=5):
        """Get top-performing staff based on task completion and ratings."""
        # This is a placeholder - in a real system this would query actual performance metrics
        # from the database based on tasks completed, response times, and customer ratings
        
        # Get actual staff users from the database
        staff_users = self.db_session.execute(
            select(User).filter(User.role != 'customer').limit(limit)
        ).scalars().all()
        
        # Create performance metrics (sample data for demonstration)
        import random
        performers = []
        
        for user in staff_users:
            performers.append({
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'tasks_completed': random.randint(10, 50),
                'efficiency_score': random.uniform(80, 99),
                'customer_rating': round(random.uniform(3.5, 5.0), 1)
            })
            
        # Sort by efficiency score
        performers.sort(key=lambda x: x['efficiency_score'], reverse=True)
        
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
        
        return {
            "user_counts": user_data,
            "total_users": total_users,
            "recent_users": recent_users_data,
            "pending_role_requests": pending_requests_data,
            "room_type_counts": room_type_data,
            "total_bookings": total_bookings,
            "active_bookings": active_bookings,
            "user_registration_history": user_registration_history
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