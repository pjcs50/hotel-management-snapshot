"""
Integration tests for enhanced booking API endpoints.

This module contains tests for the enhanced booking API endpoints,
including early check-in and late check-out features.
"""

import pytest
import json
from datetime import datetime, timedelta
from flask import url_for

from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking


@pytest.fixture
def setup_enhanced_test_data(app, db_session):
    """Set up test data for enhanced booking API tests."""
    with app.app_context():
        # Create a user and customer
        user = User(username="testuser_api_enhanced", email="test_api_enhanced@example.com")
        user.set_password("password")
        customer = Customer(user=user, name="Enhanced Test Customer")
        
        # Create room type
        room_type = RoomType(name="Standard_API_Enhanced", description="Standard room", base_rate=100, capacity=2)
        
        # Create rooms
        room1 = Room(number="101_API_Enhanced", room_type=room_type, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="102_API_Enhanced", room_type=room_type, status=Room.STATUS_AVAILABLE)
        
        # Add to database
        db_session.add_all([user, customer, room_type, room1, room2])
        db_session.commit()
        
        return {
            'user': user,
            'customer': customer,
            'room_type': room_type,
            'room1': room1,
            'room2': room2
        }


def test_create_booking_with_early_checkin(client, setup_enhanced_test_data, auth):
    """Test creating a booking with early check-in via API."""
    # Login as test user
    auth.login(username="testuser_api_enhanced", password="password")
    
    # Define date range
    today = datetime.now().date()
    check_in_date = today + timedelta(days=1)
    check_out_date = today + timedelta(days=3)
    
    # Make request with early check-in
    early_hours = 2
    response = client.post(
        url_for('api.create_booking'),
        json={
            'room_id': setup_enhanced_test_data['room1'].id,
            'customer_id': setup_enhanced_test_data['customer'].id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'num_guests': 2,
            'early_hours': early_hours,
            'special_requests': 'Early check-in test'
        }
    )
    
    # Check response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'booking' in data
    
    # Verify early check-in hours were saved
    assert data['booking']['early_hours'] == early_hours
    
    # Verify price includes early check-in fee
    base_price = setup_enhanced_test_data['room_type'].base_rate * 2  # 2 nights
    early_fee = setup_enhanced_test_data['room_type'].base_rate * 0.1 * early_hours
    expected_price = base_price + early_fee
    assert data['booking']['total_price'] == pytest.approx(expected_price, 0.01)


def test_create_booking_with_late_checkout(client, setup_enhanced_test_data, auth):
    """Test creating a booking with late check-out via API."""
    # Login as test user
    auth.login(username="testuser_api_enhanced", password="password")
    
    # Define date range
    today = datetime.now().date()
    check_in_date = today + timedelta(days=1)
    check_out_date = today + timedelta(days=3)
    
    # Make request with late check-out
    late_hours = 3
    response = client.post(
        url_for('api.create_booking'),
        json={
            'room_id': setup_enhanced_test_data['room1'].id,
            'customer_id': setup_enhanced_test_data['customer'].id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'num_guests': 2,
            'late_hours': late_hours,
            'special_requests': 'Late check-out test'
        }
    )
    
    # Check response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'booking' in data
    
    # Verify late check-out hours were saved
    assert data['booking']['late_hours'] == late_hours
    
    # Verify price includes late check-out fee
    base_price = setup_enhanced_test_data['room_type'].base_rate * 2  # 2 nights
    late_fee = setup_enhanced_test_data['room_type'].base_rate * 0.1 * late_hours
    expected_price = base_price + late_fee
    assert data['booking']['total_price'] == pytest.approx(expected_price, 0.01)


