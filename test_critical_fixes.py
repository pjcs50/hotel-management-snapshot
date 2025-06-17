#!/usr/bin/env python3
"""
Comprehensive tests for critical fixes.

This file tests all 4 critical issues that have been fixed:
1. Double Booking Vulnerability
2. Inconsistent Status Transitions
3. Price Calculation Race Conditions
4. Customer Profile Inconsistencies
"""

import threading
import time
import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError

# Test imports - these would be adjusted based on actual test setup
from app import create_app
from db import db
from app.models.user import User
from app.models.customer import Customer
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking
from app.models.seasonal_rate import SeasonalRate
from app.services.booking_service import BookingService, RoomNotAvailableError
from app.utils.state_machine import InvalidTransitionError


class TestDoublBookingPrevention:
    """Tests for double booking vulnerability fixes."""
    
    def test_concurrent_booking_prevention(self):
        """Test that concurrent booking attempts are prevented."""
        # Setup test data
        room_type = RoomType(name="Standard", base_rate=100.0, capacity=2, max_occupants=2)
        db.session.add(room_type)
        db.session.flush()
        
        room = Room(number="101", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db.session.add(room)
        db.session.flush()
        
        user1 = User(username="user1", email="user1@test.com")
        user1.set_password("password")
        user2 = User(username="user2", email="user2@test.com")
        user2.set_password("password")
        db.session.add_all([user1, user2])
        db.session.flush()
        
        customer1 = Customer(user_id=user1.id, name="Customer 1")
        customer2 = Customer(user_id=user2.id, name="Customer 2")
        db.session.add_all([customer1, customer2])
        db.session.commit()
        
        # Test concurrent booking attempts
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=3)
        
        booking_service1 = BookingService(db.session)
        booking_service2 = BookingService(db.session)
        
        results = []
        exceptions = []
        
        def attempt_booking(service, customer_id, result_list, exception_list):
            try:
                booking = service.create_booking(
                    room_id=room.id,
                    customer_id=customer_id,
                    check_in_date=check_in,
                    check_out_date=check_out
                )
                result_list.append(booking)
            except Exception as e:
                exception_list.append(e)
        
        # Start concurrent booking attempts
        thread1 = threading.Thread(
            target=attempt_booking, 
            args=(booking_service1, customer1.id, results, exceptions)
        )
        thread2 = threading.Thread(
            target=attempt_booking, 
            args=(booking_service2, customer2.id, results, exceptions)
        )
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Verify results
        assert len(results) == 1, f"Expected 1 successful booking, got {len(results)}"
        assert len(exceptions) == 1, f"Expected 1 exception, got {len(exceptions)}"
        assert isinstance(exceptions[0], RoomNotAvailableError)
        
        print("✓ Double booking prevention test passed")


