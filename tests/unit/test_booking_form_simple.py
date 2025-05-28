"""
Simple unit tests for booking form validation.

This module contains tests for the validation logic in the booking forms
without relying on database operations.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from wtforms.validators import ValidationError

from app.forms.booking_forms import BookingForm


class TestBookingFormValidation:
    """Test suite for booking form validation."""

    def test_check_in_date_validation(self):
        """Test validation of check-in date."""
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

    def test_check_out_date_validation(self):
        """Test validation of check-out date."""
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

    def test_early_hours_validation(self):
        """Test validation of early check-in hours."""
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

    def test_late_hours_validation(self):
        """Test validation of late check-out hours."""
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

    @patch('app.forms.booking_forms.Room')
    def test_num_guests_validation(self, mock_room):
        """Test validation of number of guests."""
        # Set up mock room with capacity 2
        mock_room_obj = MagicMock()
        mock_room_obj.room_type.capacity = 2
        mock_room.query.get.return_value = mock_room_obj
        
        form = BookingForm()
        form.room_id.data = 1  # Any ID will work since we're mocking
        
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

    def test_special_requests_validation(self):
        """Test validation of special requests."""
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
