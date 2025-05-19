"""
Unit tests for the receptionist routes.

This module tests the routes and controllers for receptionist operations.
"""
import pytest
from datetime import datetime, date, timedelta
from flask import url_for
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.user import User
from app.models.folio_item import FolioItem
from app.models.payment import Payment
from app.models.room_status_log import RoomStatusLog


@pytest.fixture
def receptionist_user_id(db_session):
    """Create a test receptionist user and return its ID."""
    user = User(
        username='receptionist',
        email='receptionist@example.com',
        role='receptionist'
    )
    user.set_password('password')
    db_session.add(user)
    db_session.commit()
    return user.id


@pytest.fixture
def room_types(db_session):
    """Create test room types."""
    standard = RoomType(name="Standard Room", base_rate=100.0, capacity=2)
    deluxe = RoomType(name="Deluxe Room", base_rate=150.0, capacity=3)
    suite = RoomType(name="Suite", base_rate=250.0, capacity=4)
    
    db_session.add_all([standard, deluxe, suite])
    db_session.commit()
    return {"standard": standard, "deluxe": deluxe, "suite": suite}


@pytest.fixture
def rooms(db_session, room_types):
    """Create test rooms with various statuses."""
    rooms = []
    
    # Standard rooms
    rooms.append(Room(room_type_id=room_types["standard"].id, number="101", status=Room.STATUS_AVAILABLE))
    rooms.append(Room(room_type_id=room_types["standard"].id, number="102", status=Room.STATUS_OCCUPIED))
    rooms.append(Room(room_type_id=room_types["standard"].id, number="103", status=Room.STATUS_CLEANING))
    
    # Deluxe rooms
    rooms.append(Room(room_type_id=room_types["deluxe"].id, number="201", status=Room.STATUS_AVAILABLE))
    rooms.append(Room(room_type_id=room_types["deluxe"].id, number="202", status=Room.STATUS_MAINTENANCE))
    
    # Suite
    rooms.append(Room(room_type_id=room_types["suite"].id, number="301", status=Room.STATUS_AVAILABLE))
    
    db_session.add_all(rooms)
    db_session.commit()
    return rooms


@pytest.fixture
def customer_ids(db_session):
    """Create test customers and return their IDs."""
    user1 = User(username='customer1', email='customer1@example.com', role='customer')
    user1.set_password('password')
    user2 = User(username='customer2', email='customer2@example.com', role='customer')
    user2.set_password('password')
    user3 = User(username='customer3', email='customer3@example.com', role='customer')
    user3.set_password('password')
    
    db_session.add_all([user1, user2, user3])
    db_session.commit()
    
    c1 = Customer(user_id=user1.id, name="Jane Smith", email="jane@example.com", phone="555-123-4567")
    c2 = Customer(user_id=user2.id, name="John Doe", email="john@example.com", phone="555-987-6543")
    c3 = Customer(user_id=user3.id, name="Alice Johnson", email="alice@example.com", phone="555-555-5555")
    
    db_session.add_all([c1, c2, c3])
    db_session.commit()
    return {"c1_id": c1.id, "c2_id": c2.id, "c3_id": c3.id}