def test_create_booking_with_both_early_and_late(client, setup_enhanced_test_data, auth):
    """Test creating a booking with both early check-in and late check-out via API."""
    # Login as test user
    auth.login(username="testuser_api_enhanced", password="password")
    
    # Define date range
    today = datetime.now().date()
    check_in_date = today + timedelta(days=1)
    check_out_date = today + timedelta(days=3)
    
    # Make request with both early check-in and late check-out
    early_hours = 2
    late_hours = 3
    response = client.post(
        url_for('api.create_booking'),
        json={
            'room_id': setup_enhanced_test_data['room1'].id,
            'customer_id': setup_enhanced_test_data['customer'].id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'num_guests': 2,
            'early_hours': early_hours,
            'late_hours': late_hours,
            'special_requests': 'Both early and late test'
        }
    )
    
    # Check response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'booking' in data
    
    # Verify both early check-in and late check-out hours were saved
    assert data['booking']['early_hours'] == early_hours
    assert data['booking']['late_hours'] == late_hours
    
    # Verify price includes both early check-in and late check-out fees
    base_price = setup_enhanced_test_data['room_type'].base_rate * 2  # 2 nights
    early_fee = setup_enhanced_test_data['room_type'].base_rate * 0.1 * early_hours
    late_fee = setup_enhanced_test_data['room_type'].base_rate * 0.1 * late_hours
    expected_price = base_price + early_fee + late_fee
    assert data['booking']['total_price'] == pytest.approx(expected_price, 0.01)


def test_update_booking_early_late_hours(client, setup_enhanced_test_data, auth):
    """Test updating a booking to add early check-in and late check-out hours via API."""
    # Login as test user
    auth.login(username="testuser_api_enhanced", password="password")
    
    # Create a booking first
    today = datetime.now().date()
    booking = Booking(
        room_id=setup_enhanced_test_data['room2'].id,
        customer_id=setup_enhanced_test_data['customer'].id,
        check_in_date=today + timedelta(days=5),
        check_out_date=today + timedelta(days=7),
        status=Booking.STATUS_RESERVED
    )
    from db import db
    db.session.add(booking)
    db.session.commit()
    
    # Calculate initial price
    booking.calculate_price()
    db.session.commit()
    initial_price = booking.total_price
    
    # Update booking to add early check-in and late check-out
    early_hours = 2
    late_hours = 3
    response = client.put(
        url_for('api.update_booking', booking_id=booking.id),
        json={
            'early_hours': early_hours,
            'late_hours': late_hours,
            'special_requests': 'Updated with early and late hours'
        }
    )
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'booking' in data
    
    # Verify both early check-in and late check-out hours were updated
    assert data['booking']['early_hours'] == early_hours
    assert data['booking']['late_hours'] == late_hours
    
    # Verify price was updated to include both fees
    early_fee = setup_enhanced_test_data['room_type'].base_rate * 0.1 * early_hours
    late_fee = setup_enhanced_test_data['room_type'].base_rate * 0.1 * late_hours
    expected_price = initial_price + early_fee + late_fee
    
    # Refresh booking from database to get updated price
    db.session.refresh(booking)
    booking.calculate_price()
    db.session.commit()
    
    assert booking.total_price == pytest.approx(expected_price, 0.01)


def test_validation_errors_early_late_hours(client, setup_enhanced_test_data, auth):
    """Test validation errors for early check-in and late check-out hours via API."""
    # Login as test user
    auth.login(username="testuser_api_enhanced", password="password")
    
    # Define date range
    today = datetime.now().date()
    check_in_date = today + timedelta(days=1)
    check_out_date = today + timedelta(days=3)
    
    # Test case 1: Early hours too high
    response = client.post(
        url_for('api.create_booking'),
        json={
            'room_id': setup_enhanced_test_data['room1'].id,
            'customer_id': setup_enhanced_test_data['customer'].id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'num_guests': 2,
            'early_hours': 15,  # Too high (max is 12)
            'special_requests': 'Early hours too high test'
        }
    )
    
    # Check response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'error' in data
    assert 'early_hours' in data['error'].lower()
    
    # Test case 2: Late hours too high
    response = client.post(
        url_for('api.create_booking'),
        json={
            'room_id': setup_enhanced_test_data['room1'].id,
            'customer_id': setup_enhanced_test_data['customer'].id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'num_guests': 2,
            'late_hours': 20,  # Too high (max is 12)
            'special_requests': 'Late hours too high test'
        }
    )
    
    # Check response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'error' in data
    assert 'late_hours' in data['error'].lower()
    
    # Test case 3: Negative early hours
    response = client.post(
        url_for('api.create_booking'),
        json={
            'room_id': setup_enhanced_test_data['room1'].id,
            'customer_id': setup_enhanced_test_data['customer'].id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'num_guests': 2,
            'early_hours': -2,  # Negative (min is 0)
            'special_requests': 'Negative early hours test'
        }
    )
    
    # Check response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'error' in data
    assert 'early_hours' in data['error'].lower()
