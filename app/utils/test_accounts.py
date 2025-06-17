"""
Test Accounts Utility

This module ensures that test accounts are always available in the system.
Called during app initialization to guarantee login access.
"""

from flask import current_app
from werkzeug.security import generate_password_hash
from app.models import User, db


def ensure_test_accounts_exist():
    """
    Ensures that critical test accounts exist in the database.
    This function is called during app startup to guarantee access.
    """
    try:
        # Define the test accounts that should always exist
        test_accounts = [
            {
                'username': 'admin_test',
                'email': 'admin@example.com',
                'password_hash': generate_password_hash('password'),
                'role': 'admin'
            },
            {
                'username': 'manager_test',
                'email': 'manager@example.com',
                'password_hash': generate_password_hash('password'),
                'role': 'manager'
            },
            {
                'username': 'housekeeping_test',
                'email': 'housekeeping@example.com',
                'password_hash': generate_password_hash('password'),
                'role': 'housekeeping'
            },
            {
                'username': 'reception_test',
                'email': 'reception@example.com',
                'password_hash': generate_password_hash('password'),
                'role': 'receptionist'
            },
            {
                'username': 'customer_test',
                'email': 'customer@example.com',
                'password_hash': generate_password_hash('password'),
                'role': 'customer'
            }
        ]
        
        accounts_created = 0
        
        for account_info in test_accounts:
            # Check if account already exists
            existing_user = User.query.filter_by(email=account_info['email']).first()
            
            if not existing_user:
                # Create new account with direct password hash to bypass validation
                new_user = User(
                    username=account_info['username'],
                    email=account_info['email'],
                    role=account_info['role'],
                    is_active=True
                )
                # Directly set the password hash to bypass validation
                new_user.password_hash = account_info['password_hash']
                
                db.session.add(new_user)
                accounts_created += 1
                current_app.logger.info(f"Created test account: {account_info['email']} ({account_info['role']})")
            else:
                # Update existing account to ensure it's active and has correct role
                existing_user.is_active = True
                existing_user.role = account_info['role']
                existing_user.password_hash = account_info['password_hash']
        
        if accounts_created > 0:
            db.session.commit()
            current_app.logger.info(f"Test accounts ensured: {accounts_created} created/updated")
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to ensure test accounts: {e}")
        db.session.rollback()
        return False


def get_test_credentials():
    """
    Returns a dict of test account credentials for documentation/reference.
    """
    return {
        'admin@example.com': 'password',
        'manager@example.com': 'password',
        'housekeeping@example.com': 'password',
        'reception@example.com': 'password',
        'customer@example.com': 'password'
    }


def log_test_credentials():
    """
    Logs the test credentials to the console for easy reference.
    """
    credentials = get_test_credentials()
    current_app.logger.info("🔐 Test Account Credentials Available:")
    for email, password in credentials.items():
        role = email.split('@')[0]
        current_app.logger.info(f"   {email} / {password} ({role})") 