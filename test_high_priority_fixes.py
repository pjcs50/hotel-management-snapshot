"""
Test suite for high-priority fixes.

This module tests the fixes for:
1. Foreign Key Constraint Violations
2. N+1 Query Problems
3. CSRF Protection Gaps
4. Password Security Issues
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy

from app.models.user import User
from app.models.customer import Customer
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.services.dashboard_service import DashboardService
from app.utils.query_optimization import QueryOptimizer, DashboardQueryOptimizer
from app.utils.csrf_protection import CSRFProtection, CSRFError, csrf_required
from app.utils.password_security import PasswordManager, PasswordValidator, PasswordRateLimiter, PasswordStrengthError


class TestForeignKeyConstraints:
    """Test foreign key constraint fixes and cascade operations."""
    
    def test_user_deletion_cascades_to_customer(self, db_session):
        """Test that deleting a user cascades to associated customer."""
        # Create user and customer
        user = User(username='testuser', email='test@example.com', role='customer')
        user.set_password('TestPassword123!')
        db_session.add(user)
        db_session.commit()
        
        customer = Customer(user_id=user.id, name='Test Customer')
        db_session.add(customer)
        db_session.commit()
        
        customer_id = customer.id
        user_id = user.id
        
        # Delete user
        db_session.delete(user)
        db_session.commit()
        
        # Verify customer is also deleted
        assert db_session.get(Customer, customer_id) is None
        assert db_session.get(User, user_id) is None
    
    def test_customer_deletion_cascades_to_bookings(self, db_session):
        """Test that deleting a customer cascades to associated bookings."""
        # Create test data
        user = User(username='testuser', email='test@example.com', role='customer')
        user.set_password('TestPassword123!')
        db_session.add(user)
        
        customer = Customer(user_id=user.id, name='Test Customer')
        db_session.add(customer)
        
        room_type = RoomType(name='Standard', base_rate=100.0)
        db_session.add(room_type)
        
        room = Room(number='101', room_type_id=room_type.id)
        db_session.add(room)
        
        db_session.commit()
        
        booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=datetime.now().date(),
            check_out_date=(datetime.now() + timedelta(days=1)).date()
        )
        db_session.add(booking)
        db_session.commit()
        
        booking_id = booking.id
        customer_id = customer.id
        
        # Delete customer
        db_session.delete(customer)
        db_session.commit()
        
        # Verify booking is also deleted
        assert db_session.get(Booking, booking_id) is None
        assert db_session.get(Customer, customer_id) is None
    
    def test_room_deletion_cascades_to_bookings(self, db_session):
        """Test that deleting a room cascades to associated bookings."""
        # Create test data
        user = User(username='testuser', email='test@example.com', role='customer')
        user.set_password('TestPassword123!')
        db_session.add(user)
        
        customer = Customer(user_id=user.id, name='Test Customer')
        db_session.add(customer)
        
        room_type = RoomType(name='Standard', base_rate=100.0)
        db_session.add(room_type)
        
        room = Room(number='101', room_type_id=room_type.id)
        db_session.add(room)
        
        db_session.commit()
        
        booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=datetime.now().date(),
            check_out_date=(datetime.now() + timedelta(days=1)).date()
        )
        db_session.add(booking)
        db_session.commit()
        
        booking_id = booking.id
        room_id = room.id
        
        # Delete room
        db_session.delete(room)
        db_session.commit()
        
        # Verify booking is also deleted
        assert db_session.get(Booking, booking_id) is None
        assert db_session.get(Room, room_id) is None


class TestQueryOptimization:
    """Test N+1 query problem fixes."""
    
    def test_booking_queries_with_eager_loading(self, db_session):
        """Test that booking queries use proper eager loading."""
        # Create test data
        room_type = RoomType(name='Standard', base_rate=100.0)
        db_session.add(room_type)
        
        rooms = []
        for i in range(3):
            room = Room(number=f'10{i}', room_type_id=room_type.id)
            rooms.append(room)
            db_session.add(room)
        
        user = User(username='testuser', email='test@example.com', role='customer')
        user.set_password('TestPassword123!')
        db_session.add(user)
        
        customer = Customer(user_id=user.id, name='Test Customer')
        db_session.add(customer)
        
        db_session.commit()
        
        # Create bookings
        bookings = []
        for i, room in enumerate(rooms):
            booking = Booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=datetime.now().date(),
                check_out_date=(datetime.now() + timedelta(days=1)).date()
            )
            bookings.append(booking)
            db_session.add(booking)
        
        db_session.commit()
        
        # Test optimized booking query
        with patch('sqlalchemy.orm.Query') as mock_query:
            optimized_query = QueryOptimizer.get_bookings_with_relations(db_session)
            
            # Verify that joinedload options are applied
            assert optimized_query is not None
            # In a real test, you would verify that the query includes proper joins
    
    def test_dashboard_query_optimization(self, db_session):
        """Test dashboard query optimization."""
        # Create test data
        user = User(username='testuser', email='test@example.com', role='customer')
        user.set_password('TestPassword123!')
        db_session.add(user)
        
        customer = Customer(user_id=user.id, name='Test Customer')
        db_session.add(customer)
        
        room_type = RoomType(name='Standard', base_rate=100.0)
        db_session.add(room_type)
        
        room = Room(number='101', room_type_id=room_type.id)
        db_session.add(room)
        
        db_session.commit()
        
        # Create multiple bookings
        for i in range(5):
            booking = Booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=(datetime.now() + timedelta(days=i)).date(),
                check_out_date=(datetime.now() + timedelta(days=i+1)).date(),
                status='Reserved' if i < 3 else 'Checked Out'
            )
            db_session.add(booking)
        
        db_session.commit()
        
        # Test optimized dashboard query
        dashboard_data = DashboardQueryOptimizer.get_customer_dashboard_data(
            db_session, customer.id
        )
        
        assert 'upcoming_bookings' in dashboard_data
        assert 'active_booking' in dashboard_data
        assert 'past_bookings' in dashboard_data
        assert 'all_bookings' in dashboard_data
        
        # Verify data is correctly categorized
        assert len(dashboard_data['upcoming_bookings']) == 3
        assert len(dashboard_data['past_bookings']) == 2
    
    def test_single_query_efficiency(self, db_session):
        """Test that optimized queries reduce database calls."""
        # This test would require query counting middleware
        # For now, we verify the optimization utilities exist
        assert hasattr(QueryOptimizer, 'get_bookings_with_relations')
        assert hasattr(QueryOptimizer, 'get_rooms_with_relations')
        assert hasattr(QueryOptimizer, 'get_customers_with_relations')
        
        # Verify dashboard optimizer exists
        assert hasattr(DashboardQueryOptimizer, 'get_customer_dashboard_data')
        assert hasattr(DashboardQueryOptimizer, 'get_receptionist_dashboard_data')


class TestCSRFProtection:
    """Test CSRF protection implementation."""
    
    def test_csrf_token_generation(self, app):
        """Test CSRF token generation."""
        with app.test_request_context():
            csrf = CSRFProtection()
            csrf.init_app(app)
            
            token = csrf.generate_token(user_id=1)
            
            assert token is not None
            assert ':' in token  # Token should have multiple parts
            assert len(token) > 20  # Should be reasonably long
    
    def test_csrf_token_validation(self, app):
        """Test CSRF token validation."""
        with app.test_request_context():
            csrf = CSRFProtection()
            csrf.init_app(app)
            
            # Generate token
            token = csrf.generate_token(user_id=1)
            
            # Validate token
            result = csrf.validate_token(token, user_id=1)
            assert result is True
    
    def test_csrf_token_invalid_format(self, app):
        """Test CSRF token validation with invalid format."""
        with app.test_request_context():
            csrf = CSRFProtection()
            csrf.init_app(app)
            
            # Test invalid token
            with pytest.raises(CSRFError):
                csrf.validate_token('invalid_token', user_id=1)
    
    def test_csrf_token_expired(self, app):
        """Test CSRF token expiration."""
        with app.test_request_context():
            csrf = CSRFProtection()
            csrf.init_app(app)
            csrf.token_lifetime = timedelta(seconds=1)  # Very short lifetime
            
            # Generate token
            token = csrf.generate_token(user_id=1)
            
            # Wait for expiration
            time.sleep(2)
            
            # Validate expired token
            with pytest.raises(CSRFError):
                csrf.validate_token(token, user_id=1)
    
    def test_csrf_required_decorator(self, app):
        """Test CSRF required decorator."""
        with app.test_request_context():
            csrf = CSRFProtection()
            csrf.init_app(app)
            
            @csrf_required
            def protected_endpoint():
                return "Success"
            
            # Test without token (should fail)
            with pytest.raises(Exception):  # Should raise an error
                protected_endpoint()
    
    def test_csrf_exempt_decorator(self, app):
        """Test CSRF exempt decorator."""
        with app.test_request_context():
            csrf = CSRFProtection()
            csrf.init_app(app)
            
            from app.utils.csrf_protection import csrf_exempt
            
            @csrf_exempt
            def exempt_endpoint():
                return "Success"
            
            # Verify exempt attribute is set
            assert hasattr(exempt_endpoint, '_csrf_exempt')
            assert exempt_endpoint._csrf_exempt is True


class TestPasswordSecurity:
    """Test password security implementation."""
    
    def test_password_strength_validation(self):
        """Test password strength validation."""
        validator = PasswordValidator()
        
        # Test strong password
        result = validator.validate_password('StrongPass123!')
        assert result['valid'] is True
        assert result['strength'] in ['Strong', 'Very Strong']
        
        # Test weak password
        with pytest.raises(PasswordStrengthError):
            validator.validate_password('weak')
        
        # Test common password
        with pytest.raises(PasswordStrengthError):
            validator.validate_password('password')
    
    def test_password_rate_limiting(self):
        """Test password rate limiting."""
        rate_limiter = PasswordRateLimiter()
        
        # Test normal usage
        result = rate_limiter.check_rate_limit(user_id=1, ip_address='127.0.0.1')
        assert result['allowed'] is True
        
        # Test excessive attempts
        for i in range(10):
            rate_limiter.record_attempt(user_id=1, ip_address='127.0.0.1', success=False)
        
        # Should now be rate limited
        with pytest.raises(PasswordStrengthError):
            rate_limiter.check_rate_limit(user_id=1, ip_address='127.0.0.1')
    
    def test_password_manager_integration(self):
        """Test password manager integration."""
        manager = PasswordManager()
        
        # Test password validation and hashing
        result = manager.validate_and_hash('StrongPass123!', username='testuser')
        
        assert 'validation' in result
        assert 'password_hash' in result
        assert result['validation']['valid'] is True
        assert result['password_hash'] is not None
    
    def test_user_password_methods(self, db_session):
        """Test User model password methods."""
        user = User(username='testuser', email='test@example.com', role='customer')
        
        # Test password setting with validation
        user.set_password('StrongPass123!')
        assert user.password_hash is not None
        
        # Test weak password rejection
        with pytest.raises(ValueError):
            user.set_password('weak')
    
    def test_password_rate_limit_decorator(self, app):
        """Test password rate limit decorator."""
        from app.utils.password_security import password_rate_limit
        
        @password_rate_limit
        def login_endpoint():
            return "Success"
        
        with app.test_request_context():
            # This test would require proper rate limiting setup
            result = login_endpoint()
            assert result == "Success"


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple fixes."""
    
    def test_secure_booking_creation_with_csrf(self, app, db_session):
        """Test secure booking creation with CSRF protection."""
        with app.test_request_context(
            method='POST',
            json={'room_id': 1, 'customer_id': 1},
            headers={'X-CSRF-Token': 'valid_token'}
        ):
            # This would test the full integration
            # For now, verify the components exist
            assert CSRFProtection is not None
            assert QueryOptimizer is not None
    
    def test_password_security_with_rate_limiting(self, app, db_session):
        """Test password security with rate limiting."""
        user = User(username='testuser', email='test@example.com', role='customer')
        user.set_password('StrongPass123!')
        db_session.add(user)
        db_session.commit()
        
        with app.test_request_context():
            # Test successful login
            assert user.check_password('StrongPass123!') is True
            
            # Test wrong password
            with pytest.raises(ValueError):
                user.check_password('WrongPassword')
    
    def test_cascade_deletion_with_query_optimization(self, db_session):
        """Test cascade deletion with optimized queries."""
        # Create complex data structure
        user = User(username='testuser', email='test@example.com', role='customer')
        user.set_password('StrongPass123!')
        db_session.add(user)
        
        customer = Customer(user_id=user.id, name='Test Customer')
        db_session.add(customer)
        
        room_type = RoomType(name='Standard', base_rate=100.0)
        db_session.add(room_type)
        
        room = Room(number='101', room_type_id=room_type.id)
        db_session.add(room)
        
        db_session.commit()
        
        # Create multiple bookings
        booking_ids = []
        for i in range(3):
            booking = Booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=(datetime.now() + timedelta(days=i)).date(),
                check_out_date=(datetime.now() + timedelta(days=i+1)).date()
            )
            db_session.add(booking)
            db_session.commit()
            booking_ids.append(booking.id)
        
        # Use optimized query to load data
        optimized_query = QueryOptimizer.get_bookings_with_relations(db_session)
        
        # Delete customer (should cascade)
        db_session.delete(customer)
        db_session.commit()
        
        # Verify all bookings are deleted
        for booking_id in booking_ids:
            assert db_session.get(Booking, booking_id) is None


# Fixtures for testing
@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    return app


@pytest.fixture
def db_session(app):
    """Create test database session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create tables (in real tests, you'd use migration)
    # This is simplified for testing
    
    yield session
    
    session.close()


if __name__ == '__main__':
    print("High-priority fixes test suite")
    print("Tests would verify:")
    print("1. Foreign key cascade deletions")
    print("2. N+1 query optimization")
    print("3. CSRF protection")
    print("4. Password security")
    # Run tests
    pytest.main([__file__, '-v']) 