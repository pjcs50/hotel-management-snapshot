"""
Functional tests for customer dashboard.

These tests simulate a complete user journey through the customer dashboard,
testing the integration of various features.
"""

import unittest
from datetime import datetime, timedelta
from flask import url_for
from flask_login import current_user

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


class TestCustomerDashboardFunctional(unittest.TestCase):
    """Functional tests for the customer dashboard."""

    def setUp(self):
        """Set up test environment."""
        self.app = create_app(TestingConfig())
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()
        self._create_test_data()

    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_test_data(self):
        """Create test data for the functional tests."""
        # Create a customer user
        self.user = User(
            username='customerfunctional',
            email='functional@example.com',
            role='customer'
        )
        self.user.set_password('password123')
        db.session.add(self.user)
        db.session.commit()

        # Create a customer profile
        self.customer = Customer(
            user_id=self.user.id,
            name='Functional Test',
            phone='1234567890',
            address='123 Functional St',
            emergency_contact='Emergency Contact: 999-999-9999',
            profile_complete=True
        )
        db.session.add(self.customer)
        db.session.commit()

        # Create room types
        self.room_type1 = RoomType(
            name='Standard Room',
            description='Comfortable standard room',
            base_rate=100.00,
            capacity=2,
            amenities='WiFi, TV, AC'
        )
        self.room_type2 = RoomType(
            name='Deluxe Suite',
            description='Luxurious suite with a view',
            base_rate=200.00,
            capacity=4,
            amenities='WiFi, TV, Mini Bar, Jacuzzi, Ocean View'
        )
        db.session.add_all([self.room_type1, self.room_type2])
        db.session.commit()

        # Create rooms
        self.room1 = Room(
            number='101',
            room_type_id=self.room_type1.id,
            status='Available'
        )
        self.room2 = Room(
            number='201',
            room_type_id=self.room_type2.id,
            status='Available'
        )
        db.session.add_all([self.room1, self.room2])
        db.session.commit()

        # Create a past booking
        past_checkin = datetime.now().date() - timedelta(days=30)
        past_checkout = datetime.now().date() - timedelta(days=25)
        self.past_booking = Booking(
            customer_id=self.customer.id,
            room_id=self.room1.id,
            check_in_date=past_checkin,
            check_out_date=past_checkout,
            status='Checked Out',
            num_guests=2,
            total_price=500.00,
            confirmation_code='PAST12345'
        )
        db.session.add(self.past_booking)
        db.session.commit()

        # Create a payment for the past booking
        self.payment = Payment(
            booking_id=self.past_booking.id,
            amount=500.00,
            payment_type='Credit Card',
            reference='PAY12345',
            payment_date=past_checkin
        )
        db.session.add(self.payment)
        db.session.commit()

        # Create loyalty points for staying
        self.loyalty_entry = LoyaltyLedger(
            customer_id=self.customer.id,
            points=50,
            description='Stay at Horizon Hotel',
            transaction_date=past_checkout
        )
        db.session.add(self.loyalty_entry)
        db.session.commit()

        # Create a notification
        self.notification = Notification(
            user_id=self.user.id,
            type='booking_confirmed',
            content='Thank you for your stay! We hope you enjoyed your experience.',
            is_read=False,
            created_at=past_checkout
        )
        db.session.add(self.notification)
        db.session.commit()

    def _login(self):
        """Helper function to log in as test customer."""
        with self.client as c:
            return c.post(
                url_for('auth.login'),
                data={
                    'email': 'functional@example.com',
                    'password': 'password123'
                },
                follow_redirects=True
            )

    def test_complete_customer_journey(self):
        """Test a complete customer journey through the dashboard."""
        # 1. Log in
        login_response = self._login()
        self.assertIn(b'You have been logged in!', login_response.data)
        self.assertIn(b'Customer Dashboard', login_response.data)

        # 2. View dashboard
        dashboard_response = self.client.get(url_for('customer.dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn(b'Customer Dashboard', dashboard_response.data)
        self.assertIn(b'Functional Test', dashboard_response.data)  # Customer name
        self.assertIn(b'Loyalty Status', dashboard_response.data)

        # 3. View profile
        profile_response = self.client.get(url_for('customer.profile'))
        self.assertEqual(profile_response.status_code, 200)
        self.assertIn(b'My Profile', profile_response.data)
        self.assertIn(b'Functional Test', profile_response.data)
        self.assertIn(b'1234567890', profile_response.data)

        # 4. Update profile
        update_profile_response = self.client.post(
            url_for('customer.profile'),
            data={
                'name': 'Updated Functional Test',
                'phone': '9876543210',
                'address': 'Updated Functional Address',
                'emergency_contact': 'Updated Emergency: 888-888-8888',
                'submit': 'Save Profile'
            },
            follow_redirects=True
        )
        self.assertEqual(update_profile_response.status_code, 200)
        self.assertIn(b'Your profile has been updated successfully', update_profile_response.data)
        
        # Verify profile was updated
        updated_customer = Customer.query.get(self.customer.id)
        self.assertEqual(updated_customer.name, 'Updated Functional Test')
        self.assertEqual(updated_customer.phone, '9876543210')

        # 5. View bookings
        bookings_response = self.client.get(url_for('customer.bookings'))
        self.assertEqual(bookings_response.status_code, 200)
        self.assertIn(b'My Bookings', bookings_response.data)
        self.assertIn(b'PAST12345', bookings_response.data)  # Confirmation code

        # 6. View booking details
        booking_details_response = self.client.get(
            url_for('customer.booking_details', booking_id=self.past_booking.id)
        )
        self.assertEqual(booking_details_response.status_code, 200)
        self.assertIn(b'Booking Summary', booking_details_response.data)
        self.assertIn(b'PAST12345', booking_details_response.data)
        self.assertIn(b'Payment History', booking_details_response.data)
        self.assertIn(b'PAY12345', booking_details_response.data)

        # 7. View loyalty history
        loyalty_response = self.client.get(url_for('customer.loyalty_history'))
        self.assertEqual(loyalty_response.status_code, 200)
        self.assertIn(b'Loyalty Program Summary', loyalty_response.data)
        self.assertIn(b'50 pts', loyalty_response.data)
        self.assertIn(b'Stay at Horizon Hotel', loyalty_response.data)

        # 8. View notifications
        notifications_response = self.client.get(url_for('customer.notifications_list'))
        self.assertEqual(notifications_response.status_code, 200)
        self.assertIn(b'My Notifications', notifications_response.data)
        self.assertIn(b'Thank you for your stay', notifications_response.data)

        # 9. Mark notification as read
        mark_read_response = self.client.post(
            url_for('customer.mark_one_notification_read', notification_id=self.notification.id),
            follow_redirects=True
        )
        self.assertEqual(mark_read_response.status_code, 200)
        
        # Verify notification is marked as read
        updated_notification = Notification.query.get(self.notification.id)
        self.assertTrue(updated_notification.is_read)

        # 10. Browse available room types
        room_types_response = self.client.get(url_for('customer.room_types'))
        self.assertEqual(room_types_response.status_code, 200)
        self.assertIn(b'Our Room Types', room_types_response.data)
        self.assertIn(b'Standard Room', room_types_response.data)
        self.assertIn(b'Deluxe Suite', room_types_response.data)

        # 11. View new booking form
        new_booking_response = self.client.get(url_for('customer.new_booking'))
        self.assertEqual(new_booking_response.status_code, 200)
        self.assertIn(b'Create New Booking', new_booking_response.data)
        self.assertIn(b'Special Requests', new_booking_response.data)

        # 12. Change password
        change_pw_get_response = self.client.get(url_for('customer.change_password'))
        self.assertEqual(change_pw_get_response.status_code, 200)
        self.assertIn(b'Change Your Password', change_pw_get_response.data)
        
        # Submit password change
        change_pw_response = self.client.post(
            url_for('customer.change_password'),
            data={
                'current_password': 'password123',
                'new_password': 'newpassword456',
                'confirm_new_password': 'newpassword456',
                'submit': 'Change Password'
            },
            follow_redirects=True
        )
        self.assertEqual(change_pw_response.status_code, 200)
        self.assertIn(b'Your password has been changed successfully', change_pw_response.data)
        
        # Logout and try to log in with new password
        self.client.get(url_for('auth.logout'), follow_redirects=True)
        
        new_login_response = self.client.post(
            url_for('auth.login'),
            data={
                'email': 'functional@example.com',
                'password': 'newpassword456'
            },
            follow_redirects=True
        )
        self.assertEqual(new_login_response.status_code, 200)
        self.assertIn(b'You have been logged in!', new_login_response.data)
        self.assertIn(b'Customer Dashboard', new_login_response.data)

    def test_create_booking_with_special_requests(self):
        """Test creating a new booking with special requests."""
        # Log in
        self._login()
        
        # Get to the new booking form
        response = self.client.get(url_for('customer.new_booking'))
        self.assertEqual(response.status_code, 200)
        
        # Create a new booking with special requests
        check_in_date = (datetime.now().date() + timedelta(days=10)).strftime('%Y-%m-%d')
        check_out_date = (datetime.now().date() + timedelta(days=15)).strftime('%Y-%m-%d')
        
        booking_response = self.client.post(
            url_for('customer.new_booking'),
            data={
                'room_id': self.room2.id,  # Deluxe Suite
                'check_in_date': check_in_date,
                'check_out_date': check_out_date,
                'num_guests': 3,
                'special_requests': 'Need extra pillows, early check-in, and champagne on arrival.',
                'early_hours': 2,  # 2 hours early check-in
                'late_hours': 0,
                'status': 'Reserved',
                'customer_id': self.customer.id
            },
            follow_redirects=True
        )
        
        # Check for success message (may vary depending on implementation)
        # For this test, we just check if redirection happened successfully
        self.assertEqual(booking_response.status_code, 200)
        
        # Query for the new booking
        new_booking = Booking.query.filter_by(
            customer_id=self.customer.id,
            room_id=self.room2.id,
            check_in_date=datetime.strptime(check_in_date, '%Y-%m-%d').date()
        ).first()
        
        # Assert the booking was created
        self.assertIsNotNone(new_booking)
        # Assert special requests were saved
        self.assertIn('extra pillows', new_booking.special_requests or '')
        self.assertIn('champagne', new_booking.special_requests or '')
        # Assert early hours were saved
        self.assertEqual(new_booking.early_hours, 2)
        
        # View the booking details to confirm
        details_response = self.client.get(
            url_for('customer.booking_details', booking_id=new_booking.id)
        )
        self.assertEqual(details_response.status_code, 200)
        self.assertIn(b'Booking Summary', details_response.data)
        self.assertIn(b'Deluxe Suite', details_response.data)  # Room type
        self.assertIn(b'Special Requests', details_response.data)
        self.assertIn(b'extra pillows', details_response.data)
        self.assertIn(b'champagne', details_response.data) 