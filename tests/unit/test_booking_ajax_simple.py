"""
Simple unit tests for booking form AJAX functionality.

This module contains tests for the AJAX functionality in the booking forms
without relying on database operations.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from flask import Flask

from app.routes.customer import new_booking as customer_new_booking
from app.routes.receptionist import new_booking as receptionist_new_booking
from app.models.room import Room
from app.models.room_type import RoomType


@pytest.fixture
def app():
    """Create a Flask application for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def mock_rooms():
    """Create mock room data for testing."""
    room_type1 = RoomType(id=1, name="Standard", description="Standard room", base_rate=100, capacity=2)
    room_type2 = RoomType(id=2, name="Deluxe", description="Deluxe room", base_rate=150, capacity=4)
    
    room1 = Room(id=1, number="101", room_type=room_type1, status=Room.STATUS_AVAILABLE)
    room2 = Room(id=2, number="201", room_type=room_type2, status=Room.STATUS_AVAILABLE)
    
    return [room1, room2]


class TestCustomerBookingAjax:
    """Test suite for customer booking form AJAX functionality."""

    @patch('app.routes.customer.BookingService')
    def test_update_room_options_ajax(self, mock_booking_service, app, mock_rooms):
        """Test AJAX request to update room options based on dates."""
        with app.test_request_context(
            '/new-booking',
            method='POST',
            data={
                'check_in_date': (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'check_out_date': (datetime.now().date() + timedelta(days=3)).strftime('%Y-%m-%d'),
                'action': 'update_options'
            },
            headers={'X-Requested-With': 'XMLHttpRequest'}
        ):
            # Set up mock booking service
            mock_service_instance = MagicMock()
            mock_booking_service.return_value = mock_service_instance
            mock_service_instance.get_available_rooms.return_value = mock_rooms
            
            # Mock the form
            with patch('app.routes.customer.BookingForm') as mock_form_class:
                mock_form = MagicMock()
                mock_form_class.return_value = mock_form
                mock_form.check_in_date.data = datetime.now().date() + timedelta(days=1)
                mock_form.check_out_date.data = datetime.now().date() + timedelta(days=3)
                
                # Call the function
                response = customer_new_booking()
                
                # Parse the response
                data = json.loads(response.data)
                
                # Check the response
                assert data['success'] is True
                assert 'room_options' in data
                assert len(data['room_options']) == 2
                
                # Verify room options include our test rooms
                room_ids = [option['value'] for option in data['room_options']]
                assert 1 in room_ids
                assert 2 in room_ids

    @patch('app.routes.customer.BookingService')
    def test_calculate_price_ajax(self, mock_booking_service, app, mock_rooms):
        """Test AJAX request to calculate price based on selected options."""
        with app.test_request_context(
            '/new-booking',
            method='POST',
            data={
                'room_id': '1',
                'check_in_date': (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'check_out_date': (datetime.now().date() + timedelta(days=3)).strftime('%Y-%m-%d'),
                'early_hours': '2',
                'late_hours': '3',
                'action': 'update_options'
            },
            headers={'X-Requested-With': 'XMLHttpRequest'}
        ):
            # Set up mock booking service
            mock_service_instance = MagicMock()
            mock_booking_service.return_value = mock_service_instance
            mock_service_instance.get_available_rooms.return_value = mock_rooms
            mock_service_instance.calculate_booking_price.return_value = 250.0
            
            # Mock the form
            with patch('app.routes.customer.BookingForm') as mock_form_class:
                mock_form = MagicMock()
                mock_form_class.return_value = mock_form
                mock_form.room_id.data = 1
                mock_form.check_in_date.data = datetime.now().date() + timedelta(days=1)
                mock_form.check_out_date.data = datetime.now().date() + timedelta(days=3)
                mock_form.early_hours.data = 2
                mock_form.late_hours.data = 3
                
                # Call the function
                response = customer_new_booking()
                
                # Parse the response
                data = json.loads(response.data)
                
                # Check the response
                assert data['success'] is True
                assert 'estimated_price' in data
                assert data['estimated_price'] == 250.0


class TestReceptionistBookingAjax:
    """Test suite for receptionist booking form AJAX functionality."""

    @patch('app.routes.receptionist.BookingService')
    def test_update_room_options_receptionist_ajax(self, mock_booking_service, app, mock_rooms):
        """Test AJAX request to update room options in receptionist form."""
        with app.test_request_context(
            '/new-booking',
            method='POST',
            data={
                'check_in_date': (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'check_out_date': (datetime.now().date() + timedelta(days=3)).strftime('%Y-%m-%d'),
                'action': 'update_options'
            },
            headers={'X-Requested-With': 'XMLHttpRequest'}
        ):
            # Set up mock booking service
            mock_service_instance = MagicMock()
            mock_booking_service.return_value = mock_service_instance
            mock_service_instance.get_available_rooms.return_value = mock_rooms
            
            # Mock the form
            with patch('app.routes.receptionist.BookingForm') as mock_form_class:
                mock_form = MagicMock()
                mock_form_class.return_value = mock_form
                mock_form.check_in_date.data = datetime.now().date() + timedelta(days=1)
                mock_form.check_out_date.data = datetime.now().date() + timedelta(days=3)
                
                # Call the function
                response = receptionist_new_booking()
                
                # Parse the response
                data = json.loads(response.data)
                
                # Check the response
                assert data['success'] is True
                assert 'room_options' in data
                assert len(data['room_options']) == 2
                
                # Verify room options include our test rooms
                room_ids = [option['value'] for option in data['room_options']]
                assert 1 in room_ids
                assert 2 in room_ids
                
                # Verify room details are included
                for option in data['room_options']:
                    if option['value'] == 1:
                        assert option['room_type'] == 'Standard'
                        assert option['capacity'] == 2
                        assert option['rate'] == 100
                    elif option['value'] == 2:
                        assert option['room_type'] == 'Deluxe'
                        assert option['capacity'] == 4
                        assert option['rate'] == 150
