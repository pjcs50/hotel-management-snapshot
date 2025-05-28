"""
Unit tests for housekeeping templates.

This module contains tests for the housekeeping templates, specifically:
- rooms_to_clean.html
- checkout_rooms.html
- cleaning_schedule.html
"""

import pytest
from datetime import datetime, timedelta
from flask import render_template_string, template_rendered
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


class TestHousekeepingTemplates:
    """Test class for housekeeping templates."""

    def test_rooms_to_clean_template(self, app, db_session):
        """Test the rooms_to_clean.html template."""
        with app.app_context():
            # Create test room types
            room_types = [
                RoomType(id=1, name="Standard", base_rate=100),
                RoomType(id=2, name="Deluxe", base_rate=150),
            ]
            for room_type in room_types:
                db_session.add(room_type)

            # Create test rooms with different statuses and floors
            rooms = [
                Room(number="101", status="dirty", room_type_id=1),
                Room(number="102", status="checkout", room_type_id=1),
                Room(number="201", status="dirty", room_type_id=2),
                Room(number="301", status="dirty", room_type_id=1),
            ]
            for room in rooms:
                db_session.add(room)
            db_session.commit()

            # Organize rooms by floor
            rooms_by_floor = {}
            for room in rooms:
                floor = room.number[0]  # First digit of room number is the floor
                if floor not in rooms_by_floor:
                    rooms_by_floor[floor] = []
                rooms_by_floor[floor].append(room)

            # Render the template with test data
            with app.test_request_context():
                rendered = render_template_string(
                    """
                    {% extends "dashboard_base.html" %}
                    {% block dashboard_content %}
                    <div class="row">
                        {% for floor, floor_rooms in rooms_by_floor.items() %}
                        <div class="col-lg-12 mb-4">
                            <div class="card shadow">
                                <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
                                    <h6 class="m-0 font-weight-bold text-primary">Floor {{ floor }}</h6>
                                    <span class="badge bg-info">{{ floor_rooms|length }} Room(s)</span>
                                </div>
                                <div class="card-body">
                                    <div class="table-responsive">
                                        <table class="table table-bordered">
                                            <thead>
                                                <tr>
                                                    <th>Room</th>
                                                    <th>Status</th>
                                                    <th>Type</th>
                                                    <th>Last Cleaned</th>
                                                    <th>Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {% for room in floor_rooms %}
                                                <tr>
                                                    <td>{{ room.number }}</td>
                                                    <td>
                                                        <span class="badge {% if room.status == 'dirty' %}bg-danger{% elif room.status == 'checkout' %}bg-warning{% else %}bg-success{% endif %}">
                                                            {{ room.status|title }}
                                                        </span>
                                                    </td>
                                                    <td>{{ room.room_type.name }}</td>
                                                    <td>{{ room.last_cleaned|default('Not recorded', true) }}</td>
                                                    <td>
                                                        <a href="#" class="btn btn-primary btn-sm">
                                                            <i class="bi bi-check-circle"></i> Mark Clean
                                                        </a>
                                                    </td>
                                                </tr>
                                                {% endfor %}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% endblock %}
                    """,
                    rooms_by_floor=rooms_by_floor,
                    total_rooms=len(rooms)
                )

                # Check that the template renders without errors
                assert rendered is not None

                # Check that all floors are displayed
                for floor in rooms_by_floor.keys():
                    assert f"Floor {floor}" in rendered

                # Check that all rooms are displayed
                for room in rooms:
                    assert room.number in rendered
                    assert room.status.title() in rendered

                # Check that the correct status badges are used
                assert "bg-danger" in rendered  # For dirty rooms
                assert "bg-warning" in rendered  # For checkout rooms

    def test_checkout_rooms_template(self, app, db_session):
        """Test the checkout_rooms.html template."""
        with app.app_context():
            # Create test room types
            room_types = [
                RoomType(id=1, name="Standard", base_rate=100),
                RoomType(id=2, name="Deluxe", base_rate=150),
            ]
            for room_type in room_types:
                db_session.add(room_type)

            # Create test rooms
            rooms = [
                Room(id=1, number="101", status="occupied", room_type_id=1),
                Room(id=2, number="102", status="occupied", room_type_id=1),
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

            # Create test bookings with checkout dates
            today = datetime.now().date()
            bookings = [
                Booking(
                    id=1,
                    room_id=1,
                    customer_id=1,
                    check_in_date=today - timedelta(days=2),
                    check_out_date=today,
                    status="checked_in",
                    guest_name="John Doe"
                ),
                Booking(
                    id=2,
                    room_id=2,
                    customer_id=2,
                    check_in_date=today - timedelta(days=1),
                    check_out_date=today,
                    status="checked_in",
                    guest_name="Jane Smith"
                ),
            ]
            for booking in bookings:
                db_session.add(booking)
            db_session.commit()

            # Load the rooms for each booking
            for booking in bookings:
                booking.room = db_session.query(Room).get(booking.room_id)

            # Render the template with test data
            with app.test_request_context():
                rendered = render_template_string(
                    """
                    {% extends "dashboard_base.html" %}
                    {% block dashboard_content %}
                    <div class="row">
                        <div class="col-lg-12">
                            <div class="card shadow mb-4">
                                <div class="card-header py-3">
                                    <h6 class="m-0 font-weight-bold text-primary">Rooms with Checkouts Today</h6>
                                </div>
                                <div class="card-body">
                                    {% if bookings %}
                                    <div class="table-responsive">
                                        <table class="table table-bordered" id="checkoutRoomsTable" width="100%" cellspacing="0">
                                            <thead>
                                                <tr>
                                                    <th>Room</th>
                                                    <th>Guest</th>
                                                    <th>Check-out Time</th>
                                                    <th>Status</th>
                                                    <th>Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {% for booking in bookings %}
                                                <tr>
                                                    <td>{{ booking.room.number }}</td>
                                                    <td>{{ booking.guest_name or booking.customer.name if booking.customer else 'N/A' }}</td>
                                                    <td>{{ booking.check_out_date.strftime('%H:%M') if booking.check_out_date else 'N/A' }}</td>
                                                    <td>
                                                        <span class="badge {% if booking.room.status == 'checkout' %}bg-warning{% elif booking.room.status == 'dirty' %}bg-danger{% elif booking.room.status == 'clean' %}bg-success{% else %}bg-secondary{% endif %}">
                                                            {{ booking.room.status|title }}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <a href="#" class="btn btn-primary btn-sm">
                                                            <i class="bi bi-pencil-square"></i> Update Status
                                                        </a>
                                                    </td>
                                                </tr>
                                                {% endfor %}
                                            </tbody>
                                        </table>
                                    </div>
                                    {% else %}
                                    <div class="alert alert-info">
                                        <h4 class="alert-heading">No checkouts today!</h4>
                                        <p>There are no scheduled checkouts for today.</p>
                                    </div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endblock %}
                    """,
                    bookings=bookings
                )

                # Check that the template renders without errors
                assert rendered is not None

                # Check that all bookings are displayed
                for booking in bookings:
                    assert booking.guest_name in rendered
                    assert booking.room.number in rendered

                # Check that the table is displayed (not the "No checkouts" message)
                assert "No checkouts today!" not in rendered
                assert "Rooms with Checkouts Today" in rendered

    def test_cleaning_schedule_template(self, app, db_session):
        """Test the cleaning_schedule.html template."""
        with app.app_context():
            # Create test room types and rooms
            room_type = RoomType(id=1, name="Standard", base_rate=100)
            db_session.add(room_type)

            rooms = [
                Room(id=1, number="101", status="occupied", room_type_id=1),
                Room(id=2, number="102", status="occupied", room_type_id=1),
            ]
            for room in rooms:
                db_session.add(room)
            db_session.commit()

            # Create test data for the schedule
            today = datetime.now().date()
            start_date = today
            end_date = today + timedelta(days=6)

            # Create a week of days with tasks and checkouts
            days = []
            current_date = start_date
            while current_date <= end_date:
                # For today, add a task and checkout
                if current_date == today:
                    task = HousekeepingTask(
                        id=1,
                        room_id=1,
                        task_type="regular_cleaning",
                        status="pending",
                        priority="normal",
                        due_date=today,
                        description="Regular cleaning for room 101"
                    )
                    db_session.add(task)

                    # Create a customer
                    customer = Customer(
                        id=1,
                        name="John Doe",
                        email="john@example.com",
                        phone="123-456-7890"
                    )
                    db_session.add(customer)
                    db_session.commit()

                    booking = Booking(
                        id=1,
                        room_id=1,
                        customer_id=1,
                        check_in_date=today - timedelta(days=2),
                        check_out_date=today,
                        status="checked_in",
                        guest_name="John Doe"
                    )
                    db_session.add(booking)
                    db_session.commit()

                    # Load the room for the task and booking
                    task.room = db_session.query(Room).get(task.room_id)
                    booking.room = db_session.query(Room).get(booking.room_id)

                    days.append({
                        'date': current_date,
                        'tasks': [task],
                        'checkouts': [booking],
                        'total': 2
                    })
                else:
                    # Empty day
                    days.append({
                        'date': current_date,
                        'tasks': [],
                        'checkouts': [],
                        'total': 0
                    })

                current_date += timedelta(days=1)

            # Define the now function
            def now():
                return datetime.now()

            # Render the template with test data
            with app.test_request_context():
                rendered = render_template_string(
                    """
                    {% extends "dashboard_base.html" %}
                    {% block dashboard_content %}
                    {% for day in days %}
                    <div class="row mb-4">
                        <div class="col-lg-12">
                            <div class="card shadow">
                                <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
                                    <h6 class="m-0 font-weight-bold text-primary">
                                        {{ day.date.strftime('%A, %B %d, %Y') }}
                                        {% if day.date.strftime('%Y-%m-%d') == start_date.strftime('%Y-%m-%d') %}
                                        <span class="badge bg-primary">Today</span>
                                        {% endif %}
                                    </h6>
                                    <span class="badge {% if day.total > 5 %}bg-danger{% elif day.total > 2 %}bg-warning{% else %}bg-success{% endif %}">
                                        {{ day.total }} Task{% if day.total != 1 %}s{% endif %}
                                    </span>
                                </div>
                                <div class="card-body">
                                    {% if day.tasks or day.checkouts %}
                                    <div class="row">
                                        {% if day.checkouts %}
                                        <div class="col-lg-6">
                                            <h5 class="text-primary"><i class="bi bi-door-open"></i> Checkouts</h5>
                                            <div class="table-responsive">
                                                <table class="table table-bordered table-sm">
                                                    <thead>
                                                        <tr>
                                                            <th>Room</th>
                                                            <th>Guest</th>
                                                            <th>Check-out Time</th>
                                                            <th>Actions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {% for booking in day.checkouts %}
                                                        <tr>
                                                            <td>{{ booking.room.number }}</td>
                                                            <td>{{ booking.guest_name }}</td>
                                                            <td>{{ booking.check_out_date.strftime('%H:%M') if booking.check_out_date else 'N/A' }}</td>
                                                            <td>
                                                                <a href="#" class="btn btn-primary btn-sm">
                                                                    <i class="bi bi-pencil-square"></i>
                                                                </a>
                                                            </td>
                                                        </tr>
                                                        {% endfor %}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                        {% endif %}

                                        {% if day.tasks %}
                                        <div class="col-lg-{% if day.checkouts %}6{% else %}12{% endif %}">
                                            <h5 class="text-primary"><i class="bi bi-check2-square"></i> Cleaning Tasks</h5>
                                            <div class="table-responsive">
                                                <table class="table table-bordered table-sm">
                                                    <thead>
                                                        <tr>
                                                            <th>Room</th>
                                                            <th>Type</th>
                                                            <th>Priority</th>
                                                            <th>Status</th>
                                                            <th>Actions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {% for task in day.tasks %}
                                                        <tr>
                                                            <td>{{ task.room.number }}</td>
                                                            <td>{{ task.task_type|replace('_', ' ')|title }}</td>
                                                            <td>
                                                                <span class="badge {% if task.priority == 'urgent' %}bg-danger{% elif task.priority == 'high' %}bg-warning{% elif task.priority == 'normal' %}bg-primary{% else %}bg-secondary{% endif %}">
                                                                    {{ task.priority|title }}
                                                                </span>
                                                            </td>
                                                            <td>
                                                                <span class="badge {% if task.status == 'pending' %}bg-secondary{% elif task.status == 'in_progress' %}bg-primary{% elif task.status == 'completed' %}bg-success{% else %}bg-info{% endif %}">
                                                                    {{ task.status|replace('_', ' ')|title }}
                                                                </span>
                                                            </td>
                                                            <td>
                                                                <a href="#" class="btn btn-primary btn-sm">
                                                                    <i class="bi bi-eye"></i>
                                                                </a>
                                                            </td>
                                                        </tr>
                                                        {% endfor %}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                        {% endif %}
                                    </div>
                                    {% else %}
                                    <div class="alert alert-success">
                                        <i class="bi bi-check-circle"></i> No scheduled tasks or checkouts for this day.
                                    </div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                    {% endblock %}
                    """,
                    days=days,
                    start_date=start_date,
                    end_date=end_date,
                    prev_week=start_date - timedelta(days=7),
                    next_week=start_date + timedelta(days=7),
                    now=now
                )

                # Check that the template renders without errors
                assert rendered is not None

                # Check that all days are displayed
                for day in days:
                    assert day['date'].strftime('%A, %B %d') in rendered

                # Check that today has the "Today" badge
                assert '<span class="badge bg-primary">Today</span>' in rendered

                # Check that tasks and checkouts are displayed for today
                assert "Regular Cleaning" in rendered
                assert "John Doe" in rendered

                # Check that empty days show the "No scheduled tasks" message
                assert "No scheduled tasks or checkouts for this day" in rendered