@pytest.fixture
def bookings(db_session, rooms, customer_ids):
    """Create test bookings with various statuses."""
    today = date.today()
    
    bookings_list = [
        Booking(
            room_id=rooms[0].id,
            customer_id=customer_ids["c1_id"],
            check_in_date=today,
            check_out_date=today + timedelta(days=3),
            status=Booking.STATUS_RESERVED,
            num_guests=2,
            total_price=300.0,
            confirmation_code="CONF001"
        ),
        Booking(
            room_id=rooms[1].id,
            customer_id=customer_ids["c2_id"],
            check_in_date=today - timedelta(days=2),
            check_out_date=today,
            status=Booking.STATUS_CHECKED_IN,
            num_guests=1,
            total_price=200.0,
            confirmation_code="CONF002"
        ),
        Booking(
            room_id=rooms[3].id,
            customer_id=customer_ids["c3_id"],
            check_in_date=today - timedelta(days=1),
            check_out_date=today + timedelta(days=2),
            status=Booking.STATUS_CHECKED_IN,
            num_guests=3,
            total_price=450.0,
            confirmation_code="CONF003"
        ),
        Booking(
            room_id=rooms[5].id,
            customer_id=customer_ids["c1_id"],
            check_in_date=today + timedelta(days=7),
            check_out_date=today + timedelta(days=10),
            status=Booking.STATUS_RESERVED,
            num_guests=2,
            total_price=750.0,
            confirmation_code="CONF004"
        ),
        Booking(
            room_id=rooms[0].id,
            customer_id=customer_ids["c2_id"],
            check_in_date=today - timedelta(days=10),
            check_out_date=today - timedelta(days=8),
            status=Booking.STATUS_CHECKED_OUT,
            num_guests=2,
            total_price=200.0,
            confirmation_code="CONF005"
        )
    ]
    
    db_session.add_all(bookings_list)
    db_session.commit()
    return bookings_list


