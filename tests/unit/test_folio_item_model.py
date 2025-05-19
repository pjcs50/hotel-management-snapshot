"""
Unit tests for the FolioItem model.

This module tests the FolioItem model for tracking guest charges.
"""
import pytest
from datetime import datetime, date, timedelta
from app.models.folio_item import FolioItem
from app.models.booking import Booking
from app.models.user import User
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.customer import Customer


@pytest.fixture
def setup_folio_test_data(db_session):
    """Set up test data for folio item tests."""
    # Create a room type
    room_type = RoomType(name="Standard", base_rate=100.0, capacity=2)
    db_session.add(room_type)
    db_session.commit()
    
    # Create a room
    room = Room(room_type_id=room_type.id, number="101", status=Room.STATUS_AVAILABLE)
    db_session.add(room)
    db_session.commit()
    
    # Create a staff user
    staff = User(username="staff", email="staff@example.com", role="receptionist")
    staff.set_password("password")
    db_session.add(staff)
    db_session.commit()
    
    # Create a customer user
    user = User(username="customer", email="customer@example.com", role="customer")
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    
    # Create a customer
    customer = Customer(user_id=user.id, name="Test Customer", email="customer@example.com")
    db_session.add(customer)
    db_session.commit()
    
    # Create a booking
    today = date.today()
    booking = Booking(
        room_id=room.id,
        customer_id=customer.id,
        check_in_date=today,
        check_out_date=today + timedelta(days=3),
        status=Booking.STATUS_CHECKED_IN,
        num_guests=2,
        total_price=300.0,
        confirmation_code="TEST001"
    )
    db_session.add(booking)
    db_session.commit()
    
    return {
        "room_type": room_type,
        "room": room,
        "staff": staff,
        "customer": customer,
        "booking": booking
    }