class TestStatusTransitions:
    """Tests for status transition validation."""
    
    def test_booking_status_transitions(self):
        """Test booking status transition validation."""
        from app.utils.state_machine import BookingStateMachine, InvalidTransitionError
        
        # Test valid transitions
        assert BookingStateMachine.can_transition('Reserved', 'Checked In')
        assert BookingStateMachine.can_transition('Reserved', 'Cancelled')
        assert BookingStateMachine.can_transition('Checked In', 'Checked Out')
        
        # Test invalid transitions
        assert not BookingStateMachine.can_transition('Checked Out', 'Checked In')
        assert not BookingStateMachine.can_transition('Cancelled', 'Checked In')
        
        # Test validation raises exceptions for invalid transitions
        with pytest.raises(InvalidTransitionError):
            BookingStateMachine.validate_transition('Checked Out', 'Reserved')
        
        print("✓ Booking status transition validation test passed")
    
    def test_room_status_transitions(self):
        """Test room status transition validation."""
        from app.utils.state_machine import RoomStateMachine, InvalidTransitionError
        
        # Test valid transitions
        is_valid, _ = RoomStateMachine.can_transition('Available', 'Booked')
        assert is_valid
        
        is_valid, _ = RoomStateMachine.can_transition('Occupied', 'Needs Cleaning')
        assert is_valid
        
        # Test invalid transitions
        is_valid, error = RoomStateMachine.can_transition('Occupied', 'Available')
        assert not is_valid
        assert "must be cleaned" in error
        
        # Test business logic validation
        is_valid, error = RoomStateMachine.can_transition(
            'Available', 'Under Maintenance', has_active_booking=True
        )
        assert not is_valid
        assert "active bookings" in error
        
        print("✓ Room status transition validation test passed")
    
    def test_booking_model_transition_validation(self):
        """Test that booking model enforces transition validation."""
        # Setup test booking
        room_type = RoomType(name="Standard", base_rate=100.0, capacity=2, max_occupants=2)
        db.session.add(room_type)
        db.session.flush()
        
        room = Room(number="102", room_type_id=room_type.id)
        db.session.add(room)
        db.session.flush()
        
        user = User(username="testuser", email="test@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()
        
        customer = Customer(user_id=user.id, name="Test Customer")
        db.session.add(customer)
        db.session.flush()
        
        booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=date.today() + timedelta(days=1),
            check_out_date=date.today() + timedelta(days=3),
            status=Booking.STATUS_CHECKED_OUT
        )
        db.session.add(booking)
        db.session.commit()
        
        # Try invalid transition - should raise exception
        with pytest.raises(InvalidTransitionError):
            booking.check_in()
        
        print("✓ Booking model transition validation test passed")


