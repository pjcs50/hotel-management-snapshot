"""
Tests for customer dashboard and related routes.

This module contains tests for the customer dashboard, profile management,
booking management, loyalty program, and notifications views.
"""

import unittest
from unittest.mock import patch, MagicMock
from flask import url_for
from datetime import datetime, timedelta

from app_factory import create_app
from config import TestingConfig
from db import db
from app.models.user import User
from app.models.customer import Customer
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.payment import Payment
from app.models.notification import Notification
from app.models.loyalty_ledger import LoyaltyLedger

class TestCustomerRoutes(unittest.TestCase):
    """Test case for customer routes."""

    def setUp(self):
        """Set up test environment."""
        self.app = create_app(TestingConfig())
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()
        self._setup_test_data()

    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _setup_test_data(self):
        """Set up test data for the test cases."""
        # Create a test user and customer
        self.user = User(
            username='testcustomer',
            email='testcustomer@example.com',
            role='customer'
        )
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()

        self.customer = Customer(
            user_id=self.user.id,
            name='Test Customer',
            phone='1234567890',
            address='123 Test St',
            emergency_contact='Emergency Contact: 000-000-0000',
            profile_complete=True
        )
        db.session.add(self.customer)
        db.session.commit()

        # Create a room type and room
        self.room_type = RoomType(
            name='Deluxe Suite',
            description='Luxurious suite with a view',
            base_rate=200.00,
            capacity=2,
            amenities='WiFi, TV, Mini Bar'
        )
        db.session.add(self.room_type)
        db.session.commit()

        self.room = Room(
            number='101',
            room_type_id=self.room_type.id,
            status='Available'
        )
        db.session.add(self.room)
        db.session.commit()

        # Create a booking
        self.booking = Booking(
            customer_id=self.customer.id,
            room_id=self.room.id,
            check_in_date=datetime.now().date() + timedelta(days=10),
            check_out_date=datetime.now().date() + timedelta(days=15),
            status='Reserved',
            num_guests=2,
            total_price=1000.00,
            confirmation_code='TST12345'
        )
        db.session.add(self.booking)
        db.session.commit()

        # Create a payment
        self.payment = Payment(
            booking_id=self.booking.id,
            amount=500.00,
            payment_type='Credit Card',
            reference='PAY12345',
            payment_date=datetime.now()
        )
        db.session.add(self.payment)
        db.session.commit()

        # Create a loyalty ledger entry
        self.loyalty_entry = LoyaltyLedger(
            customer_id=self.customer.id,
            points=100,
            description='Welcome bonus',
            transaction_date=datetime.now()
        )
        db.session.add(self.loyalty_entry)
        db.session.commit()

        # Create a notification
        self.notification = Notification(
            user_id=self.user.id,
            type='booking_confirmation',
            content='Your booking has been confirmed.',
            is_read=False,
            created_at=datetime.now()
        )
        db.session.add(self.notification)
        db.session.commit()

    def _login(self):
        """Helper function to log in as test customer."""
        return self.client.post(
            url_for('auth.login'),
            data={
                'email': 'testcustomer@example.com',
                'password': 'password123'
            },
            follow_redirects=True
        )

    def test_dashboard_access(self):
        """Test customer dashboard access."""
        # Log in as customer
        self._login()
        
        # Access the dashboard
        with patch('app.services.dashboard_service.DashboardService.get_customer_metrics') as mock_metrics:
            mock_metrics.return_value = {
                'customer_name': 'Test Customer',
                'profile_status': 'Complete',
                'booking_count': 1,
                'active_booking': None,
                'upcoming_bookings': [
                    {
                        'id': self.booking.id,
                        'room_number': '101',
                        'room_type': 'Deluxe Suite',
                        'check_in_date': self.booking.check_in_date.strftime('%Y-%m-%d'),
                        'check_out_date': self.booking.check_out_date.strftime('%Y-%m-%d'),
                        'nights': 5,
                        'status': 'Reserved'
                    }
                ],
                'past_bookings': [],
                'loyalty_points': 100,
                'loyalty_tier': 'Standard',
                'unread_notification_count': 1
            }
            
            response = self.client.get(url_for('customer.dashboard'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Customer Dashboard', response.data)
            self.assertIn(b'Test Customer', response.data)
            # Check for dashboard UI components
            self.assertIn(b'Loyalty Status', response.data)
            self.assertIn(b'Profile Status', response.data)
            self.assertIn(b'Total Bookings', response.data)

    def test_profile_view_and_edit(self):
        """Test customer profile view and edit."""
        # Log in as customer
        self._login()
        
        # View profile
        response = self.client.get(url_for('customer.profile'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'My Profile', response.data)
        self.assertIn(b'Test Customer', response.data)
        self.assertIn(b'1234567890', response.data)
        
        # Edit profile
        response = self.client.post(
            url_for('customer.profile'),
            data={
                'name': 'Updated Customer',
                'phone': '9876543210',
                'address': 'Updated Address',
                'emergency_contact': 'Updated Emergency Contact',
                'submit': 'Save Profile'
            },
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your profile has been updated successfully', response.data)
        
        # Verify changes in database
        updated_customer = Customer.query.get(self.customer.id)
        self.assertEqual(updated_customer.name, 'Updated Customer')
        self.assertEqual(updated_customer.phone, '9876543210')

    def test_change_password(self):
        """Test customer password change."""
        # Log in as customer
        self._login()
        
        # View change password page
        response = self.client.get(url_for('customer.change_password'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Change Your Password', response.data)
        
        # Test invalid current password
        response = self.client.post(
            url_for('customer.change_password'),
            data={
                'current_password': 'wrongpassword',
                'new_password': 'newpassword123',
                'confirm_new_password': 'newpassword123',
                'submit': 'Change Password'
            },
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Current password does not match', response.data)
        
        # Test successful password change
        response = self.client.post(
            url_for('customer.change_password'),
            data={
                'current_password': 'password123',
                'new_password': 'newpassword123',
                'confirm_new_password': 'newpassword123',
                'submit': 'Change Password'
            },
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your password has been changed successfully', response.data)
        
        # Verify password change
        updated_user = User.query.get(self.user.id)
        self.assertTrue(updated_user.check_password('newpassword123'))

    def test_booking_details(self):
        """Test booking details view."""
        # Log in as customer
        self._login()
        
        # View booking details
        response = self.client.get(
            url_for('customer.booking_details', booking_id=self.booking.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Booking Summary', response.data)
        self.assertIn(b'TST12345', response.data)  # Confirmation code
        self.assertIn(b'Payment Information', response.data)
        self.assertIn(b'Payment History', response.data)
        self.assertIn(b'PAY12345', response.data)  # Payment reference
        
        # Test access to non-existent booking
        response = self.client.get(
            url_for('customer.booking_details', booking_id=999),
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Booking not found or access denied', response.data)

    def test_loyalty_history(self):
        """Test loyalty history view."""
        # Log in as customer
        self._login()
        
        # Mock the CustomerService
        with patch('app.services.customer_service.CustomerService.get_customer_by_user_id') as mock_customer:
            mock_customer.return_value = self.customer
            
            # Mock the loyalty history
            with patch('app.services.customer_service.CustomerService.get_loyalty_history') as mock_history:
                mock_history.return_value = [
                    {
                        'transaction_date': datetime.now(),
                        'description': 'Welcome bonus',
                        'points_change': 100,
                        'balance_after_transaction': 100
                    }
                ]
                
                response = self.client.get(url_for('customer.loyalty_history'))
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Loyalty Program Summary', response.data)
                self.assertIn(b'Points Transaction History', response.data)
                self.assertIn(b'Welcome bonus', response.data)
                self.assertIn(b'100 pts', response.data)

    def test_notifications(self):
        """Test notifications view and management."""
        # Log in as customer
        self._login()
        
        # View notifications
        response = self.client.get(url_for('customer.notifications_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'My Notifications', response.data)
        self.assertIn(b'Your booking has been confirmed', response.data)
        
        # Mark notification as read
        response = self.client.post(
            url_for('customer.mark_one_notification_read', notification_id=self.notification.id),
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify notification is marked as read
        updated_notification = Notification.query.get(self.notification.id)
        self.assertTrue(updated_notification.is_read)
        
        # Test marking all notifications as read
        # First create a new unread notification
        new_notification = Notification(
            user_id=self.user.id,
            type='payment_received',
            content='Your payment has been received.',
            is_read=False,
            created_at=datetime.now()
        )
        db.session.add(new_notification)
        db.session.commit()
        
        response = self.client.post(
            url_for('customer.mark_all_customer_notifications_read'),
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify all notifications are marked as read
        unread_count = Notification.query.filter_by(user_id=self.user.id, is_read=False).count()
        self.assertEqual(unread_count, 0)

    def test_new_booking(self):
        """Test new booking creation with special requests."""
        # Log in as customer
        self._login()
        
        # Get the new booking form
        response = self.client.get(url_for('customer.new_booking'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create New Booking', response.data)
        self.assertIn(b'Special Requests', response.data)
        
        # Mock the booking service
        with patch('app.services.booking_service.BookingService.get_available_rooms') as mock_get_rooms:
            mock_get_rooms.return_value = [self.room]
            
            with patch('app.services.booking_service.BookingService.create_booking') as mock_create:
                # Set up the mock to return a new booking
                new_booking = Booking(
                    id=2,
                    customer_id=self.customer.id,
                    room_id=self.room.id,
                    check_in_date=datetime.now().date() + timedelta(days=20),
                    check_out_date=datetime.now().date() + timedelta(days=25),
                    status='Reserved',
                    num_guests=2,
                    total_price=1000.00,
                    confirmation_code='NEW12345',
                    special_requests='Need extra pillows and late checkout'
                )
                mock_create.return_value = new_booking
                
                # Submit the booking with special requests
                response = self.client.post(
                    url_for('customer.new_booking'),
                    data={
                        'room_id': self.room.id,
                        'check_in_date': (datetime.now().date() + timedelta(days=20)).strftime('%Y-%m-%d'),
                        'check_out_date': (datetime.now().date() + timedelta(days=25)).strftime('%Y-%m-%d'),
                        'num_guests': 2,
                        'special_requests': 'Need extra pillows and late checkout',
                        'early_hours': 0,
                        'late_hours': 0,
                        'status': 'Reserved',
                        'customer_id': self.customer.id
                    },
                    follow_redirects=True
                )
                
                # Verify booking creation
                self.assertEqual(response.status_code, 200)
                # Verify special requests were passed to the booking service
                mock_create.assert_called_once()
                call_args = mock_create.call_args[1]
                self.assertEqual(call_args['special_requests'], 'Need extra pillows and late checkout') 