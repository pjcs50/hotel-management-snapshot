"""
Unit tests for booking form validation.

This module contains tests for the validation logic in the booking forms.
"""

import pytest
from datetime import datetime, timedelta
from wtforms.validators import ValidationError

from app.forms.booking_forms import BookingForm
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking
from app.models.customer import Customer
from app.models.user import User


class TestBookingFormValidation:
    """Test suite for booking form validation."""

    @pytest.fixture
    def setup_test_data(self, app, db_session):
        """Set up test data for form validation tests."""
        with app.app_context():
            # Create room type
            room_type = RoomType(name="Standard_form", description="Standard room", base_rate=100, capacity=2)
            
            # Create room
            room = Room(number="101_form", room_type=room_type, status=Room.STATUS_AVAILABLE)
            
            # Create user and customer
            user = User(username="user_form", email="user_form@example.com", role="customer")
            user.set_password("password")
            customer = Customer(user=user, name="Form Test Customer")
            
            db_session.add_all([room_type, room, user, customer])
            db_session.commit()
            
            return {
                'room_type': room_type,
                'room': room,
                'user': user,
                'customer': customer
            }

    def test_check_in_date_validation(self, setup_test_data, app):
        """Test validation of check-in date."""
        with app.app_context():
            form = BookingForm()
            
            # Test past date (should fail)
            past_date = datetime.now().date() - timedelta(days=1)
            form.check_in_date.data = past_date
            
            # Create a validator function that calls the validation method
            def validate():
                form.validate_check_in_date(form.check_in_date)
            
            # Assert that validation fails for past date
            with pytest.raises(ValidationError) as excinfo:
                validate()
            assert "Check-in date cannot be in the past" in str(excinfo.value)
            
            # Test future date (should pass)
            future_date = datetime.now().date() + timedelta(days=1)
            form.check_in_date.data = future_date
            
            # Should not raise an exception
            form.validate_check_in_date(form.check_in_date)

    def test_check_out_date_validation(self, setup_test_data, app):
        """Test validation of check-out date."""
        with app.app_context():
            form = BookingForm()
            
            # Set check-in date
            check_in_date = datetime.now().date() + timedelta(days=1)
            form.check_in_date.data = check_in_date
            
            # Test check-out date before check-in date (should fail)
            form.check_out_date.data = check_in_date - timedelta(days=1)
            
            # Create a validator function that calls the validation method
            def validate():
                form.validate_check_out_date(form.check_out_date)
            
            # Assert that validation fails for check-out before check-in
            with pytest.raises(ValidationError) as excinfo:
                validate()
            assert "Check-out date must be after check-in date" in str(excinfo.value)
            
            # Test check-out date same as check-in date (should fail)
            form.check_out_date.data = check_in_date
            
            # Assert that validation fails for same-day check-out
            with pytest.raises(ValidationError) as excinfo:
                validate()
            assert "Check-out date must be after check-in date" in str(excinfo.value)
            
            # Test valid check-out date (should pass)
            form.check_out_date.data = check_in_date + timedelta(days=1)
            
            # Should not raise an exception
            form.validate_check_out_date(form.check_out_date)

    def test_early_hours_validation(self, setup_test_data, app):
        """Test validation of early check-in hours."""
        with app.app_context():
            form = BookingForm()
            
            # Test negative hours (should fail)
            form.early_hours.data = -1
            
            # Create a validator function that calls the validation method
            def validate():
                form.validate_early_hours(form.early_hours)
            
            # Assert that validation fails for negative hours
            with pytest.raises(ValidationError) as excinfo:
                validate()
            assert "Early check-in hours must be between 0 and 12" in str(excinfo.value)
            
            # Test too many hours (should fail)
            form.early_hours.data = 13
            
            # Assert that validation fails for too many hours
            with pytest.raises(ValidationError) as excinfo:
                validate()
            assert "Early check-in hours must be between 0 and 12" in str(excinfo.value)
            
            # Test valid hours (should pass)
            form.early_hours.data = 2
            
            # Should not raise an exception
            form.validate_early_hours(form.early_hours)

    def test_late_hours_validation(self, setup_test_data, app):
        """Test validation of late check-out hours."""
        with app.app_context():
            form = BookingForm()
            
            # Test negative hours (should fail)
            form.late_hours.data = -1
            
            # Create a validator function that calls the validation method
            def validate():
                form.validate_late_hours(form.late_hours)
            
            # Assert that validation fails for negative hours
            with pytest.raises(ValidationError) as excinfo:
                validate()
            assert "Late check-out hours must be between 0 and 12" in str(excinfo.value)
            
            # Test too many hours (should fail)
            form.late_hours.data = 13
            
            # Assert that validation fails for too many hours
            with pytest.raises(ValidationError) as excinfo:
                validate()
            assert "Late check-out hours must be between 0 and 12" in str(excinfo.value)
            
            # Test valid hours (should pass)
            form.late_hours.data = 3
            
            # Should not raise an exception
            form.validate_late_hours(form.late_hours)

    def test_num_guests_validation(self, setup_test_data, app, db_session):
        """Test validation of number of guests."""
        with app.app_context():
            form = BookingForm()
            
            # Set room_id to a room with capacity 2
            form.room_id.data = setup_test_data['room'].id
            
            # Test too many guests (should fail)
            form.num_guests.data = 3  # Room capacity is 2
            
            # Create a validator function that calls the validation method
            def validate():
                form.validate_num_guests(form.num_guests)
            
            # Assert that validation fails for too many guests
            with pytest.raises(ValidationError) as excinfo:
                validate()
            assert "Number of guests exceeds room capacity" in str(excinfo.value)
            
            # Test valid number of guests (should pass)
            form.num_guests.data = 2
            
            # Should not raise an exception
            form.validate_num_guests(form.num_guests)

    def test_special_requests_validation(self, setup_test_data, app):
        """Test validation of special requests."""
        with app.app_context():
            form = BookingForm()
            
            # Test special requests that are too long (should fail)
            form.special_requests.data = "a" * 1001  # Max length is 1000
            
            # Create a validator function that calls the validation method
            def validate():
                form.validate_special_requests(form.special_requests)
            
            # Assert that validation fails for too long special requests
            with pytest.raises(ValidationError) as excinfo:
                validate()
            assert "Special requests must be less than 1000 characters" in str(excinfo.value)
            
            # Test valid special requests (should pass)
            form.special_requests.data = "Please provide extra pillows."
            
            # Should not raise an exception
            form.validate_special_requests(form.special_requests)

    def test_form_validation_with_existing_booking(self, setup_test_data, app, db_session):
        """Test form validation with an existing booking for the same room."""
        with app.app_context():
            # Create an existing booking
            today = datetime.now().date()
            existing_booking = Booking(
                room_id=setup_test_data['room'].id,
                customer_id=setup_test_data['customer'].id,
                check_in_date=today + timedelta(days=5),
                check_out_date=today + timedelta(days=7),
                status=Booking.STATUS_RESERVED
            )
            db_session.add(existing_booking)
            db_session.commit()
            
            # Create form with overlapping dates
            form = BookingForm()
            form.room_id.data = setup_test_data['room'].id
            form.check_in_date.data = today + timedelta(days=6)  # Overlaps with existing booking
            form.check_out_date.data = today + timedelta(days=8)
            
            # Validate form (should fail due to room availability)
            assert not form.validate()
            
            # Check for error message
            assert any("Room is not available for the selected dates" in error for error in form.room_id.errors)
