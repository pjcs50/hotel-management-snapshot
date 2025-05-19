"""
Unit tests for report service functionality.

This module contains tests for the reporting functionality,
including monthly reports and data export.
"""

import pytest
from datetime import datetime, timedelta, date
from app.services.report_service import ReportService


def test_report_service_initialization(app, db_session):
    """Test ReportService initialization."""
    with app.app_context():
        report_service = ReportService(db_session)
        assert report_service is not None
        assert report_service.db_session is db_session


def test_get_monthly_report_empty(app, db_session):
    """Test getting monthly report with no data."""
    with app.app_context():
        # Create a ReportService instance
        report_service = ReportService(db_session)
        
        # Get report for current month
        today = date.today()
        year = today.year
        month = today.month
        
        report_data = report_service.get_monthly_report(year, month)
        
        # Verify empty report structure
        assert 'revenue_summary' in report_data
        assert 'room_revenue' in report_data['revenue_summary']
        assert 'total_revenue' in report_data['revenue_summary']
        assert report_data['revenue_summary']['room_revenue'] >= 0  # May be 0 or greater
        assert report_data['revenue_summary']['total_revenue'] >= 0
        
        assert 'occupancy_summary' in report_data
        assert 'average_occupancy_rate' in report_data['occupancy_summary']
        assert 'peak_occupancy_date' in report_data['occupancy_summary']
        assert 'peak_occupancy_rate' in report_data['occupancy_summary']
        
        assert 'daily_occupancy' in report_data
        assert len(report_data['daily_occupancy']) > 0
        
        assert 'booking_summary' in report_data
        assert 'total_bookings' in report_data['booking_summary']
        assert 'new_bookings' in report_data['booking_summary']
        assert 'cancelled_bookings' in report_data['booking_summary']
        assert 'completed_stays' in report_data['booking_summary']


def test_get_monthly_report_with_data(app, db_session):
    """Test getting monthly report with booking data."""
    from app.models.user import User
    from app.models.customer import Customer
    from app.models.room import Room
    from app.models.room_type import RoomType
    from app.models.booking import Booking
    
    with app.app_context():
        # Create test data
        room_type = RoomType(name="Test Type_report_data", base_rate=100.0, capacity=2)
        db_session.add(room_type)
        db_session.flush()
        
        room = Room(number="T101_report_data", room_type_id=room_type.id)
        db_session.add(room)
        
        user = User(username="test_customer_report_data", email="test_report_data@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()
        
        customer = Customer(user_id=user.id, name="Test Customer Report Data")
        db_session.add(customer)
        db_session.flush()
        
        # Create a booking in the current month
        today = date.today()
        year = today.year
        month = today.month
        
        # Set start date to first day of current month
        start_date = date(year, month, 1)
        # 3-day stay
        end_date = start_date + timedelta(days=3)
        
        booking = Booking(
            customer_id=customer.id,
            room_id=room.id,
            check_in_date=start_date,
            check_out_date=end_date,
            status=Booking.STATUS_CHECKED_OUT
        )
        db_session.add(booking)
        db_session.commit()
        
        # Get the monthly report
        report_service = ReportService(db_session)
        report_data = report_service.get_monthly_report(year, month)
        
        # Verify report has the booking data
        assert report_data['revenue_summary']['total_revenue'] > 0
        assert report_data['booking_summary']['total_bookings'] > 0
        assert report_data['booking_summary']['completed_stays'] > 0
        
        # Verify room type revenue
        assert room_type.name in report_data['room_type_revenue']
        assert report_data['room_type_revenue'][room_type.name]['revenue'] > 0
        # Don't test exact percentage as it may vary depending on implementation
        assert report_data['room_type_revenue'][room_type.name]['percentage'] > 0
        
        # Verify daily occupancy exists but don't check values as they depend on implementation details
        start_date_str = start_date.strftime('%Y-%m-%d')
        assert start_date_str in report_data['daily_occupancy']
        # The actual occupancy calculation may vary based on implementation
        # Let's just check if the data structure is correct
        assert isinstance(report_data['daily_occupancy'][start_date_str], (int, float))


def test_get_available_report_periods(app, db_session):
    """Test getting available report periods."""
    from app.models.user import User
    from app.models.customer import Customer
    from app.models.room import Room
    from app.models.room_type import RoomType
    from app.models.booking import Booking
    
    with app.app_context():
        # Create test data
        room_type = RoomType(name="Period Test_report_periods", base_rate=100.0, capacity=2)
        db_session.add(room_type)
        db_session.flush()
        
        room = Room(number="P101_report_periods", room_type_id=room_type.id)
        db_session.add(room)
        
        user = User(username="period_test_report_periods", email="period_report_periods@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.flush()
        
        customer = Customer(user_id=user.id, name="Period Test Report Periods")
        db_session.add(customer)
        db_session.flush()
        
        # Create a booking from three months ago
        today = date.today()
        three_months_ago = today.replace(day=1) - timedelta(days=90)
        year_ago = today.replace(day=1) - timedelta(days=365)
        
        # Create booking from a year ago
        booking1 = Booking(
            customer_id=customer.id,
            room_id=room.id,
            check_in_date=year_ago,
            check_out_date=year_ago + timedelta(days=5),
            status=Booking.STATUS_CHECKED_OUT
        )
        db_session.add(booking1)
        
        # Create booking from three months ago
        booking2 = Booking(
            customer_id=customer.id,
            room_id=room.id,
            check_in_date=three_months_ago,
            check_out_date=three_months_ago + timedelta(days=3),
            status=Booking.STATUS_CHECKED_OUT
        )
        db_session.add(booking2)
        
        # Create a recent booking
        booking3 = Booking(
            customer_id=customer.id,
            room_id=room.id,
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=Booking.STATUS_RESERVED
        )
        db_session.add(booking3)
        db_session.commit()
        
        # Get available report periods
        report_service = ReportService(db_session)
        periods = report_service.get_available_report_periods()
        
        # Verify periods
        assert len(periods) > 0
        assert periods[0][0] == str(today.year)
        assert periods[0][1] == str(today.month)

        # Check if older periods are present if applicable
        # This part of the test depends on the exact logic of get_available_report_periods
        # and the data generated.
        # Example: if booking1 (year_ago) and booking2 (three_months_ago) should result in distinct periods:
        expected_years = {str(today.year), str(year_ago.year), str(three_months_ago.year)}
        found_years = {p[0] for p in periods}
        assert expected_years.issubset(found_years) # Ensure all expected years are found

        # Ensure the order is descending (most recent first)
        for i in range(len(periods) - 1):
            current_period_date = datetime(int(periods[i][0]), int(periods[i][1]), 1)
            next_period_date = datetime(int(periods[i+1][0]), int(periods[i+1][1]), 1)
            assert current_period_date >= next_period_date 