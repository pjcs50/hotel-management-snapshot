"""
Functional tests for customer search functionality.

This module contains tests for the customer search functionality in the receptionist booking form.
"""

import pytest
import json
from flask import url_for

from app.models.user import User
from app.models.customer import Customer


@pytest.fixture
def setup_customer_search_data(app, db_session):
    """Set up test data for customer search tests."""
    with app.app_context():
        # Create a receptionist user
        receptionist = User(username="receptionist_search", email="receptionist_search@example.com", role="receptionist")
        receptionist.set_password("password")
        
        # Create test customers with various names, emails, and phone numbers
        customers = [
            Customer(name="John Smith", email="john.smith@example.com", phone="555-123-4567"),
            Customer(name="Jane Doe", email="jane.doe@example.com", phone="555-234-5678"),
            Customer(name="Robert Johnson", email="robert.johnson@example.com", phone="555-345-6789"),
            Customer(name="Emily Wilson", email="emily.wilson@example.com", phone="555-456-7890"),
            Customer(name="Michael Brown", email="michael.brown@example.com", phone="555-567-8901"),
            Customer(name="Sarah Davis", email="sarah.davis@example.com", phone="555-678-9012"),
            Customer(name="David Miller", email="david.miller@example.com", phone="555-789-0123"),
            Customer(name="Jennifer Garcia", email="jennifer.garcia@example.com", phone="555-890-1234"),
            Customer(name="James Rodriguez", email="james.rodriguez@example.com", phone="555-901-2345"),
            Customer(name="Lisa Martinez", email="lisa.martinez@example.com", phone="555-012-3456")
        ]
        
        db_session.add(receptionist)
        db_session.add_all(customers)
        db_session.commit()
        
        return {
            'receptionist': receptionist,
            'customers': customers
        }


class TestCustomerSearch:
    """Test suite for customer search functionality."""
    
    def test_search_by_name(self, client, auth, setup_customer_search_data):
        """Test searching for customers by name."""
        # Log in as receptionist
        auth.login(email=setup_customer_search_data['receptionist'].email, password="password")
        
        # Search for a customer by full name
        response = client.get(
            url_for('receptionist.search_customers', q='John Smith'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) == 1
        assert data['customers'][0]['name'] == 'John Smith'
        
        # Search for customers by partial name
        response = client.get(
            url_for('receptionist.search_customers', q='John'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) == 1
        assert data['customers'][0]['name'] == 'John Smith'
        
        # Search for customers by partial name that matches multiple customers
        response = client.get(
            url_for('receptionist.search_customers', q='a'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) > 1
    
    def test_search_by_email(self, client, auth, setup_customer_search_data):
        """Test searching for customers by email."""
        # Log in as receptionist
        auth.login(email=setup_customer_search_data['receptionist'].email, password="password")
        
        # Search for a customer by full email
        response = client.get(
            url_for('receptionist.search_customers', q='jane.doe@example.com'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) == 1
        assert data['customers'][0]['name'] == 'Jane Doe'
        assert data['customers'][0]['email'] == 'jane.doe@example.com'
        
        # Search for customers by partial email
        response = client.get(
            url_for('receptionist.search_customers', q='jane'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) == 1
        assert data['customers'][0]['name'] == 'Jane Doe'
        
        # Search for customers by domain
        response = client.get(
            url_for('receptionist.search_customers', q='example.com'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) > 1
    
    def test_search_by_phone(self, client, auth, setup_customer_search_data):
        """Test searching for customers by phone number."""
        # Log in as receptionist
        auth.login(email=setup_customer_search_data['receptionist'].email, password="password")
        
        # Search for a customer by full phone number
        response = client.get(
            url_for('receptionist.search_customers', q='555-123-4567'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) == 1
        assert data['customers'][0]['name'] == 'John Smith'
        assert data['customers'][0]['phone'] == '555-123-4567'
        
        # Search for customers by partial phone number
        response = client.get(
            url_for('receptionist.search_customers', q='555-123'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) == 1
        assert data['customers'][0]['name'] == 'John Smith'
        
        # Search for customers by area code
        response = client.get(
            url_for('receptionist.search_customers', q='555'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) > 1
    
    def test_search_with_no_results(self, client, auth, setup_customer_search_data):
        """Test searching for customers with no matching results."""
        # Log in as receptionist
        auth.login(email=setup_customer_search_data['receptionist'].email, password="password")
        
        # Search for a non-existent customer
        response = client.get(
            url_for('receptionist.search_customers', q='NonExistentCustomer'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['customers']) == 0
    
    def test_search_with_short_query(self, client, auth, setup_customer_search_data):
        """Test searching for customers with a query that is too short."""
        # Log in as receptionist
        auth.login(email=setup_customer_search_data['receptionist'].email, password="password")
        
        # Search with a single character (should fail)
        response = client.get(
            url_for('receptionist.search_customers', q='J'),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'message' in data
        assert 'at least 2 characters' in data['message']
        
        # Search with no query (should fail)
        response = client.get(
            url_for('receptionist.search_customers', q=''),
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        # Check response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'message' in data
        assert 'at least 2 characters' in data['message']
