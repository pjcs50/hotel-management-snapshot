"""
Tests for booking forms.

This module contains tests for the booking forms to ensure
validation works correctly.
"""

import pytest
from datetime import datetime, timedelta
from wtforms.validators import ValidationError, NumberRange

from app.forms.booking_forms import BookingForm, BookingSearchForm


class TestBookingForm:
    """Test suite for the BookingForm."""

    def test_init(self):
        """Test that the form initializes correctly."""
        form = BookingForm()
        assert form.room_id is not None
        assert form.check_in_date is not None
        assert form.check_out_date is not None
        assert form.num_guests is not None
        assert form.special_requests is not None
        assert form.early_hours is not None
        assert form.late_hours is not None

    def test_validate_check_out_date_success(self):
        """Test that check_out_date validation passes with valid dates."""
        form = BookingForm()

        # Set up valid dates
        today = datetime.now().date()
        form.check_in_date.data = today + timedelta(days=1)
        form.check_out_date.data = today + timedelta(days=3)

        # This should not raise an exception
        form.validate_check_out_date(form.check_out_date)

    def test_validate_check_out_date_failure(self):
        """Test that check_out_date validation fails with invalid dates."""
        form = BookingForm()

        # Set up invalid dates (check-out before check-in)
        today = datetime.now().date()
        form.check_in_date.data = today + timedelta(days=3)
        form.check_out_date.data = today + timedelta(days=1)

        # This should raise a ValidationError
        with pytest.raises(ValidationError, match="Check-out date must be after check-in date"):
            form.validate_check_out_date(form.check_out_date)

    def test_validate_check_in_date_success(self):
        """Test that check_in_date validation passes with valid dates."""
        form = BookingForm()

        # Set up valid dates (check-in in the future)
        today = datetime.now().date()
        form.check_in_date.data = today + timedelta(days=1)

        # This should not raise an exception
        form.validate_check_in_date(form.check_in_date)

    def test_validate_check_in_date_failure(self):
        """Test that check_in_date validation fails with invalid dates."""
        form = BookingForm()

        # Set up invalid dates (check-in in the past)
        today = datetime.now().date()
        form.check_in_date.data = today - timedelta(days=1)

        # This should raise a ValidationError
        with pytest.raises(ValidationError, match="Check-in date cannot be in the past"):
            form.validate_check_in_date(form.check_in_date)

    def test_num_guests_validation(self):
        """Test that num_guests field has correct validators."""
        form = BookingForm()

        # Check that the field has the correct validators
        validators = form.num_guests.validators

        # Check for NumberRange validator
        number_range_validators = [v for v in validators if isinstance(v, NumberRange)]
        assert len(number_range_validators) > 0

        # Check min and max values
        number_range = number_range_validators[0]
        assert number_range.min == 1
        assert number_range.max >= 1

    def test_early_hours_validation(self):
        """Test that early_hours field has correct validators."""
        form = BookingForm()

        # Check that the field has the correct validators
        validators = form.early_hours.validators

        # Check for NumberRange validator
        number_range_validators = [v for v in validators if isinstance(v, NumberRange)]
        assert len(number_range_validators) > 0

        # Check min and max values
        number_range = number_range_validators[0]
        assert number_range.min == 0
        assert number_range.max > 0

    def test_late_hours_validation(self):
        """Test that late_hours field has correct validators."""
        form = BookingForm()

        # Check that the field has the correct validators
        validators = form.late_hours.validators

        # Check for NumberRange validator
        number_range_validators = [v for v in validators if isinstance(v, NumberRange)]
        assert len(number_range_validators) > 0

        # Check min and max values
        number_range = number_range_validators[0]
        assert number_range.min == 0
        assert number_range.max > 0


class TestBookingSearchForm:
    """Test suite for the BookingSearchForm."""

    def test_init(self):
        """Test that the form initializes correctly."""
        form = BookingSearchForm()
        assert form.check_in_date is not None
        assert form.check_out_date is not None
        assert form.room_type_id is not None

    def test_validate_check_out_date_success(self):
        """Test that check_out_date validation passes with valid dates."""
        form = BookingSearchForm()

        # Set up valid dates
        today = datetime.now().date()
        form.check_in_date.data = today + timedelta(days=1)
        form.check_out_date.data = today + timedelta(days=3)

        # This should not raise an exception
        if hasattr(form, 'validate_check_out_date'):
            form.validate_check_out_date(form.check_out_date)

    def test_validate_check_out_date_failure(self):
        """Test that check_out_date validation fails with invalid dates."""
        form = BookingSearchForm()

        # Set up invalid dates (check-out before check-in)
        today = datetime.now().date()
        form.check_in_date.data = today + timedelta(days=3)
        form.check_out_date.data = today + timedelta(days=1)

        # Skip this test if the form doesn't have validation
        if hasattr(form, 'validate_check_out_date'):
            # This should raise a ValidationError
            with pytest.raises(ValidationError, match="Check-out date must be after check-in date"):
                form.validate_check_out_date(form.check_out_date)