class TestReceptionistDashboard:
    """Test cases for the receptionist dashboard."""
    
    def test_dashboard_access(self, client, receptionist_user_id):
        """Test receptionist can access the dashboard."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        response = client.get(url_for('receptionist.dashboard'))
        assert response.status_code == 200
        assert b'Receptionist Dashboard' in response.data
    
    def test_dashboard_metrics(self, client, receptionist_user_id, bookings):
        """Test dashboard displays correct metrics."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        response = client.get(url_for('receptionist.dashboard'))
        assert response.status_code == 200
        
        # Check essential metrics in the page
        assert b"Today's Check-ins" in response.data
        assert b"Today's Check-outs" in response.data
        assert b"Room Status" in response.data
        assert b"In-House Guests" in response.data
    
    def test_dashboard_unauthorized_access(self, client, db_session):
        """Test unauthorized users cannot access the dashboard."""
        # Create a customer user
        user = User(username='customer', email='customer@example.com', role='customer')
        user.set_password('password')
        db_session.add(user)
        db_session.commit()
        
        # Login as customer
        client.post(url_for('auth.login'), data={'email': user.email, 'password': 'password'}, follow_redirects=True)
        response = client.get(url_for('receptionist.dashboard'))
        assert response.status_code == 403  # Forbidden
    
    def test_room_inventory_access(self, client, receptionist_user_id, rooms):
        """Test receptionist can access room inventory."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        response = client.get(url_for('receptionist.room_inventory'))
        assert response.status_code == 200
        assert b'Room Inventory Management' in response.data
        
        # Verify room numbers appear in the response
        for room in rooms:
            assert room.number.encode() in response.data


class TestGuestManagement:
    """Test cases for guest management features."""
    
    def test_guest_list(self, client, receptionist_user_id, customer_ids):
        """Test guest list display."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        response = client.get(url_for('receptionist.guest_list'))
        assert response.status_code == 200
        
        for c_id_key, c_id_val in customer_ids.items():
            customer = Customer.query.get(c_id_val)
            assert customer is not None
            assert customer.name.encode() in response.data
    
    def test_guest_details(self, client, receptionist_user_id, customer_ids):
        """Test viewing guest details."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        customer_c1 = Customer.query.get(customer_ids["c1_id"])
        assert customer_c1 is not None

        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        response = client.get(url_for('receptionist.view_guest', customer_id=customer_c1.id))
        assert response.status_code == 200
        assert customer_c1.name.encode() in response.data
        assert customer_c1.email.encode() in response.data
    
    def test_add_guest_note(self, client, receptionist_user_id, customer_ids):
        """Test adding notes to a guest profile."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        customer_c1 = Customer.query.get(customer_ids["c1_id"])
        assert customer_c1 is not None

        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        note_text = "Test note for customer"
        response = client.post(url_for('receptionist.add_guest_note', customer_id=customer_c1.id), 
                               data={'note': note_text},
                               follow_redirects=True)
        assert response.status_code == 200
        
        # Verify the note appears on the customer details page
        assert note_text.encode() in response.data
    
    def test_edit_guest(self, client, receptionist_user_id, customer_ids, db_session):
        """Test editing guest information."""
        _receptionist = db_session.get(User, receptionist_user_id)
        assert _receptionist is not None
        receptionist = db_session.merge(_receptionist)
        assert receptionist.email == 'receptionist@example.com'

        _customer_c1 = db_session.get(Customer, customer_ids["c1_id"])
        assert _customer_c1 is not None
        customer_c1 = db_session.merge(_customer_c1)
        assert customer_c1.name == "Jane Smith"

        # Login as receptionist
        login_response = client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        assert login_response.status_code == 200
        
        # Get the edit guest form
        response = client.get(url_for('receptionist.edit_guest', customer_id=customer_c1.id))
        assert response.status_code == 200
        
        new_name = "Jane Smith-Johnson"
        new_email = "jane.updated@example.com"
        response = client.post(
            url_for('receptionist.edit_guest', customer_id=customer_c1.id),
            data={
                'name': new_name,
                'email': new_email,
                'phone': customer_c1.phone,
                'address': 'New Address',
                'id_type': 'Passport',
                'id_number': 'A12345678',
                'emergency_contact': '555-999-8888'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        db_session.refresh(customer_c1)
        assert customer_c1.name == new_name
        assert customer_c1.email == new_email
        assert customer_c1.id_type == 'Passport'


class TestCheckInCheckOut:
    """Test cases for check-in and check-out procedures."""
    
    def test_checkin_list(self, client, receptionist_user_id, bookings):
        """Test viewing the check-in list."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        response = client.get(url_for('receptionist.check_in'))
        assert response.status_code == 200
    
    def test_checkin_process(self, client, receptionist_user_id, bookings, db_session):
        """Test the check-in process for a guest."""
        receptionist = db_session.get(User, receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Get the check-in form for the first booking (today's check-in)
        booking_id = bookings[0].id
        response = client.get(url_for('receptionist.check_in_guest', booking_id=booking_id))
        assert response.status_code == 200
        
        # Complete the check-in process
        response = client.post(
            url_for('receptionist.check_in_guest', booking_id=booking_id),
            data={
                'payment_amount': '100.00',
                'payment_type': 'Credit Card',
                'special_notes': 'Checked in by test'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify the booking status changed
        db_session.refresh(bookings[0])
        assert bookings[0].status == Booking.STATUS_CHECKED_IN
        
        # Verify room status changed to occupied
        room = Room.query.get(bookings[0].room_id)
        assert room.status == Room.STATUS_OCCUPIED
    
    def test_checkout_list(self, client, receptionist_user_id, bookings):
        """Test viewing the check-out list."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        response = client.get(url_for('receptionist.check_out'))
        assert response.status_code == 200
    
    def test_checkout_process(self, client, receptionist_user_id, bookings, db_session):
        """Test the check-out process for a guest."""
        receptionist = db_session.get(User, receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Get the check-out form for the second booking (today's check-out)
        booking_to_checkout = bookings[1]
        
        response = client.get(url_for('receptionist.check_out_guest', booking_id=booking_to_checkout.id))
        assert response.status_code == 200
        
        # Complete the check-out process
        response = client.post(
            url_for('receptionist.check_out_guest', booking_id=booking_to_checkout.id),
            data={
                'payment_amount': booking_to_checkout.balance_due,
                'payment_type': 'Credit Card',
                'checkout_notes': 'Checked out by test'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify the booking status changed
        db_session.refresh(bookings[1])
        assert bookings[1].status == Booking.STATUS_CHECKED_OUT
        
        # Verify room status changed to needs cleaning
        room = Room.query.get(bookings[1].room_id)
        assert room.status == Room.STATUS_CLEANING


class TestRoomManagement:
    """Test cases for room management features."""
    
    def test_mark_room_clean(self, client, receptionist_user_id, rooms, db_session):
        """Test marking a room as clean."""
        receptionist = db_session.get(User, receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Select a room with Needs Cleaning status
        room = rooms[2]  # Room 103 has STATUS_CLEANING
        assert room.status == Room.STATUS_CLEANING
        
        # Mark room as clean
        response = client.post(
            url_for('receptionist.mark_room_clean', room_id=room.id),
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify room status changed to available
        db_session.refresh(room)
        assert room.status == Room.STATUS_AVAILABLE
        
        # Verify a room status log entry was created
        log_entry = RoomStatusLog.query.filter_by(
            room_id=room.id,
            old_status=Room.STATUS_CLEANING,
            new_status=Room.STATUS_AVAILABLE
        ).first()
        assert log_entry is not None
    
    def test_mark_room_maintenance(self, client, receptionist_user_id, rooms, db_session):
        """Test marking a room for maintenance."""
        receptionist = db_session.get(User, receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Select an available room
        room = rooms[0]  # Room 101 is available
        assert room.status == Room.STATUS_AVAILABLE
        
        # Mark room for maintenance
        response = client.post(
            url_for('receptionist.mark_room_maintenance', room_id=room.id),
            data={'notes': 'Maintenance needed for test'},
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify room status changed to maintenance
        db_session.refresh(room)
        assert room.status == Room.STATUS_MAINTENANCE
    
    def test_room_history(self, client, receptionist_user_id, rooms):
        """Test viewing room history."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # View history for a room
        response = client.get(url_for('receptionist.room_history', room_id=rooms[0].id))
        assert response.status_code == 200
        assert b"Room History" in response.data
        assert rooms[0].number.encode() in response.data


class TestFolioAndPayments:
    """Test cases for folio and payment management."""
    
    def test_view_folio(self, client, receptionist_user_id, bookings):
        """Test viewing a booking folio."""
        receptionist = User.query.get(receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # View folio for a booking
        booking_to_view = bookings[2]
        response = client.get(url_for('receptionist.view_folio', booking_id=booking_to_view.id))
        assert response.status_code == 200
    
    def test_post_charge(self, client, receptionist_user_id, bookings, db_session):
        """Test posting a charge to a booking."""
        receptionist = db_session.get(User, receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Get the charge form
        response = client.get(url_for('receptionist.post_charge', booking_id=bookings[2].id))
        assert response.status_code == 200
        
        # Post a charge
        charge_data = {
            'charge_amount': '50.00',
            'charge_type': FolioItem.TYPE_ROOM_SERVICE,
            'description': 'Room service - dinner',
            'reference': 'RS123456'
        }
        response = client.post(
            url_for('receptionist.post_charge', booking_id=bookings[2].id),
            data=charge_data,
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify charge was added
        charge = FolioItem.query.filter_by(
            booking_id=bookings[2].id,
            description='Room service - dinner'
        ).first()
        assert charge is not None
        assert charge.charge_amount == 50.0
    
    def test_process_payment(self, client, receptionist_user_id, bookings, db_session):
        """Test processing a payment for a booking."""
        receptionist = db_session.get(User, receptionist_user_id)
        assert receptionist is not None
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Get the payment form
        response = client.get(url_for('receptionist.process_payment', booking_id=bookings[2].id))
        assert response.status_code == 200
        
        # Process a payment
        payment_data = {
            'payment_amount': '100.00',
            'payment_type': 'Credit Card',
            'reference': 'PMT123456'
        }
        response = client.post(
            url_for('receptionist.process_payment', booking_id=bookings[2].id),
            data=payment_data,
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify payment was added
        payment = Payment.query.filter_by(
            booking_id=bookings[2].id,
            reference='PMT123456'
        ).first()
        assert payment is not None
        assert payment.amount == 100.0 