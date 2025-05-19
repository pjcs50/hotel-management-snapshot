"""
Test module for AnalyticsService.

This module provides unit tests for the analytics service.
"""

import pytest
from datetime import datetime, timedelta
from app.services.analytics_service import AnalyticsService
from app.models.room_type import RoomType
from app.models.room import Room
from app.models.user import User
from app.models.booking import Booking


@pytest.fixture
def analytics_service(db_session):
    """Create an analytics service instance for testing."""
    return AnalyticsService(db_session)


@pytest.fixture
def room_types(db_session):
    """Create room types for testing."""
    room_types = []
    
    types = [
        {"name": "Standard", "base_rate": 100.00, "capacity": 2},
        {"name": "Deluxe", "base_rate": 200.00, "capacity": 2},
        {"name": "Suite", "base_rate": 300.00, "capacity": 4}
    ]
    
    for type_data in types:
        room_type = RoomType(
            name=type_data["name"],
            description=f"{type_data['name']} room",
            base_rate=type_data["base_rate"],
            capacity=type_data["capacity"]
        )
        db_session.add(room_type)
        room_types.append(room_type)
    
    db_session.commit()
    return room_types


@pytest.fixture
def rooms(db_session, room_types):
    """Create rooms for testing."""
    rooms = []
    
    # Create 2 rooms for each room type
    for i, room_type in enumerate(room_types):
        for j in range(2):
            room = Room(
                number=f"{i+1}0{j+1}",
                room_type_id=room_type.id,
                status="clean"
            )
            db_session.add(room)
            rooms.append(room)
    
    db_session.commit()
    return rooms


@pytest.fixture
def customers(db_session):
    """Create customer users for testing."""
    customers = []
    
    for i in range(5):
        user = User(
            username=f"customer{i+1}",
            email=f"customer{i+1}@example.com",
            role="customer",
            is_active=True
        )
        user.set_password("password")
        db_session.add(user)
        customers.append(user)
    
    db_session.commit()
    return customers


@pytest.fixture
def bookings(db_session, rooms, customers):
    """Create bookings for testing."""
    bookings = []
    current_year = datetime.now().year
    
    # Create past bookings (last year)
    past_booking = Booking(
        customer_id=customers[0].id,
        room_id=rooms[0].id,
        check_in_date=datetime(current_year-1, 1, 15),
        check_out_date=datetime(current_year-1, 1, 20),
        status="checked_out",
        total_price=500.00
    )
    db_session.add(past_booking)
    bookings.append(past_booking)
    
    # Create current year bookings across different months and room types
    for month in range(1, 13):
        for i, room in enumerate(rooms[:3]):  # Use first 3 rooms
            # Skip some months to make data more realistic
            if month % 3 == i:
                continue
                
            # Vary booking length and customers
            days = 3 + (i % 3)
            customer_index = (month + i) % len(customers)
            
            start_date = datetime(current_year, month, 10)
            end_date = start_date + timedelta(days=days)
            
            # Vary status based on date
            now = datetime.now()
            if end_date < now:
                status = "checked_out"
            elif start_date < now < end_date:
                status = "checked_in"
            else:
                status = "confirmed"
            
            # Calculate price based on room type and length
            base_price = rooms[i].room_type.base_rate
            total_price = base_price * days
            
            booking = Booking(
                customer_id=customers[customer_index].id,
                room_id=room.id,
                check_in_date=start_date,
                check_out_date=end_date,
                status=status,
                total_price=total_price
            )
            db_session.add(booking)
            bookings.append(booking)
    
    db_session.commit()
    return bookings


