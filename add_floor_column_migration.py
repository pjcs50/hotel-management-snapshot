"""
Migration script to add floor column to rooms table.

This script adds the missing floor column to the rooms table.
"""

import sqlite3
from app_factory import create_app

def add_floor_column():
    """Add floor column to rooms table."""
    app = create_app()
    with app.app_context():
        # Connect to the database
        conn = sqlite3.connect('hotel_management.db')
        cursor = conn.cursor()
        
        try:
            # Check if floor column already exists
            cursor.execute("PRAGMA table_info(rooms)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'floor' not in column_names:
                # Add the floor column
                cursor.execute("ALTER TABLE rooms ADD COLUMN floor INTEGER")
                conn.commit()
                print("✅ Successfully added floor column to rooms table")
            else:
                print("✅ Floor column already exists in rooms table")
                
        except Exception as e:
            print(f"❌ Error adding floor column: {e}")
            conn.rollback()
        finally:
            conn.close()

if __name__ == "__main__":
    add_floor_column() 
 
 
 