class TestFolioItemModel:
    """Test cases for the FolioItem model."""
    
    def test_create_folio_item(self, db_session, setup_folio_test_data):
        """Test creating a folio item."""
        booking = setup_folio_test_data["booking"]
        staff = setup_folio_test_data["staff"]
        
        # Create a folio item
        folio_item = FolioItem(
            booking_id=booking.id,
            date=date.today(),
            description="Room charge",
            charge_amount=100.0,
            charge_type=FolioItem.TYPE_ROOM,
            staff_id=staff.id
        )
        
        db_session.add(folio_item)
        db_session.commit()
        
        # Verify the folio item was created
        assert folio_item.id is not None
        assert folio_item.booking_id == booking.id
        assert folio_item.charge_amount == 100.0
        assert folio_item.charge_type == FolioItem.TYPE_ROOM
        assert folio_item.status == FolioItem.STATUS_PENDING
    
    def test_get_booking_charges(self, db_session, setup_folio_test_data):
        """Test getting all charges for a booking."""
        booking = setup_folio_test_data["booking"]
        staff = setup_folio_test_data["staff"]
        
        # Create multiple folio items
        folio_items = [
            FolioItem(
                booking_id=booking.id,
                date=date.today(),
                description="Room charge",
                charge_amount=100.0,
                charge_type=FolioItem.TYPE_ROOM,
                staff_id=staff.id
            ),
            FolioItem(
                booking_id=booking.id,
                date=date.today(),
                description="Minibar",
                charge_amount=25.0,
                charge_type=FolioItem.TYPE_MINIBAR,
                staff_id=staff.id
            ),
            FolioItem(
                booking_id=booking.id,
                date=date.today() + timedelta(days=1),
                description="Restaurant",
                charge_amount=50.0,
                charge_type=FolioItem.TYPE_RESTAURANT,
                staff_id=staff.id
            )
        ]
        
        db_session.add_all(folio_items)
        db_session.commit()
        
        # Get charges for the booking
        charges = FolioItem.get_booking_charges(booking.id)
        
        # Verify the charges
        assert len(charges) == 3
        assert sum(charge.charge_amount for charge in charges) == 175.0
    
    def test_get_booking_total_charges(self, db_session, setup_folio_test_data):
        """Test calculating total charges for a booking."""
        booking = setup_folio_test_data["booking"]
        staff = setup_folio_test_data["staff"]
        
        # Create multiple folio items with different statuses
        folio_items = [
            FolioItem(
                booking_id=booking.id,
                date=date.today(),
                description="Room charge",
                charge_amount=100.0,
                charge_type=FolioItem.TYPE_ROOM,
                staff_id=staff.id,
                status=FolioItem.STATUS_PENDING
            ),
            FolioItem(
                booking_id=booking.id,
                date=date.today(),
                description="Minibar",
                charge_amount=25.0,
                charge_type=FolioItem.TYPE_MINIBAR,
                staff_id=staff.id,
                status=FolioItem.STATUS_PAID
            ),
            FolioItem(
                booking_id=booking.id,
                date=date.today(),
                description="Voided charge",
                charge_amount=50.0,
                charge_type=FolioItem.TYPE_SERVICE,
                staff_id=staff.id,
                status=FolioItem.STATUS_VOIDED
            ),
            FolioItem(
                booking_id=booking.id,
                date=date.today(),
                description="Refunded charge",
                charge_amount=30.0,
                charge_type=FolioItem.TYPE_SPA,
                staff_id=staff.id,
                status=FolioItem.STATUS_REFUNDED
            )
        ]
        
        db_session.add_all(folio_items)
        db_session.commit()
        
        # Calculate total charges (should exclude voided and refunded)
        total = FolioItem.get_booking_total_charges(booking.id)
        
        # Verify the total (100 + 25 = 125)
        assert total == 125.0
    
    def test_void_charge(self, db_session, setup_folio_test_data):
        """Test voiding a charge."""
        booking = setup_folio_test_data["booking"]
        staff = setup_folio_test_data["staff"]
        
        # Create a folio item
        folio_item = FolioItem(
            booking_id=booking.id,
            date=date.today(),
            description="Restaurant charge",
            charge_amount=75.0,
            charge_type=FolioItem.TYPE_RESTAURANT,
            staff_id=staff.id
        )
        
        db_session.add(folio_item)
        db_session.commit()
        
        # Void the charge
        reason = "Customer complaint"
        folio_item.void(staff_id=staff.id, reason=reason)
        db_session.commit()
        
        # Verify the charge was voided
        assert folio_item.status == FolioItem.STATUS_VOIDED
        assert "VOIDED" in folio_item.description
        assert reason in folio_item.description
        
        # Verify it's excluded from total charges
        total = FolioItem.get_booking_total_charges(booking.id)
        assert total == 0.0
    
    def test_refund_charge(self, db_session, setup_folio_test_data):
        """Test refunding a charge."""
        booking = setup_folio_test_data["booking"]
        staff = setup_folio_test_data["staff"]
        
        # Create a folio item
        folio_item = FolioItem(
            booking_id=booking.id,
            date=date.today(),
            description="Spa service",
            charge_amount=120.0,
            charge_type=FolioItem.TYPE_SPA,
            staff_id=staff.id
        )
        
        db_session.add(folio_item)
        db_session.commit()
        
        # Refund the charge
        reason = "Service not provided"
        folio_item.refund(staff_id=staff.id, reason=reason)
        db_session.commit()
        
        # Verify the charge was refunded
        assert folio_item.status == FolioItem.STATUS_REFUNDED
        assert "REFUNDED" in folio_item.description
        assert reason in folio_item.description
        
        # Verify it's excluded from total charges
        total = FolioItem.get_booking_total_charges(booking.id)
        assert total == 0.0
    
    def test_to_dict(self, db_session, setup_folio_test_data):
        """Test converting a folio item to a dictionary."""
        booking = setup_folio_test_data["booking"]
        staff = setup_folio_test_data["staff"]
        
        # Create a folio item
        folio_item = FolioItem(
            booking_id=booking.id,
            date=date.today(),
            description="Late checkout fee",
            charge_amount=50.0,
            charge_type=FolioItem.TYPE_LATE_CHECKOUT,
            staff_id=staff.id,
            reference="LATE001"
        )
        
        db_session.add(folio_item)
        db_session.commit()
        
        # Convert to dictionary
        folio_dict = folio_item.to_dict()
        
        # Verify the dictionary
        assert folio_dict["id"] == folio_item.id
        assert folio_dict["booking_id"] == booking.id
        assert folio_dict["description"] == "Late checkout fee"
        assert folio_dict["charge_amount"] == 50.0
        assert folio_dict["charge_type"] == FolioItem.TYPE_LATE_CHECKOUT
        assert folio_dict["staff_id"] == staff.id
        assert folio_dict["reference"] == "LATE001"
        assert folio_dict["status"] == FolioItem.STATUS_PENDING
        assert folio_dict["date"] == date.today().isoformat() 