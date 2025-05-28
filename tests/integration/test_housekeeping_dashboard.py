"""
Integration tests for the housekeeping dashboard.

This module contains integration tests for the housekeeping dashboard, specifically:
- Testing that the dashboard correctly handles the case where metrics is undefined
- Testing that the now() function is correctly passed to the cleaning_schedule template
- Testing that all three pages load without Jinja2 template errors
"""

import pytest
import re
from datetime import datetime, timedelta
from flask import url_for, template_rendered
from contextlib import contextmanager

from app.models.room import Room
from app.models.booking import Booking
from app.models.housekeeping_task import HousekeepingTask
from app.models.room_type import RoomType
from app.models.customer import Customer


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


class TestHousekeepingDashboardIntegration:
    """Integration tests for the housekeeping dashboard."""

    def setup_test_data(self, db_session):
        """Set up test data for the integration tests."""
        # Create room types
        room_types = [
            RoomType(id=1, name="Standard", base_rate=100),
            RoomType(id=2, name="Deluxe", base_rate=150),
        ]
        for room_type in room_types:
            db_session.add(room_type)

        # Create rooms with different statuses
        rooms = [
            Room(id=1, number="101", status="dirty", room_type_id=1),
            Room(id=2, number="102", status="checkout", room_type_id=1),
            Room(id=3, number="103", status="clean", room_type_id=1),
            Room(id=4, number="201", status="dirty", room_type_id=2),
            Room(id=5, number="202", status="occupied", room_type_id=2),
        ]
        for room in rooms:
            db_session.add(room)

        # Create customers
        customers = [
            Customer(id=1, name="John Doe", email="john@example.com", phone="123-456-7890"),
            Customer(id=2, name="Jane Smith", email="jane@example.com", phone="123-456-7891"),
        ]
        for customer in customers:
            db_session.add(customer)
        db_session.commit()

        # Create bookings
        today = datetime.now().date()
        bookings = [
            # Today's checkout
            Booking(
                id=1,
                room_id=1,
                customer_id=1,
                check_in_date=today - timedelta(days=2),
                check_out_date=today,
                status="checked_in",
                guest_name="John Doe"
            ),
            # Tomorrow's checkout
            Booking(
                id=2,
                room_id=2,
                customer_id=2,
                check_in_date=today - timedelta(days=1),
                check_out_date=today + timedelta(days=1),
                status="checked_in",
                guest_name="Jane Smith"
            ),
        ]
        for booking in bookings:
            db_session.add(booking)

        # Create housekeeping tasks
        tasks = [
            # Today's task
            HousekeepingTask(
                id=1,
                room_id=1,
                task_type="regular_cleaning",
                status="pending",
                priority="normal",
                due_date=today,
                description="Regular cleaning for room 101"
            ),
            # Tomorrow's task
            HousekeepingTask(
                id=2,
                room_id=2,
                task_type="deep_cleaning",
                status="pending",
                priority="high",
                due_date=today + timedelta(days=1),
                description="Deep cleaning for room 102"
            ),
        ]
        for task in tasks:
            db_session.add(task)

        db_session.commit()

        return {
            'rooms': rooms,
            'bookings': bookings,
            'tasks': tasks,
            'today': today
        }

    def test_dashboard_metrics_undefined(self, client, app, db_session, housekeeping_user, login_user):
        """Test that the dashboard correctly handles the case where metrics is undefined."""
        # Log in as housekeeping user
        login_user(housekeeping_user)

        # Set up test data
        self.setup_test_data(db_session)

        # Access the dashboard
        response = client.get(url_for('housekeeping.dashboard'))

        # Check response status
        assert response.status_code == 200

        # Check that the page loads without errors
        assert b"Housekeeping Dashboard" in response.data

        # Check that the dashboard doesn't try to access undefined metrics
        assert b"metrics.error" not in response.data

    def test_now_function_in_cleaning_schedule(self, client, app, db_session, housekeeping_user, login_user):
        """Test that the now() function is correctly passed to the cleaning_schedule template."""
        # Log in as housekeeping user
        login_user(housekeeping_user)

        # Set up test data
        test_data = self.setup_test_data(db_session)

        # Access the cleaning schedule
        with captured_templates(app) as templates:
            response = client.get(url_for('housekeeping.cleaning_schedule'))

            # Check response status
            assert response.status_code == 200

            # Check that the correct template was rendered
            assert len(templates) == 1
            template, context = templates[0]
            assert template.name == 'housekeeping/cleaning_schedule.html'

            # Check that the now() function is passed to the template
            assert 'now' in context
            assert callable(context['now'])

            # Check that the now() function returns the current time
            now_result = context['now']()
            assert isinstance(now_result, datetime)

            # Check that the "Today" badge is displayed for today's date
            today_str = test_data['today'].strftime('%Y-%m-%d')
            assert f'if day.date.strftime(\'%Y-%m-%d\') == start_date.strftime(\'%Y-%m-%d\')' in template.render(context)

    def test_all_pages_load_without_errors(self, client, app, db_session, housekeeping_user, login_user):
        """Test that all three pages load without Jinja2 template errors."""
        # Log in as housekeeping user
        login_user(housekeeping_user)

        # Set up test data
        self.setup_test_data(db_session)

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

    def test_edge_case_no_data(self, client, app, db_session, housekeeping_user, login_user):
        """Test the edge case where there is no data to display."""
        # Log in as housekeeping user
        login_user(housekeeping_user)

        # Don't set up any test data - we want to test with empty database

        # Test routes to check
        routes = [
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

            # Check for appropriate "no data" messages based on the route
            if route == 'housekeeping.rooms_to_clean_view':
                # Either no rooms message or empty table
                assert b"No rooms to clean" in response.data or b"<tbody></tbody>" in response.data
            elif route == 'housekeeping.checkout_rooms_view':
                assert b"No checkouts today" in response.data or b"There are no scheduled checkouts for today" in response.data
            elif route == 'housekeeping.cleaning_schedule':
                assert b"No scheduled tasks or checkouts for this day" in response.data

    def test_dashboard_base_template_metrics(self, client, app, db_session, housekeeping_user, login_user):
        """Test that the dashboard_base.html template correctly handles metrics."""
        # Log in as housekeeping user
        login_user(housekeeping_user)

        # Set up test data
        self.setup_test_data(db_session)

        # Access the dashboard
        with captured_templates(app) as templates:
            response = client.get(url_for('housekeeping.dashboard'))

            # Check response status
            assert response.status_code == 200

            # Check that the correct template was rendered
            assert any(t.name == 'dashboard_base.html' for t, _ in templates)

            # Check that the dashboard_base.html template is correctly handling metrics
            # by checking that there are no Jinja2 errors in the response
            assert b"jinja2.exceptions" not in response.data
            assert b"UndefinedError" not in response.data

            # Check the HTML content to ensure the metrics check is properly implemented
            html_content = response.data.decode('utf-8')

            # Look for the pattern that checks if metrics is defined
            # This could be either {% if metrics is defined and metrics.error %}
            # or {% if metrics and metrics.error %}
            metrics_check_pattern = re.compile(r'{%\s*if\s+metrics(\s+is\s+defined)?(\s+and\s+metrics\.error)?\s*%}')

            # If we find the pattern in any of the templates, that's good
            templates_content = ''.join([t.render() for t, _ in templates if hasattr(t, 'render')])
            assert metrics_check_pattern.search(templates_content) or metrics_check_pattern.search(html_content)
