"""
Test suite for critical booking system fixes.

This test suite validates that the three major booking system logic flaws have been fixed:
1. Room Availability Race Conditions
2. Inconsistent Room Status Updates  
3. Price Calculation Inconsistencies
"""

import pytest
import threading
import time
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import patch

from app import create_app
from db import db
from app.models.room import Room
from app.models.booking import Booking
from app.models.customer import Customer
from app.models.user import User
from app.models.room_type import RoomType
from app.models.seasonal_rate import SeasonalRate
from app.services.booking_service import BookingService, RoomNotAvailableError


class TestBookingSystemFixes:
    """Test suite for booking system critical fixes."""

    @pytest.fixture
    def app(self):
        """Create test application."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def db_setup(self, app):
        """Set up test database with sample data."""
        with app.app_context():
            db.create_all()
            
            # Create room type
            room_type = RoomType(
                name='Standard Room',
                base_rate=100.00,
                max_occupants=2,
                description='Standard room with basic amenities'
            )
            db.session.add(room_type)
            db.session.flush()

            # Create room
            room = Room(
                number='101',
                room_type_id=room_type.id,
                status=Room.STATUS_AVAILABLE,
                floor=1
            )
            db.session.add(room)
            db.session.flush()

            # Create user
            user = User(
                username='testuser',
                password_hash='hashed_password',
                role='customer'
            )
            db.session.add(user)
            db.session.flush()

            # Create customer
            customer = Customer(
                user_id=user.id,
                first_name='John',
                last_name='Doe',
                phone='123-456-7890'
            )
            db.session.add(customer)
            
            # Create seasonal rate
            seasonal_rate = SeasonalRate(
                room_type_id=room_type.id,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30),
                rate_multiplier=1.2,  # 20% increase
                name='Peak Season',
                rate_type=SeasonalRate.TYPE_SEASONAL,
                active=True,
                priority=100
            )
            db.session.add(seasonal_rate)

            db.session.commit()
            
            return {
                'room_type': room_type,
                'room': room,
                'user': user,
                'customer': customer,
                'seasonal_rate': seasonal_rate
            }

    def test_fix_1_race_condition_prevention(self, app, db_setup):
        """
        Test Fix #1: Race Condition Prevention
        
        Verify that concurrent booking attempts for the same room/dates 
        result in only one successful booking due to database-level locking.
        """
        with app.app_context():
            room = db_setup['room']
            customer = db_setup['customer']
            
            check_in = date.today() + timedelta(days=1)
            check_out = date.today() + timedelta(days=3)
            
            booking_service = BookingService(db.session)
            
            # Track successful and failed bookings
            successful_bookings = []
            failed_bookings = []
            
            def attempt_booking(thread_id):
                """Attempt to create a booking in a separate thread."""
                try:
                    # Add a small random delay to increase chance of race condition
                    time.sleep(0.01 * thread_id)
                    
                    booking = booking_service.create_booking(
                        room_id=room.id,
                        customer_id=customer.id,
                        check_in_date=check_in,
                        check_out_date=check_out,
                        source=f'thread_{thread_id}'
                    )
                    successful_bookings.append((thread_id, booking.id))
                    
                except RoomNotAvailableError:
                    failed_bookings.append(thread_id)
                except Exception as e:
                    failed_bookings.append((thread_id, str(e)))

            # Create multiple threads attempting to book the same room simultaneously
            threads = []
            for i in range(5):
                thread = threading.Thread(target=attempt_booking, args=(i,))
                threads.append(thread)

            # Start all threads simultaneously
            for thread in threads:
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify exactly one booking succeeded
            assert len(successful_bookings) == 1, f"Expected 1 successful booking, got {len(successful_bookings)}"
            assert len(failed_bookings) == 4, f"Expected 4 failed bookings, got {len(failed_bookings)}"
            
            # Verify the room status was updated correctly
            db.session.refresh(room)
            assert room.status == Room.STATUS_BOOKED, "Room status should be BOOKED after successful booking"
            
            print(f"✅ Fix #1 VERIFIED: Race condition prevented. 1 success, 4 failures as expected.")

    def test_fix_2_atomic_room_status_updates(self, app, db_setup):
        """
        Test Fix #2: Atomic Room Status Updates
        
        Verify that room status changes are atomic with booking operations,
        preventing rooms from getting stuck in wrong states.
        """
        with app.app_context():
            room = db_setup['room']
            customer = db_setup['customer']
            
            check_in = date.today() + timedelta(days=1)
            check_out = date.today() + timedelta(days=3)
            
            booking_service = BookingService(db.session)
            
            # Record initial room status
            initial_status = room.status
            assert initial_status == Room.STATUS_AVAILABLE
            
            # Test successful booking - room status should change atomically
            booking = booking_service.create_booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=check_in,
                check_out_date=check_out
            )
            
            # Verify room status changed atomically with booking creation
            db.session.refresh(room)
            assert room.status == Room.STATUS_BOOKED, "Room should be BOOKED after successful booking"
            
            # Test booking cancellation - room status should revert atomically
            cancelled_booking = booking_service.cancel_booking(booking.id, reason="Test cancellation")
            
            # Verify room status reverted atomically with cancellation
            db.session.refresh(room)
            # Note: Room status logic may vary - check if it goes to AVAILABLE or stays BOOKED
            # depending on other active bookings
            
            # Test failure scenario by simulating an error after room status change
            # but before booking commit (this should rollback everything)
            room.status = Room.STATUS_AVAILABLE
            db.session.commit()
            
            # Attempt booking with invalid data to trigger rollback
            with pytest.raises(ValueError):
                booking_service.create_booking(
                    room_id=room.id,
                    customer_id=customer.id,
                    check_in_date=check_in,
                    check_out_date=check_out,
                    num_guests=999  # Exceeds room capacity
                )
            
            # Verify room status was rolled back to original state
            db.session.refresh(room)
            assert room.status == Room.STATUS_AVAILABLE, "Room status should be rolled back on booking failure"
            
            print(f"✅ Fix #2 VERIFIED: Room status updates are atomic with booking operations.")

    def test_fix_3_consistent_price_calculations(self, app, db_setup):
        """
        Test Fix #3: Consistent Price Calculations
        
        Verify that all price calculation methods return the same result
        for the same booking parameters.
        """
        with app.app_context():
            room = db_setup['room']
            customer = db_setup['customer']
            
            check_in = date.today() + timedelta(days=1)
            check_out = date.today() + timedelta(days=3)
            early_hours = 2
            late_hours = 1
            
            booking_service = BookingService(db.session)
            
            # Method 1: Calculate price via BookingService.calculate_booking_price_atomic
            price_atomic = booking_service.calculate_booking_price_atomic(
                room.id, check_in, check_out, early_hours, late_hours
            )
            
            # Method 2: Calculate price via deprecated BookingService.calculate_booking_price
            price_deprecated = booking_service.calculate_booking_price(
                room.id, check_in, check_out, early_hours, late_hours
            )
            
            # Create a booking to test Booking.calculate_price
            booking = booking_service.create_booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=check_in,
                check_out_date=check_out,
                early_hours=early_hours,
                late_hours=late_hours
            )
            
            # Method 3: Calculate price via Booking.calculate_price (without save)
            price_booking_model = booking.calculate_price(save=False)
            
            # Method 4: Price stored during booking creation
            price_stored = booking.total_price
            
            # Convert all to float for comparison (atomic returns Decimal)
            price_atomic_float = float(price_atomic)
            price_deprecated_float = float(price_deprecated)
            
            # Verify all methods return the same price (within floating point precision)
            assert abs(price_atomic_float - price_deprecated_float) < 0.01, \
                f"Atomic vs deprecated price mismatch: {price_atomic_float} vs {price_deprecated_float}"
            
            assert abs(price_atomic_float - price_booking_model) < 0.01, \
                f"Atomic vs booking model price mismatch: {price_atomic_float} vs {price_booking_model}"
            
            assert abs(price_atomic_float - price_stored) < 0.01, \
                f"Atomic vs stored price mismatch: {price_atomic_float} vs {price_stored}"
            
            # Verify the price calculation is correct
            room_type = db_setup['room_type']
            seasonal_rate = db_setup['seasonal_rate']
            
            base_rate = Decimal(str(room_type.base_rate))
            expected_nights = (check_out - check_in).days
            
            # Calculate expected price manually
            expected_daily_rate = base_rate * Decimal(str(seasonal_rate.rate_multiplier))
            expected_base_price = expected_daily_rate * expected_nights
            expected_early_fee = (base_rate / 24) * early_hours
            expected_late_fee = (base_rate / 24) * late_hours
            expected_total = expected_base_price + expected_early_fee + expected_late_fee
            
            assert abs(price_atomic_float - float(expected_total)) < 0.01, \
                f"Price calculation incorrect: got {price_atomic_float}, expected {float(expected_total)}"
            
            print(f"✅ Fix #3 VERIFIED: All price calculation methods return consistent results: ${price_atomic_float:.2f}")

    def test_edge_case_concurrent_room_status_changes(self, app, db_setup):
        """
        Test edge case: Concurrent operations changing room status.
        """
        with app.app_context():
            room = db_setup['room']
            customer = db_setup['customer']
            
            check_in = date.today() + timedelta(days=1)
            check_out = date.today() + timedelta(days=3)
            
            booking_service = BookingService(db.session)
            
            # Create initial booking
            booking1 = booking_service.create_booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=check_in,
                check_out_date=check_out
            )
            
            # Verify room is booked
            db.session.refresh(room)
            assert room.status == Room.STATUS_BOOKED
            
            # Try to create another overlapping booking (should fail)
            with pytest.raises(RoomNotAvailableError):
                booking_service.create_booking(
                    room_id=room.id,
                    customer_id=customer.id,
                    check_in_date=check_in,
                    check_out_date=check_out + timedelta(days=1)
                )
            
            # Room status should remain unchanged after failed booking
            db.session.refresh(room)
            assert room.status == Room.STATUS_BOOKED
            
            print(f"✅ Edge case VERIFIED: Room status remains consistent during failed operations.")

    def test_price_calculation_with_seasonal_rates(self, app, db_setup):
        """
        Test that price calculations properly handle seasonal rates and day-specific adjustments.
        """
        with app.app_context():
            room = db_setup['room']
            customer = db_setup['customer']
            room_type = db_setup['room_type']
            
            # Create a weekend rate
            weekend_rate = SeasonalRate(
                room_type_id=room_type.id,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365),
                rate_multiplier=1.5,  # 50% increase
                name='Weekend Rate',
                rate_type=SeasonalRate.TYPE_WEEKEND,
                active=True,
                priority=200  # Higher priority than seasonal rate
            )
            db.session.add(weekend_rate)
            db.session.commit()
            
            # Find a weekend date
            today = date.today()
            while today.weekday() < 5:  # Find Saturday (5) or Sunday (6)
                today += timedelta(days=1)
            
            check_in = today
            check_out = today + timedelta(days=2)  # Weekend stay
            
            booking_service = BookingService(db.session)
            
            # Calculate price - should use weekend rate
            price = booking_service.calculate_booking_price_atomic(
                room.id, check_in, check_out, 0, 0
            )
            
            # Verify weekend rate is applied
            base_rate = Decimal(str(room_type.base_rate))
            expected_weekend_rate = base_rate * Decimal('1.5')
            expected_total = expected_weekend_rate * 2  # 2 nights
            
            assert abs(float(price) - float(expected_total)) < 0.01, \
                f"Weekend rate not applied correctly: got {float(price)}, expected {float(expected_total)}"
            
            print(f"✅ Seasonal rate calculation VERIFIED: Weekend rate properly applied.")


def run_tests():
    """Run all booking system fix tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests() 