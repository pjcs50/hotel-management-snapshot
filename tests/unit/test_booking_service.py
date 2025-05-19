"""
Unit tests for BookingService class.

This module contains tests for the BookingService class methods.
"""

import pytest
from datetime import datetime, timedelta

from app.services.booking_service import BookingService, RoomNotAvailableError
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.user import User


def test_get_availability_calendar_data_empty_hotel(app, db_session):
    """Test the method with no rooms."""
    with app.app_context():
        # Clear existing RoomType objects
        db_session.query(RoomType).delete()
        db_session.query(Room).delete()
        db_session.commit()
        
        # Create the service with a database session
        booking_service = BookingService(db_session)
        
        # Define date range
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=7)
        
        # Get availability data
        data = booking_service.get_availability_calendar_data(start_date, end_date)
        
        # Verify data structure
        assert 'dates' in data
        assert 'room_types' in data
        assert 'availability' in data
        
        # Verify dates (should be 8 days - inclusive of start and end dates)
        assert len(data['dates']) == 8
        assert data['dates'][0] == start_date.strftime('%Y-%m-%d')
        assert data['dates'][-1] == end_date.strftime('%Y-%m-%d')
        
        # No room types, so these should be empty
        assert len(data['room_types']) == 0
        assert len(data['availability']) == 0


def test_get_availability_calendar_data_with_rooms(app, db_session):
    """Test the method with rooms but no bookings."""
    with app.app_context():
        # Clear existing RoomType and Room objects
        db_session.query(Booking).delete()
        db_session.query(Room).delete()
        db_session.query(RoomType).delete()
        db_session.commit()
        
        # Create room types
        room_type1 = RoomType(name="Standard_bs_rooms", description="Standard room", base_rate=100, capacity=2)
        room_type2 = RoomType(name="Deluxe_bs_rooms", description="Deluxe room", base_rate=150, capacity=2)
        
        # Create rooms
        room1 = Room(number="101_test", room_type=room_type1, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="102_test", room_type=room_type1, status=Room.STATUS_AVAILABLE)
        room3 = Room(number="201_test", room_type=room_type2, status=Room.STATUS_AVAILABLE)
        
        # Add to database
        db_session.add_all([room_type1, room_type2, room1, room2, room3])
        db_session.commit()
        
        # Create the service
        booking_service = BookingService(db_session)
        
        # Define date range
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=3)
        
        # Get availability data
        data = booking_service.get_availability_calendar_data(start_date, end_date)
        
        # Verify room types
        assert len(data['room_types']) == 2
        
        # Verify availability data structure
        assert len(data['dates']) == 4  # 4 days, inclusive
        
        # Test specific values - assert availability for the new room types
        room_type_ids = [rt['id'] for rt in data['room_types']]
        assert str(room_type1.id) in data['availability']
        assert str(room_type2.id) in data['availability']


