#!/usr/bin/env python3
"""
Add email column to the customers table.

This script directly adds the missing email column to the customers table
to fix the 'no such column: customers.email' error.
"""

import os
import sqlite3
import sys

# Add the parent directory to the path if necessary (though for direct execution, it might not be)
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def add_email_column_to_customers():
    """Add email column to customers table using SQLite ALTER TABLE."""
    print("Attempting to add email column to customers table...")

    # Determine database path (assuming it's in the instance folder or project root)
    # Prioritize instance folder if it exists
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

    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if the column already exists
        cursor.execute("PRAGMA table_info(customers);")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'email' in columns:
            print("Column 'email' already exists in 'customers' table.")
        else:
            # SQL statement to add the email column
            # Assuming it should be TEXT and nullable, similar to model definition
            alter_statement = "ALTER TABLE customers ADD COLUMN email VARCHAR(120);"
            
            try:
                cursor.execute(alter_statement)
                print(f"Executed: {alter_statement}")
                print("Column 'email' added successfully.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"Column 'email' already exists (detected by ALTER TABLE attempt).")
                else:
                    print(f"Error executing {alter_statement}: {e}")
                    # Re-raise other operational errors for clarity, or handle as needed
                    # For this script, printing the error might be sufficient.

        conn.commit()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

    print("Finished attempt to update customers table.")

if __name__ == "__main__":
    add_email_column_to_customers() 