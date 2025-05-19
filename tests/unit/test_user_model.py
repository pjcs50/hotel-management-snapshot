"""
Unit tests for User model.

Tests user registration, validation, and authentication functionality.
"""

import pytest
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.models.user import User
from app.services.user_service import UserService, DuplicateEmailError


class TestUserModel:
    """Test suite for User model functionality."""

    def test_create_user(self, db_session):
        """Test basic user creation."""
        user = User(
            username="testuser_model_create",
            email="test_model_create@example.com",
            role="customer"
        )
        user.set_password("password123")
        
        db_session.add(user)
        db_session.commit()
        
        retrieved_user = db_session.get(User, user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.email == "test_model_create@example.com"
        assert retrieved_user.role == "customer"
        assert retrieved_user.is_active is True
        assert check_password_hash(retrieved_user.password_hash, "password123")

    def test_reject_duplicate_email(self, db_session):
        """Test that users with duplicate emails are rejected."""
        # Create first user
        user1 = User(
            username="user1_model_dup",
            email="duplicate_model@example.com",
            role="customer"
        )
        user1.set_password("password123")
        db_session.add(user1)
        db_session.commit()
        
        # Try to create second user with same email
        user2 = User(
            username="user2_model_dup",
            email="duplicate_model@example.com",
            role="customer"
        )
        user2.set_password("password456")
        db_session.add(user2)
        
        # Should raise an integrity error due to unique constraint
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_service_create_with_duplicate_email(self, db_session):
        """Test UserService raises appropriate error for duplicate email."""
        service = UserService(db_session)
        
        # Create first user
        service.create_user(
            username="service_user1",
            email="service_duplicate@example.com",
            password="password123",
            role="customer"
        )
        
        # Try to create second user with same email
        with pytest.raises(DuplicateEmailError):
            service.create_user(
                username="service_user2",
                email="service_duplicate@example.com",
                password="password456",
                role="customer"
            )

    def test_create_staff_with_approval_required(self, db_session):
        """Test staff creation with pending approval."""
        service = UserService(db_session)
        
        user = service.create_staff(
            username="staff_user",
            email="staff@example.com",
            password="password123",
            role_requested="receptionist"
        )
        
        assert user.is_active is False
        assert user.role == "pending"
        assert user.role_requested == "receptionist"
        
        # Check that a staff request was created
        from app.models.staff_request import StaffRequest
        
        # Ensure user has an ID after commit by UserService
        assert user.id is not None
        
        request = db_session.execute(
            select(StaffRequest).filter_by(user_id=user.id)
        ).scalar_one_or_none()
        
        assert request is not None
        assert request.status == "pending" 