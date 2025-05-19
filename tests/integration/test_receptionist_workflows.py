"""
Integration tests for receptionist workflows.

This module tests complete receptionist workflows involving multiple features.
"""
import pytest
from datetime import datetime, date, timedelta
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer
from app.models.user import User
from app.models.folio_item import FolioItem
from app.models.payment import Payment
from app.models.room_status_log import RoomStatusLog
from flask import url_for


@pytest.fixture
def setup_test_data(db_session):
    """Set up test data for integration tests."""
    # Create a room type
    room_type = RoomType(name="Standard", base_rate=100.0, capacity=2)
    db_session.add(room_type)
    db_session.commit()
    
    # Create a room
    room = Room(room_type_id=room_type.id, number="101", status=Room.STATUS_AVAILABLE)
    db_session.add(room)
    db_session.commit()
    
    # Create a receptionist user
    receptionist = User(username="receptionist", email="receptionist@example.com", role="receptionist")
    receptionist.set_password("password")
    db_session.add(receptionist)
    db_session.commit()
    
    # Create a customer user
    user = User(username="customer", email="customer@example.com", role="customer")
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    
    # Create a customer
    customer = Customer(user_id=user.id, name="Test Customer", email="customer@example.com", phone="555-123-4567")
    db_session.add(customer)
    db_session.commit()
    
    # Create a booking (arriving today)
    today = date.today()
    booking = Booking(
        room_id=room.id,
        customer_id=customer.id,
        check_in_date=today,
        check_out_date=today + timedelta(days=3),
        status=Booking.STATUS_RESERVED,
        num_guests=2,
        total_price=300.0,
        confirmation_code="INT001"
    )
    db_session.add(booking)
    db_session.commit()
    
    return {
        "room_type": room_type,
        "room": room,
        "receptionist": receptionist,
        "customer": customer,
        "booking": booking
    }


