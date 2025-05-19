"""
Integration tests for maintenance and housekeeping features.

This module provides integration tests for the maintenance and housekeeping features,
testing the interaction between models, services, and room status.
"""

import pytest
from datetime import datetime, timedelta
from app.services.maintenance_service import MaintenanceService
from app.services.housekeeping_service import HousekeepingService
from app.models.maintenance_request import MaintenanceRequest
from app.models.housekeeping_task import HousekeepingTask
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.room_status_log import RoomStatusLog
from app.models.user import User
from app.models.booking import Booking


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
def maintenance_staff(db_session):
    """Create a maintenance staff user."""
    user = User(
        username="maintenance",
        email="maintenance@example.com",
        role="maintenance",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def housekeeping_staff(db_session):
    """Create a housekeeping staff user."""
    user = User(
        username="housekeeper",
        email="housekeeper@example.com",
        role="housekeeping",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user


def test_room_maintenance_workflow(db_session, room, receptionist_user, maintenance_staff, manager_user):
    """Test the full room maintenance workflow."""
    # Create maintenance service
    maintenance_service = MaintenanceService(db_session)
    
    # 1. Room starts as clean
    assert room.status == "clean"
    
    # 2. Create maintenance request
    request_data = {
        'room_id': room.id,
        'reported_by': receptionist_user.id,
        'issue_type': 'plumbing',
        'description': 'Sink is clogged',
        'priority': 'high',
        'notes': 'Water is backing up'
    }
    
    maintenance_request = maintenance_service.create_maintenance_request(request_data)
    assert maintenance_request.status == "open"
    
    # 3. Set room to maintenance status
    room.status = "maintenance"
    db_session.commit()
    
    # Create a room status log (normally done by a controller or service)
    status_log = RoomStatusLog(
        room_id=room.id,
        old_status="clean",
        new_status="maintenance",
        changed_by=receptionist_user.id
    )
    db_session.add(status_log)
    db_session.commit()
    
    # 4. Assign maintenance request
    assigned_request = maintenance_service.assign_maintenance_request(
        request_id=maintenance_request.id,
        staff_id=maintenance_staff.id
    )
    assert assigned_request.status == "assigned"
    assert assigned_request.assigned_to == maintenance_staff.id
    
    # 5. Mark as in progress
    in_progress_request = maintenance_service.mark_in_progress(
        request_id=maintenance_request.id,
        notes="Working on unclogging the sink"
    )
    assert in_progress_request.status == "in_progress"
    
    # 6. Resolve maintenance request
    resolved_request = maintenance_service.resolve_maintenance_request(
        request_id=maintenance_request.id,
        notes="Sink unclogged, tested and working properly"
    )
    assert resolved_request.status == "resolved"
    assert resolved_request.resolved_at is not None
    
    # 7. Verify room status was updated to clean
    room = db_session.query(Room).get(room.id)
    assert room.status == "clean"
    
    # 8. Manager verifies and closes the request
    closed_request = maintenance_service.close_maintenance_request(
        request_id=maintenance_request.id,
        verified_by=manager_user.id,
        notes="Verified the repair is satisfactory"
    )
    assert closed_request.status == "closed"
    
    # 9. Verify room status logs were created
    status_logs = db_session.query(RoomStatusLog).filter_by(room_id=room.id).all()
    assert len(status_logs) >= 2  # At least the initial change and the maintenance->clean change


def test_room_housekeeping_workflow(db_session, room, housekeeping_staff, manager_user):
    """Test the full room housekeeping workflow."""
    # Create housekeeping service
    housekeeping_service = HousekeepingService(db_session)
    
    # 1. Set room to dirty status
    room.status = "dirty"
    db_session.commit()
    
    # Create a room status log
    status_log = RoomStatusLog(
        room_id=room.id,
        old_status="clean",
        new_status="dirty",
        changed_by=manager_user.id
    )
    db_session.add(status_log)
    db_session.commit()
    
    # 2. Create housekeeping task
    due_date = datetime.now() + timedelta(hours=2)
    task_data = {
        'room_id': room.id,
        'task_type': 'regular_cleaning',
        'description': 'Clean room after guest checkout',
        'priority': 'high',
        'due_date': due_date,
        'notes': 'Guest checking in later today'
    }
    
    housekeeping_task = housekeeping_service.create_housekeeping_task(task_data)
    assert housekeeping_task.status == "pending"
    
    # 3. Assign task to staff
    assigned_task = housekeeping_service.assign_housekeeping_task(
        task_id=housekeeping_task.id,
        staff_id=housekeeping_staff.id
    )
    assert assigned_task.assigned_to == housekeeping_staff.id
    
    # 4. Mark as in progress
    in_progress_task = housekeeping_service.mark_in_progress(
        task_id=housekeeping_task.id,
        notes="Started cleaning"
    )
    assert in_progress_task.status == "in_progress"
    
    # 5. Complete housekeeping task
    completed_task = housekeeping_service.complete_housekeeping_task(
        task_id=housekeeping_task.id,
        notes="Room cleaned and ready"
    )
    assert completed_task.status == "completed"
    assert completed_task.completed_at is not None
    
    # 6. Verify room status was updated to clean
    room = db_session.query(Room).get(room.id)
    assert room.status == "clean"
    
    # 7. Manager verifies the task
    verified_task = housekeeping_service.verify_housekeeping_task(
        task_id=housekeeping_task.id,
        verified_by=manager_user.id,
        notes="Room is properly cleaned"
    )
    assert verified_task.status == "verified"
    assert verified_task.verified_by == manager_user.id
    
    # 8. Verify room status logs were created
    status_logs = db_session.query(RoomStatusLog).filter_by(room_id=room.id).all()
    assert len(status_logs) >= 2  # At least the initial change and the dirty->clean change


def test_checkout_turnover_task_generation(db_session, room, customer_user, housekeeping_service):
    """Test generation of turnover tasks when bookings check out."""
    # 1. Create a booking with checkout tomorrow
    checkout_date = datetime.now().date() + timedelta(days=1)
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
    
    # 2. Generate turnover tasks
    tasks_created = housekeeping_service.generate_turnover_tasks(checkout_date)
    assert tasks_created == 1
    
    # 3. Verify the task was created correctly
    task = db_session.query(HousekeepingTask).filter(
        HousekeepingTask.room_id == room.id,
        HousekeepingTask.task_type == 'turnover'
    ).first()
    
    assert task is not None
    assert task.status == 'pending'
    assert task.priority == 'high'
    assert task.due_date.date() == checkout_date
    
    # 4. Run again - should not create duplicate tasks
    tasks_created = housekeeping_service.generate_turnover_tasks(checkout_date)
    assert tasks_created == 0


def test_maintenance_housekeeping_coordination(db_session, room, receptionist_user, 
                                           maintenance_staff, housekeeping_staff):
    """Test coordination between maintenance and housekeeping."""
    # Create services
    maintenance_service = MaintenanceService(db_session)
    housekeeping_service = HousekeepingService(db_session)
    
    # 1. Create maintenance request
    maintenance_request = maintenance_service.create_maintenance_request({
        'room_id': room.id,
        'reported_by': receptionist_user.id,
        'issue_type': 'electrical',
        'description': 'Light fixture broken',
        'priority': 'medium'
    })
    
    # 2. Set room to maintenance status
    room.status = "maintenance"
    db_session.commit()
    
    # 3. Resolve maintenance issue
    maintenance_service.resolve_maintenance_request(
        maintenance_request.id,
        "Light fixture replaced"
    )
    
    # 4. Verify room is now clean
    room = db_session.query(Room).get(room.id)
    assert room.status == "clean"
    
    # 5. Now create a housekeeping task
    housekeeping_task = housekeeping_service.create_housekeeping_task({
        'room_id': room.id,
        'task_type': 'deep_cleaning',
        'description': 'Deep clean after maintenance',
        'priority': 'normal',
        'due_date': datetime.now() + timedelta(hours=3)
    })
    
    # 6. Set room to dirty for housekeeping
    room.status = "dirty"
    db_session.commit()
    
    # 7. Complete housekeeping task
    housekeeping_service.complete_housekeeping_task(
        housekeeping_task.id,
        "Room deep cleaned after maintenance"
    )
    
    # 8. Verify room is clean again
    room = db_session.query(Room).get(room.id)
    assert room.status == "clean"
    
    # 9. Verify room status log history
    status_logs = db_session.query(RoomStatusLog).filter_by(room_id=room.id).order_by(
        RoomStatusLog.created_at
    ).all()
    
    # Should have at least:
    # 1. clean -> maintenance (manual in test)
    # 2. maintenance -> clean (from resolve)
    # 3. clean -> dirty (manual in test)
    # 4. dirty -> clean (from complete)
    assert len(status_logs) >= 4 