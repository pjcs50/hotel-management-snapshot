"""
Tests for booking-related templates.

This module contains tests to ensure that all booking-related templates
render correctly with various input data.
"""

import pytest
from datetime import datetime, timedelta
from flask import url_for, render_template
from bs4 import BeautifulSoup

from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking


@pytest.fixture
def setup_template_test_data(app, db_session):
    """Set up test data for template tests."""
    with app.app_context():
        # Create a user and customer
        user = User(username="template_test_user", email="template_test@example.com")
        user.set_password("password")
        customer = Customer(
            user=user, 
            name="Template Test Customer",
            phone="555-1234",
            address="123 Template St",
            profile_complete=True
        )
        
        # Create room types
        standard_room_type = RoomType(
            name="Standard Template Room",
            description="A standard room for template testing",
            base_rate=100.0,
            capacity=2,
            has_view=False,
            has_balcony=False,
            smoking_allowed=False,
            size_sqm=25.0,
            bed_type="Queen Bed",
            max_occupants=2,
            image_main="https://example.com/standard.jpg"
        )
        
        # Create rooms
        standard_room = Room(number="T101", room_type=standard_room_type, status=Room.STATUS_AVAILABLE)
        
        # Create a booking
        today = datetime.now().date()
        check_in_date = today + timedelta(days=1)
        check_out_date = today + timedelta(days=3)
        
        booking = Booking(
            room=standard_room,
            customer=customer,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED,
            num_guests=2,
            special_requests="Template test special request",
            confirmation_code="TEMPLATE123",
            total_price=200.0
        )
        
        # Add to database
        db_session.add_all([user, customer, standard_room_type, standard_room, booking])
        db_session.commit()
        
        return {
            'user': user,
            'customer': customer,
            'room_type': standard_room_type,
            'room': standard_room,
            'booking': booking
        }


class TestBookingTemplates:
    """Test suite for booking-related templates."""
    
    def test_new_booking_template(self, app, setup_template_test_data):
        """Test that the new_booking.html template renders correctly."""
        with app.app_context():
            from app.forms.booking_forms import BookingForm
            
            # Create a form with test data
            form = BookingForm()
            form.room_id.choices = [(setup_template_test_data['room'].id, f"Room {setup_template_test_data['room'].number}")]
            
            # Render the template
            rendered = render_template(
                'customer/new_booking.html',
                form=form,
                room_types=[setup_template_test_data['room_type']],
                estimated_price=200.0
            )
            
            # Parse the HTML
            soup = BeautifulSoup(rendered, 'html.parser')
            
            # Check that key elements are present
            assert "New Booking" in soup.text
            assert "Room Reservation" in soup.text
            assert "Check-in Date" in soup.text
            assert "Check-out Date" in soup.text
            assert "Estimated Total Price" in soup.text
            assert "$200.00" in soup.text
            
            # Check that the form has the correct fields
            form_element = soup.find('form', id='newBookingForm')
            assert form_element is not None
            assert form_element.find('input', {'name': 'csrf_token'}) is not None
            assert form_element.find('select', id='room_id_select') is not None
            assert form_element.find('input', id='check_in_date') is not None
            assert form_element.find('input', id='check_out_date') is not None
            assert form_element.find('input', id='num_guests') is not None
            assert form_element.find('textarea', id='special_requests') is not None
    
    def test_booking_confirmation_template(self, app, setup_template_test_data):
        """Test that the booking_confirmation.html template renders correctly."""
        with app.app_context():
            # Render the template
            rendered = render_template(
                'customer/booking_confirmation.html',
                booking=setup_template_test_data['booking']
            )
            
            # Parse the HTML
            soup = BeautifulSoup(rendered, 'html.parser')
            
            # Check that key elements are present
            assert "Booking Confirmed" in soup.text
            assert "Thank you for your reservation" in soup.text
            assert setup_template_test_data['booking'].confirmation_code in soup.text
            assert setup_template_test_data['room'].number in soup.text
            assert setup_template_test_data['customer'].name in soup.text
            
            # Check for important booking details
            assert "Check-in Date" in soup.text
            assert "Check-out Date" in soup.text
            assert "Total Price" in soup.text
            assert "$200.00" in soup.text
    
    def test_booking_details_template(self, app, setup_template_test_data):
        """Test that the booking_details.html template renders correctly."""
        with app.app_context():
            # Render the template
            rendered = render_template(
                'customer/booking_details.html',
                booking=setup_template_test_data['booking']
            )
            
            # Parse the HTML
            soup = BeautifulSoup(rendered, 'html.parser')
            
            # Check that key elements are present
            assert "Booking Details" in soup.text
            assert setup_template_test_data['booking'].confirmation_code in soup.text
            assert setup_template_test_data['room'].number in soup.text
            assert setup_template_test_data['room_type'].name in soup.text
            
            # Check for important booking details
            assert "Check-in Date" in soup.text
            assert "Check-out Date" in soup.text
            assert "Number of Guests" in soup.text
            assert "Special Requests" in soup.text
            assert "Template test special request" in soup.text
            
            # Check for action buttons
            edit_button = soup.find('a', string=lambda text: 'Edit Booking' in text if text else False)
            assert edit_button is not None
            cancel_button = soup.find('button', string=lambda text: 'Cancel Booking' in text if text else False)
            assert cancel_button is not None
