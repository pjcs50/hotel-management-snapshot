"""
Integration tests for staff routes.

Tests the staff registration and approval routes.
"""

import unittest
from unittest.mock import patch
import os
import tempfile
from datetime import datetime
from sqlalchemy import select

from app_factory import create_app
from db import db
from app.models.user import User
from app.models.staff_request import StaffRequest


class TestStaffRoutes(unittest.TestCase):
    """Test cases for staff routes."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        test_config = {
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'DEBUG': False,
            'SERVER_NAME': 'localhost',
            'SECRET_KEY': 'test-key',
            'LOG_LEVEL': 'ERROR',
            'LOG_FILE': None  # Disable file logging for tests
        }
        
        # Create app with test config
        self.app = create_app(test_config)
        self.client = self.app.test_client()
        
        # Create application context and tables ONLY if they don't exist
        # This setup might be better suited for setUpClass if tables are common
        with self.app.app_context():
            db.create_all() # Ensure tables are created

            # Create a manager user for testing approvals/denials IF IT DOESN'T EXIST
            # to prevent IntegrityError across tests if setUp is run multiple times for a class
            manager_user = db.session.execute(select(User).filter_by(email='test_staff_routes_manager@example.com')).scalar_one_or_none()
            if not manager_user:
                manager = User(
                    username='test_staff_routes_manager',
                    email='test_staff_routes_manager@example.com', # Unique email
                    role='manager',
                    is_active=True
                )
                manager.set_password('password123')
                db.session.add(manager)
                db.session.commit() # Commit manager creation here as it's a setup step
    
    def tearDown(self):
        """Clean up after each test."""
        with self.app.app_context():
            db.session.remove() 
            db.drop_all()
            db.engine.dispose() # Ensure all connections from the engine are closed
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_staff_register_route(self):
        """Test staff registration route (POST request)."""
        with self.app.app_context(): # Ensure app context for the test operations
            response = self.client.post('/auth/register_staff', data={
                'username': 'newstaff_staff_routes',
                'email': 'newstaff_staff_routes@example.com',
                'password': 'password123',
                'role_requested': 'receptionist'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Request submitted for approval', response.data)
            
            # Verify user and staff request were created
            user = db.session.execute(select(User).filter_by(email='newstaff_staff_routes@example.com')).scalar_one_or_none()
            self.assertIsNotNone(user)
            self.assertEqual(user.role, 'pending')
            self.assertEqual(user.role_requested, 'receptionist')
            self.assertFalse(user.is_active)

            staff_request = db.session.execute(select(StaffRequest).filter_by(user_id=user.id)).scalar_one_or_none()
            self.assertIsNotNone(staff_request)
            self.assertEqual(staff_request.status, 'pending')
            # db.session.commit() # No commit needed here, test ends, tearDown cleans up

    def test_manager_approve_request(self):
        """Test manager approving a staff request."""
        with self.app.app_context(): # Ensure app context
            # Create a pending staff user and request
            staff_user = User(
                username='pendingstaff_approve_staff_routes',
                email='pending_approve_staff_routes@example.com', # Unique email
                role='pending',
                role_requested='housekeeping',
                is_active=False
            )
            staff_user.set_password('password123')
            db.session.add(staff_user)
            db.session.flush() # Get ID

            staff_request = StaffRequest(
                user_id=staff_user.id,
                role_requested='housekeeping',
                status='pending',
                notes='Initial request'
            )
            db.session.add(staff_request)
            db.session.commit() # Commit this setup data

            # Log in as manager
            manager = db.session.execute(select(User).filter_by(email='test_staff_routes_manager@example.com')).scalar_one()
            with self.client.session_transaction() as sess:
                sess['_user_id'] = manager.id
                sess['_fresh'] = True
            
            response = self.client.post(f'/manager/staff_requests/{staff_request.id}/approve', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Staff request approved', response.data)

            approved_user = db.session.get(User, staff_user.id)
            self.assertEqual(approved_user.role, 'housekeeping')
            self.assertTrue(approved_user.is_active)
            self.assertIsNone(approved_user.role_requested)
            
            approved_request = db.session.get(StaffRequest, staff_request.id)
            self.assertEqual(approved_request.status, 'approved')
            # db.session.commit() # No commit needed here

    def test_manager_deny_request(self):
        """Test manager denying a staff request."""
        with self.app.app_context(): # Ensure app context
            # Create a pending staff user and request
            staff_user = User(
                username='pendingstaff_deny_staff_routes',
                email='pending_deny_staff_routes@example.com', # Unique email
                role='pending',
                role_requested='receptionist',
                is_active=False
            )
            staff_user.set_password('password123')
            db.session.add(staff_user)
            db.session.flush()

            staff_request = StaffRequest(
                user_id=staff_user.id,
                role_requested='receptionist',
                status='pending',
                notes='Initial request'
            )
            db.session.add(staff_request)
            db.session.commit() # Commit this setup data

            # Log in as manager
            manager = db.session.execute(select(User).filter_by(email='test_staff_routes_manager@example.com')).scalar_one()
            with self.client.session_transaction() as sess:
                sess['_user_id'] = manager.id
                sess['_fresh'] = True

            response = self.client.post(f'/manager/staff_requests/{staff_request.id}/deny', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Staff request denied', response.data)

            denied_user = db.session.get(User, staff_user.id)
            self.assertEqual(denied_user.role, 'pending') # Role should not change on denial
            self.assertFalse(denied_user.is_active)
            self.assertIsNone(denied_user.role_requested) # role_requested should be cleared
            
            denied_request = db.session.get(StaffRequest, staff_request.id)
            self.assertEqual(denied_request.status, 'denied')
            # db.session.commit() # No commit needed here


if __name__ == '__main__':
    unittest.main() 