"""
Simple tests for housekeeping templates.
"""

import pytest
from flask import url_for, template_rendered
from contextlib import contextmanager


@contextmanager
def captured_templates(app):
    """Context manager to capture templates rendered during a request."""
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def test_rooms_to_clean_template(client, app, housekeeping_user, login_user):
    """Test the rooms_to_clean.html template."""
    # Log in as housekeeping user
    login_user(housekeeping_user)
    
    # Access the rooms_to_clean_view route
    with captured_templates(app) as templates:
        response = client.get(url_for('housekeeping.rooms_to_clean_view'))
        
        # Check response status
        assert response.status_code == 200
        
        # Check that the correct template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'housekeeping/rooms_to_clean.html'
        
        # Check that the rooms_by_floor is in the context
        assert 'rooms_by_floor' in context


def test_checkout_rooms_template(client, app, housekeeping_user, login_user):
    """Test the checkout_rooms.html template."""
    # Log in as housekeeping user
    login_user(housekeeping_user)
    
    # Access the checkout_rooms_view route
    with captured_templates(app) as templates:
        response = client.get(url_for('housekeeping.checkout_rooms_view'))
        
        # Check response status
        assert response.status_code == 200
        
        # Check that the correct template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'housekeeping/checkout_rooms.html'
        
        # Check that the bookings is in the context
        assert 'bookings' in context


def test_cleaning_schedule_template(client, app, housekeeping_user, login_user):
    """Test the cleaning_schedule.html template."""
    # Log in as housekeeping user
    login_user(housekeeping_user)
    
    # Access the cleaning_schedule route
    with captured_templates(app) as templates:
        response = client.get(url_for('housekeeping.cleaning_schedule'))
        
        # Check response status
        assert response.status_code == 200
        
        # Check that the correct template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'housekeeping/cleaning_schedule.html'
        
        # Check that the days is in the context
        assert 'days' in context
        
        # Check that the now() function is passed to the template
        assert 'now' in context
        assert callable(context['now'])
