"""
Script to add total_price column to the bookings table.

This script adds the total_price column to existing bookings table and
calculates prices based on room base rate and stay duration.
"""

from app_factory import create_app
from db import db
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from sqlalchemy import inspect, text

def add_total_price_column():
    """Add total_price column to bookings table if it doesn't exist."""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check if total_price column already exists
        columns = [col['name'] for col in inspector.get_columns('bookings')]
        if 'total_price' not in columns:
            print("Adding total_price column to bookings table...")
            # Add the column
            db.session.execute(text('ALTER TABLE bookings ADD COLUMN total_price FLOAT'))
            db.session.commit()
            print("Column added successfully.")
        else:
            print("total_price column already exists.")
        
        # Calculate prices for existing bookings
        print("Calculating prices for existing bookings...")
        bookings = db.session.query(Booking).all()
        updated_count = 0
        
        for booking in bookings:
            if booking.total_price is None:
                # Get room type base rate
                room = db.session.query(Room).get(booking.room_id)
                if room:
                    room_type = db.session.query(RoomType).get(room.room_type_id)
                    if room_type:
                        # Calculate total price based on nights and base rate
                        nights = (booking.check_out_date - booking.check_in_date).days
                        booking.total_price = nights * room_type.base_rate
                        updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"Updated prices for {updated_count} bookings.")
        else:
            print("No bookings needed price updates.")

if __name__ == "__main__":
    add_total_price_column() 