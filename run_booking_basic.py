#!/usr/bin/env python3
"""
Bare-bones script to run a single booking test.
"""
import unittest
import importlib.util
import sys
import os
from app_factory import create_app
from flask import Flask

# Create a clean application for testing
test_app = create_app({
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'WTF_CSRF_ENABLED': False,
    'SECRET_KEY': 'test-secret-key'
})

# Load a test file
def load_test_file(file_path):
    """Load test cases from a file."""
    try:
        # Import the module
        module_name = os.path.basename(file_path).replace('.py', '')
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find test cases
        test_cases = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, unittest.TestCase) and attr is not unittest.TestCase:
                test_cases.append(attr)
        
        return test_cases
    except Exception as e:
        print(f"Error loading test file: {e}")
        return []

# Main function
def main():
    # Get test file from command line or use default
    test_file = sys.argv[1] if len(sys.argv) > 1 else 'tests/unit/test_booking_service.py'
    print(f"Loading tests from {test_file}")
    
    # Ensure path is set properly
    sys.path.insert(0, os.getcwd())
    
    # Create app context
    with test_app.app_context():
        # Initialize DB if needed
        from db import db
        db.init_app(test_app)
        db.create_all()
        
        # Load test cases
        test_cases = load_test_file(test_file)
        
        if not test_cases:
            print("No test cases found.")
            return 1
        
        # Create and run test suite
        suite = unittest.TestSuite()
        for test_class in test_cases:
            print(f"Adding test class: {test_class.__name__}")
            suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(test_class))
        
        # Run the tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # Clean up
        db.session.remove()
        
        return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main()) 