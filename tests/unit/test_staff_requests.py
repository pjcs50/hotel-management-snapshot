"""
Unit tests for staff request functionality.

Tests the staff registration and approval process.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.services.user_service import UserService, DuplicateEmailError, DuplicateUsernameError
from app.models.user import User
from app.models.staff_request import StaffRequest


class TestStaffRequests(unittest.TestCase):
    """Test suite for staff request approval and denial in UserService."""

    def setUp(self):
        """Set up for test methods."""
        self.mock_db_session = MagicMock()
        self.user_service = UserService(self.mock_db_session)

    def test_approve_staff_request_success(self):
        """Test successful approval of a staff request."""
        request_id = 1
        admin_id = 100
        notes = "Approved by admin."

        mock_staff_request = MagicMock(spec=StaffRequest)
        mock_staff_request.id = request_id
        mock_staff_request.user_id = 200
        mock_staff_request.role_requested = 'receptionist'
        mock_staff_request.status = 'pending'

        mock_user = MagicMock(spec=User)
        mock_user.id = 200
        mock_user.role = 'pending'
        mock_user.is_active = False

        # Configure db_session.get to return our mocks
        def get_side_effect(model, record_id):
            if model == StaffRequest and record_id == request_id:
                return mock_staff_request
            if model == User and record_id == mock_staff_request.user_id:
                return mock_user
            return None
        self.mock_db_session.get.side_effect = get_side_effect

        returned_request = self.user_service.approve_staff_request(request_id, admin_id, notes)

        self.assertEqual(returned_request, mock_staff_request)
        self.assertEqual(mock_staff_request.status, 'approved')
        self.assertIsNotNone(mock_staff_request.handled_at)
        self.assertEqual(mock_staff_request.handled_by, admin_id)
        self.assertEqual(mock_staff_request.notes, notes)
        
        self.assertEqual(mock_user.role, 'receptionist')
        self.assertIsNone(mock_user.role_requested)
        self.assertTrue(mock_user.is_active)
        self.mock_db_session.commit.assert_called_once()

    def test_approve_staff_request_not_found(self):
        """Test approving a non-existent staff request."""
        request_id = 999
        admin_id = 100
        self.mock_db_session.get.return_value = None

        with self.assertRaisesRegex(Exception, f"Failed to approve staff request: Staff request with ID {request_id} not found"):
            self.user_service.approve_staff_request(request_id, admin_id)
        self.mock_db_session.rollback.assert_called_once()

    def test_approve_staff_request_user_not_found(self):
        """Test approving a staff request when the associated user is not found."""
        request_id = 1
        admin_id = 100
        mock_staff_request = MagicMock(spec=StaffRequest, user_id=998)

        def get_side_effect(model, record_id):
            if model == StaffRequest and record_id == request_id:
                return mock_staff_request
            if model == User and record_id == mock_staff_request.user_id: # User not found
                return None
            return None
        self.mock_db_session.get.side_effect = get_side_effect
        
        with self.assertRaisesRegex(Exception, f"Failed to approve staff request: User with ID {mock_staff_request.user_id} not found"):
            self.user_service.approve_staff_request(request_id, admin_id)
        self.mock_db_session.rollback.assert_called_once()

    def test_deny_staff_request_success(self):
        """Test successful denial of a staff request."""
        request_id = 2
        admin_id = 101
        notes = "Denied by admin."

        mock_staff_request = MagicMock(spec=StaffRequest)
        mock_staff_request.id = request_id
        mock_staff_request.user_id = 201
        mock_staff_request.status = 'pending'

        mock_user = MagicMock(spec=User)
        mock_user.id = 201
        mock_user.role_requested = 'housekeeping' # User had a role_requested

        def get_side_effect(model, record_id):
            if model == StaffRequest and record_id == request_id:
                return mock_staff_request
            if model == User and record_id == mock_staff_request.user_id:
                return mock_user
            return None
        self.mock_db_session.get.side_effect = get_side_effect

        returned_request = self.user_service.deny_staff_request(request_id, admin_id, notes)

        self.assertEqual(returned_request, mock_staff_request)
        self.assertEqual(mock_staff_request.status, 'denied')
        self.assertIsNotNone(mock_staff_request.handled_at)
        self.assertEqual(mock_staff_request.handled_by, admin_id)
        self.assertEqual(mock_staff_request.notes, notes)

        self.assertIsNone(mock_user.role_requested) # Should be cleared
        self.mock_db_session.commit.assert_called_once()

    def test_deny_staff_request_not_found(self):
        """Test denying a non-existent staff request."""
        request_id = 998
        admin_id = 101
        self.mock_db_session.get.return_value = None

        with self.assertRaisesRegex(Exception, f"Failed to deny staff request: Staff request with ID {request_id} not found"):
            self.user_service.deny_staff_request(request_id, admin_id)
        self.mock_db_session.rollback.assert_called_once()

    # Example of testing the general exception handling in approve/deny if db_session.commit() fails
    def test_approve_request_commit_failure(self):
        request_id = 1
        admin_id = 100
        mock_staff_request = MagicMock(spec=StaffRequest, user_id=1)
        mock_user = MagicMock(spec=User)
        
        def get_side_effect(model, record_id):
            if model == StaffRequest: return mock_staff_request
            if model == User: return mock_user
            return None
        self.mock_db_session.get.side_effect = get_side_effect
        self.mock_db_session.commit.side_effect = Exception("DB Commit Error")

        with self.assertRaisesRegex(Exception, "Failed to approve staff request: DB Commit Error"):
            self.user_service.approve_staff_request(request_id, admin_id)
        self.mock_db_session.rollback.assert_called_once()


if __name__ == '__main__':
    unittest.main() 