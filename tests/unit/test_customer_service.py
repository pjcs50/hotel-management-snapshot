"""
Unit tests for the customer service.

This module contains tests for the CustomerService class.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.customer_service import CustomerService, DuplicateUserError
from app.models.customer import Customer
from app.models.user import User


class TestCustomerService:
    """Tests for the CustomerService class."""
    
    def test_get_customer_by_user_id(self, db_session):
        """Test getting a customer by user ID."""
        # Arrange
        customer_service = CustomerService(db_session)
        
        # Mock customer
        expected_customer = MagicMock(spec=Customer)
        expected_customer.user_id = 1
        
        # Mock query
        with patch('app.models.customer.Customer.query') as mock_query:
            mock_query.filter_by.return_value.first.return_value = expected_customer
            
            # Act
            result = customer_service.get_customer_by_user_id(1)
            
            # Assert
            assert result == expected_customer
            mock_query.filter_by.assert_called_with(user_id=1)
    
    def test_create_customer_success(self, db_session):
        """Test creating a customer successfully."""
        # Arrange
        mock_db_session = MagicMock()
        customer_service = CustomerService(mock_db_session)
        
        # Mock user
        user = MagicMock(spec=User)
        user.id = 1
        
        # Mock queries
        with patch('app.models.user.User.query') as mock_user_query:
            mock_user_query.get.return_value = user
            with patch('app.models.customer.Customer.query') as mock_customer_query:
                mock_customer_query.filter_by.return_value.first.return_value = None
                
                # Act
                result = customer_service.create_customer(
                    user_id=1,
                    name="John Doe",
                    phone="555-1234",
                    address="123 Main St"
                )
                
                # Assert
                assert result is not None
                assert result.user_id == 1
                assert result.name == "John Doe"
                assert result.phone == "555-1234"
                assert result.address == "123 Main St"
                assert result.profile_complete == True
                mock_db_session.add.assert_called_once()
                mock_db_session.commit.assert_called_once()
    
    def test_create_customer_duplicate_user(self, db_session):
        """Test that creating a customer with a duplicate user ID raises an error."""
        # Arrange
        customer_service = CustomerService(db_session)
        
        # Mock user
        user = MagicMock(spec=User)
        user.id = 1
        
        # Mock existing customer
        existing_customer = MagicMock(spec=Customer)
        existing_customer.user_id = 1
        
        # Mock queries
        with patch('app.models.user.User.query') as mock_user_query:
            mock_user_query.get.return_value = user
            with patch('app.models.customer.Customer.query') as mock_customer_query:
                mock_customer_query.filter_by.return_value.first.return_value = existing_customer
                
                # Act & Assert
                with pytest.raises(DuplicateUserError):
                    customer_service.create_customer(
                        user_id=1,
                        name="John Doe",
                        phone="555-1234"
                    )
    
    def test_update_customer_success(self, db_session):
        """Test updating a customer successfully."""
        # Arrange
        mock_db_session = MagicMock()
        customer_service = CustomerService(mock_db_session)
        
        # Mock customer
        customer = MagicMock(spec=Customer)
        customer.id = 1
        customer.name = "John Doe"
        customer.phone = "555-1234"
        
        # Mock query
        with patch('app.models.customer.Customer.query') as mock_query:
            mock_query.get.return_value = customer
            
            # Act
            result = customer_service.update_customer(
                customer_id=1,
                name="Jane Doe",
                phone="555-5678"
            )
            
            # Assert
            assert result is not None
            assert result.name == "Jane Doe"
            assert result.phone == "555-5678"
            assert result.profile_complete == True
            mock_db_session.commit.assert_called_once() 