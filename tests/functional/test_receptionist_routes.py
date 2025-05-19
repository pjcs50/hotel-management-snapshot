"""
Tests for receptionist routes.

This module contains tests for the receptionist routes functionality.
"""

import pytest
from flask import url_for, session
from app.models.user import User
from app.models.customer import Customer
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from datetime import date, timedelta

# Helper to create a room
def _create_room(db_session, room_type_id, room_number_str, status='Available'):
    room = Room(room_type_id=room_type_id, number=room_number_str, status=status)
    db_session.add(room)
    db_session.commit()
    return room

# Helper to create a room type
def _create_room_type(db_session, name, base_rate=100.0):
    rt = RoomType(name=name, base_rate=base_rate, capacity=2)
    db_session.add(rt)
    db_session.commit()
    return rt

# Helper to create a customer
def _create_customer(db_session, user_id, name):
    customer = Customer(user_id=user_id, name=name, email=f'{name.lower().replace(" ", "_")}@example.com')
    db_session.add(customer)
    db_session.commit()
    return customer

# Helper to create a booking
def _create_booking(db_session, room_id, customer_id, check_in, check_out, status='Reserved'):
    booking = Booking(
        room_id=room_id,
        customer_id=customer_id,
        check_in_date=check_in,
        check_out_date=check_out,
        status=status,
        total_price=100.0 # Placeholder
    )
    db_session.add(booking)
    db_session.commit()
    return booking


@pytest.fixture
def sample_bookings_data(db_session, receptionist_user):
    # Create some room types
    rt1 = _create_room_type(db_session, "Standard Single")
    rt2 = _create_room_type(db_session, "Deluxe Double")

    # Create some rooms
    room101 = _create_room(db_session, rt1.id, "101")
    room202 = _create_room(db_session, rt2.id, "202")

    # Create some customers (need associated users first)
    cust_user1 = User(username='testcust1', email='testcust1@example.com', role='customer')
    cust_user1.set_password('password')
    cust_user2 = User(username='testcust2', email='testcust2@example.com', role='customer')
    cust_user2.set_password('password')
    db_session.add_all([cust_user1, cust_user2])
    db_session.commit()

    customer1 = _create_customer(db_session, cust_user1.id, "Alice Wonderland")
    customer2 = _create_customer(db_session, cust_user2.id, "Bob The Builder")

    today = date.today()
    # Booking 1: Reserved, in the future
    b1 = _create_booking(db_session, room101.id, customer1.id, today + timedelta(days=5), today + timedelta(days=7))
    # Booking 2: Checked In, current
    b2 = _create_booking(db_session, room202.id, customer2.id, today - timedelta(days=1), today + timedelta(days=2), status='Checked In')
    # Booking 3: Checked Out, past
    b3 = _create_booking(db_session, room101.id, customer1.id, today - timedelta(days=10), today - timedelta(days=8), status='Checked Out')
    return [b1, b2, b3]

@pytest.fixture
def sample_customers_data(db_session, receptionist_user):
    cust_userA = User(username='custA', email='custA@example.com', role='customer')
    cust_userA.set_password('password')
    cust_userB = User(username='custB', email='custB@example.com', role='customer')
    cust_userB.set_password('password')
    cust_userC = User(username='custC', email='custC@example.com', role='customer')
    cust_userC.set_password('password')
    db_session.add_all([cust_userA, cust_userB, cust_userC])
    db_session.commit()

    cust1 = _create_customer(db_session, cust_userA.id, "Charlie Brown")
    cust1.phone = "555-1234"
    cust1.address = "123 Main St"
    cust2 = _create_customer(db_session, cust_userB.id, "Diana Prince")
    cust2.phone = "555-5678"
    cust2.address = "456 Amazon Ave"
    cust3 = _create_customer(db_session, cust_userC.id, "Edward Scissorhands")
    db_session.commit()
    return [cust1, cust2, cust3]


class TestReceptionistDashboard:
    def test_receptionist_dashboard_loads(self, client, auth, receptionist_user, db_session):
        auth.login(receptionist_user.email, "password")
        response = client.get(url_for('receptionist.dashboard'))
        assert response.status_code == 200
        assert b"Receptionist Dashboard" in response.data
        # Check for a known metric box title, e.g., Today's Check-ins
        assert b"Today's Check-ins" in response.data

    def test_receptionist_dashboard_unauthorized(self, client, customer_user, auth):
        auth.login(customer_user.email, "password")
        response = client.get(url_for('receptionist.dashboard'))
        assert response.status_code == 403 # Forbidden

