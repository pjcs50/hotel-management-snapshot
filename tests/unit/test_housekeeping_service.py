"""
Test module for HousekeepingService.

This module provides unit tests for the housekeeping service.
"""

import pytest
from datetime import datetime, timedelta
from app.services.housekeeping_service import HousekeepingService
from app.models.housekeeping_task import HousekeepingTask
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.user import User
from app.models.booking import Booking
from app.models.room_status_log import RoomStatusLog


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
def housekeeping_service(db_session):
    """Create a housekeeping service instance for testing."""
    return HousekeepingService(db_session)


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


@pytest.fixture
def booking(db_session, room, customer_user):
    """Create a booking for testing."""
    check_out_date = datetime.now().date() + timedelta(days=1)
    booking = Booking(
        customer_id=customer_user.id,
        room_id=room.id,
        check_in_date=datetime.now().date() - timedelta(days=2),
        check_out_date=check_out_date,
        status="checked_in",
        total_price=300.00
    )
    db_session.add(booking)
    db_session.commit()
    return booking


class TestHousekeepingService:
    """Test class for HousekeepingService."""

    def test_get_all_housekeeping_tasks(self, housekeeping_service, housekeeping_task):
        """Test getting all housekeeping tasks."""
        # Test without filters
        result = housekeeping_service.get_all_housekeeping_tasks()
        assert result.total == 1
        assert result.items[0].id == housekeeping_task.id

        # Test with status filter
        result = housekeeping_service.get_all_housekeeping_tasks(filters={'status': 'pending'})
        assert result.total == 1
        assert result.items[0].id == housekeeping_task.id

        # Test with non-matching status filter
        result = housekeeping_service.get_all_housekeeping_tasks(filters={'status': 'completed'})
        assert result.total == 0

        # Test with task_type filter
        result = housekeeping_service.get_all_housekeeping_tasks(filters={'task_type': 'regular_cleaning'})
        assert result.total == 1

        # Test with search term
        result = housekeeping_service.get_all_housekeeping_tasks(filters={'q': 'bathroom'})
        assert result.total == 1

        # Test with non-matching search term
        result = housekeeping_service.get_all_housekeeping_tasks(filters={'q': 'nonexistent'})
        assert result.total == 0

    def test_get_housekeeping_task(self, housekeeping_service, housekeeping_task):
        """Test getting a housekeeping task by ID."""
        task = housekeeping_service.get_housekeeping_task(housekeeping_task.id)
        assert task is not None
        assert task.id == housekeeping_task.id
        assert task.room_id == housekeeping_task.room_id
        assert task.task_type == housekeeping_task.task_type

        # Test with non-existing ID
        task = housekeeping_service.get_housekeeping_task(9999)
        assert task is None

    def test_create_housekeeping_task(self, housekeeping_service, room):
        """Test creating a new housekeeping task."""
        due_date = datetime.now() + timedelta(hours=4)
        data = {
            'room_id': room.id,
            'task_type': 'deep_cleaning',
            'description': 'Deep cleaning of the room',
            'priority': 'high',
            'due_date': due_date,
            'notes': 'Focus on carpet stains'
        }
        
        # Create task
        task = housekeeping_service.create_housekeeping_task(data)
        
        assert task is not None
        assert task.room_id == room.id
        assert task.task_type == 'deep_cleaning'
        assert task.description == 'Deep cleaning of the room'
        assert task.priority == 'high'
        assert task.status == 'pending'
        assert task.due_date == due_date
        assert task.notes == 'Focus on carpet stains'

    def test_update_housekeeping_task(self, housekeeping_service, housekeeping_task):
        """Test updating a housekeeping task."""
        # Update fields
        new_due_date = datetime.now() + timedelta(hours=6)
        data = {
            'priority': 'high',
            'due_date': new_due_date,
            'notes': 'Updated notes'
        }
        
        updated_task = housekeeping_service.update_housekeeping_task(housekeeping_task.id, data)
        
        assert updated_task is not None
        assert updated_task.priority == 'high'
        assert updated_task.due_date == new_due_date
        assert updated_task.notes == 'Updated notes'

        # Test with non-existing ID
        updated_task = housekeeping_service.update_housekeeping_task(9999, data)
        assert updated_task is None

    def test_assign_housekeeping_task(self, housekeeping_service, housekeeping_task, housekeeping_staff):
        """Test assigning a housekeeping task."""
        # Assign task
        task = housekeeping_service.assign_housekeeping_task(
            task_id=housekeeping_task.id,
            staff_id=housekeeping_staff.id
        )
        
        assert task is not None
        assert task.assigned_to == housekeeping_staff.id

    def test_mark_in_progress(self, housekeeping_service, housekeeping_task):
        """Test marking a housekeeping task as in progress."""
        # Mark as in progress
        task = housekeeping_service.mark_in_progress(
            task_id=housekeeping_task.id,
            notes="Started cleaning"
        )
        
        assert task is not None
        assert task.status == 'in_progress'
        assert "Started cleaning" in task.notes

    def test_complete_housekeeping_task(self, housekeeping_service, housekeeping_task, db_session, room):
        """Test completing a housekeeping task."""
        # First set room to dirty status
        room.status = 'dirty'
        db_session.commit()
        
        # Then complete the task
        task = housekeeping_service.complete_housekeeping_task(
            task_id=housekeeping_task.id,
            notes="Cleaning completed"
        )
        
        assert task is not None
        assert task.status == 'completed'
        assert task.completed_at is not None
        assert "Cleaning completed" in task.notes
        
        # Verify room status is updated
        room = db_session.query(Room).get(room.id)
        assert room.status == 'clean'
        
        # Verify room status log is created
        status_log = db_session.query(RoomStatusLog).filter_by(room_id=room.id).first()
        assert status_log is not None
        assert status_log.old_status == 'dirty'
        assert status_log.new_status == 'clean'

    def test_verify_housekeeping_task(self, housekeeping_service, housekeeping_task, manager_user):
        """Test verifying a completed housekeeping task."""
        # First complete the task
        housekeeping_service.update_housekeeping_task(
            housekeeping_task.id, 
            {'status': 'completed', 'completed_at': datetime.now()}
        )
        
        # Then verify it
        task = housekeeping_service.verify_housekeeping_task(
            task_id=housekeeping_task.id,
            verified_by=manager_user.id,
            notes="Room is spotless"
        )
        
        assert task is not None
        assert task.status == 'verified'
        assert task.verified_by == manager_user.id
        assert task.verified_at is not None
        assert "Room is spotless" in task.notes

    def test_delete_housekeeping_task(self, housekeeping_service, housekeeping_task):
        """Test deleting a housekeeping task."""
        # Delete task
        result = housekeeping_service.delete_housekeeping_task(housekeeping_task.id)
        assert result is True
        
        # Verify it's deleted
        task = housekeeping_service.get_housekeeping_task(housekeeping_task.id)
        assert task is None

        # Test deleting non-existing task
        result = housekeeping_service.delete_housekeeping_task(9999)
        assert result is False

    def test_get_housekeeping_stats(self, housekeeping_service, housekeeping_task, db_session, room):
        """Test getting housekeeping statistics."""
        # Add a few more tasks with different statuses and types
        task2 = HousekeepingTask(
            room_id=room.id,
            task_type="turnover",
            description="Room turnover after checkout",
            status="in_progress",
            priority="high",
            due_date=datetime.now() - timedelta(hours=1)  # Overdue
        )
        
        task3 = HousekeepingTask(
            room_id=room.id,
            task_type="deep_cleaning",
            description="Deep cleaning",
            status="completed",
            priority="normal",
            due_date=datetime.now() + timedelta(days=1),
            completed_at=datetime.now() - timedelta(hours=2)
        )
        
        db_session.add_all([task2, task3])
        db_session.commit()
        
        # Get stats
        stats = housekeeping_service.get_housekeeping_stats()
        
        assert stats is not None
        assert 'status_counts' in stats
        assert 'type_counts' in stats
        assert 'overdue_count' in stats
        assert 'today_count' in stats
        assert 'total' in stats
        
        # Verify counts
        assert stats['status_counts'].get('pending', 0) == 1
        assert stats['status_counts'].get('in_progress', 0) == 1
        assert stats['status_counts'].get('completed', 0) == 1
        
        assert stats['type_counts'].get('regular_cleaning', 0) == 1
        assert stats['type_counts'].get('turnover', 0) == 1
        assert stats['type_counts'].get('deep_cleaning', 0) == 1
        
        assert stats['overdue_count'] == 1  # task2 is overdue
        assert stats['today_count'] >= 1    # Depends on test execution time
        
        assert stats['total'] == 3
        
        # Verify avg_completion_hours (approximate check since timing may vary)
        if stats['avg_completion_hours'] is not None:
            assert stats['avg_completion_hours'] > 0

    def test_generate_turnover_tasks(self, housekeeping_service, booking, db_session):
        """Test generating turnover tasks for rooms with checkouts."""
        # Use tomorrow as the checkout date (matches our booking fixture)
        checkout_date = datetime.now().date() + timedelta(days=1)
        
        # Generate turnover tasks
        tasks_created = housekeeping_service.generate_turnover_tasks(checkout_date)
        
        assert tasks_created == 1  # Should create 1 task for our booking
        
        # Verify the task was created correctly
        task = db_session.query(HousekeepingTask).filter(
            HousekeepingTask.room_id == booking.room_id,
            HousekeepingTask.task_type == 'turnover'
        ).first()
        
        assert task is not None
        assert task.priority == 'high'
        assert task.due_date.date() == checkout_date
        
        # Test running again - should not create duplicate tasks
        tasks_created = housekeeping_service.generate_turnover_tasks(checkout_date)
        assert tasks_created == 0 