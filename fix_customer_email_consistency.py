#!/usr/bin/env python3
"""
Migration script to fix customer email consistency issues.

This script:
1. Migrates any customer email data to the corresponding user record
2. Removes the email column from the customers table
3. Ensures data consistency between User and Customer models

Run this script BEFORE deploying the updated models.
"""

import os
import sys
import sqlite3
from pathlib import Path

def find_database():
    """Find the SQLite database file."""
    possible_paths = [
        "hotel_management.db",
        "instance/hotel_management.db",
        os.path.join(os.getcwd(), "hotel_management.db"),
        os.path.join(os.getcwd(), "instance", "hotel_management.db")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    print("Error: Database file hotel_management.db not found in expected locations.")
    print("Checked paths:", possible_paths)
    return None

def migrate_customer_emails():
    """Migrate customer emails to user table and remove customer email column."""
    db_path = find_database()
    if not db_path:
        return False
    
    print(f"Using database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if customers table has email column
        cursor.execute("PRAGMA table_info(customers)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'email' not in columns:
            print("Email column not found in customers table. Migration may have already been completed.")
            conn.close()
            return True
        
        print("Starting customer email migration...")
        
        # Step 1: Migrate email data from customers to users where customer email exists
        # but user email is empty or different
        migration_query = """
        UPDATE users 
        SET email = (
            SELECT customers.email 
            FROM customers 
            WHERE customers.user_id = users.id 
            AND customers.email IS NOT NULL 
            AND customers.email != ''
        )
        WHERE EXISTS (
            SELECT 1 
            FROM customers 
            WHERE customers.user_id = users.id 
            AND customers.email IS NOT NULL 
            AND customers.email != ''
            AND (users.email IS NULL OR users.email = '' OR users.email != customers.email)
        )
        """
        
        cursor.execute(migration_query)
        migrated_count = cursor.rowcount
        print(f"Migrated {migrated_count} customer email records to user table")
        
        # Step 2: Check for any conflicts where customer and user emails differ
        conflict_query = """
        SELECT c.id as customer_id, c.email as customer_email, u.email as user_email, u.username
        FROM customers c
        JOIN users u ON c.user_id = u.id
        WHERE c.email IS NOT NULL 
        AND c.email != '' 
        AND u.email IS NOT NULL 
        AND u.email != ''
        AND c.email != u.email
        """
        
        cursor.execute(conflict_query)
        conflicts = cursor.fetchall()
        
        if conflicts:
            print(f"Warning: Found {len(conflicts)} email conflicts:")
            for conflict in conflicts:
                print(f"  Customer {conflict[0]}: customer_email='{conflict[1]}', user_email='{conflict[2]}' (username: {conflict[3]})")
            print("User email will be kept as the authoritative source.")
        
        # Step 3: Create new customers table without email column
        print("Creating new customers table structure...")
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(customers)")
        current_columns = cursor.fetchall()
        
        # Build new column list excluding email
        new_columns = []
        for col in current_columns:
            col_name = col[1]
            if col_name != 'email':
                col_type = col[2]
                nullable = "NOT NULL" if col[3] else ""
                default = f"DEFAULT {col[4]}" if col[4] is not None else ""
                primary_key = "PRIMARY KEY" if col[5] else ""
                
                column_def = f"{col_name} {col_type} {nullable} {default} {primary_key}".strip()
                new_columns.append(column_def)
        
        # Create new table
        create_table_sql = f"""
        CREATE TABLE customers_new (
            {', '.join(new_columns)}
        )
        """
        
        cursor.execute(create_table_sql)
        
        # Copy data (excluding email column)
        copy_columns = [col[1] for col in current_columns if col[1] != 'email']
        copy_sql = f"""
        INSERT INTO customers_new ({', '.join(copy_columns)})
        SELECT {', '.join(copy_columns)} FROM customers
        """
        
        cursor.execute(copy_sql)
        copied_count = cursor.rowcount
        print(f"Copied {copied_count} customer records to new table")
        
        # Step 4: Replace old table with new table
        cursor.execute("DROP TABLE customers")
        cursor.execute("ALTER TABLE customers_new RENAME TO customers")
        
        # Step 5: Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_loyalty ON customers (loyalty_tier, loyalty_points)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_user_id ON customers (user_id)")
        
        print("Table structure updated successfully")
        
        # Commit all changes
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE email IS NOT NULL AND email != ''")
        user_email_count = cursor.fetchone()[0]
        
        print(f"Verification: {customer_count} customers, {user_email_count} users with email")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error during migration: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"Unexpected error during migration: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def verify_migration():
    """Verify that the migration was successful."""
    db_path = find_database()
    if not db_path:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check that email column is gone from customers table
        cursor.execute("PRAGMA table_info(customers)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'email' in columns:
            print("Verification failed: Email column still exists in customers table")
            return False
        
        # Check that all customers have corresponding users with emails
        cursor.execute("""
            SELECT COUNT(*) 
            FROM customers c
            JOIN users u ON c.user_id = u.id
            WHERE u.email IS NULL OR u.email = ''
        """)
        
        customers_without_user_email = cursor.fetchone()[0]
        
        if customers_without_user_email > 0:
            print(f"Warning: {customers_without_user_email} customers have users without email addresses")
        
        print("Migration verification completed successfully!")
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error during verification: {e}")
        return False

if __name__ == "__main__":
    print("Customer Email Consistency Migration")
    print("=" * 40)
    
    if migrate_customer_emails():
        print("\nRunning verification...")
        verify_migration()
        print("\nMigration process completed!")
        print("\nNext steps:")
        print("1. Deploy the updated Customer model code")
        print("2. Test that customer.email property works correctly")
        print("3. Update any code that directly accessed customer.email field")
    else:
        print("\nMigration failed. Please check the errors above.")
        sys.exit(1) 