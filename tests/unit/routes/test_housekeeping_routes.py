"""
Unit tests for housekeeping routes.

This module contains tests for the housekeeping routes, specifically:
- rooms_to_clean_view
- checkout_rooms_view
- cleaning_schedule
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import url_for, template_rendered
from contextlib import contextmanager

from app.models.room import Room
from app.models.booking import Booking
from app.models.housekeeping_task import HousekeepingTask
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


class TestHousekeepingRoutes:
    """Test class for housekeeping routes."""

    def test_rooms_to_clean_view(self, client, app, db_session, housekeeping_user, login_user):
        """Test the rooms_to_clean_view route."""
        # Log in as housekeeping user
        login_user(housekeeping_user)

        # Create test rooms with different statuses
        rooms = [
            Room(number="101", status="dirty", room_type_id=1),
            Room(number="102", status="checkout", room_type_id=1),
            Room(number="103", status="clean", room_type_id=1),
            Room(number="201", status="dirty", room_type_id=2),
            Room(number="202", status="occupied", room_type_id=2),
        ]
        for room in rooms:
            db_session.add(room)
        db_session.commit()

        # Access the rooms_to_clean_view route
        with captured_templates(app) as templates:
            response = client.get(url_for('housekeeping.rooms_to_clean_view'))

            # Check response status
            assert response.status_code == 200

            # Check that the correct template was rendered
            assert len(templates) == 1
            template, context = templates[0]
            assert template.name == 'housekeeping/rooms_to_clean.html'

            # Check that only dirty and checkout rooms are included
            assert len(context['rooms_by_floor']) > 0

            # Count total rooms that should be displayed
            total_rooms = 0
            for floor, rooms in context['rooms_by_floor'].items():
                for room in rooms:
                    assert room.status in ['dirty', 'checkout']
                    total_rooms += 1

            # Verify total count matches expected
            assert total_rooms == 3
            assert context['total_rooms'] == 3

    def test_checkout_rooms_view(self, client, app, db_session, housekeeping_user, login_user):
        """Test the checkout_rooms_view route."""
        # Log in as housekeeping user
        login_user(housekeeping_user)

        # Create test rooms
        rooms = [
            Room(id=1, number="101", status="occupied", room_type_id=1),
            Room(id=2, number="102", status="occupied", room_type_id=1),
            Room(id=3, number="103", status="clean", room_type_id=1),
        ]
        for room in rooms:
            db_session.add(room)

        # Create test customers
        customers = [
            Customer(id=1, name="John Doe", email="john@example.com", phone="123-456-7890"),
            Customer(id=2, name="Jane Smith", email="jane@example.com", phone="123-456-7891"),
            Customer(id=3, name="Bob Johnson", email="bob@example.com", phone="123-456-7892"),
        ]
        for customer in customers:
            db_session.add(customer)
        db_session.commit()

        # Create test bookings with different checkout dates
        today = datetime.now().date()
        bookings = [
            # Today's checkout
            Booking(
                room_id=1,
                customer_id=1,
                check_in_date=today - timedelta(days=2),
                check_out_date=today,
                status="checked_in",
                guest_name="John Doe"
            ),
            # Tomorrow's checkout
            Booking(
                room_id=2,
                customer_id=2,
                check_in_date=today - timedelta(days=1),
                check_out_date=today + timedelta(days=1),
                status="checked_in",
                guest_name="Jane Smith"
            ),
            # Yesterday's checkout (already completed)
            Booking(
                room_id=3,
                customer_id=3,
                check_in_date=today - timedelta(days=3),
                check_out_date=today - timedelta(days=1),
                status="completed",
                guest_name="Bob Johnson"
            ),
        ]
        for booking in bookings:
            db_session.add(booking)
        db_session.commit()

        # Access the checkout_rooms_view route
        with captured_templates(app) as templates:
            response = client.get(url_for('housekeeping.checkout_rooms_view'))

            # Check response status
            assert response.status_code == 200

            # Check that the correct template was rendered
            assert len(templates) == 1
            template, context = templates[0]
            assert template.name == 'housekeeping/checkout_rooms.html'

            # Check that only today's checkouts are included
            assert len(context['bookings']) == 1
            assert context['bookings'][0].guest_name == "John Doe"
            assert context['bookings'][0].check_out_date.date() == today

    def test_cleaning_schedule(self, client, app, db_session, housekeeping_user, login_user):
        """Test the cleaning_schedule route."""
        # Log in as housekeeping user
        login_user(housekeeping_user)

        # Create test rooms
        rooms = [
            Room(id=1, number="101", status="occupied", room_type_id=1),
            Room(id=2, number="102", status="occupied", room_type_id=1),
            Room(id=3, number="103", status="clean", room_type_id=1),
        ]
        for room in rooms:
            db_session.add(room)

        # Create test customers
        customers = [
            Customer(id=1, name="John Doe", email="john@example.com", phone="123-456-7890"),
            Customer(id=2, name="Jane Smith", email="jane@example.com", phone="123-456-7891"),
        ]
        for customer in customers:
            db_session.add(customer)
        db_session.commit()

        # Create test bookings with different checkout dates
        today = datetime.now().date()
        bookings = [
            # Today's checkout
            Booking(
                room_id=1,
                customer_id=1,
                check_in_date=today - timedelta(days=2),
                check_out_date=today,
                status="checked_in",
                guest_name="John Doe"
            ),
            # Tomorrow's checkout
            Booking(
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

        # Create test housekeeping tasks
        tasks = [
            # Today's task
            HousekeepingTask(
                room_id=1,
                task_type="regular_cleaning",
                status="pending",
                priority="normal",
                due_date=today,
                description="Regular cleaning for room 101"
            ),
            # Tomorrow's task
            HousekeepingTask(
                room_id=2,
                task_type="deep_cleaning",
                status="pending",
                priority="high",
                due_date=today + timedelta(days=1),
                description="Deep cleaning for room 102"
            ),
            # Completed task (should not appear in schedule)
            HousekeepingTask(
                room_id=3,
                task_type="regular_cleaning",
                status="completed",
                priority="normal",
                due_date=today,
                description="Regular cleaning for room 103"
            ),
        ]
        for task in tasks:
            db_session.add(task)

        db_session.commit()

        # Access the cleaning_schedule route
        with captured_templates(app) as templates:
            response = client.get(url_for('housekeeping.cleaning_schedule'))

            # Check response status
            assert response.status_code == 200

            # Check that the correct template was rendered
            assert len(templates) == 1
            template, context = templates[0]
            assert template.name == 'housekeeping/cleaning_schedule.html'

            # Check that days are organized correctly
            assert len(context['days']) == 7  # A week of days

            # Check that the now() function is passed to the template
            assert 'now' in context
            assert callable(context['now'])

            # Check that today's date is included
            assert context['start_date'] <= today <= context['end_date']

            # Find today in the days list
            today_data = None
            for day in context['days']:
                if day['date'] == today:
                    today_data = day
                    break

            assert today_data is not None
            assert len(today_data['tasks']) == 1
            assert len(today_data['checkouts']) == 1
            assert today_data['total'] == 2
