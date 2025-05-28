#!/usr/bin/env python3
"""
Run all booking tests individually using pytest.

This script finds all booking-related test files and runs them
with proper Flask app context, one file at a time.
"""
import sys
import os
import subprocess
import argparse
import glob

def find_test_files(test_type):
    """Find booking-related test files of the specified type."""
    test_files = []
    
    if test_type == 'unit' or test_type is None:
        unit_files = glob.glob('tests/unit/test_booking*.py')
        service_unit_files = glob.glob('tests/unit/services/test_booking*.py')
        test_files.extend(unit_files)
        test_files.extend(service_unit_files)
    
    if test_type == 'integration' or test_type is None:
        integration_files = glob.glob('tests/integration/test_booking*.py')
        test_files.extend(integration_files)
    
    if test_type == 'functional' or test_type is None:
        functional_files = glob.glob('tests/functional/test_booking*.py')
        test_files.extend(functional_files)
    
    return sorted(test_files)

def run_tests(test_type=None, verbose=True):
    """
    Run all booking tests individually.
    
    Args:
        test_type: Type of tests to run (unit, integration, functional, or None for all)
        verbose: Whether to run in verbose mode
    """
    # Get test files
    test_files = find_test_files(test_type)
    
    if not test_files:
        print(f"No {test_type or 'booking'} test files found.")
        return 1
    
    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file}")
    
    # Results tracking
    passed = 0
    failed = 0
    skipped = 0
    
    # Run each test file with pytest
    for test_file in test_files:
        print(f"\n{'='*80}\nRunning tests in {test_file}\n{'='*80}")
        
        # Build command
        cmd = ['python3', '-m', 'pytest']
        if verbose:
            cmd.append('-v')
        
        # Add coverage args for units
        if 'unit' in test_file:
            cmd.extend([
                '--cov=app/services/booking_service.py',
                '--cov=app/models/booking.py', 
                '--cov-report=term'
            ])
        
        # Add the test file
        cmd.append(test_file)
        
        # Run the command
        result = subprocess.run(cmd, text=True, capture_output=True)
        
        # Parse the output to count tests
        output = result.stdout
        print(output)
        
        # Check for errors
        if result.returncode not in [0, 5]:  # 0=success, 5=no tests collected
            print(f"Error running {test_file}: {result.stderr}")
            failed += 1
        else:
            # Simple parsing to count tests
            if "failed" in output:
                failed += 1
            elif "passed" in output:
                passed += 1
            else:
                skipped += 1
    
    # Report results
    print(f"\n{'='*80}")
    print(f"SUMMARY: {passed} files passed, {failed} files failed, {skipped} files skipped")
    print(f"{'='*80}")
    
    # Optional: Generate consolidated coverage report
    print("\nGenerating consolidated coverage report...")
    subprocess.run(['python3', '-m', 'pytest', 
                   '--cov=app/services/booking_service.py',
                   '--cov=app/models/booking.py', 
                   '--cov=app/routes/customer.py',
                   '--cov=app/routes/receptionist.py',
                   '--cov-report=html:htmlcov/booking_coverage'])
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run booking tests with pytest')
    parser.add_argument('--type', choices=['unit', 'integration', 'functional', 'all'], 
                      default='all', help='Type of tests to run')
    parser.add_argument('--quiet', action='store_true', help='Run tests in quiet mode')
    
    args = parser.parse_args()
    
    # Convert 'all' to None for convenience in function call
    test_type = None if args.type == 'all' else args.type
    
    # Run tests and exit with the result code
    sys.exit(run_tests(test_type, not args.quiet)) 