def test_get_availability_calendar_data_with_bookings(app, db_session):
    """Test the method with rooms and bookings."""
    with app.app_context():
        # Create a user and customer
        user = User(username="testuser_bs_bookings", email="test_bs_bookings@example.com")
        user.set_password("password")
        customer = Customer(user=user, name="Test Customer")
        
        # Create room type
        room_type = RoomType(name="Standard_bs_bookings", description="Standard room", base_rate=100, capacity=2)
        
        # Create rooms
        room1 = Room(number="101", room_type=room_type, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="102", room_type=room_type, status=Room.STATUS_AVAILABLE)
        
        # Add to database
        db_session.add_all([user, customer, room_type, room1, room2])
        db_session.commit()
        
        # Create booking for room1
        today = datetime.now().date()
        booking = Booking(
            room=room1,
            customer=customer,
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=Booking.STATUS_RESERVED
        )
        
        # Update room status
        room1.status = Room.STATUS_BOOKED
        
        db_session.add(booking)
        db_session.commit()
        
        # Create the service
        booking_service = BookingService(db_session)
        
        # Define date range
        start_date = today
        end_date = today + timedelta(days=4)
        
        # Get availability data
        data = booking_service.get_availability_calendar_data(start_date, end_date)
        
        # Verify availability
        rt_id = str(room_type.id)
        
        # Day 1: Room1 is booked, Room2 is available (1 of 2 available)
        assert data['availability'][rt_id][today.strftime('%Y-%m-%d')]['available'] == 1
        assert data['availability'][rt_id][today.strftime('%Y-%m-%d')]['total'] == 2
        
        # Day 2: Room1 is booked, Room2 is available (1 of 2 available)
        day2 = today + timedelta(days=1)
        assert data['availability'][rt_id][day2.strftime('%Y-%m-%d')]['available'] == 1
        
        # Day 3: Both rooms available (2 of 2 available)
        day3 = today + timedelta(days=2)
        assert data['availability'][rt_id][day3.strftime('%Y-%m-%d')]['available'] == 2
        
        # Day 4: Both rooms available (2 of 2 available)
        day4 = today + timedelta(days=3)
        assert data['availability'][rt_id][day4.strftime('%Y-%m-%d')]['available'] == 2
        
        # Day 5: Both rooms available (2 of 2 available)
        day5 = today + timedelta(days=4)
        assert data['availability'][rt_id][day5.strftime('%Y-%m-%d')]['available'] == 2


def test_get_availability_calendar_data_filtered_by_room_type(app, db_session):
    """Test the method with room type filtering."""
    with app.app_context():
        # Create room types
        room_type1 = RoomType(name="Standard_bs_filter", description="Standard room", base_rate=100, capacity=2)
        room_type2 = RoomType(name="Deluxe_bs_filter", description="Deluxe room", base_rate=150, capacity=2)
        
        # Create rooms
        room1 = Room(number="101", room_type=room_type1, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="201", room_type=room_type2, status=Room.STATUS_AVAILABLE)
        
        # Add to database
        db_session.add_all([room_type1, room_type2, room1, room2])
        db_session.commit()
        
        # Create the service
        booking_service = BookingService(db_session)
        
        # Define date range
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=3)
        
        # Get availability data filtered by room_type1
        data = booking_service.get_availability_calendar_data(start_date, end_date, room_type_id=room_type1.id)
        
        # Verify only room_type1 is included
        assert len(data['room_types']) == 1
        assert data['room_types'][0]['id'] == room_type1.id
        
        # Verify availability only for room_type1
        assert len(data['availability']) == 1
        assert str(room_type1.id) in data['availability']
        assert str(room_type2.id) not in data['availability']


def test_to_dict_methods(app, db_session):
    """Test the to_dict methods of RoomType and Room models."""
    with app.app_context():
        # Create room type
        room_type = RoomType(name="Standard_bs_dict", description="Standard room", base_rate=100, capacity=2)
        db_session.add(room_type)
        db_session.commit()
        
        # Test RoomType.to_dict
        room_type_dict = room_type.to_dict()
        assert room_type_dict['id'] == room_type.id
        assert room_type_dict['name'] == "Standard_bs_dict"
        assert room_type_dict['description'] == "Standard room"
        assert room_type_dict['amenities'] == [] # Check for empty list as no boolean flags set
        assert room_type_dict['base_rate'] == 100.0
        assert room_type_dict['capacity'] == 2
        
        # Create room
        room = Room(number="101_unique_for_dict_test", room_type=room_type, status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        db_session.commit()
        
        # Test Room.to_dict
        room_dict = room.to_dict()
        assert room_dict['id'] == room.id
        assert room_dict['number'] == "101_unique_for_dict_test"
        assert room_dict['room_type_id'] == room_type.id
        assert room_dict['status'] == Room.STATUS_AVAILABLE
        
        # Verify that room_type is included and properly converted
        assert 'room_type' in room_dict
        assert room_dict['room_type']['id'] == room_type.id
        assert room_dict['room_type']['name'] == "Standard_bs_dict" 