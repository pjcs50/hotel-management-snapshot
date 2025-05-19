"""
Script to add missing columns to the room_types table in the database.

This script directly modifies the database schema to ensure the room_types table
has all required columns defined in the model.
"""

import sqlite3
import os

def update_room_types_table():
    """Add missing columns to the room_types table."""
    # Connect to the database
    db_path = os.path.join('instance', 'hotel_management.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(room_types)")
    columns = [info[1] for info in cursor.fetchall()]
    
    # Add missing columns
    if 'has_view' not in columns:
        print("Adding has_view column to room_types table...")
        cursor.execute("ALTER TABLE room_types ADD COLUMN has_view BOOLEAN DEFAULT FALSE")
    
    if 'has_balcony' not in columns:
        print("Adding has_balcony column to room_types table...")
        cursor.execute("ALTER TABLE room_types ADD COLUMN has_balcony BOOLEAN DEFAULT FALSE")
    
    if 'smoking_allowed' not in columns:
        print("Adding smoking_allowed column to room_types table...")
        cursor.execute("ALTER TABLE room_types ADD COLUMN smoking_allowed BOOLEAN DEFAULT FALSE")
    
    # Commit and close
    conn.commit()
    conn.close()
    print("Database schema updated successfully!")

if __name__ == "__main__":
    update_room_types_table() 