class TestCompleteGuestStay:
    """Test the complete workflow of a guest stay from check-in to check-out."""
    
    def test_complete_guest_stay(self, client, db_session, setup_test_data):
        """Test the complete guest stay workflow."""
        # Get the test data
        receptionist = setup_test_data["receptionist"]
        customer = setup_test_data["customer"]
        booking = setup_test_data["booking"]
        room = setup_test_data["room"]
        
        # Login as receptionist
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # 1. View the check-in list to see today's arrivals
        response = client.get(url_for('receptionist.check_in'))
        assert response.status_code == 200
        assert b"Today's Check-ins" in response.data
        assert customer.name.encode() in response.data
        
        # 2. Process guest check-in
        response = client.post(
            url_for('receptionist.check_in_guest', booking_id=booking.id),
            data={
                'payment_amount': '150.00',  # Partial payment
                'payment_type': 'Credit Card',
                'special_notes': 'VIP guest, provide complimentary water'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify booking status changed to checked in
        db_session.refresh(booking)
        assert booking.status == Booking.STATUS_CHECKED_IN
        
        # Verify room status changed to occupied
        db_session.refresh(room)
        assert room.status == Room.STATUS_OCCUPIED
        
        # Verify payment was recorded
        payment = Payment.query.filter_by(booking_id=booking.id).first()
        assert payment is not None
        assert payment.amount == 150.0
        
        # 3. View the in-house guest in the dashboard
        response = client.get(url_for('receptionist.dashboard'))
        assert response.status_code == 200
        assert customer.name.encode() in response.data
        
        # 4. Post charges to the guest folio
        # Add room service charge
        response = client.post(
            url_for('receptionist.post_charge', booking_id=booking.id),
            data={
                'charge_amount': '45.00',
                'charge_type': FolioItem.TYPE_RESTAURANT,
                'description': 'Room service - breakfast',
                'reference': 'RS001'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Add minibar charge
        response = client.post(
            url_for('receptionist.post_charge', booking_id=booking.id),
            data={
                'charge_amount': '25.00',
                'charge_type': FolioItem.TYPE_MINIBAR,
                'description': 'Minibar items',
                'reference': 'MB001'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify charges were added
        charges = FolioItem.get_booking_charges(booking.id)
        assert len(charges) == 2
        assert sum(charge.charge_amount for charge in charges) == 70.0
        
        # 5. Process additional payment
        response = client.post(
            url_for('receptionist.process_payment', booking_id=booking.id),
            data={
                'payment_amount': '70.00',  # Pay for the charges
                'payment_type': 'Cash',
                'reference': 'CASH001'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # 6. Advance the booking to check-out day
        # Update the booking dates to simulate passage of time
        booking.check_in_date = date.today() - timedelta(days=3)
        booking.check_out_date = date.today()
        db_session.commit()
        
        # 7. View check-out list
        response = client.get(url_for('receptionist.check_out'))
        assert response.status_code == 200
        assert customer.name.encode() in response.data
        
        # 8. Process guest check-out with late check-out fee
        response = client.post(
            url_for('receptionist.check_out_guest', booking_id=booking.id),
            data={
                'payment_amount': '80.00',  # Remaining balance
                'payment_type': 'Credit Card',
                'late_checkout_hours': 2,
                'checkout_notes': 'Guest satisfied with stay'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify booking status changed to checked out
        db_session.refresh(booking)
        assert booking.status == Booking.STATUS_CHECKED_OUT
        assert booking.late_hours == 2
        
        # Verify room status changed to needs cleaning
        db_session.refresh(room)
        assert room.status == Room.STATUS_CLEANING
        
        # Verify late checkout fee was added
        late_fee = FolioItem.query.filter_by(
            booking_id=booking.id,
            charge_type=FolioItem.TYPE_LATE_CHECKOUT
        ).first()
        assert late_fee is not None
        
        # Verify final payment was recorded
        payments = Payment.query.filter_by(booking_id=booking.id).all()
        assert len(payments) == 3  # Initial, charges, and final payment
        assert sum(payment.amount for payment in payments) == 300.0
        
        # 9. Housekeeping process - mark room as clean
        response = client.post(
            url_for('receptionist.mark_room_clean', room_id=room.id),
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify room status changed to available
        db_session.refresh(room)
        assert room.status == Room.STATUS_AVAILABLE
        
        # 10. Verify room status log entries were created
        status_logs = RoomStatusLog.query.filter_by(room_id=room.id).all()
        assert len(status_logs) >= 3  # Check-in, Check-out, Clean


class TestGuestProfileAndBookingManagement:
    """Test guest profile and booking management workflows."""
    
    def test_create_and_manage_guest(self, client, db_session):
        """Test creating and managing a guest profile."""
        # Create a receptionist user
        receptionist = User(username="recept2", email="recept2@example.com", role="receptionist")
        receptionist.set_password("password")
        db_session.add(receptionist)
        db_session.commit()
        
        # Login as receptionist
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # Create a room type and room for later booking
        room_type = RoomType(name="Deluxe", base_rate=150.0, capacity=2)
        db_session.add(room_type)
        db_session.commit()
        
        room = Room(room_type_id=room_type.id, number="202", status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        db_session.commit()
        
        # 1. Create a customer user first
        user = User(username="newguest", email="newguest@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        # 2. Create a new guest with detailed information
        new_customer = Customer(
            user_id=user.id, 
            name="New Test Guest", 
            email="newguest@example.com",
            phone="555-987-6543",
            address="123 Test Street, Testville"
        )
        # Set document information using the property
        new_customer.documents = {
            "id_type": "Passport",
            "id_number": "AB123456"
        }
        db_session.add(new_customer)
        db_session.commit()
        
        # 3. Add notes to the guest profile
        response = client.post(
            url_for('receptionist.add_guest_note', customer_id=new_customer.id),
            data={'note': 'Guest prefers quiet rooms away from elevators'},
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify the note was added
        db_session.refresh(new_customer)
        assert "Guest prefers quiet rooms" in new_customer.notes
        
        # 4. Edit guest information
        response = client.post(
            url_for('receptionist.edit_guest', customer_id=new_customer.id),
            data={
                'name': new_customer.name,
                'email': new_customer.email,
                'phone': '555-111-2222',  # Updated phone
                'address': new_customer.address,
                'emergency_contact': '555-999-8888'  # Added emergency contact
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify the guest was updated
        db_session.refresh(new_customer)
        assert new_customer.phone == '555-111-2222'
        assert new_customer.emergency_contact == '555-999-8888'
        # Verify document info was retained/updated if edit form handles it
        # For now, let's assume the edit form doesn't clear it if not provided
        assert new_customer.documents.get("id_type") == "Passport"
        assert new_customer.documents.get("id_number") == "AB123456"
        
        # The subsequent steps would be:
        # 5. Create a booking for the guest (not directly testable here as the route isn't implemented yet)
        # 6. Process check-in, charges, payments etc. (as in previous test)


class TestRoomManagementWorkflow:
    """Test room management workflows."""
    
    def test_room_status_cycle(self, client, db_session):
        """Test the complete cycle of room status changes."""
        # Create a receptionist user
        receptionist = User(username="recept3", email="recept3@example.com", role="receptionist")
        receptionist.set_password("password")
        db_session.add(receptionist)
        db_session.commit()
        
        # Create a room type and room
        room_type = RoomType(name="Suite", base_rate=250.0, capacity=4)
        db_session.add(room_type)
        db_session.commit()
        
        room = Room(room_type_id=room_type.id, number="301", status=Room.STATUS_AVAILABLE)
        db_session.add(room)
        db_session.commit()
        
        # Login as receptionist
        client.post(url_for('auth.login'), data={'email': receptionist.email, 'password': 'password'}, follow_redirects=True)
        
        # 1. View room inventory
        response = client.get(url_for('receptionist.room_inventory'))
        assert response.status_code == 200
        assert room.number.encode() in response.data
        assert b"Available" in response.data
        
        # 2. Mark room for maintenance
        response = client.post(
            url_for('receptionist.mark_room_maintenance', room_id=room.id),
            data={'notes': 'Bathroom leak needs repair'},
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify status changed to maintenance
        db_session.refresh(room)
        assert room.status == Room.STATUS_MAINTENANCE
        
        # 3. View room history
        response = client.get(url_for('receptionist.room_history', room_id=room.id))
        assert response.status_code == 200
        assert b"Status History" in response.data
        assert b"Available" in response.data
        assert b"Under Maintenance" in response.data
        
        # 4. Mark room as available after maintenance
        response = client.post(
            url_for('receptionist.mark_room_available', room_id=room.id),
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify status changed to available
        db_session.refresh(room)
        assert room.status == Room.STATUS_AVAILABLE
        
        # 5. Create a customer for booking
        user = User(username="suite_guest", email="suite@example.com", role="customer")
        user.set_password("password")
        db_session.add(user)
        db_session.commit()
        
        customer = Customer(user_id=user.id, name="Suite Guest", email="suite@example.com")
        db_session.add(customer)
        db_session.commit()
        
        # 6. Create a booking for the room
        today = date.today()
        booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=Booking.STATUS_RESERVED,
            num_guests=2,
            total_price=250.0,
            confirmation_code="ROOM001"
        )
        db_session.add(booking)
        db_session.commit()
        
        # 7. Check in the guest
        response = client.post(
            url_for('receptionist.check_in_guest', booking_id=booking.id),
            data={
                'payment_amount': '250.00',
                'payment_type': 'Credit Card',
                'special_notes': 'Suite test check-in'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify room status changed to occupied
        db_session.refresh(room)
        assert room.status == Room.STATUS_OCCUPIED
        
        # 8. Check out the guest
        response = client.post(
            url_for('receptionist.check_out_guest', booking_id=booking.id),
            data={
                'payment_amount': '0.00',  # Already paid in full
                'payment_type': 'Credit Card',
                'checkout_notes': 'Suite test check-out'
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify room status changed to cleaning
        db_session.refresh(room)
        assert room.status == Room.STATUS_CLEANING
        
        # 9. Mark room as clean
        response = client.post(
            url_for('receptionist.mark_room_clean', room_id=room.id),
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify status changed back to available
        db_session.refresh(room)
        assert room.status == Room.STATUS_AVAILABLE
        
        # 10. Verify the full status history contains all changes
        status_logs = RoomStatusLog.query.filter_by(room_id=room.id).all()
        # Should have at least 5 status changes: 
        # Initial available → maintenance → available → occupied → cleaning → available
        assert len(status_logs) >= 5 