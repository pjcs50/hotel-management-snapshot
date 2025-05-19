"""
Performance tests for receptionist features.

This module tests the performance of receptionist features under load.
"""
import pytest
import time
from datetime import datetime, date, timedelta
import random
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.user import User
from app.models.folio_item import FolioItem
from app.models.payment import Payment
from app.services.dashboard_service import DashboardService
from flask import url_for


@pytest.fixture
def large_dataset(db_session):
    """Create a large dataset for performance testing."""
    # Create room types
    room_types = []
    for i, name in enumerate(["Standard", "Deluxe", "Suite", "Executive", "Presidential"]):
        rt = RoomType(name=f"{name} Room", base_rate=100.0 * (i + 1), capacity=i + 1)
        db_session.add(rt)
        db_session.commit()
        room_types.append(rt)
    
    # Create rooms (100 rooms)
    rooms = []
    for i in range(1, 101):
        floor = i // 10 + 1
        room_num = i % 10
        room_type_id = room_types[min(floor - 1, len(room_types) - 1)].id
        
        # Distribute statuses
        if i % 5 == 0:
            status = Room.STATUS_OCCUPIED
        elif i % 7 == 0:
            status = Room.STATUS_CLEANING
        elif i % 11 == 0:
            status = Room.STATUS_MAINTENANCE
        else:
            status = Room.STATUS_AVAILABLE
            
        room = Room(room_type_id=room_type_id, number=f"{floor}0{room_num}", status=status)
        db_session.add(room)
        rooms.append(room)
    db_session.commit()
    
    # Create a receptionist
    receptionist = User(username="perf_recept", email="perf_recept@example.com", role="receptionist")
    receptionist.set_password("password")
    db_session.add(receptionist)
    db_session.commit()
    
    # Create customers (50 customers)
    customers = []
    for i in range(1, 51):
        user = User(username=f"cust{i}", email=f"customer{i}@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        customer = Customer(
            user_id=user.id,
            name=f"Test Customer {i}",
            email=f"customer{i}@example.com",
            phone=f"555-{i:03d}-{i*2:04d}"
        )
        db_session.add(customer)
        customers.append(customer)
    db_session.commit()
    
    # Create bookings (200 bookings)
    today = date.today()
    bookings = []
    
    # Past bookings (checked out)
    for i in range(50):
        check_in = today - timedelta(days=random.randint(10, 100))
        check_out = check_in + timedelta(days=random.randint(1, 7))
        customer = random.choice(customers)
        room = random.choice(rooms)
        
        booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in,
            check_out_date=check_out,
            status=Booking.STATUS_CHECKED_OUT,
            num_guests=random.randint(1, 4),
            total_price=random.randint(100, 1000),
            confirmation_code=f"PERF{i:03d}"
        )
        db_session.add(booking)
        bookings.append(booking)
    
    # Current bookings (checked in)
    for i in range(50, 100):
        check_in = today - timedelta(days=random.randint(1, 5))
        check_out = today + timedelta(days=random.randint(1, 5))
        customer = random.choice(customers)
        
        # Find an occupied room
        for room in rooms:
            if room.status == Room.STATUS_OCCUPIED:
                break
        
        booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in,
            check_out_date=check_out,
            status=Booking.STATUS_CHECKED_IN,
            num_guests=random.randint(1, 4),
            total_price=random.randint(100, 1000),
            confirmation_code=f"PERF{i:03d}"
        )
        db_session.add(booking)
        bookings.append(booking)
        
        # Add some folio items to each booking - ONLY if booking was added
        if booking.id: # Ensure booking has an ID, meaning it was committed
            for j in range(random.randint(2, 5)):
                charge_type = random.choice(FolioItem.TYPE_CHOICES)
                folio_item = FolioItem(
                    booking_id=booking.id,
                    date=today - timedelta(days=random.randint(0, 3)),
                    description=f"{charge_type} charge",
                    charge_amount=random.randint(10, 200),
                    charge_type=charge_type,
                    staff_id=receptionist.id
                )
                db_session.add(folio_item)
        
            # Add some payments - ONLY if booking was added
            payment = Payment(
                booking_id=booking.id,
                amount=booking.total_price * 0.5,  # 50% payment
                payment_type="Credit Card",
                payment_date=check_in,
                reference=f"PERF-PMT-{i}"
            )
            db_session.add(payment)
    
    # Future bookings (reserved)
    for i in range(100, 150):
        check_in = today + timedelta(days=random.randint(1, 30))
        check_out = check_in + timedelta(days=random.randint(1, 7))
        customer = random.choice(customers)
        
        # Find an available room
        for room in rooms:
            if room.status == Room.STATUS_AVAILABLE:
                break
        
        booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in,
            check_out_date=check_out,
            status=Booking.STATUS_RESERVED,
            num_guests=random.randint(1, 4),
            total_price=random.randint(100, 1000),
            confirmation_code=f"PERF{i:03d}"
        )
        db_session.add(booking)
        bookings.append(booking)
    
    # Today's check-ins
    for i in range(150, 175):
        check_out = today + timedelta(days=random.randint(1, 7))
        customer = random.choice(customers)
        
        # Find an available room
        for room in rooms:
            if room.status == Room.STATUS_AVAILABLE:
                break
        
        booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=today,
            check_out_date=check_out,
            status=Booking.STATUS_RESERVED,
            num_guests=random.randint(1, 4),
            total_price=random.randint(100, 1000),
            confirmation_code=f"PERF{i:03d}"
        )
        db_session.add(booking)
        bookings.append(booking)
    
    # Today's check-outs
    for i in range(175, 200):
        check_in = today - timedelta(days=random.randint(1, 7))
        customer = random.choice(customers)
        
        # Find an occupied room
        for room in rooms:
            if room.status == Room.STATUS_OCCUPIED:
                break
        
        booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in,
            check_out_date=today,
            status=Booking.STATUS_CHECKED_IN,
            num_guests=random.randint(1, 4),
            total_price=random.randint(100, 1000),
            confirmation_code=f"PERF{i:03d}"
        )
        db_session.add(booking)
        bookings.append(booking)
    
    db_session.commit()
    
    return {
        "room_types": room_types,
        "rooms": rooms,
        "receptionist": receptionist,
        "customers": customers,
        "bookings": bookings
    }


