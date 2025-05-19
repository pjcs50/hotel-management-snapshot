"""
Functional tests for manager analytics routes.

This module tests the analytics dashboard functionality for managers.
"""

import pytest
from flask import url_for
import json
from datetime import datetime


def test_analytics_dashboard_view(client, manager_user, auth):
    """Test the analytics dashboard view."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Access analytics dashboard
    response = client.get(url_for('manager.analytics'))
    assert response.status_code == 200
    
    # Check if chart containers exist
    content = response.data.decode('utf-8')
    assert 'occupancyChart' in content
    assert 'revenueChart' in content
    assert 'topCustomersContainer' in content
    assert 'bookingSourcesChart' in content
    assert 'forecastChart' in content
    
    # Check if filter controls exist
    assert 'yearSelect' in content
    assert 'monthSelect' in content


def test_analytics_with_year_filter(client, manager_user, auth):
    """Test the analytics dashboard with year filter."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Access analytics dashboard with year filter
    current_year = datetime.now().year
    response = client.get(url_for('manager.analytics', year=current_year-1))
    assert response.status_code == 200
    
    # Check if year is applied
    content = response.data.decode('utf-8')
    assert f'value="{current_year-1}" selected' in content


def test_analytics_with_month_filter(client, manager_user, auth):
    """Test the analytics dashboard with month filter."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Access analytics dashboard with year and month filter
    current_year = datetime.now().year
    month = 6  # June
    response = client.get(url_for('manager.analytics', year=current_year, month=month))
    assert response.status_code == 200
    
    # Check if month is applied
    content = response.data.decode('utf-8')
    assert f'value="{month}" selected' in content


def test_monthly_occupancy_data_api(client, manager_user, auth):
    """Test the monthly occupancy data API."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Request occupancy chart data
    current_year = datetime.now().year
    response = client.get(url_for('manager.analytics_data', chart='occupancy', year=current_year))
    assert response.status_code == 200
    
    # Parse response as JSON
    data = json.loads(response.data)
    
    # Verify structure
    assert 'labels' in data
    assert 'datasets' in data
    assert len(data['labels']) == 12  # 12 months
    assert len(data['datasets']) == 1
    assert len(data['datasets'][0]['data']) == 12
    
    # Verify months
    expected_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    assert data['labels'] == expected_months


def test_revenue_by_room_type_api(client, manager_user, auth):
    """Test the revenue by room type API."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Request revenue chart data
    current_year = datetime.now().year
    response = client.get(url_for('manager.analytics_data', chart='revenue', year=current_year))
    assert response.status_code == 200
    
    # Parse response as JSON
    data = json.loads(response.data)
    
    # Verify structure
    assert 'labels' in data
    assert 'datasets' in data
    assert len(data['datasets']) == 1
    assert 'data' in data['datasets'][0]
    
    # Test with month filter
    response = client.get(url_for('manager.analytics_data', chart='revenue', year=current_year, month=1))
    assert response.status_code == 200
    
    # Parse response as JSON
    data = json.loads(response.data)
    assert 'labels' in data
    assert 'datasets' in data


def test_top_customers_api(client, manager_user, auth):
    """Test the top customers API."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Request top customers data
    response = client.get(url_for('manager.analytics_data', chart='top_customers', limit=5))
    assert response.status_code == 200
    
    # Parse response as JSON
    data = json.loads(response.data)
    
    # Verify it's a list (might be empty if no bookings)
    assert isinstance(data, list)
    
    # If there are customers, verify structure
    if len(data) > 0:
        customer = data[0]
        assert 'id' in customer
        assert 'username' in customer
        assert 'email' in customer
        assert 'total_spend' in customer
        assert 'booking_count' in customer


def test_booking_sources_api(client, manager_user, auth):
    """Test the booking sources API."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Request booking sources data
    response = client.get(url_for('manager.analytics_data', chart='booking_sources'))
    assert response.status_code == 200
    
    # Parse response as JSON
    data = json.loads(response.data)
    
    # Verify structure
    assert 'labels' in data
    assert 'datasets' in data
    assert len(data['datasets']) == 1
    assert 'data' in data['datasets'][0]
    
    # Verify percentages sum to 100
    assert sum(data['datasets'][0]['data']) == 100


def test_forecast_data_api(client, manager_user, auth):
    """Test the forecast data API."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Request forecast data with default days (30)
    response = client.get(url_for('manager.analytics_data', chart='forecast'))
    assert response.status_code == 200
    
    # Parse response as JSON
    data = json.loads(response.data)
    
    # Verify structure
    assert 'labels' in data
    assert 'datasets' in data
    assert len(data['labels']) == 30  # Default is 30 days
    assert len(data['datasets']) == 1
    assert len(data['datasets'][0]['data']) == 30
    
    # Test with custom days
    response = client.get(url_for('manager.analytics_data', chart='forecast', days=7))
    assert response.status_code == 200
    
    # Parse response as JSON
    data = json.loads(response.data)
    assert len(data['labels']) == 7
    assert len(data['datasets'][0]['data']) == 7


def test_invalid_chart_type(client, manager_user, auth):
    """Test requesting an invalid chart type."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Request invalid chart type
    response = client.get(url_for('manager.analytics_data', chart='invalid_chart'))
    assert response.status_code == 200
    
    # Parse response as JSON
    data = json.loads(response.data)
    
    # Should return an error
    assert 'error' in data 