class TestAnalyticsService:
    """Test class for AnalyticsService."""

    def test_get_monthly_occupancy(self, analytics_service, bookings):
        """Test getting monthly occupancy rates."""
        current_year = datetime.now().year
        
        # Test current year
        result = analytics_service.get_monthly_occupancy(current_year)
        
        assert 'labels' in result
        assert 'datasets' in result
        assert len(result['labels']) == 12
        assert len(result['datasets']) == 1
        assert len(result['datasets'][0]['data']) == 12
        
        # Verify some occupancy data exists (exact values will depend on fixture data)
        assert any(rate > 0 for rate in result['datasets'][0]['data'])
        
        # Test previous year
        result = analytics_service.get_monthly_occupancy(current_year - 1)
        assert len(result['datasets'][0]['data']) == 12
        # Should have some data in January from our fixture
        assert result['datasets'][0]['data'][0] > 0

    def test_get_revenue_by_room_type(self, analytics_service, room_types, bookings):
        """Test getting revenue data grouped by room type."""
        current_year = datetime.now().year
        
        # Test current year, all months
        result = analytics_service.get_revenue_by_room_type(current_year)
        
        assert 'labels' in result
        assert 'datasets' in result
        assert len(result['labels']) > 0
        assert len(result['datasets']) == 1
        assert len(result['datasets'][0]['data']) == len(result['labels'])
        
        # Test current year, specific month
        result = analytics_service.get_revenue_by_room_type(current_year, 1)
        assert 'labels' in result
        assert 'datasets' in result

    def test_get_top_customers(self, analytics_service, customers, bookings):
        """Test getting the top customers by booking amount."""
        # Test default limit
        result = analytics_service.get_top_customers()
        
        assert isinstance(result, list)
        assert len(result) <= 5  # Default limit is 5
        
        if len(result) > 0:
            # Verify customer data structure
            customer = result[0]
            assert 'id' in customer
            assert 'username' in customer
            assert 'email' in customer
            assert 'total_spend' in customer
            assert 'booking_count' in customer
        
        # Test custom limit
        result = analytics_service.get_top_customers(limit=2)
        assert len(result) <= 2

    def test_get_booking_source_distribution(self, analytics_service):
        """Test getting the distribution of booking sources."""
        result = analytics_service.get_booking_source_distribution()
        
        assert 'labels' in result
        assert 'datasets' in result
        assert len(result['labels']) > 0
        assert len(result['datasets']) == 1
        assert len(result['datasets'][0]['data']) == len(result['labels'])
        
        # Sum of percentages should be 100
        total_percentage = sum(result['datasets'][0]['data'])
        assert total_percentage == 100

    def test_get_forecast_data(self, analytics_service):
        """Test getting forecast data for upcoming days."""
        # Test default days
        result = analytics_service.get_forecast_data()
        
        assert 'labels' in result
        assert 'datasets' in result
        assert len(result['labels']) == 30  # Default is 30 days
        assert len(result['datasets']) == 1
        assert len(result['datasets'][0]['data']) == 30
        
        # Test custom days
        result = analytics_service.get_forecast_data(days=7)
        assert len(result['labels']) == 7
        assert len(result['datasets'][0]['data']) == 7

    # --- Tests for ADR and RevPAR ---
    def test_get_total_room_revenue(self, analytics_service, bookings, db_session, rooms, customers):
        """Test calculating total room revenue for a period."""
        # Scenario 1: No bookings in period
        start_date_s1 = datetime(2000, 1, 1).date()
        end_date_s1 = datetime(2000, 1, 31).date()
        revenue_s1 = analytics_service.get_total_room_revenue(start_date_s1, end_date_s1)
        assert revenue_s1 == 0.0

        # Scenario 2: Bookings within the period - Create specific data
        # This makes the test independent of the global 'bookings' fixture's date logic for this specific assertion.
        test_year = 2024 # Use a fixed year for predictability
        start_date_s2 = datetime(test_year, 1, 1).date()
        end_date_s2 = datetime(test_year, 1, 31).date()

        # Clear any existing bookings from other tests that might interfere with this specific date range
        # This is aggressive; ideally fixtures handle isolation, but for this test let's ensure a clean slate for the period.
        existing_bookings_in_period = db_session.query(Booking).filter(
            Booking.check_in_date <= end_date_s2,
            Booking.check_out_date > start_date_s2
        ).all()
        for b in existing_bookings_in_period:
            db_session.delete(b)
        db_session.commit()

        room1 = rooms[0]
        cust1 = customers[0]
        b1_s2 = Booking(customer_id=cust1.id, room_id=room1.id, 
                        check_in_date=datetime(test_year, 1, 5).date(), 
                        check_out_date=datetime(test_year, 1, 10).date(), 
                        status=Booking.STATUS_CHECKED_OUT, total_price=500.0)
        b2_s2 = Booking(customer_id=cust1.id, room_id=rooms[1].id, 
                        check_in_date=datetime(test_year, 1, 15).date(), 
                        check_out_date=datetime(test_year, 1, 20).date(), 
                        status=Booking.STATUS_RESERVED, total_price=600.0)
        db_session.add_all([b1_s2, b2_s2])
        db_session.commit()
        
        expected_revenue_s2 = 1100.0
        actual_revenue_s2 = analytics_service.get_total_room_revenue(start_date_s2, end_date_s2)
        assert actual_revenue_s2 == expected_revenue_s2

    def test_get_number_of_rooms_sold(self, analytics_service, rooms, customers, db_session):
        """Test calculating the number of rooms sold (occupied room nights)."""
        start_date = datetime(2023, 1, 1).date()
        end_date = datetime(2023, 1, 5).date() # 5 nights period

        # Scenario 1: No rooms sold
        rooms_sold_none = analytics_service.get_number_of_rooms_sold(start_date, end_date)
        assert rooms_sold_none == 0

        # Scenario 2: Create some specific bookings for this test
        room1 = rooms[0]
        cust1 = customers[0]
        # Booking 1: covers 3 nights in period (Jan 1, 2, 3)
        b1 = Booking(customer_id=cust1.id, room_id=room1.id, check_in_date=datetime(2023,1,1).date(), check_out_date=datetime(2023,1,4).date(), status=Booking.STATUS_CHECKED_IN, total_price=300)
        # Booking 2: covers 2 nights in period (Jan 4, 5) - different room to avoid overlap issue in simple count
        room2 = rooms[1]
        b2 = Booking(customer_id=cust1.id, room_id=room2.id, check_in_date=datetime(2023,1,4).date(), check_out_date=datetime(2023,1,6).date(), status=Booking.STATUS_RESERVED, total_price=200)
        db_session.add_all([b1, b2])
        db_session.commit()

        rooms_sold_some = analytics_service.get_number_of_rooms_sold(start_date, end_date)
        # b1: Jan 1, Jan 2, Jan 3 = 3 room nights
        # b2: Jan 4, Jan 5 = 2 room nights
        assert rooms_sold_some == 5 

        # Scenario 3: Booking spans beyond the period
        db_session.delete(b1); db_session.delete(b2); db_session.commit() # Clear previous
        b3 = Booking(customer_id=cust1.id, room_id=room1.id, check_in_date=datetime(2022,12,30).date(), check_out_date=datetime(2023,1,3).date(), status=Booking.STATUS_CHECKED_IN, total_price=400)
        db_session.add(b3); db_session.commit()
        rooms_sold_span = analytics_service.get_number_of_rooms_sold(start_date, end_date)
        # b3: Jan 1, Jan 2 = 2 room nights in period
        assert rooms_sold_span == 2

    def test_get_total_available_room_nights(self, analytics_service, rooms, db_session):
        """Test calculating total available room nights."""
        start_date = datetime(2023, 1, 1).date()
        end_date = datetime(2023, 1, 10).date() # 10 days period
        
        num_total_rooms = len(rooms)
        expected_available_nights = num_total_rooms * 10
        
        actual_available_nights = analytics_service.get_total_available_room_nights(start_date, end_date)
        assert actual_available_nights == expected_available_nights

        # Test with no rooms in DB (edge case, though fixture ensures rooms)
        # This would require a separate fixture or modifying db_session, complex for this unit test
        # Instead, we trust the query func.count(Room.id) returning 0 is handled by the method

    def test_calculate_adr(self, analytics_service, rooms, customers, db_session):
        """Test ADR calculation."""
        start_date = datetime(2023, 2, 1).date()
        end_date = datetime(2023, 2, 5).date()

        # Scenario 1: No rooms sold, ADR should be 0
        adr_none = analytics_service.calculate_adr(start_date, end_date)
        assert adr_none == 0.0

        # Scenario 2: Some rooms sold
        room1 = rooms[0]
        cust1 = customers[0]
        b1 = Booking(customer_id=cust1.id, room_id=room1.id, check_in_date=datetime(2023,2,1).date(), check_out_date=datetime(2023,2,3).date(), status=Booking.STATUS_CHECKED_IN, total_price=200) # 2 nights, revenue 200
        b2 = Booking(customer_id=cust1.id, room_id=rooms[1].id, check_in_date=datetime(2023,2,3).date(), check_out_date=datetime(2023,2,5).date(), status=Booking.STATUS_RESERVED, total_price=180) # 2 nights, revenue 180
        db_session.add_all([b1,b2]); db_session.commit()

        # Total revenue = 200 + 180 = 380
        # Rooms sold: b1 (Feb 1, Feb 2) = 2; b2 (Feb 3, Feb 4) = 2. Total = 4 room nights.
        # ADR = 380 / 4 = 95.0
        expected_adr = 95.0
        actual_adr = analytics_service.calculate_adr(start_date, end_date)
        assert actual_adr == expected_adr

    def test_calculate_revpar(self, analytics_service, rooms, customers, db_session):
        """Test RevPAR calculation."""
        start_date = datetime(2023, 3, 1).date()
        end_date = datetime(2023, 3, 5).date() # 5 days period
        num_total_rooms = len(rooms)

        # Scenario 1: No revenue, RevPAR should be 0
        revpar_none = analytics_service.calculate_revpar(start_date, end_date)
        assert revpar_none == 0.0

        # Scenario 2: Some revenue
        room1 = rooms[0]
        cust1 = customers[0]
        # Total revenue = 500 for this booking
        b1 = Booking(customer_id=cust1.id, room_id=room1.id, check_in_date=datetime(2023,3,1).date(), check_out_date=datetime(2023,3,4).date(), status=Booking.STATUS_CHECKED_IN, total_price=500) # 3 nights
        db_session.add(b1); db_session.commit();

        # Total revenue = 500
        # Total available room nights = num_total_rooms * 5 days
        # RevPAR = 500 / (num_total_rooms * 5)
        total_available_nights = analytics_service.get_total_available_room_nights(start_date, end_date)
        expected_revpar = round(500 / total_available_nights, 2) if total_available_nights else 0.0
        actual_revpar = analytics_service.calculate_revpar(start_date, end_date)
        assert actual_revpar == expected_revpar 