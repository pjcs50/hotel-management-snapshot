"""
Room Type model module.

This module defines the RoomType model which represents types of rooms in the hotel.
"""

from datetime import datetime
import json
from db import db


class RoomType(db.Model):
    """Model representing a type of room in the hotel.
    
    This model stores information about room types, including their
    name, description, base price, capacity, amenities, and images.
    """

    __tablename__ = 'room_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    base_rate = db.Column(db.Float, nullable=False, default=0.0)
    capacity = db.Column(db.Integer, nullable=False, default=2)
    has_view = db.Column(db.Boolean, default=False)
    has_balcony = db.Column(db.Boolean, default=False)
    smoking_allowed = db.Column(db.Boolean, default=False)
    
    # New fields for enhanced functionality
    amenities_json = db.Column(db.Text, nullable=True, default='[]')
    image_main = db.Column(db.String(255), nullable=True)
    image_gallery = db.Column(db.Text, nullable=True, default='[]')  # JSON string of image URLs
    size_sqm = db.Column(db.Float, nullable=True)  # Room size in square meters
    bed_type = db.Column(db.String(100), nullable=True)  # e.g., "King", "Queen", "Twin"
    max_occupants = db.Column(db.Integer, default=2)  # Maximum number of occupants
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - these will be defined by SQLAlchemy backref
    # rooms: One-to-many relationship with Room model
    # pricing_rules: One-to-many relationship with SeasonalRate model

    def __repr__(self):
        """Return a helpful representation of this instance."""
        return f"<RoomType id={self.id} name={self.name} price=${self.base_rate:.2f}>"
    
    @property
    def amenities(self):
        """Return a list of amenities for this room type.
        
        Returns:
            list: A list of strings representing the amenities for this room type.
        """
        standard_amenities = []
        
        if self.has_view:
            standard_amenities.append("Scenic View")
        if self.has_balcony:
            standard_amenities.append("Private Balcony")
        if self.smoking_allowed:
            standard_amenities.append("Smoking Allowed")
        
        # Add custom amenities from JSON
        try:
            custom_amenities = json.loads(self.amenities_json or '[]')
            return standard_amenities + custom_amenities
        except (json.JSONDecodeError, TypeError):
            return standard_amenities
    
    @amenities.setter
    def amenities(self, amenities_list):
        """Set the amenities list for this room type.
        
        Args:
            amenities_list: A list of strings representing custom amenities
        """
        # Filter out standard amenities that are tracked in separate fields
        standard_amenities = ["Scenic View", "Private Balcony", "Smoking Allowed"]
        custom_amenities = [a for a in amenities_list if a not in standard_amenities]
        
        self.amenities_json = json.dumps(custom_amenities)
    
    @property
    def gallery_images(self):
        """Return the list of image URLs for the gallery.
        
        Returns:
            list: A list of strings representing image URLs
        """
        try:
            return json.loads(self.image_gallery or '[]')
        except (json.JSONDecodeError, TypeError):
            return []
    
    @gallery_images.setter
    def gallery_images(self, image_urls):
        """Set the gallery images for this room type.
        
        Args:
            image_urls: A list of strings representing image URLs
        """
        self.image_gallery = json.dumps(image_urls)
    
    @property
    def is_available(self):
        """Check if there are any available rooms of this type.
        
        Returns:
            bool: True if there are available rooms, False otherwise
        """
        from app.models.room import Room
        
        available_count = Room.query.filter_by(
            room_type_id=self.id,
            status=Room.STATUS_AVAILABLE
        ).count()
        
        return available_count > 0
    
    @property
    def available_count(self):
        """Get the number of available rooms of this type.
        
        Returns:
            int: The number of available rooms
        """
        from app.models.room import Room
        
        return Room.query.filter_by(
            room_type_id=self.id,
            status=Room.STATUS_AVAILABLE
        ).count()
    
    def to_dict(self):
        """Return a dictionary representation of the room type."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'base_rate': self.base_rate,
            'capacity': self.capacity,
            'amenities': self.amenities,
            'has_view': self.has_view,
            'has_balcony': self.has_balcony,
            'smoking_allowed': self.smoking_allowed,
            'image_main': self.image_main,
            'gallery_images': self.gallery_images,
            'size_sqm': self.size_sqm,
            'bed_type': self.bed_type,
            'max_occupants': self.max_occupants,
            'available_count': self.available_count,
            'is_available': self.is_available,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 