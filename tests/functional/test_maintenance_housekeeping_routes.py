"""
Functional tests for maintenance and housekeeping routes.

This module tests the maintenance and housekeeping functionality for managers.
"""

import pytest
from flask import url_for
from datetime import datetime, timedelta
import json
from app.models.maintenance_request import MaintenanceRequest
from app.models.housekeeping_task import HousekeepingTask
from app.models.room import Room
from app.models.room_type import RoomType


@pytest.fixture
def room_type(db_session):
    """Create a room type for testing."""
    room_type = RoomType(
        name="Standard",
        description="Standard room",
        base_rate=100.00,
        capacity=2
    )
    db_session.add(room_type)
    db_session.commit()
    return room_type


@pytest.fixture
def room(db_session, room_type):
    """Create a room for testing."""
    room = Room(
        number="101",
        room_type_id=room_type.id,
        status="clean"
    )
    db_session.add(room)
    db_session.commit()
    return room


@pytest.fixture
def maintenance_request(db_session, room, receptionist_user):
    """Create a maintenance request for testing."""
    request = MaintenanceRequest(
        room_id=room.id,
        reported_by=receptionist_user.id,
        issue_type="plumbing",
        description="Leaking faucet in bathroom",
        status="open",
        priority="medium",
        notes="Water is dripping constantly"
    )
    db_session.add(request)
    db_session.commit()
    return request


@pytest.fixture
def housekeeping_task(db_session, room):
    """Create a housekeeping task for testing."""
    task = HousekeepingTask(
        room_id=room.id,
        task_type="regular_cleaning",
        description="Regular daily cleaning",
        status="pending",
        priority="normal",
        due_date=datetime.now() + timedelta(hours=2),
        notes="Please clean the bathroom thoroughly"
    )
    db_session.add(task)
    db_session.commit()
    return task


# Maintenance Route Tests

def test_maintenance_index_view(client, manager_user, auth, maintenance_request):
    """Test the maintenance index view."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Access maintenance index page
    response = client.get(url_for('manager.maintenance'))
    assert response.status_code == 200
    
    # Check if maintenance request is displayed
    content = response.data.decode('utf-8')
    assert 'Leaking faucet' in content
    assert 'plumbing' in content
    assert 'open' in content or 'Open' in content


def test_maintenance_filtered_views(client, manager_user, auth, maintenance_request, db_session, room, receptionist_user):
    """Test filtered views in the maintenance index."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # 1. Create another request with different status
    in_progress_request = MaintenanceRequest(
        room_id=room.id,
        reported_by=receptionist_user.id,
        issue_type="electrical",
        description="Light fixture not working",
        status="in_progress",
        priority="high",
        notes="Room is dark at night"
    )
    db_session.add(in_progress_request)
    db_session.commit()
    
    # 2. Test 'open' filter
    response = client.get(url_for('manager.maintenance', status='open'))
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    
    # Should contain open request but not in_progress request
    assert 'Leaking faucet' in content
    assert 'Light fixture not working' not in content
    
    # 3. Test 'in_progress' filter
    response = client.get(url_for('manager.maintenance', status='in_progress'))
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    
    # Should contain in_progress request but not open request
    assert 'Light fixture not working' in content
    assert 'Leaking faucet' not in content
    
    # 4. Test priority filter
    response = client.get(url_for('manager.maintenance', priority='high'))
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    
    # Should contain high priority request but not medium priority request
    assert 'Light fixture not working' in content
    assert 'Leaking faucet' not in content


