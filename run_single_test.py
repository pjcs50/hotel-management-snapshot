#!/usr/bin/env python3
"""
Run a single pytest test with the Flask application context.
"""
import sys
import os
import pytest

# Test to run (this will be imported by pytest)
TEST_FILE = 'tests/unit/test_booking_service.py::test_get_availability_calendar_data_empty_hotel'

if __name__ == "__main__":
    # Add current directory to path
    sys.path.insert(0, os.getcwd())
    
    # Get test file from arguments if provided
    if len(sys.argv) > 1:
        TEST_FILE = sys.argv[1]
    
    print(f"Running test: {TEST_FILE}")
    
    # Run the test with pytest
    try:
        result = pytest.main(['-v', TEST_FILE])
        sys.exit(result)
    except Exception as e:
        print(f"Error running test: {e}")
        sys.exit(1) 