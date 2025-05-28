#!/usr/bin/env python3
"""
Run basic booking service tests with Flask application context.

This is a simplified script that runs a specific booking test
within the application context, ensuring proper SQLAlchemy initialization.
"""

import unittest
import sys
import os
from app_factory import create_app
import importlib.util

# Create a single Flask app instance for testing
app = create_app({
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'WTF_CSRF_ENABLED': False,
    'SECRET_KEY': 'test-secret-key-for-sessions'  # Add a secret key for sessions
})

def run_single_test(test_file):
    """
    Run a single test file within the Flask application context.
    """
    # Add the current directory to path to ensure imports work
    sys.path.insert(0, os.getcwd())
    
    try:
        print(f"Testing file: {test_file}")
        
        # Import the db module after creating the app
        if "sqlalchemy" in app.extensions:
            print("SQLAlchemy already registered with app, using existing instance")
            # Get the db from the app's extensions
            from flask import current_app
        else:
            print("Initializing SQLAlchemy")
            # Import the db module to initialize it
            from db import db
        
        # Create a Flask app context for the test
        with app.app_context():
            # Get database from app extensions
            if "sqlalchemy" in app.extensions:
                db = app.extensions['sqlalchemy'].db
                print("Using existing SQLAlchemy from app")
            else:
                from db import db
                db.init_app(app)
                print("Initialized new SQLAlchemy instance")
            
            # Create all tables
            db.create_all()
            print("Created database tables")
            
            # Import the test module dynamically
            module_name = os.path.splitext(os.path.basename(test_file))[0]
            spec = importlib.util.spec_from_file_location(module_name, test_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find test cases in the module
            test_cases = []
            for item_name in dir(module):
                item = getattr(module, item_name)
                if isinstance(item, type) and issubclass(item, unittest.TestCase) and item is not unittest.TestCase:
                    test_cases.append(item)
            
            if not test_cases:
                print(f"No test cases found in {test_file}")
                return False
            
            # Create a test suite and run the tests
            suite = unittest.TestSuite()
            for test_class in test_cases:
                print(f"Adding test case: {test_class.__name__}")
                suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(test_class))
            
            # Run the tests
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            
            # Clean up
            try:
                db.session.remove()
                print("Database session cleaned up")
            except:
                pass
            
            return result.wasSuccessful()
            
    except Exception as e:
        print(f"Error running test {test_file}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Simple test file to run
    test_file_path = 'tests/unit/test_booking_service.py'
    
    if len(sys.argv) > 1:
        test_file_path = sys.argv[1]
    
    success = run_single_test(test_file_path)
    print(f"\nTests {'passed' if success else 'failed'}") 