def test_maintenance_detail_view(client, manager_user, auth, maintenance_request):
    """Test viewing a specific maintenance request."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Access maintenance detail page
    response = client.get(url_for('manager.view_maintenance_request', request_id=maintenance_request.id))
    assert response.status_code == 200
    
    # Check if details are displayed
    content = response.data.decode('utf-8')
    assert 'Leaking faucet in bathroom' in content
    assert 'plumbing' in content
    assert 'Water is dripping constantly' in content


def test_create_maintenance_request(client, manager_user, auth, room):
    """Test creating a new maintenance request."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send create request
    response = client.post(
        url_for('manager.new_maintenance_request'),
        data={
            'csrf_token': csrf_token,
            'room_id': str(room.id),
            'reported_by': str(manager_user.id),
            'issue_type': 'furniture',
            'description': 'Broken chair',
            'priority': 'low',
            'notes': 'Chair leg is broken'
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'created successfully' in content
    
    # Verify request was created
    request = MaintenanceRequest.query.filter_by(description='Broken chair').first()
    assert request is not None
    assert request.room_id == room.id
    assert request.issue_type == 'furniture'
    assert request.priority == 'low'


def test_update_maintenance_request(client, manager_user, auth, maintenance_request):
    """Test updating a maintenance request."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send update request
    response = client.post(
        url_for('manager.update_maintenance_request', request_id=maintenance_request.id),
        data={
            'csrf_token': csrf_token,
            'priority': 'high',
            'notes': 'Updated: Water damage is severe'
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'updated successfully' in content
    
    # Verify request was updated
    updated_request = MaintenanceRequest.query.get(maintenance_request.id)
    assert updated_request.priority == 'high'
    assert 'Water damage is severe' in updated_request.notes


def test_resolve_maintenance_request(client, manager_user, auth, maintenance_request):
    """Test resolving a maintenance request."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send resolve request
    response = client.post(
        url_for('manager.resolve_maintenance_request', request_id=maintenance_request.id),
        data={
            'csrf_token': csrf_token,
            'notes': 'Fixed the leak by replacing washer'
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'marked as resolved' in content
    
    # Verify request was resolved
    resolved_request = MaintenanceRequest.query.get(maintenance_request.id)
    assert resolved_request.status == 'resolved'
    assert resolved_request.resolved_at is not None
    assert 'Fixed the leak' in resolved_request.notes


# Housekeeping Route Tests

def test_housekeeping_index_view(client, manager_user, auth, housekeeping_task):
    """Test the housekeeping index view."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Access housekeeping index page
    response = client.get(url_for('manager.housekeeping'))
    assert response.status_code == 200
    
    # Check if housekeeping task is displayed
    content = response.data.decode('utf-8')
    assert 'Regular daily cleaning' in content
    assert 'regular_cleaning' in content or 'Regular Cleaning' in content
    assert 'pending' in content or 'Pending' in content


def test_housekeeping_filtered_views(client, manager_user, auth, housekeeping_task, db_session, room):
    """Test filtered views in the housekeeping index."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # 1. Create another task with different status
    in_progress_task = HousekeepingTask(
        room_id=room.id,
        task_type="deep_cleaning",
        description="Deep cleaning of room",
        status="in_progress",
        priority="high",
        due_date=datetime.now() + timedelta(hours=4)
    )
    db_session.add(in_progress_task)
    db_session.commit()
    
    # 2. Test 'pending' filter
    response = client.get(url_for('manager.housekeeping', status='pending'))
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    
    # Should contain pending task but not in_progress task
    assert 'Regular daily cleaning' in content
    assert 'Deep cleaning of room' not in content
    
    # 3. Test 'in_progress' filter
    response = client.get(url_for('manager.housekeeping', status='in_progress'))
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    
    # Should contain in_progress task but not pending task
    assert 'Deep cleaning of room' in content
    assert 'Regular daily cleaning' not in content
    
    # 4. Test task_type filter
    response = client.get(url_for('manager.housekeeping', task_type='deep_cleaning'))
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    
    # Should contain deep cleaning task but not regular cleaning task
    assert 'Deep cleaning of room' in content
    assert 'Regular daily cleaning' not in content


def test_housekeeping_detail_view(client, manager_user, auth, housekeeping_task):
    """Test viewing a specific housekeeping task."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Access housekeeping detail page
    response = client.get(url_for('manager.view_housekeeping_task', task_id=housekeeping_task.id))
    assert response.status_code == 200
    
    # Check if details are displayed
    content = response.data.decode('utf-8')
    assert 'Regular daily cleaning' in content
    assert 'Please clean the bathroom thoroughly' in content
    assert 'regular_cleaning' in content or 'Regular Cleaning' in content


def test_create_housekeeping_task(client, manager_user, auth, room):
    """Test creating a new housekeeping task."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send create request
    due_date = (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M')
    response = client.post(
        url_for('manager.new_housekeeping_task'),
        data={
            'csrf_token': csrf_token,
            'room_id': str(room.id),
            'task_type': 'turnover',
            'description': 'Room turnover after checkout',
            'priority': 'high',
            'due_date': due_date,
            'notes': 'Guest checking in at 3pm'
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'created successfully' in content
    
    # Verify task was created
    task = HousekeepingTask.query.filter_by(description='Room turnover after checkout').first()
    assert task is not None
    assert task.room_id == room.id
    assert task.task_type == 'turnover'
    assert task.priority == 'high'


def test_update_housekeeping_task(client, manager_user, auth, housekeeping_task):
    """Test updating a housekeeping task."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send update request
    response = client.post(
        url_for('manager.update_housekeeping_task', task_id=housekeeping_task.id),
        data={
            'csrf_token': csrf_token,
            'priority': 'high',
            'notes': 'Updated: Focus on bathroom cleaning'
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'updated successfully' in content
    
    # Verify task was updated
    updated_task = HousekeepingTask.query.get(housekeeping_task.id)
    assert updated_task.priority == 'high'
    assert 'Focus on bathroom cleaning' in updated_task.notes


def test_complete_housekeeping_task(client, manager_user, auth, housekeeping_task):
    """Test completing a housekeeping task."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send complete request
    response = client.post(
        url_for('manager.complete_housekeeping_task', task_id=housekeeping_task.id),
        data={
            'csrf_token': csrf_token,
            'notes': 'Room cleaned to standards'
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'marked as completed' in content
    
    # Verify task was completed
    completed_task = HousekeepingTask.query.get(housekeeping_task.id)
    assert completed_task.status == 'completed'
    assert completed_task.completed_at is not None
    assert 'Room cleaned to standards' in completed_task.notes


def test_generate_turnover_tasks(client, manager_user, auth, room, customer_user, db_session):
    """Test generating turnover tasks."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Create a booking with checkout tomorrow
    checkout_date = datetime.now().date() + timedelta(days=1)
    from app.models.booking import Booking
    booking = Booking(
        customer_id=customer_user.id,
        room_id=room.id,
        check_in_date=datetime.now().date() - timedelta(days=2),
        check_out_date=checkout_date,
        status="checked_in",
        total_price=300.00
    )
    db_session.add(booking)
    db_session.commit()
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send generate turnover tasks request
    response = client.post(
        url_for('manager.generate_turnover_tasks'),
        data={
            'csrf_token': csrf_token,
            'date': checkout_date.strftime('%Y-%m-%d')
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'generated' in content and 'turnover tasks' in content
    
    # Verify task was created
    task = HousekeepingTask.query.filter_by(
        room_id=room.id,
        task_type='turnover'
    ).first()
    
    assert task is not None
    assert task.status == 'pending'
    assert task.priority == 'high'
    assert task.due_date.date() == checkout_date 