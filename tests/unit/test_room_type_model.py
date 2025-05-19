'''
Unit tests for the RoomType model.
'''
import pytest
import json
from app.models.room_type import RoomType


def test_create_room_type_with_all_fields(db_session):
    """Test creating a RoomType instance with all enhanced fields."""
    room_type_data = {
        'name': 'Deluxe Suite',
        'description': 'A luxurious suite with ocean view.',
        'base_rate': 299.99,
        'capacity': 2,
        'has_view': True,
        'has_balcony': True,
        'smoking_allowed': False,
        'amenities_json': '["Jacuzzi", "Mini Bar"]',
        'image_main': '/static/images/deluxe_suite_main.jpg',
        'image_gallery': '["/static/images/deluxe_suite_1.jpg", "/static/images/deluxe_suite_2.jpg"]',
        'size_sqm': 55.5,
        'bed_type': 'King Size',
        'max_occupants': 3
    }
    room_type = RoomType(**room_type_data)
    db_session.add(room_type)
    db_session.commit()

    retrieved_room_type = RoomType.query.filter_by(name='Deluxe Suite').first()
    assert retrieved_room_type is not None
    assert retrieved_room_type.description == 'A luxurious suite with ocean view.'
    assert retrieved_room_type.base_rate == 299.99
    assert retrieved_room_type.capacity == 2
    assert retrieved_room_type.has_view is True
    assert retrieved_room_type.has_balcony is True
    assert retrieved_room_type.smoking_allowed is False
    assert json.loads(retrieved_room_type.amenities_json) == ["Jacuzzi", "Mini Bar"]
    assert retrieved_room_type.image_main == '/static/images/deluxe_suite_main.jpg'
    assert json.loads(retrieved_room_type.image_gallery) == ["/static/images/deluxe_suite_1.jpg", "/static/images/deluxe_suite_2.jpg"]
    assert retrieved_room_type.size_sqm == 55.5
    assert retrieved_room_type.bed_type == 'King Size'
    assert retrieved_room_type.max_occupants == 3

def test_room_type_amenities_property(db_session):
    """Test the amenities property getter and setter."""
    room_type = RoomType(name='Standard Room', base_rate=100.0, amenities_json='["Wi-Fi", "TV"]')
    db_session.add(room_type)
    db_session.commit()

    # Test getter
    assert "Wi-Fi" in room_type.amenities
    assert "TV" in room_type.amenities

    # Test setter
    room_type.amenities = ["Coffee Maker", "Hair Dryer"]
    db_session.commit()
    assert "Coffee Maker" in room_type.amenities
    assert "Hair Dryer" in room_type.amenities
    assert "Wi-Fi" not in room_type.amenities # Old amenities should be replaced
    assert json.loads(room_type.amenities_json) == ["Coffee Maker", "Hair Dryer"]

    # Test with standard amenities mixed in
    room_type.has_view = True
    room_type.amenities = ["Scenic View", "Iron"] # "Scenic View" should be handled by has_view
    db_session.commit()
    assert "Scenic View" in room_type.amenities
    assert "Iron" in room_type.amenities
    assert json.loads(room_type.amenities_json) == ["Iron"] # Only "Iron" should be in JSON

def test_room_type_gallery_images_property(db_session):
    """Test the gallery_images property getter and setter."""
    room_type = RoomType(name='Economy Room', base_rate=50.0, image_gallery='["img1.jpg"]')
    db_session.add(room_type)
    db_session.commit()

    # Test getter
    assert room_type.gallery_images == ["img1.jpg"]

    # Test setter
    new_gallery = ["img2.jpg", "img3.jpg"]
    room_type.gallery_images = new_gallery
    db_session.commit()
    assert room_type.gallery_images == new_gallery
    assert json.loads(room_type.image_gallery) == new_gallery

def test_room_type_default_values(db_session):
    """Test that default values are set correctly."""
    room_type = RoomType(name='Basic Room', base_rate=75.0)
    db_session.add(room_type)
    db_session.commit()

    assert room_type.amenities_json == '[]'
    assert room_type.amenities == []
    assert room_type.image_gallery == '[]'
    assert room_type.gallery_images == []
    assert room_type.max_occupants == 2 # Default from model
    assert room_type.has_view is False
    assert room_type.has_balcony is False
    assert room_type.smoking_allowed is False


def test_room_type_to_dict(db_session):
    """Test the to_dict method."""
    room_type = RoomType(
        name='Test Dict Room',
        description='Testing to_dict',
        base_rate=120.0,
        capacity=2,
        has_view=True,
        amenities_json='["Test Amenity"]',
        image_main='main.jpg',
        size_sqm=30.0,
        bed_type='Queen',
        max_occupants=2
    )
    db_session.add(room_type)
    db_session.commit()

    room_type_dict = room_type.to_dict()
    assert room_type_dict['name'] == 'Test Dict Room'
    assert room_type_dict['base_rate'] == 120.0
    assert "Test Amenity" in room_type_dict['amenities']
    assert "Scenic View" in room_type_dict['amenities'] # From has_view=True
    assert room_type_dict['image_main'] == 'main.jpg'
    assert room_type_dict['size_sqm'] == 30.0
    assert room_type_dict['bed_type'] == 'Queen'
    assert room_type_dict['max_occupants'] == 2
    assert room_type_dict['is_available'] is False # No rooms created yet
    assert room_type_dict['available_count'] == 0

# Add more tests for edge cases or invalid data if necessary 