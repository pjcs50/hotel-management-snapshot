"""
Migration script to update the loyalty_ledger table.

This script updates the loyalty_ledger table to add txn_type column if it doesn't exist.
"""

import sys
import os
import datetime
from sqlalchemy import inspect

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app and models
from app_factory import create_app
from db import db
from app.models.loyalty_ledger import LoyaltyLedger

def check_if_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table."""
    
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return any(column['name'] == column_name for column in columns)

def check_if_table_exists(engine, table_name):
    """Check if a table exists in the database."""
    
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def main():
    """Update the loyalty_ledger table."""
    
    # Create app
    app = create_app()
    
    # Use app context
    with app.app_context():
        try:
            engine = db.engine
            
            # Check if the loyalty_ledger table exists
            if not check_if_table_exists(engine, 'loyalty_ledger'):
                print("Table loyalty_ledger does not exist. Creating...")
                
                # Create the table using SQLAlchemy models
                db.create_all()
                print("Created loyalty_ledger table")
            else:
                print("Table loyalty_ledger exists. Checking columns...")
                
                # Check if columns that we need exist
                columns_to_check = {
                    'txn_type': "ALTER TABLE loyalty_ledger ADD COLUMN txn_type VARCHAR(20) NOT NULL DEFAULT 'earn'",
                    'txn_dt': "ALTER TABLE loyalty_ledger ADD COLUMN txn_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
                    'staff_id': "ALTER TABLE loyalty_ledger ADD COLUMN staff_id INTEGER REFERENCES users(id)"
                }
                
                for column_name, sql in columns_to_check.items():
                    if not check_if_column_exists(engine, 'loyalty_ledger', column_name):
                        print(f"Column {column_name} does not exist. Adding...")
                        db.session.execute(sql)
                        db.session.commit()
                        print(f"Added column {column_name}")
                    else:
                        print(f"Column {column_name} exists")
            
            print("Loyalty ledger table update completed successfully")
        except Exception as e:
            print(f"Error: {str(e)}")
            db.session.rollback()


if __name__ == "__main__":
    main() 