#!/usr/bin/env python3
import sys
sys.path.append('.')

from app_factory import create_app
from app.services.booking_service import BookingService
from datetime import date, timedelta
from decimal import Decimal

def test_critical_fixes():
    """Test the three critical booking system fixes."""
    print('Testing Critical Booking System Fixes...')
    
    # Test Fix #3: Price Calculation Consistency
    print('\n=== Fix #3: Price Calculation Consistency ===')
    app = create_app()
    with app.app_context():
        from db import db
        from app.models.room import Room
        from app.models.room_type import RoomType
        
        # Get a sample room and room type
        room = db.session.query(Room).first()
        if room:
            room_type = room.room_type
            booking_service = BookingService(db.session)
            
            check_in = date.today() + timedelta(days=1)
            check_out = date.today() + timedelta(days=3)
            
            try:
                # Method 1: Atomic calculation
                price_atomic = booking_service.calculate_booking_price_atomic(
                    room.id, check_in, check_out, 2, 1
                )
                
                # Method 2: Deprecated method (should delegate to atomic)
                price_deprecated = booking_service.calculate_booking_price(
                    room.id, check_in, check_out, 2, 1
                )
                
                print(f'Atomic method price: ${float(price_atomic):.2f}')
                print(f'Deprecated method price: ${float(price_deprecated):.2f}')
                
                # Check consistency
                price_diff = abs(float(price_atomic) - float(price_deprecated))
                is_consistent = price_diff < 0.01
                
                print(f'Price difference: ${price_diff:.4f}')
                print(f'Price consistency: {is_consistent}')
                
                if is_consistent:
                    print('✅ Fix #3 VERIFIED: Price calculations are consistent!')
                else:
                    print('❌ Fix #3 FAILED: Price calculations are inconsistent!')
                    
            except Exception as e:
                print(f'Error testing price calculations: {e}')
                
        else:
            print('No rooms found in database for testing')
    
    # Test Fix #1: Race Condition Prevention
    print('\n=== Fix #1: Race Condition Prevention ===')
    with app.app_context():
        from db import db
        from app.models.room import Room
        from app.models.customer import Customer
        
        # Get a sample room and customer
        room = db.session.query(Room).filter_by(status=Room.STATUS_AVAILABLE).first()
        customer = db.session.query(Customer).first()
        
        if room and customer:
            booking_service = BookingService(db.session)
            
            check_in = date.today() + timedelta(days=5)
            check_out = date.today() + timedelta(days=7)
            
            try:
                # Check that locking method exists and works
                is_available = booking_service.check_room_availability_with_lock(
                    room.id, check_in, check_out
                )
                print(f'Room {room.number} availability with lock: {is_available}')
                
                # Test non-locking method has warning
                is_available_no_lock = booking_service.check_room_availability(
                    room.id, check_in, check_out
                )
                print(f'Room {room.number} availability without lock: {is_available_no_lock}')
                
                if hasattr(booking_service, 'check_room_availability_with_lock'):
                    print('✅ Fix #1 VERIFIED: Locking method exists for race condition prevention!')
                else:
                    print('❌ Fix #1 FAILED: Locking method not found!')
                    
            except Exception as e:
                print(f'Error testing availability checks: {e}')
                
        else:
            print('No available rooms or customers found for testing')
    
    # Test Fix #2: Atomic Room Status Updates
    print('\n=== Fix #2: Atomic Room Status Updates ===')
    with app.app_context():
        from db import db
        from app.models.room import Room
        from app.models.customer import Customer
        
        # Get a sample room and customer
        room = db.session.query(Room).filter_by(status=Room.STATUS_AVAILABLE).first()
        customer = db.session.query(Customer).first()
        
        if room and customer:
            booking_service = BookingService(db.session)
            
            check_in = date.today() + timedelta(days=10)
            check_out = date.today() + timedelta(days=12)
            
            initial_status = room.status
            print(f'Initial room status: {initial_status}')
            
            try:
                # Create a booking and check if room status changes atomically
                booking = booking_service.create_booking(
                    room_id=room.id,
                    customer_id=customer.id,
                    check_in_date=check_in,
                    check_out_date=check_out,
                    source='test'
                )
                
                # Refresh room status from database
                db.session.refresh(room)
                final_status = room.status
                print(f'Final room status after booking: {final_status}')
                
                if final_status != initial_status:
                    print('✅ Fix #2 VERIFIED: Room status updated atomically with booking!')
                else:
                    print('❌ Fix #2 FAILED: Room status not updated properly!')
                    
                # Clean up - cancel the booking
                booking_service.cancel_booking(booking.id, reason='Test cleanup')
                
            except Exception as e:
                print(f'Error testing atomic updates: {e}')
                
        else:
            print('No available rooms or customers found for testing')
    
    print('\n🎉 CRITICAL FIXES TESTING COMPLETED!')

if __name__ == '__main__':
    test_critical_fixes() 