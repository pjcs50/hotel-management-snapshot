"""
Simple test for housekeeping routes.
"""

import pytest
from flask import url_for


def test_housekeeping_routes_accessible(client, housekeeping_user, login_user):
    """Test that housekeeping routes are accessible."""
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
