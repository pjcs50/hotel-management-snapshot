"""
Functional tests for availability calendar routes.

This module contains tests for customer and receptionist availability calendar routes.
"""

import pytest
from datetime import datetime, timedelta
from flask import url_for

from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking


def test_customer_availability_calendar_unauthorized(client):
    """Test that unauthorized users cannot access the customer availability calendar."""
    response = client.get(url_for('customer.availability_calendar'))
    assert response.status_code == 302  # Redirect to login page


def test_customer_availability_calendar_wrong_role(client, auth, app, db):
    """Test that non-customer users cannot access customer availability calendar."""
    with app.app_context():
        # Create receptionist user
        user = User(username="receptionist_avail_c", email="receptionist_avail_c@example.com", role="receptionist")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as receptionist
        auth.login(user.email, "password")
        
        # Try to access customer availability calendar
        response = client.get(url_for('customer.availability_calendar'))
        assert response.status_code == 403  # Forbidden


def test_receptionist_availability_calendar_unauthorized(client):
    """Test that unauthorized users cannot access the receptionist availability calendar."""
    response = client.get(url_for('receptionist.availability_calendar'))
    assert response.status_code == 302  # Redirect to login page


def test_receptionist_availability_calendar_wrong_role(client, auth, app, db):
    """Test that non-receptionist users cannot access receptionist availability calendar."""
    with app.app_context():
        # Create customer user
        user = User(username="customer_avail_r", email="customer_avail_r@example.com", role="customer")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Try to access receptionist availability calendar
        response = client.get(url_for('receptionist.availability_calendar'))
        assert response.status_code == 403  # Forbidden


def test_customer_availability_calendar_authorized(client, auth, app, db):
    """Test that authorized customer users can access customer availability calendar."""
    with app.app_context():
        # Create customer user
        user = User(username="customer_auth_cal", email="customer_auth_cal@example.com", role="customer")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Access customer availability calendar
        response = client.get(url_for('customer.availability_calendar'))
        assert response.status_code == 200
        # Success is just getting a 200 status code
        

def test_receptionist_availability_calendar_authorized(client, auth, app, db):
    """Test that authorized receptionist users can access receptionist availability calendar."""
    with app.app_context():
        # Create receptionist user
        user = User(username="receptionist_auth_cal", email="receptionist_auth_cal@example.com", role="receptionist")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        # Log in as receptionist
        auth.login(user.email, "password")
        
        # Access receptionist availability calendar
        response = client.get(url_for('receptionist.availability_calendar'))
        assert response.status_code == 200
        # Success is just getting a 200 status code
        

def test_customer_availability_calendar_with_data(client, auth, app, db):
    """Test availability calendar with room and booking data."""
    with app.app_context():
        # Create room types
        room_type1 = RoomType(name="Standard_cal_cust", description="Standard room", base_rate=100, capacity=2)
        room_type2 = RoomType(name="Deluxe_cal_cust", description="Deluxe room", base_rate=150, capacity=2)
        
        # Create rooms
        room1 = Room(number="101_cal1", room_type=room_type1, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="102_cal1", room_type=room_type1, status=Room.STATUS_AVAILABLE)
        room3 = Room(number="201_cal1", room_type=room_type2, status=Room.STATUS_AVAILABLE)
        
        # Create customer
        user = User(username="customer_cal_cust", email="customer_cal_cust@example.com", role="customer")
        user.set_password("password")
        customer = Customer(
            user=user,
            name="Calendar Customer",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        
        # Create booking
        today = datetime.now().date()
        booking = Booking(
            room=room1,
            customer=customer,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        
        # Add to database
        db.session.add_all([room_type1, room_type2, room1, room2, room3, user, customer, booking])
        db.session.commit()
        
        # Log in as customer
        auth.login(user.email, "password")
        
        # Access customer availability calendar
        response = client.get(url_for('customer.availability_calendar'))
        assert response.status_code == 200
        # Success is just getting a 200 status code


def test_receptionist_availability_calendar_with_data(client, auth, app, db):
    """Test availability calendar with room and booking data."""
    with app.app_context():
        # Create room types
        room_type1 = RoomType(name="Standard_cal_rec", description="Standard room", base_rate=100, capacity=2)
        room_type2 = RoomType(name="Deluxe_cal_rec", description="Deluxe room", base_rate=150, capacity=2)
        
        # Create rooms
        room1 = Room(number="101_cal2", room_type=room_type1, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="102_cal2", room_type=room_type1, status=Room.STATUS_AVAILABLE)
        room3 = Room(number="201_cal2", room_type=room_type2, status=Room.STATUS_AVAILABLE)
        
        # Create customer
        cust_user = User(username="customer_cal_rec", email="customer_cal_rec@example.com", role="customer")
        cust_user.set_password("password")
        customer = Customer(
            user=cust_user,
            name="Calendar Customer 2",
            phone="123-456-7890",
            address="123 Main St",
            emergency_contact="Jane Doe, 555-1234",
            profile_complete=True
        )
        
        # Create receptionist
        rec_user = User(username="receptionist_cal_rec", email="receptionist_cal_rec@example.com", role="receptionist")
        rec_user.set_password("password")
        
        # Create booking
        today = datetime.now().date()
        booking = Booking(
            room=room1,
            customer=customer,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        
        # Add to database
        db.session.add_all([room_type1, room_type2, room1, room2, room3, cust_user, rec_user, customer, booking])
        db.session.commit()
        
        # Log in as receptionist
        auth.login(rec_user.email, "password")
        
        # Access receptionist availability calendar
        response = client.get(url_for('receptionist.availability_calendar'))
        assert response.status_code == 200
        # Success is just getting a 200 status code 