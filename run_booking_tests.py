#!/usr/bin/env python3
"""
Run all booking-related tests using pytest.

This script uses pytest to run booking tests from the unit, integration,
and functional test directories.
"""
import sys
import os
import pytest
import argparse

def run_tests(test_type=None, verbose=True):
    """
    Run booking tests of the specified type.
    
    Args:
        test_type: Type of tests to run (unit, integration, functional, or None for all)
        verbose: Whether to run tests in verbose mode
    
    Returns:
        Exit code from pytest
    """
    # Add current directory to path
    sys.path.insert(0, os.getcwd())
    
    # Set up test patterns based on test_type
    test_patterns = []
    
    if test_type == 'unit' or test_type is None:
        test_patterns.append('tests/unit/test_booking*.py')
        if os.path.exists('tests/unit/services'):
            test_patterns.append('tests/unit/services/test_booking*.py')
    
    if test_type == 'integration' or test_type is None:
        test_patterns.append('tests/integration/test_booking*.py')
    
    if test_type == 'functional' or test_type is None:
        test_patterns.append('tests/functional/test_booking*.py')
    
    # Set up pytest args
    pytest_args = []
    
    # Add verbose flag if requested
    if verbose:
        pytest_args.append('-v')
    
    # Add coverage reporting
    pytest_args.extend([
        '--cov=app/services/booking_service.py',
        '--cov=app/models/booking.py',
        '--cov=app/routes/customer.py',
        '--cov=app/routes/receptionist.py',
        '--cov-report=term',
        '--cov-report=html:htmlcov/booking_coverage'
    ])
    
    # Add test patterns
    pytest_args.extend(test_patterns)
    
    print(f"Running booking tests with args: {pytest_args}")
    
    # Run the tests
    try:
        return pytest.main(pytest_args)
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run booking tests with pytest')
    parser.add_argument('--type', choices=['unit', 'integration', 'functional', 'all'], 
                      default='all', help='Type of tests to run')
    parser.add_argument('--quiet', action='store_true', help='Run tests in quiet mode')
    
    args = parser.parse_args()
    
    # Convert 'all' to None for convenience in function call
    test_type = None if args.type == 'all' else args.type
    
    # Exit with the pytest return code
    sys.exit(run_tests(test_type, not args.quiet))
