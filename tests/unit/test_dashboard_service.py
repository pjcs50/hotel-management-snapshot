'''
Unit tests for the DashboardService.
'''
import pytest
from datetime import datetime, date, timedelta
from app.services.dashboard_service import DashboardService
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.user import User # Import User model

# Helper to create a room type
def _create_room_type(db_session, name="Standard Room", base_rate=100.0):
    rt = RoomType(name=name, base_rate=base_rate, capacity=2)
    db_session.add(rt)
    db_session.commit()
    return rt

# Helper to create a room
def _create_room(db_session, room_type_id, room_number_str, status='Available'):
    room = Room(room_type_id=room_type_id, number=room_number_str, status=status)
    db_session.add(room)
    db_session.commit()
    return room

# Helper to create a customer
def _create_customer(db_session, user_id, name="Test Customer"):
    # Ensure a user exists for the customer
    user = db_session.get(User, user_id)
    if not user:
        user = User(id=user_id, username=f'user{user_id}', email=f'user{user_id}@example.com', role='customer')
        user.set_password('password') # Set a password for the user
        db_session.add(user)
        db_session.commit()

    customer = Customer(user_id=user_id, name=name, email=f'{name.lower().replace(" ", "_")}@example.com')
    db_session.add(customer)
    db_session.commit()
    return customer

# Helper to create a booking
def _create_booking(db_session, room_id, customer_id, check_in, check_out, status='Reserved', total_price=100.0):
    booking = Booking(
        room_id=room_id,
        customer_id=customer_id,
        check_in_date=check_in,
        check_out_date=check_out,
        status=status,
        total_price=total_price,
        confirmation_code=f'CONF-{datetime.now().timestamp()}' # Add confirmation code
    )
    db_session.add(booking)
    db_session.commit()
    return booking

@pytest.fixture
def dashboard_service(db_session):
    return DashboardService(db_session)

@pytest.fixture
def setup_data_for_dashboard(db_session):
    today = date.today()

    # Room Types
    rt1 = _create_room_type(db_session, "Single")
    rt2 = _create_room_type(db_session, "Double")

    # Rooms
    room101 = _create_room(db_session, rt1.id, "101", status='Available')
    room102 = _create_room(db_session, rt1.id, "102", status='Occupied')
    room201 = _create_room(db_session, rt2.id, "201", status='Available')
    room202 = _create_room(db_session, rt2.id, "202", status='Maintenance')

    # Customers (Ensure unique user_ids, e.g., starting from 1)
    customer1 = _create_customer(db_session, 1, "Alice Smith")
    customer2 = _create_customer(db_session, 2, "Bob Johnson")
    customer3 = _create_customer(db_session, 3, "Carol Williams")

    # Bookings
    # 1. Check-in today for Alice Smith - Changed to 'Checked In' for active_booking test
    _create_booking(db_session, room101.id, customer1.id, today, today + timedelta(days=2), status=Booking.STATUS_CHECKED_IN)
    # 2. Check-out today
    _create_booking(db_session, room102.id, customer2.id, today - timedelta(days=3), today, status=Booking.STATUS_CHECKED_IN)
    # 3. Ongoing booking (Checked In)
    _create_booking(db_session, room201.id, customer3.id, today - timedelta(days=1), today + timedelta(days=1), status=Booking.STATUS_CHECKED_IN)
    # 4. Future booking
    _create_booking(db_session, room101.id, customer1.id, today + timedelta(days=5), today + timedelta(days=7), status=Booking.STATUS_RESERVED)
    # 5. Past booking (Checked Out)
    _create_booking(db_session, room202.id, customer2.id, today - timedelta(days=10), today - timedelta(days=8), status=Booking.STATUS_CHECKED_OUT)
    
    return {"c1": customer1, "c2": customer2, "c3": customer3}


class TestReceptionistDashboardMetrics:
    def test_get_receptionist_dashboard_metrics(self, dashboard_service, setup_data_for_dashboard):
        metrics = dashboard_service.get_receptionist_metrics()

        # Alice's booking is now STATUS_CHECKED_IN (was Reserved for today).
        # The metric counts STATUS_RESERVED for today's check-ins.
        assert metrics['todays_checkins'] == 0 
        assert metrics['todays_checkouts'] == 1 # Bob Johnson is STATUS_CHECKED_IN and check_out_date is today.
        
        # The service counts Room.status directly. Bookings in fixture don't alter Room.status.
        # room101 (Available), room102 (Occupied), room201 (Available), room202 (Maintenance)
        assert metrics['occupied_rooms'] == 1 # Only room102 is initially Occupied.
        assert metrics['available_rooms'] == 2 # room101 and room201 are initially Available.
        
        assert metrics['tomorrows_checkins'] == 0 # No 'Reserved' bookings for tomorrow in fixture.
        
        assert 'recent_bookings' in metrics
        assert 'room_status' in metrics

    def test_receptionist_metrics_no_data(self, dashboard_service):
        metrics = dashboard_service.get_receptionist_metrics()
        assert metrics['todays_checkins'] == 0
        assert metrics['todays_checkouts'] == 0
        assert metrics['occupied_rooms'] == 0
        assert metrics['available_rooms'] == 0
        assert metrics['tomorrows_checkins'] == 0
        assert 'recent_bookings' in metrics and not metrics['recent_bookings']
        assert 'room_status' in metrics and not metrics['room_status']


