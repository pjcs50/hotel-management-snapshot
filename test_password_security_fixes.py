"""
Comprehensive Password Security Fixes Test Suite

This test validates all implemented password security enhancements including:
- Password strength validation
- Rate limiting protection  
- Secure hashing
- Attack prevention measures
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from flask import Flask

try:
    from app_factory import create_app
    from db import db
    from app.models.user import User
    from app.models.customer import Customer
    from app.services.user_service import UserService
    from app.utils.password_security import (
        PasswordManager, PasswordValidator, PasswordRateLimiter,
        PasswordStrengthError, PasswordRateLimitError
    )
    from app.forms.user_forms import PasswordStrengthValidator
except ImportError as e:
    print(f"Import error: {e}")
    print("Running basic tests without Flask app context...")


class TestPasswordStrengthValidation:
    """Test password strength validation."""
    
    def test_password_validator_initialization(self):
        """Test password validator initializes correctly."""
        validator = PasswordValidator()
        assert validator.min_length == 8
        assert validator.max_length == 128
        assert validator.require_uppercase == True
        assert validator.require_lowercase == True
        assert validator.require_digits == True
        assert validator.require_special == True
        assert len(validator.common_passwords) > 10
        print('✅ Password validator initialized correctly')
    
    def test_strong_password_validation(self):
        """Test validation of strong passwords."""
        validator = PasswordValidator()
        
        strong_passwords = [
            'MySecure123!',
            'Complex#Password456',
            'Ultra$trong789',
            'Mega&Safe2024!',
            'Super@Complex99'
        ]
        
        for password in strong_passwords:
            result = validator.validate_password(password)
            assert result['valid'] == True
            assert result['score'] >= 6
            print(f'✅ Strong password validated: {password} (score: {result["score"]})')
    
    def test_weak_password_rejection(self):
        """Test rejection of weak passwords."""
        validator = PasswordValidator()
        
        weak_passwords = [
            ('weak', 'Too short'),
            ('password', 'Common password'),
            ('PASSWORD', 'No lowercase/digits/special'),
            ('12345678', 'No letters'),
            ('abc123', 'Too simple'),
            ('qwerty123', 'Keyboard pattern'),
            ('aaa111!!!', 'Repeated characters'),
            ('123456789', 'Sequential')
        ]
        
        for password, reason in weak_passwords:
            try:
                validator.validate_password(password)
                assert False, f"Should have rejected {password} ({reason})"
            except PasswordStrengthError:
                print(f'✅ Weak password rejected: {password} ({reason})')
    
    def test_username_similarity_check(self):
        """Test password cannot contain username."""
        validator = PasswordValidator()
        
        try:
            validator.validate_password('testuser123!', username='testuser')
            assert False, "Should reject password containing username"
        except PasswordStrengthError:
            print('✅ Password containing username rejected')
        
        # Should pass if username not in password
        result = validator.validate_password('ComplexPass123!', username='testuser')
        assert result['valid'] == True
        print('✅ Username similarity check working')
    
    def test_password_generator(self):
        """Test secure password generation."""
        validator = PasswordValidator()
        
        for length in [8, 12, 16, 20]:
            password = validator.generate_secure_password(length)
            assert len(password) == length
            
            # Validate generated password meets requirements
            result = validator.validate_password(password)
            assert result['valid'] == True
            assert result['score'] >= 7
            print(f'✅ Generated secure password (length {length}): score {result["score"]}')


class TestPasswordRateLimiting:
    """Test password rate limiting functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes with proper settings."""
        rate_limiter = PasswordRateLimiter()
        assert rate_limiter.max_attempts_per_ip == 10
        assert rate_limiter.max_attempts_per_user == 5
        assert rate_limiter.lockout_duration.total_seconds() == 1800  # 30 minutes
        print('✅ Rate limiter initialized correctly')
    
    def test_normal_rate_limiting(self):
        """Test normal operation within rate limits."""
        rate_limiter = PasswordRateLimiter()
        
        # Should allow normal attempts
        for i in range(3):
            rate_limiter.check_rate_limit(user_id=1, ip_address='192.168.1.1')
            rate_limiter.record_attempt(user_id=1, ip_address='192.168.1.1', success=False)
        
        print('✅ Normal rate limiting allows legitimate attempts')
    
    def test_rate_limit_exceeded(self):
        """Test rate limit enforcement."""
        rate_limiter = PasswordRateLimiter()
        
        # Simulate failed attempts
        for i in range(6):  # Exceed user limit of 5
            try:
                rate_limiter.check_rate_limit(user_id=1, ip_address='192.168.1.1')
                rate_limiter.record_attempt(user_id=1, ip_address='192.168.1.1', success=False)
            except PasswordRateLimitError:
                print(f'✅ Rate limit triggered after {i+1} attempts')
                break
        else:
            raise AssertionError("Rate limit should have been triggered")
    
    def test_successful_login_resets_attempts(self):
        """Test successful login resets attempt counter."""
        rate_limiter = PasswordRateLimiter()
        
        # Make some failed attempts
        for i in range(3):
            rate_limiter.record_attempt(user_id=1, ip_address='192.168.1.1', success=False)
        
        # Successful login should reset
        rate_limiter.record_attempt(user_id=1, ip_address='192.168.1.1', success=True)
        
        # Should be able to attempt again
        rate_limiter.check_rate_limit(user_id=1, ip_address='192.168.1.1')
        print('✅ Successful login resets rate limiting')


class TestPasswordManagerIntegration:
    """Test integrated password management functionality."""
    
    def test_password_manager_initialization(self):
        """Test password manager components initialize correctly."""
        manager = PasswordManager()
        assert isinstance(manager.validator, PasswordValidator)
        assert isinstance(manager.rate_limiter, PasswordRateLimiter)
        assert manager.hash_algorithm == 'pbkdf2:sha256:100000'
        print('✅ Password manager initialized correctly')
    
    def test_validate_and_hash_integration(self):
        """Test password validation and hashing integration."""
        manager = PasswordManager()
        
        result = manager.validate_and_hash(
            'SecurePass123!', 
            username='testuser',
            user_data={'email': 'test@example.com'}
        )
        
        assert 'validation' in result
        assert 'password_hash' in result
        assert result['validation']['valid'] == True
        assert result['password_hash'] is not None
        assert result['password_hash'].startswith('pbkdf2:sha256:100000')
        print('✅ Password validation and hashing integration working')


class TestPasswordSecurityIntegration:
    """Test complete password security integration."""
    
    def test_complete_workflow(self):
        """Test complete password security workflow."""
        print('\n=== Testing Complete Password Security Workflow ===')
        
        # 1. Password validation
        validator = PasswordValidator()
        result = validator.validate_password('ComplexPass123!')
        assert result['valid'] == True
        print('1. ✅ Password strength validation')
        
        # 2. Rate limiting
        rate_limiter = PasswordRateLimiter()
        rate_limiter.check_rate_limit(user_id=1, ip_address='192.168.1.1')
        print('2. ✅ Rate limiting check')
        
        # 3. Secure hashing
        manager = PasswordManager()
        hash_result = manager.validate_and_hash('ComplexPass123!')
        assert hash_result['password_hash'] is not None
        print('3. ✅ Secure password hashing')
        
        print('\n✅ Complete password security workflow validated!')


def run_password_security_tests():
    """Run all password security tests."""
    print('🔐 COMPREHENSIVE PASSWORD SECURITY TEST SUITE')
    print('=' * 50)
    
    test_classes = [
        TestPasswordStrengthValidation,
        TestPasswordRateLimiting,
        TestPasswordManagerIntegration,
        TestPasswordSecurityIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f'\n📋 Running {test_class.__name__}...')
        test_instance = test_class()
        
        # Get test methods
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                # Run test
                method = getattr(test_instance, method_name)
                method()
                passed_tests += 1
                
            except Exception as e:
                print(f'❌ {method_name} failed: {e}')
    
    print(f'\n🔐 PASSWORD SECURITY TEST RESULTS')
    print(f'Total Tests: {total_tests}')
    print(f'Passed: {passed_tests}')
    print(f'Failed: {total_tests - passed_tests}')
    print(f'Success Rate: {(passed_tests/total_tests)*100:.1f}%')
    
    if passed_tests == total_tests:
        print('\n🎉 ALL PASSWORD SECURITY TESTS PASSED!')
        return True
    else:
        print(f'\n⚠️  {total_tests - passed_tests} tests failed')
        return False


if __name__ == '__main__':
    success = run_password_security_tests()
    exit(0 if success else 1) 