class TestReceptionistBookings:
    def test_bookings_page_loads(self, client, auth, receptionist_user, sample_bookings_data, db_session):
        auth.login(receptionist_user.email, "password")
        response = client.get(url_for('receptionist.bookings'))
        assert response.status_code == 200
        assert b"Bookings Management" in response.data
        assert sample_bookings_data[0].customer.name.encode() in response.data # Alice Wonderland
        assert sample_bookings_data[1].customer.name.encode() in response.data # Bob The Builder

    def test_bookings_filter_by_status(self, client, auth, receptionist_user, sample_bookings_data, db_session):
        auth.login(receptionist_user.email, "password")
        response = client.get(url_for('receptionist.bookings', status='Reserved'))
        assert response.status_code == 200
        assert b"Alice Wonderland" in response.data # Booking 1
        assert b"Bob The Builder" not in response.data # Booking 2 is Checked In

    def test_bookings_filter_by_guest_name(self, client, auth, receptionist_user, sample_bookings_data, db_session):
        auth.login(receptionist_user.email, "password")
        response = client.get(url_for('receptionist.bookings', q='Alice'))
        assert response.status_code == 200
        assert b"Alice Wonderland" in response.data
        assert b"Bob The Builder" not in response.data

    def test_bookings_filter_by_date_from(self, client, auth, receptionist_user, sample_bookings_data, db_session):
        auth.login(receptionist_user.email, "password")
        today = date.today()
        future_date_str = (today + timedelta(days=4)).strftime('%Y-%m-%d')
        response = client.get(url_for('receptionist.bookings', date_from=future_date_str))
        assert response.status_code == 200
        assert b"Alice Wonderland" in response.data # B1 is in 5 days
        assert b"Bob The Builder" not in response.data # B2 is current
        assert sample_bookings_data[2].customer.name.encode() not in response.data # B3 is past

    def test_bookings_pagination(self, client, auth, receptionist_user, db_session):
        auth.login(receptionist_user.email, "password")
        rt = _create_room_type(db_session, "PagTest Type")
        room = _create_room(db_session, rt.id, "PAG01")
        cust_user = User(username='pagecust', email='pagecust@example.com', role='customer')
        cust_user.set_password('password')
        db_session.add(cust_user)
        db_session.commit()
        customer = _create_customer(db_session, cust_user.id, "Page Test Customer")

        for i in range(25):
            _create_booking(db_session, room.id, customer.id, date.today() + timedelta(days=i+1), date.today() + timedelta(days=i+2), status='Reserved')
        
        response = client.get(url_for('receptionist.bookings', per_page=20))
        assert response.status_code == 200
        assert b"Page Test Customer" in response.data
        assert b"Next" in response.data # Pagination link

        response_page2 = client.get(url_for('receptionist.bookings', per_page=20, page=2))
        assert response_page2.status_code == 200
        assert b"Previous" in response_page2.data
        # Check if content on page 2 is different or less than 20 items

class TestReceptionistGuestList:
    def test_guest_list_page_loads(self, client, auth, receptionist_user, sample_customers_data, db_session):
        auth.login(receptionist_user.email, "password")
        response = client.get(url_for('receptionist.guest_list'))
        assert response.status_code == 200
        assert b"Guest Management" in response.data
        assert b"Charlie Brown" in response.data
        assert b"Diana Prince" in response.data

    def test_guest_list_search_name(self, client, auth, receptionist_user, sample_customers_data, db_session):
        auth.login(receptionist_user.email, "password")
        response = client.get(url_for('receptionist.guest_list', q='Charlie'))
        assert response.status_code == 200
        assert b"Charlie Brown" in response.data
        assert b"Diana Prince" not in response.data

    def test_guest_list_search_phone(self, client, auth, receptionist_user, sample_customers_data, db_session):
        auth.login(receptionist_user.email, "password")
        response = client.get(url_for('receptionist.guest_list', q='555-1234'))
        assert response.status_code == 200
        assert b"Charlie Brown" in response.data
        assert b"Diana Prince" not in response.data

    def test_guest_list_search_address_partial(self, client, auth, receptionist_user, sample_customers_data, db_session):
        auth.login(receptionist_user.email, "password")
        response = client.get(url_for('receptionist.guest_list', q='Amazon'))
        assert response.status_code == 200
        assert b"Diana Prince" in response.data
        assert b"Charlie Brown" not in response.data

    def test_guest_list_pagination(self, client, auth, receptionist_user, db_session):
        auth.login(receptionist_user.email, "password")
        for i in range(25):
            user = User(username=f'guestuser{i}', email=f'guest{i}@example.com', role='customer')
            user.set_password('password')
            db_session.add(user)
            db_session.commit()
            _create_customer(db_session, user.id, f"Guest Tester {i}")
        
        response = client.get(url_for('receptionist.guest_list', per_page=20))
        assert response.status_code == 200
        assert b"Guest Tester 0" in response.data
        assert b"Next" in response.data

        response_page2 = client.get(url_for('receptionist.guest_list', per_page=20, page=2))
        assert response_page2.status_code == 200
        assert b"Previous" in response_page2.data

    def test_guests_redirect_to_guest_list(self, client, auth, receptionist_user, db_session):
        auth.login(receptionist_user.email, "password")
        response = client.get(url_for('receptionist.guests'), follow_redirects=True)
        assert response.status_code == 200
        assert request.path == url_for('receptionist.guest_list')
        assert b"Guest Management" in response.data # Check content of guest_list page

# Placeholder tests for routes that are not yet fully implemented
@pytest.mark.parametrize("endpoint", [
    'receptionist.new_booking',
    'receptionist.search_guest',
    'receptionist.room_availability',
    'receptionist.check_in',
    'receptionist.check_out',
])
def test_receptionist_nyi_routes(client, auth, receptionist_user, endpoint):
    auth.login(receptionist_user.email, "password")
    response = client.get(url_for(endpoint))
    assert response.status_code == 200
    assert response.json['message'].endswith("Not yet implemented")