class TestCustomerDashboardMetrics:
    def test_get_customer_dashboard_metrics(self, dashboard_service, setup_data_for_dashboard):
        customer1 = setup_data_for_dashboard["c1"]
        metrics = dashboard_service.get_customer_metrics(customer1.id)

        assert metrics['booking_count'] == 2 # One current (Checked In), one future (Reserved) for Alice
        assert metrics['active_booking'] is not None
        assert metrics['active_booking']['check_in_date'] == date.today().strftime("%Y-%m-%d")
        assert len(metrics['upcoming_bookings']) == 1
        # Loyalty points tests would require LoyaltyTier and LoyaltyTransaction models & data
        # For now, just checking if the keys exist
        assert 'customer_name' in metrics
        assert 'profile_status' in metrics

    def test_get_customer_metrics_no_bookings(self, dashboard_service, db_session):
        # Create a customer with no bookings
        no_booking_user = User(username='nobookuser', email='nobook@example.com', role='customer')
        no_booking_user.set_password('password')
        db_session.add(no_booking_user)
        db_session.commit()
        customer_no_bookings = _create_customer(db_session, no_booking_user.id, "No Booking Nelly")
        
        metrics = dashboard_service.get_customer_metrics(customer_no_bookings.id)
        assert metrics['booking_count'] == 0
        assert metrics['active_booking'] is None
        assert len(metrics['upcoming_bookings']) == 0

    def test_get_customer_metrics_only_past_bookings(self, dashboard_service, setup_data_for_dashboard):
        customer2 = setup_data_for_dashboard["c2"] # Bob Johnson has only past and current_checkout_today
        # Modify Bob's current booking to be in the past for this specific test
        booking_to_modify = Booking.query.filter(
            Booking.customer_id == customer2.id, 
            Booking.check_out_date == date.today()
        ).first()
        if booking_to_modify:
            booking_to_modify.check_in_date = date.today() - timedelta(days=5)
            booking_to_modify.check_out_date = date.today() - timedelta(days=3)
            booking_to_modify.status = Booking.STATUS_CHECKED_OUT # Explicitly set status
            dashboard_service.db_session.commit() # Use dashboard_service.db_session

        metrics = dashboard_service.get_customer_metrics(customer2.id)
        assert metrics['booking_count'] == 2 # He has two bookings in setup, one now modified to be past.
        assert metrics['active_booking'] is None
        assert len(metrics['upcoming_bookings']) == 0

# Add more tests for edge cases, different booking statuses, etc. 

class TestManagerDashboardMetrics:
    def test_get_manager_metrics_structure_and_kpis(self, dashboard_service, setup_data_for_dashboard, db_session):
        """Test the structure of manager metrics and presence of ADR/RevPAR."""
        # setup_data_for_dashboard creates some rooms and bookings.
        # Ensure there are rooms for KPI calculations
        if not db_session.query(Room).first():
            rt = _create_room_type(db_session, "Test Room Type For Manager", 100.0)
            _create_room(db_session, rt.id, "MGR01")
            _create_room(db_session, rt.id, "MGR02")
            db_session.commit()

        metrics = dashboard_service.get_manager_metrics()

        assert "occupancy_rate" in metrics
        assert "customer_count" in metrics
        assert "room_status" in metrics
        assert "total_rooms" in metrics
        assert "monthly_bookings" in metrics
        assert "staff_counts" in metrics
        assert "historical_occupancy" in metrics
        assert "top_performers" in metrics
        assert "alerts" in metrics
        assert "booking_forecast" in metrics
        assert "maintenance_status" in metrics
        assert "housekeeping_status" in metrics
        
        # Test for new KPIs
        assert "adr" in metrics
        assert "revpar" in metrics
        assert isinstance(metrics["adr"], float)
        assert isinstance(metrics["revpar"], float)

        # Basic value checks (exact values depend on AnalyticsService logic and period)
        # For a 30-day period with some data from setup_data_for_dashboard (current and past month data)
        # we expect ADR and RevPAR to be non-negative. If bookings exist in the last 30 days, they should be positive.
        assert metrics["adr"] >= 0.0
        assert metrics["revpar"] >= 0.0

    def test_get_manager_metrics_no_data_kpis(self, dashboard_service, db_session):
        """Test manager metrics ADR/RevPAR when there is no booking/room data."""
        # Ensure no bookings exist that could influence a 30-day ADR/RevPAR from today
        today = date.today()
        thirty_days_ago = today - timedelta(days=29)
        bookings_in_period = db_session.query(Booking).filter(
            Booking.check_in_date <= today,
            Booking.check_out_date > thirty_days_ago
        ).all()
        for b in bookings_in_period:
            db_session.delete(b)
        db_session.commit()
        
        # If there are no rooms, total_available_room_nights will be 0, so RevPAR is 0
        # If there are no rooms sold (no relevant bookings), ADR is 0
        metrics = dashboard_service.get_manager_metrics()
        assert metrics["adr"] == 0.0
        assert metrics["revpar"] == 0.0 