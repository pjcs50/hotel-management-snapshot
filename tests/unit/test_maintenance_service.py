"""
Test module for MaintenanceService.

This module provides unit tests for the maintenance service.
"""

import pytest
from datetime import datetime, timedelta
from app.services.maintenance_service import MaintenanceService
from app.models.maintenance_request import MaintenanceRequest
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.user import User
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
def maintenance_service(db_session):
    """Create a maintenance service instance for testing."""
    return MaintenanceService(db_session)


@pytest.fixture
def reporter(db_session):
    """Create a user for reporting maintenance issues."""
    user = User(
        username="reporter",
        email="reporter@example.com",
        role="receptionist",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user


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
def maintenance_request(db_session, room, reporter):
    """Create a maintenance request for testing."""
    request = MaintenanceRequest(
        room_id=room.id,
        reported_by=reporter.id,
        issue_type="plumbing",
        description="Leaking faucet in bathroom",
        status="open",
        priority="medium",
        notes="Water is dripping constantly"
    )
    db_session.add(request)
    db_session.commit()
    return request


class TestMaintenanceService:
    """Test class for MaintenanceService."""

    def test_get_all_maintenance_requests(self, maintenance_service, maintenance_request):
        """Test getting all maintenance requests."""
        # Test without filters
        result = maintenance_service.get_all_maintenance_requests()
        assert result.total == 1
        assert result.items[0].id == maintenance_request.id

        # Test with status filter
        result = maintenance_service.get_all_maintenance_requests(filters={'status': 'open'})
        assert result.total == 1
        assert result.items[0].id == maintenance_request.id

        # Test with non-matching status filter
        result = maintenance_service.get_all_maintenance_requests(filters={'status': 'closed'})
        assert result.total == 0

        # Test with issue_type filter
        result = maintenance_service.get_all_maintenance_requests(filters={'issue_type': 'plumbing'})
        assert result.total == 1

        # Test with search term
        result = maintenance_service.get_all_maintenance_requests(filters={'q': 'faucet'})
        assert result.total == 1

        # Test with non-matching search term
        result = maintenance_service.get_all_maintenance_requests(filters={'q': 'nonexistent'})
        assert result.total == 0

    def test_get_maintenance_request(self, maintenance_service, maintenance_request):
        """Test getting a maintenance request by ID."""
        request = maintenance_service.get_maintenance_request(maintenance_request.id)
        assert request is not None
        assert request.id == maintenance_request.id
        assert request.room_id == maintenance_request.room_id
        assert request.issue_type == maintenance_request.issue_type

        # Test with non-existing ID
        request = maintenance_service.get_maintenance_request(9999)
        assert request is None

    def test_create_maintenance_request(self, maintenance_service, room, reporter):
        """Test creating a new maintenance request."""
        data = {
            'room_id': room.id,
            'reported_by': reporter.id,
            'issue_type': 'electrical',
            'description': 'Light switch not working',
            'priority': 'high',
            'notes': 'Room is dark when lights are needed'
        }
        
        # Create request
        request = maintenance_service.create_maintenance_request(data)
        
        assert request is not None
        assert request.room_id == room.id
        assert request.reported_by == reporter.id
        assert request.issue_type == 'electrical'
        assert request.description == 'Light switch not working'
        assert request.priority == 'high'
        assert request.status == 'open'
        assert request.notes == 'Room is dark when lights are needed'

        # Test with assigned_to
        data['assigned_to'] = reporter.id  # Just for testing purposes
        request = maintenance_service.create_maintenance_request(data)
        
        assert request.assigned_to == reporter.id
        assert request.status == 'assigned'

    def test_update_maintenance_request(self, maintenance_service, maintenance_request):
        """Test updating a maintenance request."""
        # Update fields
        data = {
            'priority': 'high',
            'notes': 'Updated notes'
        }
        
        updated_request = maintenance_service.update_maintenance_request(maintenance_request.id, data)
        
        assert updated_request is not None
        assert updated_request.priority == 'high'
        assert updated_request.notes == 'Updated notes'

        # Test with non-existing ID
        updated_request = maintenance_service.update_maintenance_request(9999, data)
        assert updated_request is None

    def test_assign_maintenance_request(self, maintenance_service, maintenance_request, maintenance_staff):
        """Test assigning a maintenance request."""
        # Assign request
        request = maintenance_service.assign_maintenance_request(
            request_id=maintenance_request.id,
            staff_id=maintenance_staff.id
        )
        
        assert request is not None
        assert request.assigned_to == maintenance_staff.id
        assert request.status == 'assigned'

    def test_mark_in_progress(self, maintenance_service, maintenance_request):
        """Test marking a maintenance request as in progress."""
        # Mark as in progress
        request = maintenance_service.mark_in_progress(
            request_id=maintenance_request.id,
            notes="Started working on it"
        )
        
        assert request is not None
        assert request.status == 'in_progress'
        assert "Started working on it" in request.notes

    def test_resolve_maintenance_request(self, maintenance_service, maintenance_request, db_session, room):
        """Test resolving a maintenance request."""
        # First set room to maintenance status
        room.status = 'maintenance'
        db_session.commit()
        
        # Then resolve the request
        request = maintenance_service.resolve_maintenance_request(
            request_id=maintenance_request.id,
            notes="Fixed the issue"
        )
        
        assert request is not None
        assert request.status == 'resolved'
        assert request.resolved_at is not None
        assert "Fixed the issue" in request.notes
        
        # Verify room status is updated
        room = db_session.query(Room).get(room.id)
        assert room.status == 'clean'
        
        # Verify room status log is created
        status_log = db_session.query(RoomStatusLog).filter_by(room_id=room.id).first()
        assert status_log is not None
        assert status_log.old_status == 'maintenance'
        assert status_log.new_status == 'clean'

    def test_close_maintenance_request(self, maintenance_service, maintenance_request, manager_user):
        """Test closing a resolved maintenance request."""
        # First resolve the request
        maintenance_service.resolve_maintenance_request(maintenance_request.id)
        
        # Then close it
        request = maintenance_service.close_maintenance_request(
            request_id=maintenance_request.id,
            verified_by=manager_user.id,
            notes="Verified the repair"
        )
        
        assert request is not None
        assert request.status == 'closed'
        assert "Verified the repair" in request.notes

    def test_delete_maintenance_request(self, maintenance_service, maintenance_request):
        """Test deleting a maintenance request."""
        # Delete request
        result = maintenance_service.delete_maintenance_request(maintenance_request.id)
        assert result is True
        
        # Verify it's deleted
        request = maintenance_service.get_maintenance_request(maintenance_request.id)
        assert request is None

        # Test deleting non-existing request
        result = maintenance_service.delete_maintenance_request(9999)
        assert result is False

    def test_get_maintenance_stats(self, maintenance_service, maintenance_request, db_session, room, reporter):
        """Test getting maintenance statistics."""
        # Add a few more requests with different statuses and priorities
        request2 = MaintenanceRequest(
            room_id=room.id,
            reported_by=reporter.id,
            issue_type="electrical",
            description="TV not working",
            status="assigned",
            priority="low"
        )
        
        request3 = MaintenanceRequest(
            room_id=room.id,
            reported_by=reporter.id,
            issue_type="furniture",
            description="Broken chair",
            status="resolved",
            priority="high",
            resolved_at=datetime.now() - timedelta(hours=4)
        )
        
        db_session.add_all([request2, request3])
        db_session.commit()
        
        # Get stats
        stats = maintenance_service.get_maintenance_stats()
        
        assert stats is not None
        assert 'status_counts' in stats
        assert 'priority_counts' in stats
        assert 'issue_type_counts' in stats
        assert 'total' in stats
        
        # Verify counts
        assert stats['status_counts'].get('open', 0) == 1
        assert stats['status_counts'].get('assigned', 0) == 1
        assert stats['status_counts'].get('resolved', 0) == 1
        
        assert stats['priority_counts'].get('medium', 0) == 1
        assert stats['priority_counts'].get('low', 0) == 1
        assert stats['priority_counts'].get('high', 0) == 1
        
        assert stats['issue_type_counts'].get('plumbing', 0) == 1
        assert stats['issue_type_counts'].get('electrical', 0) == 1
        assert stats['issue_type_counts'].get('furniture', 0) == 1
        
        assert stats['total'] == 3
        
        # Verify avg_resolution_hours (approximate check since timing may vary)
        if stats['avg_resolution_hours'] is not None:
            assert 0 < stats['avg_resolution_hours'] < 24 