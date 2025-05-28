"""
Simple unit tests for customer search functionality.

This module contains tests for the customer search functionality
without relying on database operations.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from flask import Flask

from app.routes.receptionist import search_customers
from app.models.customer import Customer


@pytest.fixture
def app():
    """Create a Flask application for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def mock_customers():
    """Create mock customer data for testing."""
    customers = [
        Customer(id=1, name="John Smith", email="john.smith@example.com", phone="555-123-4567"),
        Customer(id=2, name="Jane Doe", email="jane.doe@example.com", phone="555-234-5678"),
        Customer(id=3, name="Robert Johnson", email="robert.johnson@example.com", phone="555-345-6789"),
        Customer(id=4, name="Emily Wilson", email="emily.wilson@example.com", phone="555-456-7890"),
        Customer(id=5, name="Michael Brown", email="michael.brown@example.com", phone="555-567-8901")
    ]
    return customers


class TestCustomerSearch:
    """Test suite for customer search functionality."""

    @patch('app.routes.receptionist.Customer')
    def test_search_by_name(self, mock_customer_model, app):
        """Test searching for customers by name."""
        with app.test_request_context('/search-customers?q=John'):
            # Set up mock query
            mock_query = MagicMock()
            mock_customer_model.query.filter.return_value.limit.return_value.all.return_value = [
                Customer(id=1, name="John Smith", email="john.smith@example.com", phone="555-123-4567")
            ]
            
            # Call the function
            response = search_customers()
            
            # Parse the response
            data = json.loads(response.data)
            
            # Check the response
            assert data['success'] is True
            assert len(data['customers']) == 1
            assert data['customers'][0]['name'] == 'John Smith'
            assert data['customers'][0]['email'] == 'john.smith@example.com'
            assert data['customers'][0]['phone'] == '555-123-4567'

    @patch('app.routes.receptionist.Customer')
    def test_search_by_email(self, mock_customer_model, app):
        """Test searching for customers by email."""
        with app.test_request_context('/search-customers?q=jane.doe'):
            # Set up mock query
            mock_query = MagicMock()
            mock_customer_model.query.filter.return_value.limit.return_value.all.return_value = [
                Customer(id=2, name="Jane Doe", email="jane.doe@example.com", phone="555-234-5678")
            ]
            
            # Call the function
            response = search_customers()
            
            # Parse the response
            data = json.loads(response.data)
            
            # Check the response
            assert data['success'] is True
            assert len(data['customers']) == 1
            assert data['customers'][0]['name'] == 'Jane Doe'
            assert data['customers'][0]['email'] == 'jane.doe@example.com'
            assert data['customers'][0]['phone'] == '555-234-5678'

    @patch('app.routes.receptionist.Customer')
    def test_search_by_phone(self, mock_customer_model, app):
        """Test searching for customers by phone number."""
        with app.test_request_context('/search-customers?q=555-345'):
            # Set up mock query
            mock_query = MagicMock()
            mock_customer_model.query.filter.return_value.limit.return_value.all.return_value = [
                Customer(id=3, name="Robert Johnson", email="robert.johnson@example.com", phone="555-345-6789")
            ]
            
            # Call the function
            response = search_customers()
            
            # Parse the response
            data = json.loads(response.data)
            
            # Check the response
            assert data['success'] is True
            assert len(data['customers']) == 1
            assert data['customers'][0]['name'] == 'Robert Johnson'
            assert data['customers'][0]['email'] == 'robert.johnson@example.com'
            assert data['customers'][0]['phone'] == '555-345-6789'

    @patch('app.routes.receptionist.Customer')
    def test_search_with_multiple_results(self, mock_customer_model, app):
        """Test searching for customers with multiple results."""
        with app.test_request_context('/search-customers?q=example.com'):
            # Set up mock query
            mock_query = MagicMock()
            mock_customer_model.query.filter.return_value.limit.return_value.all.return_value = [
                Customer(id=1, name="John Smith", email="john.smith@example.com", phone="555-123-4567"),
                Customer(id=2, name="Jane Doe", email="jane.doe@example.com", phone="555-234-5678")
            ]
            
            # Call the function
            response = search_customers()
            
            # Parse the response
            data = json.loads(response.data)
            
            # Check the response
            assert data['success'] is True
            assert len(data['customers']) == 2
            assert data['customers'][0]['name'] == 'John Smith'
            assert data['customers'][1]['name'] == 'Jane Doe'

    @patch('app.routes.receptionist.Customer')
    def test_search_with_no_results(self, mock_customer_model, app):
        """Test searching for customers with no matching results."""
        with app.test_request_context('/search-customers?q=NonExistentCustomer'):
            # Set up mock query
            mock_query = MagicMock()
            mock_customer_model.query.filter.return_value.limit.return_value.all.return_value = []
            
            # Call the function
            response = search_customers()
            
            # Parse the response
            data = json.loads(response.data)
            
            # Check the response
            assert data['success'] is True
            assert len(data['customers']) == 0

    @patch('app.routes.receptionist.Customer')
    def test_search_with_short_query(self, mock_customer_model, app):
        """Test searching for customers with a query that is too short."""
        with app.test_request_context('/search-customers?q=J'):
            # Call the function
            response = search_customers()
            
            # Parse the response
            data = json.loads(response.data)
            
            # Check the response
            assert data['success'] is False
            assert 'message' in data
            assert 'at least 2 characters' in data['message']

    @patch('app.routes.receptionist.Customer')
    def test_search_with_no_query(self, mock_customer_model, app):
        """Test searching for customers with no query."""
        with app.test_request_context('/search-customers'):
            # Call the function
            response = search_customers()
            
            # Parse the response
            data = json.loads(response.data)
            
            # Check the response
            assert data['success'] is False
            assert 'message' in data
            assert 'at least 2 characters' in data['message']
