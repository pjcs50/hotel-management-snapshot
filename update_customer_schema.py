#!/usr/bin/env python3
"""
Update the customers table schema.

This script adds potentially missing columns to the customers table
based on the current Customer model definition to fix 'no such column' errors.
"""

import os
import sqlite3
import sys

def update_customer_table_schema():
    """Add missing columns to the customers table using SQLite ALTER TABLE."""
    print("Attempting to update customers table schema...")

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
    # Based on app/models/customer.py
    columns_to_add = {
        'email': 'VARCHAR(120)',
        'preferences_json': 'TEXT',
        'documents_json': 'TEXT',
        'notes': 'TEXT',
        'loyalty_points': 'INTEGER DEFAULT 0',
        'loyalty_tier': 'VARCHAR(20) DEFAULT \'Standard\'',
        'date_of_birth': 'DATE',
        'nationality': 'VARCHAR(50)',
        'vip': 'BOOLEAN DEFAULT 0',  # SQLite uses 0 for False, 1 for True
        'stay_count': 'INTEGER DEFAULT 0',
        'total_spent': 'FLOAT DEFAULT 0.0'
    }

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get current columns
        cursor.execute("PRAGMA table_info(customers);")
        existing_columns = [info[1] for info in cursor.fetchall()]
        print(f"Existing columns in 'customers' table: {existing_columns}")

        for col_name, col_def in columns_to_add.items():
            if col_name in existing_columns:
                print(f"Column '{col_name}' already exists.")
            else:
                alter_statement = f"ALTER TABLE customers ADD COLUMN {col_name} {col_def};"
                try:
                    cursor.execute(alter_statement)
                    print(f"Executed: {alter_statement}")
                    print(f"Column '{col_name}' added successfully.")
                except sqlite3.OperationalError as e:
                    # This specific error check might be redundant due to the initial check,
                    # but kept for safety / partial writes.
                    if "duplicate column name" in str(e).lower():
                        print(f"Column '{col_name}' already exists (detected by ALTER TABLE attempt).")
                    else:
                        print(f"Error executing {alter_statement}: {e}")
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

    print("Finished schema update attempt for customers table.")

if __name__ == "__main__":
    update_customer_table_schema() 