class TestPriceCalculationConsistency:
    """Tests for price calculation race condition fixes."""
    
    def test_atomic_price_calculation(self):
        """Test that price calculation is atomic and consistent."""
        # Setup test data
        room_type = RoomType(name="Deluxe", base_rate=200.0, capacity=2, max_occupants=2)
        db.session.add(room_type)
        db.session.flush()
        
        room = Room(number="201", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db.session.add(room)
        db.session.flush()
        
        # Add seasonal rate
        seasonal_rate = SeasonalRate(
            room_type_id=room_type.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            rate_multiplier=1.5
        )
        db.session.add(seasonal_rate)
        db.session.flush()
        
        user = User(username="priceuser", email="price@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()
        
        customer = Customer(user_id=user.id, name="Price Customer")
        db.session.add(customer)
        db.session.commit()
        
        # Test atomic price calculation
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=3)
        
        booking_service = BookingService(db.session)
        
        # Calculate expected price
        expected_price = 200.0 * 1.5 * 2  # base_rate * multiplier * nights
        
        # Create booking with atomic price calculation
        booking = booking_service.create_booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in,
            check_out_date=check_out
        )
        
        # Verify price was calculated and stored atomically
        assert booking.total_price == expected_price
        
        # Verify price is stored in database
        db.session.refresh(booking)
        assert booking.total_price == expected_price
        
        print("✓ Atomic price calculation test passed")
    
    def test_concurrent_price_calculations(self):
        """Test that concurrent price calculations don't interfere."""
        # Setup test data
        room_type = RoomType(name="Suite", base_rate=300.0, capacity=4, max_occupants=4)
        db.session.add(room_type)
        db.session.flush()
        
        room1 = Room(number="301", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        room2 = Room(number="302", room_type_id=room_type.id, status=Room.STATUS_AVAILABLE)
        db.session.add_all([room1, room2])
        db.session.flush()
        
        user1 = User(username="concurrent1", email="c1@test.com")
        user1.set_password("password")
        user2 = User(username="concurrent2", email="c2@test.com")  
        user2.set_password("password")
        db.session.add_all([user1, user2])
        db.session.flush()
        
        customer1 = Customer(user_id=user1.id, name="Concurrent Customer 1")
        customer2 = Customer(user_id=user2.id, name="Concurrent Customer 2")
        db.session.add_all([customer1, customer2])
        db.session.commit()
        
        check_in = date.today() + timedelta(days=2)
        check_out = date.today() + timedelta(days=4)
        
        bookings = []
        exceptions = []
        
        def create_booking_with_price(room_id, customer_id, booking_list, exception_list):
            try:
                service = BookingService(db.session)
                booking = service.create_booking(
                    room_id=room_id,
                    customer_id=customer_id,
                    check_in_date=check_in,
                    check_out_date=check_out
                )
                booking_list.append(booking)
            except Exception as e:
                exception_list.append(e)
        
        # Start concurrent bookings with price calculations
        thread1 = threading.Thread(
            target=create_booking_with_price,
            args=(room1.id, customer1.id, bookings, exceptions)
        )
        thread2 = threading.Thread(
            target=create_booking_with_price,
            args=(room2.id, customer2.id, bookings, exceptions)
        )
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Both bookings should succeed with correct prices
        assert len(bookings) == 2
        assert len(exceptions) == 0
        
        expected_price = 300.0 * 2  # base_rate * nights
        for booking in bookings:
            assert booking.total_price == expected_price
        
        print("✓ Concurrent price calculation test passed")


class TestCustomerEmailConsistency:
    """Tests for customer email consistency fixes."""
    
    def test_email_property_delegation(self):
        """Test that customer email property delegates to user model."""
        user = User(username="emailuser", email="original@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()
        
        customer = Customer(user_id=user.id, name="Email Customer")
        db.session.add(customer)
        db.session.commit()
        
        # Test email reading
        assert customer.email == "original@test.com"
        
        # Test email writing
        customer.email = "updated@test.com"
        assert customer.email == "updated@test.com"
        assert user.email == "updated@test.com"
        
        # Test database persistence
        db.session.commit()
        db.session.refresh(user)
        db.session.refresh(customer)
        
        assert customer.email == "updated@test.com"
        assert user.email == "updated@test.com"
        
        print("✓ Customer email property delegation test passed")
    
    def test_profile_completeness_with_email(self):
        """Test that profile completeness uses user email."""
        user = User(username="completeuser", email="complete@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()
        
        customer = Customer(user_id=user.id, name="Complete Customer")
        db.session.add(customer)
        db.session.commit()
        
        # Profile should be incomplete without phone and address
        assert not customer.is_profile_complete
        
        # Add required fields
        customer.phone = "123-456-7890"
        customer.address = "123 Test St"
        
        # Now profile should be complete (using user email)
        assert customer.is_profile_complete
        
        # Test update method
        result = customer.update_profile_completeness()
        assert result
        assert customer.profile_complete
        
        print("✓ Profile completeness with email test passed")
    
    def test_email_without_user_error(self):
        """Test that setting email without user raises error."""
        customer = Customer(user_id=None, name="Orphan Customer")
        
        with pytest.raises(ValueError, match="Cannot set email: Customer has no associated user"):
            customer.email = "test@test.com"
        
        print("✓ Email without user error test passed")


def run_all_tests():
    """Run all critical fix tests."""
    print("Running Critical Fixes Tests")
    print("=" * 50)
    
    # Setup test database
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    
    with app.app_context():
        db.create_all()
        
        try:
            # Test 1: Double Booking Prevention
            print("\n1. Testing Double Booking Prevention:")
            test_double_booking = TestDoublBookingPrevention()
            test_double_booking.test_concurrent_booking_prevention()
            
            # Test 2: Status Transitions
            print("\n2. Testing Status Transitions:")
            test_transitions = TestStatusTransitions()
            test_transitions.test_booking_status_transitions()
            test_transitions.test_room_status_transitions()
            test_transitions.test_booking_model_transition_validation()
            
            # Test 3: Price Calculation Consistency
            print("\n3. Testing Price Calculation Consistency:")
            test_pricing = TestPriceCalculationConsistency()
            test_pricing.test_atomic_price_calculation()
            test_pricing.test_concurrent_price_calculations()
            
            # Test 4: Customer Email Consistency
            print("\n4. Testing Customer Email Consistency:")
            test_email = TestCustomerEmailConsistency()
            test_email.test_email_property_delegation()
            test_email.test_profile_completeness_with_email()
            test_email.test_email_without_user_error()
            
            print("\n" + "=" * 50)
            print("✅ ALL CRITICAL FIXES TESTS PASSED!")
            print("=" * 50)
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
        finally:
            db.drop_all()


if __name__ == "__main__":
    run_all_tests() 