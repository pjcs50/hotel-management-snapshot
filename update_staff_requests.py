"""
Direct database update script for staff_requests table.

This script updates the SQLite database schema for the staff_requests table
to ensure all required columns are present and properly named.
"""

import sqlite3
import os
from datetime import datetime

# Configure the database path
DB_PATH = os.path.join('instance', 'hotel_management.db')

def update_staff_requests_table():
    """Update the staff_requests table schema."""
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get current table structure
    cursor.execute("PRAGMA table_info(staff_requests)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    print(f"Current columns: {column_names}")
    
    try:
        # Start a transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Check if we need to add missing columns
        if 'notes' not in column_names:
            print("Adding 'notes' column")
            cursor.execute("ALTER TABLE staff_requests ADD COLUMN notes TEXT")
        
        # Check if we have the right column names
        if 'processed_at' in column_names and 'handled_at' not in column_names:
            print("Renaming 'processed_at' to 'handled_at'")
            # SQLite doesn't support direct column rename, so we need to create a new table
            cursor.execute("""
                CREATE TABLE staff_requests_new (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    role_requested VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    notes TEXT,
                    created_at DATETIME,
                    handled_at DATETIME,
                    handled_by INTEGER,
                    updated_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(handled_by) REFERENCES users(id)
                )
            """)
            
            # Copy data with column name transformation
            copy_columns = []
            for col in column_names:
                if col == 'processed_at':
                    copy_columns.append('processed_at AS handled_at')
                elif col == 'processed_by':
                    copy_columns.append('processed_by AS handled_by')
                else:
                    copy_columns.append(col)
            
            copy_sql = f"INSERT INTO staff_requests_new SELECT {', '.join(copy_columns)} FROM staff_requests"
            cursor.execute(copy_sql)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE staff_requests")
            cursor.execute("ALTER TABLE staff_requests_new RENAME TO staff_requests")
            
            print("Table structure updated successfully")
        elif 'processed_by' in column_names and 'handled_by' not in column_names:
            print("Only 'processed_by' needs to be renamed")
            # Similar approach as above but just for the one column
            cursor.execute("""
                CREATE TABLE staff_requests_new (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    role_requested VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    notes TEXT,
                    created_at DATETIME,
                    handled_at DATETIME,
                    handled_by INTEGER,
                    updated_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(handled_by) REFERENCES users(id)
                )
            """)
            
            # Copy data with column name transformation
            copy_columns = []
            for col in column_names:
                if col == 'processed_by':
                    copy_columns.append('processed_by AS handled_by')
                else:
                    copy_columns.append(col)
            
            copy_sql = f"INSERT INTO staff_requests_new SELECT {', '.join(copy_columns)} FROM staff_requests"
            cursor.execute(copy_sql)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE staff_requests")
            cursor.execute("ALTER TABLE staff_requests_new RENAME TO staff_requests")
            
            print("Table structure updated successfully")
        
        # Commit the transaction
        conn.commit()
        print("Database schema update completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating database schema: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_staff_requests_table() 