class TestDashboardPerformance:
    """Test the performance of the receptionist dashboard."""
    
    def test_dashboard_metrics_performance(self, db_session, large_dataset):
        """Test the performance of getting dashboard metrics."""
        dashboard_service = DashboardService(db_session)
        
        # Time how long it takes to get receptionist metrics
        start_time = time.time()
        metrics = dashboard_service.get_receptionist_metrics()
        end_time = time.time()
        
        # Verify all metrics are present
        assert "todays_checkins" in metrics
        assert "todays_checkouts" in metrics
        assert "occupied_rooms" in metrics
        assert "available_rooms" in metrics
        assert "room_status" in metrics
        assert "todays_checkin_list" in metrics
        assert "todays_checkout_list" in metrics
        assert "in_house_guests" in metrics
        
        # Check performance - should be reasonably fast (under 1 second)
        execution_time = end_time - start_time
        print(f"\nDashboard metrics execution time: {execution_time:.4f} seconds")
        assert execution_time < 1.0, "Dashboard metrics should load in under 1 second"


class TestGuestListPerformance:
    """Test the performance of guest list operations."""
    
    def test_guest_list_performance(self, client, large_dataset):
        """Test the performance of loading the guest list."""
        # Login as receptionist
        receptionist = large_dataset["receptionist"]
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Time how long it takes to load the guest list
        start_time = time.time()
        response = client.get('/receptionist/guest-list')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Check performance - should be reasonably fast
        execution_time = end_time - start_time
        print(f"\nGuest list page load time: {execution_time:.4f} seconds")
        assert execution_time < 2.0, "Guest list should load in under 2 seconds"
    
    def test_guest_search_performance(self, client, large_dataset):
        """Test the performance of searching for guests."""
        # Login as receptionist
        receptionist = large_dataset["receptionist"]
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Time how long it takes to search for guests
        start_time = time.time()
        response = client.get('/receptionist/guest-list?q=Customer')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Check performance
        execution_time = end_time - start_time
        print(f"\nGuest search execution time: {execution_time:.4f} seconds")
        assert execution_time < 1.0, "Guest search should complete in under 1 second"


class TestBookingPerformance:
    """Test the performance of booking-related operations."""
    
    def test_bookings_list_performance(self, client, large_dataset):
        """Test the performance of loading the bookings list."""
        # Login as receptionist
        receptionist = large_dataset["receptionist"]
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Time how long it takes to load the bookings list
        start_time = time.time()
        response = client.get('/receptionist/bookings')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Check performance
        execution_time = end_time - start_time
        print(f"\nBookings list page load time: {execution_time:.4f} seconds")
        assert execution_time < 2.0, "Bookings list should load in under 2 seconds"
    
    def test_checkin_checkout_lists_performance(self, client, large_dataset):
        """Test the performance of check-in and check-out lists."""
        # Login as receptionist
        receptionist = large_dataset["receptionist"]
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Time how long it takes to load the check-in list
        start_time = time.time()
        response = client.get('/receptionist/check-in')
        end_time = time.time()
        
        assert response.status_code == 200
        
        checkin_time = end_time - start_time
        print(f"\nCheck-in list page load time: {checkin_time:.4f} seconds")
        assert checkin_time < 1.0, "Check-in list should load in under 1 second"
        
        # Time how long it takes to load the check-out list
        start_time = time.time()
        response = client.get('/receptionist/check-out')
        end_time = time.time()
        
        assert response.status_code == 200
        
        checkout_time = end_time - start_time
        print(f"\nCheck-out list page load time: {checkout_time:.4f} seconds")
        assert checkout_time < 1.0, "Check-out list should load in under 1 second"


class TestRoomInventoryPerformance:
    """Test the performance of room inventory management."""
    
    def test_room_inventory_performance(self, client, large_dataset):
        """Test the performance of loading the room inventory."""
        # Login as receptionist
        receptionist = large_dataset["receptionist"]
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Time how long it takes to load the room inventory
        start_time = time.time()
        response = client.get('/receptionist/room-inventory')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Check performance
        execution_time = end_time - start_time
        print(f"\nRoom inventory page load time: {execution_time:.4f} seconds")
        assert execution_time < 2.0, "Room inventory should load in under 2 seconds"
        
        # Verify all rooms are displayed
        for room in large_dataset["rooms"][:10]:  # Check just first 10 to avoid too many assertions
            assert room.number.encode() in response.data 