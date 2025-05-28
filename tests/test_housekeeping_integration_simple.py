"""
Simple integration tests for the housekeeping dashboard.
"""

import pytest
from flask import url_for


def test_dashboard_metrics_undefined(client, housekeeping_user, login_user):
    """Test that the dashboard correctly handles the case where metrics is undefined."""
    # Log in as housekeeping user
    login_user(housekeeping_user)
    
    # Access the dashboard
    response = client.get(url_for('housekeeping.dashboard'))
    
    # Check response status
    assert response.status_code == 200
    
    # Check that the page loads without errors
    assert b"Housekeeping Dashboard" in response.data
    
    # Check that the dashboard doesn't try to access undefined metrics
    assert b"metrics.error" not in response.data


def test_all_pages_load_without_errors(client, housekeeping_user, login_user):
    """Test that all three pages load without Jinja2 template errors."""
    # Log in as housekeeping user
    login_user(housekeeping_user)
    
    # Test routes to check
    routes = [
        'housekeeping.dashboard',
        'housekeeping.rooms_to_clean_view',
        'housekeeping.checkout_rooms_view',
        'housekeeping.cleaning_schedule'
    ]
    
    # Check each route
    for route in routes:
        response = client.get(url_for(route))
        
        # Check response status
        assert response.status_code == 200, f"Route {route} failed with status {response.status_code}"
        
        # Check that there are no Jinja2 errors in the response
        assert b"jinja2.exceptions" not in response.data
        assert b"UndefinedError" not in response.data
        
        # Check for specific content based on the route
        if route == 'housekeeping.dashboard':
            assert b"Housekeeping Dashboard" in response.data
        elif route == 'housekeeping.rooms_to_clean_view':
            assert b"Rooms to Clean" in response.data
        elif route == 'housekeeping.checkout_rooms_view':
            assert b"Rooms with Checkouts Today" in response.data
        elif route == 'housekeeping.cleaning_schedule':
            assert b"Cleaning Schedule" in response.data
