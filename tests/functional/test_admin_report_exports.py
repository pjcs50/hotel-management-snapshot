"""
Functional tests for admin report export functionality.

This module tests the export of reports in different formats
(PDF, Excel, and CSV).
"""

import pytest
from datetime import datetime, timedelta, date
from flask import url_for
from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking


def test_report_csv_export(client, auth, app, db):
    """Test CSV export of reports."""
    with app.app_context():
        # Create admin user
        admin = User(username="report_csv_admin", email="csv_admin@example.com", role="admin")
        admin.set_password("password")
        db.session.add(admin)
        
        # Create some test data
        _create_test_booking_data_with_prefix(db, "CSV")
        
        # Log in as admin
        auth.login(admin.email, "password")
        
        # Access reports endpoint
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        response = client.get(
            f'/admin/reports/export?month={current_month}&year={current_year}&format=csv',
            follow_redirects=True
        )
        
        # Verify response
        assert response.status_code == 200
        assert 'text/csv' in response.headers['Content-Type']
        assert 'attachment;filename=hotel_report_' in response.headers['Content-Disposition']
        
        # Basic content check
        content = response.data.decode('utf-8')
        assert 'Hotel Monthly Report' in content
        assert 'Revenue Summary' in content
        assert 'Occupancy Summary' in content
        assert 'Booking Summary' in content
        assert 'Room Type Revenue' in content


def test_report_excel_export(client, auth, app, db):
    """Test Excel export of reports."""
    with app.app_context():
        # Create admin user
        admin = User(username="report_excel_admin", email="excel_admin@example.com", role="admin")
        admin.set_password("password")
        db.session.add(admin)
        
        # Create some test data
        _create_test_booking_data_with_prefix(db, "XLS")
        
        # Log in as admin
        auth.login(admin.email, "password")
        
        # Access reports endpoint
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        response = client.get(
            f'/admin/reports/export?month={current_month}&year={current_year}&format=excel',
            follow_redirects=True
        )
        
        # Verify response
        assert response.status_code == 200
        # If pandas and xlsxwriter are installed, it should be Excel format
        # Otherwise, it may fall back to CSV
        content_type = response.headers['Content-Type']
        assert ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type or 
                'text/csv' in content_type)
        assert 'attachment;filename=hotel_report_' in response.headers['Content-Disposition']
        assert len(response.data) > 0  # Should have some content


def test_report_pdf_export(client, auth, app, db):
    """Test PDF export of reports."""
    with app.app_context():
        # Create admin user
        admin = User(username="report_pdf_admin", email="pdf_admin@example.com", role="admin")
        admin.set_password("password")
        db.session.add(admin)
        
        # Create some test data
        _create_test_booking_data_with_prefix(db, "PDF")
        
        # Log in as admin
        auth.login(admin.email, "password")
        
        # Access reports endpoint
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        response = client.get(
            f'/admin/reports/export?month={current_month}&year={current_year}&format=pdf',
            follow_redirects=True
        )
        
        # Verify response
        assert response.status_code == 200
        # If reportlab is installed, it should be PDF format
        # Otherwise, it may fall back to CSV
        content_type = response.headers['Content-Type']
        assert ('application/pdf' in content_type or 
                'text/csv' in content_type)
        assert 'attachment;filename=hotel_report_' in response.headers['Content-Disposition']
        assert len(response.data) > 0  # Should have some content


def test_report_export_unauthorized(client, app, db):
    """Test report export is not accessible without login."""
    with app.app_context():
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        response = client.get(
            f'/admin/reports/export?month={current_month}&year={current_year}&format=csv',
            follow_redirects=True
        )
        
        # Should redirect to login
        assert response.status_code == 200
        assert b'Please log in to access this page' in response.data


def test_report_export_wrong_role(client, auth, app, db):
    """Test report export is forbidden for non-admin users."""
    with app.app_context():
        # Create customer user
        user = User(username="customer_export", email="customer_export@example.com", role="customer")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Try to access export
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        response = client.get(f'/admin/reports/export?month={current_month}&year={current_year}&format=csv')
        
        # Should be forbidden
        assert response.status_code == 403


def test_report_export_invalid_format(client, auth, app, db):
    """Test report export with invalid format falls back to CSV."""
    with app.app_context():
        # Create admin user
        admin = User(username="invalid_export_admin", email="invalid_admin@example.com", role="admin")
        admin.set_password("password")
        db.session.add(admin)
        db.session.commit()
        
        # Log in as admin
        auth.login(admin.email, "password")
        
        # Access export with invalid format
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        response = client.get(
            f'/admin/reports/export?month={current_month}&year={current_year}&format=invalid',
            follow_redirects=True
        )
        
        # Should default to CSV
        assert response.status_code == 200
        assert 'text/csv' in response.headers['Content-Type']


def _create_test_booking_data_with_prefix(db, prefix):
    """Helper function to create test data for reports with unique room numbers."""
    # Create test room types
    standard = RoomType(name=f"Standard_{prefix}", base_rate=100.0, capacity=2)
    deluxe = RoomType(name=f"Deluxe_{prefix}", base_rate=150.0, capacity=4)
    db.session.add_all([standard, deluxe])
    db.session.flush()
    
    # Create test rooms with unique numbers
    room1 = Room(number=f"{prefix}101", room_type_id=standard.id)
    room2 = Room(number=f"{prefix}102", room_type_id=deluxe.id)
    db.session.add_all([room1, room2])
    
    # Create test user and customer
    user = User(username=f"report_{prefix.lower()}_customer", email=f"report_{prefix.lower()}@example.com", role="customer")
    user.set_password("password")
    db.session.add(user)
    db.session.flush()
    
    customer = Customer(name=f"Report {prefix} Customer", user_id=user.id)
    db.session.add(customer)
    db.session.flush()
    
    # Create bookings in the current month
    today = date.today()
    start_date = date(today.year, today.month, 1)
    
    # Create a few bookings with different statuses
    booking1 = Booking(
        customer_id=customer.id,
        room_id=room1.id,
        check_in_date=start_date,
        check_out_date=start_date + timedelta(days=3),
        status=Booking.STATUS_CHECKED_OUT
    )
    
    booking2 = Booking(
        customer_id=customer.id,
        room_id=room2.id,
        check_in_date=start_date + timedelta(days=5),
        check_out_date=start_date + timedelta(days=7),
        status=Booking.STATUS_RESERVED
    )
    
    booking3 = Booking(
        customer_id=customer.id,
        room_id=room1.id,
        check_in_date=start_date + timedelta(days=10),
        check_out_date=start_date + timedelta(days=12),
        status=Booking.STATUS_CANCELLED
    )
    
    db.session.add_all([booking1, booking2, booking3])
    db.session.commit() 