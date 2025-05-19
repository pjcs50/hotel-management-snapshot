"""
Integration tests for virtual staff request functionality.

Tests the virtual staff request approval/denial process.
"""

import unittest
import os
import tempfile
from datetime import datetime
from sqlalchemy import select

from app_factory import create_app
from db import db
from app.models.user import User
from app.models.staff_request import StaffRequest


class TestVirtualStaffRequests(unittest.TestCase):
    """Test cases for virtual staff request functionality."""
    
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
        
        with self.app.app_context():
            db.create_all()
            # Create a manager user for testing approvals
            manager_user = db.session.execute(select(User).filter_by(email='manager_virtual_staff@example.com')).scalar_one_or_none()
            if not manager_user:
                manager = User(
                    username='testmanager_virtual',
                    email='manager_virtual_staff@example.com', # Unique email
                    role='manager',
                    is_active=True
                )
                manager.set_password('password123')
                db.session.add(manager)
                db.session.commit() # Commit manager creation
    
    def tearDown(self):
        """Clean up after test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose() # Ensure all connections from the engine are closed
        
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_approve_virtual_request(self):
        """Test approving a virtual staff request (user exists with role_requested)."""
        with self.app.app_context(): # Ensure app context for the test
            # Create a user with a role_requested but no StaffRequest record
            virtual_user = User(
                username='virtualstaff_approve',
                email='virtual_approve@example.com', # Unique email
                role='pending',
                role_requested='receptionist',
                is_active=False
            )
            virtual_user.set_password('password123')
            db.session.add(virtual_user)
            db.session.commit() # Commit this setup data

            # Log in as manager
            manager = db.session.execute(select(User).filter_by(email='manager_virtual_staff@example.com')).scalar_one()
            # Manually log in manager for the client session
            with self.client.session_transaction() as sess:
                sess['_user_id'] = manager.id
                sess['_fresh'] = True # For Flask-Login freshness
            
            # Attempt to approve the virtual request (user_id directly)
            response = self.client.post(f'/manager/staff_requests/virtual/{virtual_user.id}/approve', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Staff request approved for existing user', response.data)

            approved_user = db.session.get(User, virtual_user.id)
            self.assertEqual(approved_user.role, 'receptionist')
            self.assertTrue(approved_user.is_active)
            self.assertIsNone(approved_user.role_requested)

    def test_deny_virtual_request(self):
        """Test denying a virtual staff request."""
        with self.app.app_context(): # Ensure app context for the test
            # Create a user with a role_requested
            virtual_user = User(
                username='virtualstaff_deny',
                email='virtual_deny@example.com', # Unique email
                role='pending',
                role_requested='housekeeping',
                is_active=False
            )
            virtual_user.set_password('password123')
            db.session.add(virtual_user)
            db.session.commit() # Commit this setup data

            # Log in as manager
            manager = db.session.execute(select(User).filter_by(email='manager_virtual_staff@example.com')).scalar_one()
            with self.client.session_transaction() as sess:
                sess['_user_id'] = manager.id
                sess['_fresh'] = True

            response = self.client.post(f'/manager/staff_requests/virtual/{virtual_user.id}/deny', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Staff request denied for existing user', response.data)

            denied_user = db.session.get(User, virtual_user.id)
            self.assertEqual(denied_user.role, 'pending') # Role should remain pending
            self.assertFalse(denied_user.is_active) # Should remain inactive
            self.assertIsNone(denied_user.role_requested) # role_requested should be cleared


if __name__ == '__main__':
    unittest.main() 