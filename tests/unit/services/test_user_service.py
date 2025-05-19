"""
Unit tests for UserService.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.user_service import UserService
from app.models.user import User # Assuming User model structure

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def user_service(mock_db_session):
    return UserService(mock_db_session)

@pytest.fixture
def sample_user():
    user = User(id=1, username='testuser', email='test@example.com', role='customer')
    user.set_password('old_password123') # Set initial password
    return user

def test_change_password_success(user_service, mock_db_session, sample_user):
    """Test successful password change."""
    mock_db_session.get.return_value = sample_user
    
    changed = user_service.change_password(1, 'old_password123', 'new_Password123!')
    
    assert changed is True
    # Check if user.set_password was called with the new password
    # This requires sample_user.set_password to be mockable if we want to assert its call directly,
    # or we check the side effect (password_hash changed).
    # For simplicity, we assume check_password on the user object works.
    assert sample_user.check_password('new_Password123!')
    mock_db_session.commit.assert_called_once()

def test_change_password_user_not_found(user_service, mock_db_session):
    """Test password change when user is not found."""
    mock_db_session.get.return_value = None
    
    with pytest.raises(ValueError, match="User not found"): # Adjusted to expect ValueError as per service code
        user_service.change_password(99, 'old_password123', 'new_Password123!')
    mock_db_session.commit.assert_not_called()

def test_change_password_incorrect_current_password(user_service, mock_db_session, sample_user):
    """Test password change with incorrect current password."""
    mock_db_session.get.return_value = sample_user
    
    with pytest.raises(ValueError, match="Current password does not match."): # Updated expected message
        user_service.change_password(1, 'wrong_old_password', 'new_Password123!')
    mock_db_session.commit.assert_not_called()
    # Ensure password hasn't changed
    assert sample_user.check_password('old_password123') 

# Test for new_password being same as current_password (if this logic is added to service later)
# def test_change_password_new_is_same_as_current(user_service, mock_db_session, sample_user):
#     mock_db_session.get.return_value = sample_user
#     with pytest.raises(ValueError, match="New password cannot be the same as the current password."):
#         user_service.change_password(1, 'old_password123', 'old_password123')
#     mock_db_session.commit.assert_not_called() 