"""
Functional tests for manager waitlist routes.

This module tests the waitlist management functionality for managers.
"""

import pytest
from flask import url_for
from datetime import datetime, timedelta
import re
from app.models.waitlist import Waitlist
from app.models.room_type import RoomType
from app.models.user import User


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
def test_customer(db_session):
    """Create a test customer."""
    user = User(
        username="waitlist_customer",
        email="waitlist_customer@example.com",
        role="customer",
        is_active=True
    )
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def waitlist_entry(db_session, test_customer, room_type):
    """Create a waitlist entry for testing."""
    start_date = datetime.now().date() + timedelta(days=7)
    end_date = start_date + timedelta(days=3)
    entry = Waitlist(
        customer_id=test_customer.id,
        room_type_id=room_type.id,
        requested_date_start=start_date,
        requested_date_end=end_date,
        status='waiting',
        notes="Test waitlist entry"
    )
    db_session.add(entry)
    db_session.commit()
    return entry


def test_waitlist_index_view(client, manager_user, auth, waitlist_entry):
    """Test the waitlist index view."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Access waitlist index page
    response = client.get(url_for('manager.waitlist'))
    assert response.status_code == 200
    
    # Check if waitlist entry is displayed
    content = response.data.decode('utf-8')
    assert 'waitlist_customer' in content
    assert 'Standard' in content
    assert 'Waiting' in content


def test_waitlist_filtered_views(client, manager_user, auth, waitlist_entry, db_session):
    """Test filtered views in the waitlist index."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # 1. Create another entry with different status
    promoted_entry = Waitlist(
        customer_id=waitlist_entry.customer_id,
        room_type_id=waitlist_entry.room_type_id,
        requested_date_start=waitlist_entry.requested_date_start + timedelta(days=10),
        requested_date_end=waitlist_entry.requested_date_end + timedelta(days=10),
        status='promoted',
        notes="Promoted entry"
    )
    db_session.add(promoted_entry)
    db_session.commit()
    
    # 2. Test 'waiting' filter
    response = client.get(url_for('manager.waitlist', status='waiting'))
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    
    # Should contain waitlist_entry but not promoted_entry
    assert f'waitlist_entry.id' in content or 'Waiting' in content
    assert 'Promoted entry' not in content
    
    # 3. Test 'promoted' filter
    response = client.get(url_for('manager.waitlist', status='promoted'))
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    
    # Should contain promoted_entry but not waitlist_entry
    assert 'Promoted entry' in content or 'Promoted' in content
    assert 'Test waitlist entry' not in content


def test_waitlist_detail_view(client, manager_user, auth, waitlist_entry):
    """Test viewing a specific waitlist entry."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Access waitlist detail page
    response = client.get(url_for('manager.view_waitlist_entry', entry_id=waitlist_entry.id))
    assert response.status_code == 200
    
    # Check if details are displayed
    content = response.data.decode('utf-8')
    assert 'waitlist_customer' in content
    assert 'Standard' in content
    assert 'Test waitlist entry' in content
    
    # Check if action buttons are present
    assert 'Expire Entry' in content
    assert 'Promote to Booking' in content


def test_promote_waitlist_entry(client, manager_user, auth, waitlist_entry):
    """Test promoting a waitlist entry to a booking."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send promotion request
    response = client.post(
        url_for('manager.promote_waitlist_entry', entry_id=waitlist_entry.id),
        data={'csrf_token': csrf_token},
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'successfully promoted' in content
    
    # Verify entry was updated
    updated_entry = Waitlist.query.get(waitlist_entry.id)
    assert updated_entry.status == 'promoted'


def test_expire_waitlist_entry(client, manager_user, auth, waitlist_entry):
    """Test expiring a waitlist entry."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send expire request with a reason
    reason = "No longer needed"
    response = client.post(
        url_for('manager.expire_waitlist_entry', entry_id=waitlist_entry.id),
        data={
            'csrf_token': csrf_token,
            'reason': reason
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'marked as expired' in content
    
    # Verify entry was updated
    updated_entry = Waitlist.query.get(waitlist_entry.id)
    assert updated_entry.status == 'expired'
    assert reason in updated_entry.notes


def test_process_cancellations(client, manager_user, auth):
    """Test processing all cancellations."""
    # Login as manager
    auth.login(email=manager_user.email, password="password")
    
    # Get CSRF token
    csrf_token = client.get_csrf_token()
    
    # Send process cancellations request
    response = client.post(
        url_for('manager.process_waitlist_cancellations'),
        data={'csrf_token': csrf_token},
        follow_redirects=True
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'cancellations have been processed' in content 