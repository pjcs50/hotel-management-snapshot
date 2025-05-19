"""
Sample data creation script.

This script creates sample data for testing the Hotel Management System.
"""

from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

from app_factory import create_app
from db import db
from app.models.user import User
from app.models.room_type import RoomType
from app.models.room import Room
from app.models.customer import Customer


def create_sample_data():
    """Create sample data for the application."""
    app = create_app()
    with app.app_context():
        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("password"),
            role="admin",
            is_active=True
        )
        
        # Create a manager
        manager = User(
            username="manager",
            email="manager@example.com",
            password_hash=generate_password_hash("password"),
            role="manager",
            is_active=True
        )
        
        # Create a receptionist
        receptionist = User(
            username="reception",
            email="reception@example.com",
            password_hash=generate_password_hash("password"),
            role="receptionist",
            is_active=True
        )
        
        # Create a housekeeping user
        housekeeping = User(
            username="housekeeping",
            email="housekeeping@example.com",
            password_hash=generate_password_hash("password"),
            role="housekeeping",
            is_active=True
        )
        
        # Create a customer user
        customer_user = User(
            username="customer",
            email="customer@example.com",
            password_hash=generate_password_hash("password"),
            role="customer",
            is_active=True
        )
        
        db.session.add_all([admin, manager, receptionist, housekeeping, customer_user])
        db.session.commit()
        
        # Create customer profile
        customer = Customer(
            user_id=customer_user.id,
            name="John Doe",
            phone="555-1234",
            address="123 Main St, Anytown",
            emergency_contact="Jane Doe: 555-5678",
            profile_complete=True
        )
        
        db.session.add(customer)
        db.session.commit()
        
        # Create room types
        standard = RoomType(
            name="Standard",
            description="A comfortable room with all basic amenities for a pleasant stay.",
            amenities="Free WiFi, TV, AC, Private bathroom, Queen-size bed",
            base_rate=100.00,
            capacity=2
        )
        
        deluxe = RoomType(
            name="Deluxe",
            description="Spacious room with premium furnishings and additional amenities.",
            amenities="Free WiFi, 50-inch TV, AC, Private bathroom, King-size bed, Mini-bar, Work desk",
            base_rate=150.00,
            capacity=2
        )
        
        suite = RoomType(
            name="Suite",
            description="Luxurious suite with separate living area and premium amenities.",
            amenities="Free WiFi, 55-inch TV, AC, Private bathroom, King-size bed, Mini-bar, Sofa, Dining area",
            base_rate=250.00,
            capacity=4
        )
        
        db.session.add_all([standard, deluxe, suite])
        db.session.commit()
        
        # Create rooms
        rooms = [
            Room(number="101", room_type_id=standard.id, status=Room.STATUS_AVAILABLE),
            Room(number="102", room_type_id=standard.id, status=Room.STATUS_AVAILABLE),
            Room(number="103", room_type_id=standard.id, status=Room.STATUS_AVAILABLE),
            Room(number="201", room_type_id=deluxe.id, status=Room.STATUS_AVAILABLE),
            Room(number="202", room_type_id=deluxe.id, status=Room.STATUS_AVAILABLE),
            Room(number="301", room_type_id=suite.id, status=Room.STATUS_AVAILABLE),
        ]
        
        db.session.add_all(rooms)
        db.session.commit()
        
        print("Sample data created successfully!")


if __name__ == "__main__":
    create_sample_data() 