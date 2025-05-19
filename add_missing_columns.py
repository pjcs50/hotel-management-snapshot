#!/usr/bin/env python3
"""
Add missing columns to room_types table.

This script directly adds the missing columns to the room_types table 
to fix the 'no such column: room_types.amenities_json' error.
"""

import os
import sqlite3
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def add_missing_columns():
    """Add missing columns to room_types table using SQLite ALTER TABLE statements."""
    print("Adding missing columns to room_types table...")
    
    # Database path is in the instance folder
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'hotel_management.db')
    
    print(f"Database path: {db_path}")
    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of tables to verify room_types exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables in database: {tables}")
    
    # SQL statements to add the missing columns
    alter_table_statements = [
        "ALTER TABLE room_types ADD COLUMN amenities_json TEXT DEFAULT '[]';",
        "ALTER TABLE room_types ADD COLUMN image_main VARCHAR(255);",
        "ALTER TABLE room_types ADD COLUMN image_gallery TEXT DEFAULT '[]';",
        "ALTER TABLE room_types ADD COLUMN size_sqm FLOAT;",
        "ALTER TABLE room_types ADD COLUMN bed_type VARCHAR(100);",
        "ALTER TABLE room_types ADD COLUMN max_occupants INTEGER DEFAULT 2;"
    ]
    
    # Execute each ALTER TABLE statement
    for statement in alter_table_statements:
        try:
            cursor.execute(statement)
            print(f"Executed: {statement}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column already exists: {statement}")
            else:
                print(f"Error executing {statement}: {e}")
    
    # Commit the changes
    conn.commit()
    
    # Close the connection
    conn.close()
    
    print("Database schema update completed!")

if __name__ == "__main__":
    add_missing_columns() 