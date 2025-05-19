"""
Pricing table initialization script.

This script creates the pricing table and adds pricing entries for all existing room types.
"""

from app_factory import create_app
from db import db
from app.models.pricing import Pricing
from app.models.room_type import RoomType
from sqlalchemy import inspect

def init_pricing_tables():
    """Initialize the pricing table with default entries for all room types."""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check if pricing table exists
        if 'pricing' not in inspector.get_table_names():
            print("Creating pricing table...")
            # Create all tables - this will create the pricing table
            Pricing.__table__.create(db.engine)
            print("Pricing table created successfully.")
        else:
            print("Pricing table already exists.")
        
        print("Checking for room types without pricing entries...")
        
        # Get all room types
        room_types = RoomType.query.all()
        count = 0
        
        for room_type in room_types:
            # Check if pricing entry already exists
            pricing = db.session.query(Pricing).filter_by(room_type_id=room_type.id).first()
            
            if pricing is None:
                # Create pricing entry with default values
                pricing = Pricing(
                    room_type_id=room_type.id,
                    weekend_multiplier=1.25,  # 25% higher on weekends
                    peak_season_multiplier=1.5,  # 50% higher in peak season
                    special_event_multiplier=1.75,  # 75% higher for special events
                    last_minute_discount=0.85,  # 15% discount for last minute
                    extended_stay_discount=0.9   # 10% discount for extended stays
                )
                db.session.add(pricing)
                count += 1
        
        if count > 0:
            db.session.commit()
            print(f"Created {count} new pricing entries.")
        else:
            print("All room types already have pricing entries.")

if __name__ == "__main__":
    init_pricing_tables() 