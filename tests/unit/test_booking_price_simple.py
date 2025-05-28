"""
Simple unit tests for booking price calculation.

This module contains tests for the price calculation features of the Booking model,
including early check-in and late check-out fees.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType


def test_early_checkin_fee_calculation():
    """Test calculation of early check-in fee."""
    # Create mock room and room type
    room_type = MagicMock()
    room_type.base_rate = 100
    
    room = MagicMock()
    room.room_type = room_type
    
    # Create booking with early check-in
    booking = Booking()
    booking.room = room
    booking.early_hours = 2
    booking.late_hours = 0
    booking.check_in_date = datetime.now().date()
    booking.check_out_date = datetime.now().date() + timedelta(days=2)
    
    # Mock the SeasonalRate.calculate_stay_price method
    with patch('app.models.seasonal_rate.SeasonalRate.calculate_stay_price', return_value=200):
        # Calculate price
        total_price = booking.calculate_price(save=False)
    
    # Verify price includes early check-in fee (base price + early fee)
    # Base price: $200 (from mocked calculate_stay_price)
    # Early fee: 2 hours * 10% of $100 = $20
    assert total_price == 220


def test_late_checkout_fee_calculation():
    """Test calculation of late check-out fee."""
    # Create mock room and room type
    room_type = MagicMock()
    room_type.base_rate = 100
    
    room = MagicMock()
    room.room_type = room_type
    
    # Create booking with late check-out
    booking = Booking()
    booking.room = room
    booking.early_hours = 0
    booking.late_hours = 3
    booking.check_in_date = datetime.now().date()
    booking.check_out_date = datetime.now().date() + timedelta(days=2)
    
    # Mock the SeasonalRate.calculate_stay_price method
    with patch('app.models.seasonal_rate.SeasonalRate.calculate_stay_price', return_value=200):
        # Calculate price
        total_price = booking.calculate_price(save=False)
    
    # Verify price includes late check-out fee (base price + late fee)
    # Base price: $200 (from mocked calculate_stay_price)
    # Late fee: 3 hours * 10% of $100 = $30
    assert total_price == 230


def test_both_early_and_late_fee_calculation():
    """Test calculation of both early check-in and late check-out fees."""
    # Create mock room and room type
    room_type = MagicMock()
    room_type.base_rate = 100
    
    room = MagicMock()
    room.room_type = room_type
    
    # Create booking with both early check-in and late check-out
    booking = Booking()
    booking.room = room
    booking.early_hours = 2
    booking.late_hours = 3
    booking.check_in_date = datetime.now().date()
    booking.check_out_date = datetime.now().date() + timedelta(days=2)
    
    # Mock the SeasonalRate.calculate_stay_price method
    with patch('app.models.seasonal_rate.SeasonalRate.calculate_stay_price', return_value=200):
        # Calculate price
        total_price = booking.calculate_price(save=False)
    
    # Verify price includes both early check-in and late check-out fees
    # Base price: $200 (from mocked calculate_stay_price)
    # Early fee: 2 hours * 10% of $100 = $20
    # Late fee: 3 hours * 10% of $100 = $30
    assert total_price == 250


def test_zero_early_late_hours():
    """Test calculation with zero early check-in and late check-out hours."""
    # Create mock room and room type
    room_type = MagicMock()
    room_type.base_rate = 100
    
    room = MagicMock()
    room.room_type = room_type
    
    # Create booking with zero early check-in and late check-out hours
    booking = Booking()
    booking.room = room
    booking.early_hours = 0
    booking.late_hours = 0
    booking.check_in_date = datetime.now().date()
    booking.check_out_date = datetime.now().date() + timedelta(days=2)
    
    # Mock the SeasonalRate.calculate_stay_price method
    with patch('app.models.seasonal_rate.SeasonalRate.calculate_stay_price', return_value=200):
        # Calculate price
        total_price = booking.calculate_price(save=False)
    
    # Verify price does not include any fees
    # Base price: $200 (from mocked calculate_stay_price)
    assert total_price == 200


def test_null_early_late_hours():
    """Test calculation with null early check-in and late check-out hours."""
    # Create mock room and room type
    room_type = MagicMock()
    room_type.base_rate = 100
    
    room = MagicMock()
    room.room_type = room_type
    
    # Create booking with null early check-in and late check-out hours
    booking = Booking()
    booking.room = room
    booking.early_hours = None
    booking.late_hours = None
    booking.check_in_date = datetime.now().date()
    booking.check_out_date = datetime.now().date() + timedelta(days=2)
    
    # Mock the SeasonalRate.calculate_stay_price method
    with patch('app.models.seasonal_rate.SeasonalRate.calculate_stay_price', return_value=200):
        # Calculate price
        total_price = booking.calculate_price(save=False)
    
    # Verify price does not include any fees
    # Base price: $200 (from mocked calculate_stay_price)
    assert total_price == 200
