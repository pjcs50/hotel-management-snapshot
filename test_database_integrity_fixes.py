"""
Test Database Integrity and Error Handling Fixes.

This test suite verifies that the database integrity and error handling
improvements are working correctly.
"""

import pytest
import logging
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError, OperationalError
from app_factory import create_app
from db import db
from app.models.user import User
from app.models.customer import Customer
from app.models.booking import Booking
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.payment import Payment
from app.utils.database_integrity import db_integrity, safe_delete_with_cascade
from app.utils.error_handling import error_handler, ErrorContext, ErrorSeverity, ErrorCategory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def app():
    """Create test application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def db_session(app):
    """Create database session for testing."""
    with app.app_context():
        yield db.session


class TestDatabaseIntegrity:
    """Test database integrity features."""
    
    def test_cascade_delete_user_to_customer(self, db_session):
        """Test that deleting a user cascades to customer."""
        # Create user and customer
        user = User(username='testuser', email='test@example.com', role='customer')
        user.set_password('TestPassword123!')
        db_session.add(user)
        db_session.commit()
        
        customer = Customer(user_id=user.id, name='Test Customer')
        db_session.add(customer)
        db_session.commit()
        
        user_id = user.id
        customer_id = customer.id
        
        # Use safe delete
        result = safe_delete_with_cascade(User, user_id)
        
        # Verify both records are deleted
        assert db_session.get(User, user_id) is None
        assert db_session.get(Customer, customer_id) is None
        assert result['success'] is True
        assert 'customer_profile' in result['affected_records']
    
    def test_cascade_delete_customer_to_bookings(self, db_session):
        """Test that deleting a customer cascades to bookings."""
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
        
        customer_id = customer.id
        booking_id = booking.id
        
        # Use safe delete
        result = safe_delete_with_cascade(Customer, customer_id)
        
        # Verify booking is also deleted
        assert db_session.get(Customer, customer_id) is None
        assert db_session.get(Booking, booking_id) is None
        assert result['success'] is True
        assert 'bookings' in result['affected_records']
    
    def test_restrict_delete_room_with_bookings(self, db_session):
        """Test that room deletion is restricted when bookings exist."""
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
        
        room_id = room.id
        
        # Attempt to delete room should fail
        with pytest.raises(Exception) as exc_info:
            safe_delete_with_cascade(Room, room_id)
        
        assert "RESTRICT" in str(exc_info.value) or "related" in str(exc_info.value).lower()
        
        # Room should still exist
        assert db_session.get(Room, room_id) is not None
    
    def test_validate_business_rules(self, db_session):
        """Test business rule validation."""
        # Test invalid booking dates
        invalid_booking_data = {
            'check_in_date': datetime.now().date() + timedelta(days=2),
            'check_out_date': datetime.now().date() + timedelta(days=1),  # Before check-in
            'num_guests': 2,
            'total_price': 100.0
        }
        
        with pytest.raises(Exception) as exc_info:
            db_integrity.validate_business_rules(Booking, invalid_booking_data)
        
        assert "check_in_date" in str(exc_info.value).lower() or "date" in str(exc_info.value).lower()
    
    def test_referential_integrity_check(self, db_session):
        """Test referential integrity checking."""
        # Create some test data
        user = User(username='testuser', email='test@example.com', role='customer')
        user.set_password('TestPassword123!')
        db_session.add(user)
        db_session.commit()
        
        customer = Customer(user_id=user.id, name='Test Customer')
        db_session.add(customer)
        db_session.commit()
        
        # Check integrity
        integrity_result = db_integrity.check_referential_integrity()
        
        assert integrity_result['integrity_ok'] is True
        assert len(integrity_result['issues']) == 0
        assert 'checked_at' in integrity_result


class TestErrorHandling:
    """Test enhanced error handling features."""
    
    def test_error_classification(self, db_session):
        """Test that errors are properly classified."""
        context = ErrorContext(
            operation="test_operation",
            user_id=1,
            additional_data={'test': 'data'}
        )
        
        # Test database error handling
        db_error = IntegrityError("statement", "params", "orig")
        result = error_handler.handle_error(
            error=db_error,
            context=context,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE
        )
        
        assert result['error_type'] == 'IntegrityError'
        assert result['severity'] == 'high'
        assert result['category'] == 'database'
        assert result['operation'] == 'test_operation'
        assert 'error_id' in result
        assert 'user_message' in result
    
    def test_error_recovery_strategies(self, db_session):
        """Test automatic error recovery strategies."""
        context = ErrorContext(operation="test_recovery")
        
        # Test integrity error recovery
        integrity_error = IntegrityError("foreign key constraint", "params", "orig")
        result = error_handler.handle_error(
            error=integrity_error,
            context=context,
            auto_recover=True
        )
        
        assert result['recovered'] is False  # Recovery attempted but failed (expected)
        assert 'user_message' in result
    
    def test_error_frequency_tracking(self, db_session):
        """Test error frequency tracking."""
        context = ErrorContext(operation="test_frequency")
        
        # Generate multiple errors of the same type
        for i in range(3):
            error = ValueError(f"Test error {i}")
            error_handler.handle_error(error, context)
        
        # Check error statistics
        stats = error_handler.error_counts
        assert 'ValueError:test_frequency' in stats
        assert stats['ValueError:test_frequency'] == 3
    
    def test_transaction_rollback(self, db_session):
        """Test that database transactions are properly rolled back on error."""
        # Start a transaction
        user = User(username='testuser', email='test@example.com', role='customer')
        db_session.add(user)
        
        # Simulate an error that should trigger rollback
        context = ErrorContext(operation="test_rollback")
        db_error = OperationalError("statement", "params", "database error")
        
        error_handler.handle_error(
            error=db_error,
            context=context,
            category=ErrorCategory.DATABASE
        )
        
        # Transaction should be rolled back
        assert not db_session.is_active or len(db_session.new) == 0
    
    def test_critical_error_alerting(self, db_session):
        """Test critical error alerting."""
        context = ErrorContext(operation="test_critical")
        
        critical_error = Exception("Critical system failure")
        result = error_handler.handle_error(
            error=critical_error,
            context=context,
            severity=ErrorSeverity.CRITICAL
        )
        
        assert result['severity'] == 'critical'
        assert 'critical' in result['user_message'].lower()


class TestIntegrationScenarios:
    """Test integration scenarios combining database integrity and error handling."""
    
    def test_booking_creation_with_error_handling(self, db_session):
        """Test booking creation with comprehensive error handling."""
        from app.services.booking_service import BookingService
        
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
        
        booking_service = BookingService(db_session)
        
        # Test successful booking creation
        booking = booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=datetime.now().date() + timedelta(days=1),
            check_out_date=datetime.now().date() + timedelta(days=2)
        )
        
        assert booking is not None
        assert booking.room_id == room.id
        assert booking.customer_id == customer.id
    
    def test_cascade_delete_with_error_recovery(self, db_session):
        """Test cascade delete operations with error recovery."""
        # Create complex data structure
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
        bookings = []
        for i in range(3):
            booking = Booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=(datetime.now() + timedelta(days=i)).date(),
                check_out_date=(datetime.now() + timedelta(days=i+1)).date()
            )
            db_session.add(booking)
            bookings.append(booking)
        
        db_session.commit()
        
        # Create payments for bookings
        for booking in bookings:
            payment = Payment(
                booking_id=booking.id,
                amount=100.0,
                payment_type='Credit Card'
            )
            db_session.add(payment)
        
        db_session.commit()
        
        user_id = user.id
        
        # Delete user (should cascade properly)
        result = safe_delete_with_cascade(User, user_id)
        
        assert result['success'] is True
        assert db_session.get(User, user_id) is None
        
        # All related records should be deleted
        for booking in bookings:
            assert db_session.get(Booking, booking.id) is None


def run_tests():
    """Run all database integrity and error handling tests."""
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    run_tests() 