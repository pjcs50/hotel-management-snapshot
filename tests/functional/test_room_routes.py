"""
Functional tests for room routes.

This module contains tests for the room routes and CRUD operations.
"""

import pytest
from flask import url_for
from flask_login import login_user
from bs4 import BeautifulSoup

from app.models.room import Room
from app.models.room_type import RoomType


class TestRoomRoutes:
    """Tests for room routes."""
    
    def test_list_rooms(self, client, admin_user, db_session):
        """Test that the rooms list page loads correctly."""
        with client.application.test_request_context():
            login_user(admin_user)
            
            # Create a room type for testing
            room_type = RoomType(
                name="Standard_list_rooms",
                description="Standard room",
                base_rate=100.0,
                capacity=2
            )
            db_session.add(room_type)
            db_session.commit()
            
            # Create a room for testing
            room = Room(
                number="101",
                room_type_id=room_type.id,
                status=Room.STATUS_AVAILABLE
            )
            db_session.add(room)
            db_session.commit()
            
            # Access room list page
            response = client.get(url_for('room.list_rooms'))
            assert response.status_code == 200
            
            # Check that the room is displayed
            soup = BeautifulSoup(response.data, 'html.parser')
            assert "Room Management" in soup.h1.text
            assert "101" in response.get_data(as_text=True)
    
    def test_view_room(self, client, admin_user, db_session):
        """Test that the room view page loads correctly."""
        with client.application.test_request_context():
            login_user(admin_user)
            
            # Create a room type for testing
            room_type = RoomType(
                name="Standard_view_room",
                description="Standard room",
                base_rate=100.0,
                capacity=2
            )
            db_session.add(room_type)
            db_session.commit()
            
            # Create a room for testing
            room = Room(
                number="102",
                room_type_id=room_type.id,
                status=Room.STATUS_AVAILABLE
            )
            db_session.add(room)
            db_session.commit()
            
            # Access room view page
            response = client.get(url_for('room.view_room', room_id=room.id))
            assert response.status_code == 200
            
            # Check that the room details are displayed
            soup = BeautifulSoup(response.data, 'html.parser')
            assert f"Room {room.number}" in soup.h2.text
            assert "Standard" in response.get_data(as_text=True)
    
    def test_create_room_form(self, client, admin_user, db_session):
        """Test that the room creation form loads correctly."""
        with client.application.test_request_context():
            login_user(admin_user)
            
            # Create a room type for testing
            room_type = RoomType(
                name="Standard_create_form",
                description="Standard room",
                base_rate=100.0,
                capacity=2
            )
            db_session.add(room_type)
            db_session.commit()
            
            # Access room creation form
            response = client.get(url_for('room.create_room'))
            assert response.status_code == 200
            
            # Check that the form is displayed
            soup = BeautifulSoup(response.data, 'html.parser')
            assert "Add New Room" in soup.h2.text
            assert "Room Number" in response.get_data(as_text=True)
            assert "Room Type" in response.get_data(as_text=True)
    
    def test_create_room_submit(self, client, admin_user, db_session):
        """Test that a room can be created successfully."""
        with client.application.test_request_context():
            login_user(admin_user)
            
            # Create a room type for testing
            room_type = RoomType(
                name="Standard_create_submit",
                description="Standard room",
                base_rate=100.0,
                capacity=2
            )
            db_session.add(room_type)
            db_session.commit()
            
            # Submit form to create a room
            response = client.post(
                url_for('room.create_room'),
                data={
                    'number': '103',
                    'room_type_id': room_type.id,
                    'status': Room.STATUS_AVAILABLE,
                    'csrf_token': client.get_csrf_token()
                },
                follow_redirects=True
            )
            
            assert response.status_code == 200
            
            # Check that the room was created
            room = Room.query.filter_by(number='103').first()
            assert room is not None
            
            # Check that we were redirected to the view page
            soup = BeautifulSoup(response.data, 'html.parser')
            assert f"Room {room.number}" in soup.h2.text
    
    def test_create_room_duplicate(self, client, admin_user, db_session):
        """Test that creating a room with a duplicate number shows an error."""
        with client.application.test_request_context():
            login_user(admin_user)
            
            # Create a room type for testing
            room_type = RoomType(
                name="Standard_create_duplicate",
                description="Standard room",
                base_rate=100.0,
                capacity=2
            )
            db_session.add(room_type)
            db_session.commit()
            
            # Create a room
            room = Room(
                number="104",
                room_type_id=room_type.id,
                status=Room.STATUS_AVAILABLE
            )
            db_session.add(room)
            db_session.commit()
            
            # Try to create another room with the same number
            response = client.post(
                url_for('room.create_room'),
                data={
                    'number': '104',
                    'room_type_id': room_type.id,
                    'status': Room.STATUS_AVAILABLE,
                    'csrf_token': client.get_csrf_token()
                },
                follow_redirects=True
            )
            
            assert response.status_code == 200
            
            # Check that an error message is displayed
            assert "already exists" in response.get_data(as_text=True)
    
    def test_edit_room_form(self, client, admin_user, db_session):
        """Test that the room edit form loads correctly."""
        with client.application.test_request_context():
            login_user(admin_user)
            
            # Create a room type for testing
            room_type = RoomType(
                name="Standard_edit_form",
                description="Standard room",
                base_rate=100.0,
                capacity=2
            )
            db_session.add(room_type)
            db_session.commit()
            
            # Create a room for testing
            room = Room(
                number="105",
                room_type_id=room_type.id,
                status=Room.STATUS_AVAILABLE
            )
            db_session.add(room)
            db_session.commit()
            
            # Access room edit form
            response = client.get(url_for('room.edit_room', room_id=room.id))
            assert response.status_code == 200
            
            # Check that the form is displayed with the correct values
            soup = BeautifulSoup(response.data, 'html.parser')
            assert f"Edit Room {room.number}" in soup.h2.text
            
            # Check that the form fields are pre-populated
            form = soup.find('form')
            number_input = form.find('input', {'id': 'number'})
            assert number_input['value'] == '105'
    
    def test_edit_room_submit(self, client, admin_user, db_session):
        """Test that a room can be edited successfully."""
        with client.application.test_request_context():
            login_user(admin_user)
            
            # Create a room type for testing
            room_type = RoomType(
                name="Standard_edit_submit",
                description="Standard room",
                base_rate=100.0,
                capacity=2
            )
            db_session.add(room_type)
            db_session.commit()
            
            # Create a room for testing
            room = Room(
                number="106",
                room_type_id=room_type.id,
                status=Room.STATUS_AVAILABLE
            )
            db_session.add(room)
            db_session.commit()
            
            # Submit form to edit the room
            response = client.post(
                url_for('room.edit_room', room_id=room.id),
                data={
                    'number': '106A',
                    'room_type_id': room_type.id,
                    'status': Room.STATUS_MAINTENANCE,
                    'csrf_token': client.get_csrf_token()
                },
                follow_redirects=True
            )
            
            assert response.status_code == 200
            
            # Check that the room was updated
            db_session.refresh(room)
            assert room.number == '106A'
            assert room.status == Room.STATUS_MAINTENANCE
            
            # Check that we were redirected to the view page
            soup = BeautifulSoup(response.data, 'html.parser')
            assert f"Room {room.number}" in soup.h2.text
    
    def test_delete_room(self, client, admin_user, db_session):
        """Test that a room can be deleted successfully."""
        with client.application.test_request_context():
            login_user(admin_user)
            
            # Create a room type for testing
            room_type = RoomType(
                name="Standard_delete_room",
                description="Standard room",
                base_rate=100.0,
                capacity=2
            )
            db_session.add(room_type)
            db_session.commit()
            
            # Create a room for testing
            room = Room(
                number="107",
                room_type_id=room_type.id,
                status=Room.STATUS_AVAILABLE
            )
            db_session.add(room)
            db_session.commit()
            room_id = room.id
            
            # Submit form to delete the room
            response = client.post(
                url_for('room.delete_room', room_id=room_id),
                data={'csrf_token': client.get_csrf_token()},
                follow_redirects=True
            )
            
            assert response.status_code == 200
            
            # Check that the room was deleted
            room = Room.query.get(room_id)
            assert room is None
            
            # Check that we were redirected to the list page
            soup = BeautifulSoup(response.data, 'html.parser')
            assert "Room Management" in soup.h1.text 