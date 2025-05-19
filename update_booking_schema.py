#!/usr/bin/env python3
"""
Update the bookings table schema.

This script adds potentially missing columns to the bookings table
based on the current Booking model definition to fix 'no such column' errors.
"""

import os
import sqlite3
import sys

def update_booking_table_schema():
    """Add missing columns to the bookings table using SQLite ALTER TABLE."""
    print("Attempting to update bookings table schema...")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    instance_folder_db_path = os.path.join(current_dir, 'instance', 'hotel_management.db')
    root_folder_db_path = os.path.join(current_dir, 'hotel_management.db')

    if os.path.exists(instance_folder_db_path):
        db_path = instance_folder_db_path
    elif os.path.exists(root_folder_db_path):
        db_path = root_folder_db_path
    else:
        print(f"Error: Database file hotel_management.db not found in instance/ or project root.")
        print(f"Checked paths: {instance_folder_db_path} and {root_folder_db_path}")
        return

    print(f"Using database at: {db_path}")

    # Columns to ensure exist, their types, and default values if applicable
    # Based on app/models/booking.py
    columns_to_add = {
        'early_hours': 'INTEGER DEFAULT 0',
        'late_hours': 'INTEGER DEFAULT 0',
        'total_price': 'FLOAT',
        'num_guests': 'INTEGER DEFAULT 1',
        'payment_status': 'VARCHAR(20) DEFAULT \'Not Paid\'',
        'notes': 'TEXT',
        'special_requests_json': 'TEXT',
        'room_preferences_json': 'TEXT',
        'confirmation_code': 'VARCHAR(20)',
        'payment_amount': 'FLOAT DEFAULT 0.0',
        'deposit_amount': 'FLOAT DEFAULT 0.0',
        'source': 'VARCHAR(50)',
        'booking_date': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
        'loyalty_points_earned': 'INTEGER DEFAULT 0',
        'guest_name': 'VARCHAR(100)',
        'cancellation_reason': 'TEXT',
        'cancelled_by': 'INTEGER', # Nullable, FK handled by SQLAlchemy model
        'cancellation_date': 'DATETIME',
        'cancellation_fee': 'FLOAT DEFAULT 0.0'
    }

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get current columns
        cursor.execute("PRAGMA table_info(bookings);")
        existing_columns = [info[1] for info in cursor.fetchall()]
        print(f"Existing columns in 'bookings' table: {existing_columns}")

        for col_name, col_def in columns_to_add.items():
            if col_name in existing_columns:
                print(f"Column '{col_name}' already exists in bookings table.")
            else:
                alter_statement = f"ALTER TABLE bookings ADD COLUMN {col_name} {col_def};"
                try:
                    cursor.execute(alter_statement)
                    print(f"Executed: {alter_statement}")
                    print(f"Column '{col_name}' added successfully to bookings table.")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"Column '{col_name}' already exists in bookings table (detected by ALTER TABLE attempt).")
                    else:
                        print(f"Error executing {alter_statement} for bookings table: {e}")
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

    print("Finished schema update attempt for bookings table.")

if __name__ == "__main__":
    update_booking_table_schema() 