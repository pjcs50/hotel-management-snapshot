#!/usr/bin/env python3
"""
Comprehensive Hotel Management System Seed Data Generator.

This script creates highly consistent, time-aware dummy data for the entire
Flask + SQLite-based Hotel Management System. All data is relational and 
reflects real hotel operations.

Features:
- Time-based booking lifecycle automation
- Consistent foreign key relationships
- Realistic customer authentication data
- Staff user accounts with appropriate roles
- Dashboard-ready metrics and reporting data
"""

import sys
import os
import random
import string
from datetime import datetime, date, timedelta
from decimal import Decimal
from faker import Faker

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app_factory import create_app
from db import db

# Import all models
from app.models.user import User
from app.models.customer import Customer
from app.models.room_type import RoomType
from app.models.room import Room
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.housekeeping_task import HousekeepingTask
from app.models.loyalty_ledger import LoyaltyLedger
from app.models.loyalty_redemption import LoyaltyRedemption

# Initialize Faker
fake = Faker()

# Global data storage for consistent referencing
USERS = {}
CUSTOMERS = {}
ROOM_TYPES = {}
ROOMS = {}
BOOKINGS = {}

def clear_all_data():
    """Clear all existing data from the database."""
    print("🗑️  Clearing existing data...")
    
    # Delete in proper order to respect foreign key constraints
    db.session.query(LoyaltyRedemption).delete()
    db.session.query(LoyaltyLedger).delete()
    db.session.query(HousekeepingTask).delete()
    db.session.query(Payment).delete()
    db.session.query(Booking).delete()
    db.session.query(Customer).delete()
    db.session.query(Room).delete()
    db.session.query(RoomType).delete()
    db.session.query(User).delete()
    
    db.session.commit()
    print("✅ All existing data cleared!")

def create_staff_users():
    """Create staff users with different roles and authentication credentials."""
    print("👥 Creating staff users...")
    
    # Import the password generator
    from app.utils.password_security import PasswordValidator
    password_generator = PasswordValidator()
    
    staff_data = [
        # Admin users
        {
            'username': 'admin',
            'email': 'admin@hotel.com',
            'role': 'admin',
            'name': 'System Administrator'
        },
        {
            'username': 'manager1',
            'email': 'manager@hotel.com',
            'role': 'manager',
            'name': 'Hotel Manager'
        },
        
        # Receptionist users
        {
            'username': 'receptionist1',
            'email': 'reception1@hotel.com',
            'role': 'receptionist',
            'name': 'Sarah Johnson'
        },
        {
            'username': 'receptionist2',
            'email': 'reception2@hotel.com',
            'role': 'receptionist',
            'name': 'Mike Chen'
        },
        
        # Housekeeping users
        {
            'username': 'housekeeper1',
            'email': 'housekeeper1@hotel.com',
            'role': 'housekeeping',
            'name': 'Maria Rodriguez'
        },
        {
            'username': 'housekeeper2',
            'email': 'housekeeper2@hotel.com',
            'role': 'housekeeping',
            'name': 'James Wilson'
        },
        {
            'username': 'housekeeper3',
            'email': 'housekeeper3@hotel.com',
            'role': 'housekeeping',
            'name': 'Lisa Thompson'
        },
    ]
    
    created_credentials = []
    
    for staff in staff_data:
        # Generate a secure password
        secure_password = password_generator.generate_secure_password(length=12)
        
        user = User(
            username=staff['username'],
            email=staff['email'],
            role=staff['role'],
            is_active=True
        )
        
        # Set password using the model's secure method
        user.set_password(secure_password)
        
        db.session.add(user)
        USERS[staff['role'] + '_' + staff['username']] = user
        
        # Store credentials for display
        created_credentials.append({
            'role': staff['role'],
            'username': staff['username'],
            'password': secure_password
        })
        
    db.session.commit()
    print(f"✅ Created {len(staff_data)} staff users")
    
    # Print login credentials for testing
    print("\n🔑 STAFF LOGIN CREDENTIALS:")
    for cred in created_credentials:
        print(f"   {cred['role'].upper()}: {cred['username']} / {cred['password']}")

def create_customer_users():
    """Create customer users with full profiles and authentication."""
    print("\n👤 Creating customer users...")
    
    # Import the password generator
    from app.utils.password_security import PasswordValidator
    password_generator = PasswordValidator()
    
    # Generate one secure password for all customers for easy testing
    customer_password = password_generator.generate_secure_password(length=10)
    
    customer_names = [
        'John Smith', 'Emily Johnson', 'Michael Brown', 'Sarah Davis',
        'David Wilson', 'Lisa Anderson', 'Robert Taylor', 'Jennifer Moore',
        'William Jackson', 'Jessica White', 'James Martin', 'Ashley Garcia',
        'Christopher Rodriguez', 'Amanda Lewis', 'Daniel Thompson'
    ]
    
    loyalty_tiers = [Customer.TIER_STANDARD] * 8 + [Customer.TIER_SILVER] * 4 + [Customer.TIER_GOLD] * 2 + [Customer.TIER_PLATINUM] * 1
    
    for i, name in enumerate(customer_names):
        # Create user account
        username = name.lower().replace(' ', '_')
        email = f"{username}@email.com"
        
        user = User(
            username=username,
            email=email,
            role='customer',
            is_active=True
        )
        user.set_password(customer_password)  # Same secure password for all customers for easy testing
        
        db.session.add(user)
        db.session.flush()  # Get the user ID
        
        # Create customer profile
        customer = Customer(
            user_id=user.id,
            name=name,
            phone=fake.phone_number(),
            address=fake.address(),
            date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=80),
            nationality=fake.country(),
            loyalty_tier=loyalty_tiers[i],
            loyalty_points=random.randint(0, 15000),
            stay_count=random.randint(0, 25),
            total_spent=random.uniform(0, 5000),
            vip=(i < 3),  # First 3 customers are VIP
            profile_complete=True
        )
        
        # Set customer preferences
        preferences = {
            'room_type': random.choice(['Standard Room', 'Deluxe Room', 'Suite']),
            'floor_preference': random.choice(['low', 'high', 'no_preference']),
            'view_preference': random.choice(['city', 'garden', 'no_preference']),
            'bed_type': random.choice(['king', 'queen', 'twin', 'no_preference']),
            'amenities': random.sample(['wifi', 'minibar', 'room_service', 'late_checkout'], k=random.randint(1, 3))
        }
        customer.preferences = preferences
        
        db.session.add(customer)
        CUSTOMERS[f'customer_{i+1}'] = customer
        USERS[f'customer_{username}'] = user
    
    db.session.commit()
    print(f"✅ Created {len(customer_names)} customer accounts")
    
    # Print some customer login credentials
    print("\n🔑 SAMPLE CUSTOMER LOGIN CREDENTIALS:")
    print(f"   All customers use password: {customer_password}")
    for i, name in enumerate(customer_names[:5]):
        username = name.lower().replace(' ', '_')
        print(f"   {name}: {username}")

def create_room_types():
    """Create comprehensive room types with pricing."""
    print("\n🏨 Creating room types...")
    
    room_types_data = [
        {
            'name': 'Standard Room',
            'description': 'Comfortable standard room with essential amenities',
            'base_rate': 89.99,
            'capacity': 2,
            'size_sqm': 25,
            'bed_type': 'Queen',
            'max_occupants': 2,
            'has_view': False,
            'has_balcony': False,
            'smoking_allowed': False,
            'amenities': ['Free Wi-Fi', 'TV', 'Air Conditioning', 'Phone', 'Mini Fridge']
        },
        {
            'name': 'Deluxe Room',
            'description': 'Spacious deluxe room with premium furnishings and city view',
            'base_rate': 149.99,
            'capacity': 2,
            'size_sqm': 35,
            'bed_type': 'King',
            'max_occupants': 3,
            'has_view': True,
            'has_balcony': False,
            'smoking_allowed': False,
            'amenities': ['Free Wi-Fi', 'Smart TV', 'Premium Bedding', 'Desk', 'Coffee Maker', 'Mini Bar', 'Safe']
        },
        {
            'name': 'Suite',
            'description': 'Luxurious suite with separate living area and panoramic views',
            'base_rate': 249.99,
            'capacity': 4,
            'size_sqm': 55,
            'bed_type': 'King',
            'max_occupants': 4,
            'has_view': True,
            'has_balcony': True,
            'smoking_allowed': False,
            'amenities': ['Free Wi-Fi', 'Smart TV', 'Premium Bedding', 'Sofa', 'Dining Area', 'Coffee Maker', 'Mini Bar', 'Safe', 'Bathrobe', 'Slippers']
        },
        {
            'name': 'Family Room',
            'description': 'Large family room with multiple beds and family amenities',
            'base_rate': 179.99,
            'capacity': 6,
            'size_sqm': 45,
            'bed_type': 'Queen + Twin',
            'max_occupants': 6,
            'has_view': False,
            'has_balcony': False,
            'smoking_allowed': False,
            'amenities': ['Free Wi-Fi', 'TV', 'Air Conditioning', 'Desk', 'Refrigerator', 'Microwave', 'Cribs Available']
        }
    ]
    
    for room_type_data in room_types_data:
        amenities = room_type_data.pop('amenities', [])
        room_type = RoomType(**room_type_data)
        room_type.amenities = amenities
        
        db.session.add(room_type)
        ROOM_TYPES[room_type_data['name']] = room_type
    
    db.session.commit()
    print(f"✅ Created {len(room_types_data)} room types")

def create_rooms():
    """Create 60 rooms across different types and floors."""
    print("\n🚪 Creating 60 rooms...")
    
    room_type_distribution = {
        'Standard Room': 25,
        'Deluxe Room': 20,
        'Suite': 10,
        'Family Room': 5
    }
    
    room_statuses = [
        Room.STATUS_AVAILABLE,
        Room.STATUS_BOOKED,
        Room.STATUS_OCCUPIED,
        Room.STATUS_CLEANING,
        Room.STATUS_MAINTENANCE
    ]
    
    room_counter = 1
    
    for room_type_name, count in room_type_distribution.items():
        room_type = ROOM_TYPES[room_type_name]
        
        for i in range(count):
            # Generate room number (101-106, 201-206, etc.)
            floor = (room_counter - 1) // 10 + 1
            room_on_floor = (room_counter - 1) % 10 + 1
            room_number = f"{floor}{room_on_floor:02d}"
            
            # Assign status based on realistic distribution
            if room_counter <= 35:
                status = Room.STATUS_AVAILABLE
            elif room_counter <= 45:
                status = Room.STATUS_BOOKED
            elif room_counter <= 52:
                status = Room.STATUS_OCCUPIED
            elif room_counter <= 57:
                status = Room.STATUS_CLEANING
            else:
                status = Room.STATUS_MAINTENANCE
            
            room = Room(
                number=room_number,
                room_type_id=room_type.id,
                status=status,
                last_cleaned=fake.date_time_between(start_date='-7d', end_date='now') if status != Room.STATUS_MAINTENANCE else None
            )
            
            db.session.add(room)
            ROOMS[room_number] = room
            room_counter += 1
    
    db.session.commit()
    print(f"✅ Created {len(ROOMS)} rooms")
    
    # Print room distribution
    for status in room_statuses:
        count = len([r for r in ROOMS.values() if r.status == status])
        print(f"   {status}: {count} rooms")

def create_bookings_with_lifecycle():
    """Create bookings with proper time-based lifecycle automation."""
    print("\n📅 Creating bookings with lifecycle automation...")
    
    today = date.today()
    customers = list(CUSTOMERS.values())
    available_rooms = [r for r in ROOMS.values() if r.status in [Room.STATUS_AVAILABLE, Room.STATUS_BOOKED, Room.STATUS_OCCUPIED]]
    
    booking_scenarios = [
        # Past bookings (checked out)
        {'type': 'past', 'count': 15, 'status': Booking.STATUS_CHECKED_OUT},
        
        # Current bookings (active today)
        {'type': 'current', 'count': 12, 'status': Booking.STATUS_CHECKED_IN},
        
        # Future bookings (upcoming)
        {'type': 'future', 'count': 18, 'status': Booking.STATUS_RESERVED},
        
        # Some cancelled bookings
        {'type': 'cancelled', 'count': 5, 'status': Booking.STATUS_CANCELLED}
    ]
    
    booking_id = 1
    
    for scenario in booking_scenarios:
        for i in range(scenario['count']):
            customer = random.choice(customers)
            room = random.choice(available_rooms)
            
            # Generate dates based on scenario type
            if scenario['type'] == 'past':
                check_in = today - timedelta(days=random.randint(7, 90))
                check_out = check_in + timedelta(days=random.randint(1, 7))
                room.status = Room.STATUS_CLEANING if random.random() < 0.3 else Room.STATUS_AVAILABLE
                
            elif scenario['type'] == 'current':
                check_in = today - timedelta(days=random.randint(0, 3))
                check_out = today + timedelta(days=random.randint(1, 5))
                room.status = Room.STATUS_OCCUPIED
                
            elif scenario['type'] == 'future':
                check_in = today + timedelta(days=random.randint(1, 60))
                check_out = check_in + timedelta(days=random.randint(1, 7))
                room.status = Room.STATUS_BOOKED
                
            else:  # cancelled
                check_in = today + timedelta(days=random.randint(1, 30))
                check_out = check_in + timedelta(days=random.randint(1, 5))
            
            # Calculate pricing
            nights = (check_out - check_in).days
            base_price = room.room_type.base_rate * nights
            
            # Add early/late fees occasionally
            early_hours = random.randint(0, 6) if random.random() < 0.2 else 0
            late_hours = random.randint(0, 8) if random.random() < 0.3 else 0
            
            early_fee = early_hours * 15.0
            late_fee = late_hours * 20.0
            total_price = base_price + early_fee + late_fee
            
            # Create booking
            booking = Booking(
                room_id=room.id,
                customer_id=customer.id,
                check_in_date=check_in,
                check_out_date=check_out,
                status=scenario['status'],
                early_hours=early_hours,
                late_hours=late_hours,
                total_price=total_price,
                num_guests=random.randint(1, room.room_type.max_occupants),
                guest_name=customer.name,
                confirmation_code=f"HTL{booking_id:06d}",
                source=random.choice(['Website', 'Phone', 'Walk-in', 'Travel Agency']),
                booking_date=check_in - timedelta(days=random.randint(1, 30))
            )
            
            # Set payment status based on booking status
            if scenario['status'] == Booking.STATUS_CHECKED_OUT:
                booking.payment_status = Booking.PAYMENT_FULL
                booking.payment_amount = total_price
            elif scenario['status'] == Booking.STATUS_CHECKED_IN:
                booking.payment_status = random.choice([Booking.PAYMENT_FULL, Booking.PAYMENT_DEPOSIT])
                booking.payment_amount = total_price if booking.payment_status == Booking.PAYMENT_FULL else total_price * 0.5
            elif scenario['status'] == Booking.STATUS_RESERVED:
                booking.payment_status = random.choice([Booking.PAYMENT_DEPOSIT, Booking.PAYMENT_NOT_PAID])
                booking.payment_amount = total_price * 0.3 if booking.payment_status == Booking.PAYMENT_DEPOSIT else 0
            else:  # cancelled
                booking.payment_status = Booking.PAYMENT_REFUNDED
                booking.cancellation_reason = "Customer requested cancellation"
                booking.cancellation_date = datetime.now()
                booking.cancelled_by = USERS['receptionist_receptionist1'].id
            
            # Add special requests occasionally
            if random.random() < 0.4:
                requests = random.sample([
                    'Late check-in', 'Early check-out', 'High floor', 'Quiet room',
                    'Extra towels', 'Room near elevator', 'Baby crib', 'Airport pickup'
                ], k=random.randint(1, 2))
                booking.special_requests = requests
            
            db.session.add(booking)
            BOOKINGS[f'booking_{booking_id}'] = booking
            booking_id += 1
    
    db.session.commit()
    print(f"✅ Created {len(BOOKINGS)} bookings with proper lifecycle")
    
    # Print booking distribution
    for scenario in booking_scenarios:
        count = len([b for b in BOOKINGS.values() if b.status == scenario['status']])
        print(f"   {scenario['status']}: {count} bookings")

def create_payments():
    """Create payments for all bookings that require them."""
    print("\n💰 Creating payments linked to bookings...")
    
    payment_types = [Payment.TYPE_CREDIT_CARD, Payment.TYPE_CASH, Payment.TYPE_BANK_TRANSFER, Payment.TYPE_DEBIT_CARD]
    staff_processors = [
        USERS['receptionist_receptionist1'].id,
        USERS['receptionist_receptionist2'].id,
        USERS['manager_manager1'].id
    ]
    
    payment_count = 0
    
    for booking in BOOKINGS.values():
        if booking.payment_amount > 0:
            # Determine payment pattern based on booking status
            if booking.payment_status == Booking.PAYMENT_FULL:
                # Single full payment
                payment = Payment(
                    booking_id=booking.id,
                    amount=booking.payment_amount,
                    payment_date=booking.booking_date + timedelta(hours=random.randint(1, 48)),
                    payment_type=random.choice(payment_types),
                    reference=f"TXN{random.randint(100000, 999999)}",
                    processed_by=random.choice(staff_processors),
                    notes="Full payment received"
                )
                db.session.add(payment)
                payment_count += 1
                
            elif booking.payment_status == Booking.PAYMENT_DEPOSIT:
                # Deposit payment
                payment = Payment(
                    booking_id=booking.id,
                    amount=booking.payment_amount,
                    payment_date=booking.booking_date + timedelta(hours=random.randint(1, 24)),
                    payment_type=random.choice(payment_types),
                    reference=f"DEP{random.randint(100000, 999999)}",
                    processed_by=random.choice(staff_processors),
                    notes="Deposit payment received"
                )
                db.session.add(payment)
                payment_count += 1
            
            elif booking.payment_status == Booking.PAYMENT_REFUNDED:
                # Original payment + refund
                original_payment = Payment(
                    booking_id=booking.id,
                    amount=booking.total_price * 0.5,  # They paid a deposit
                    payment_date=booking.booking_date + timedelta(hours=random.randint(1, 24)),
                    payment_type=random.choice(payment_types),
                    reference=f"REF{random.randint(100000, 999999)}",
                    processed_by=random.choice(staff_processors),
                    refunded=True,
                    refund_date=booking.cancellation_date,
                    refund_reason=booking.cancellation_reason,
                    refunded_by=booking.cancelled_by,
                    notes="Payment refunded due to cancellation"
                )
                db.session.add(original_payment)
                payment_count += 1
        
        # Update customer loyalty points for completed bookings
        if booking.status == Booking.STATUS_CHECKED_OUT:
            points_earned = int(booking.total_price * 0.1)  # 10% of spend as points
            booking.loyalty_points_earned = points_earned
            booking.customer.loyalty_points += points_earned
            booking.customer.stay_count += 1
            booking.customer.total_spent += booking.total_price
            booking.customer.update_loyalty_tier()
    
    db.session.commit()
    print(f"✅ Created {payment_count} payments")

def create_housekeeping_tasks():
    """Create housekeeping tasks linked to room checkouts and maintenance."""
    print("\n🧹 Creating housekeeping tasks...")
    
    housekeeping_staff = [
        USERS['housekeeping_housekeeper1'].id,
        USERS['housekeeping_housekeeper2'].id,
        USERS['housekeeping_housekeeper3'].id
    ]
    
    task_types = ['regular_cleaning', 'deep_cleaning', 'turnover', 'maintenance_support']
    task_statuses = ['pending', 'in_progress', 'completed']
    priorities = ['normal', 'high', 'urgent']
    
    task_count = 0
    
    # Create tasks for rooms that need cleaning (post-checkout)
    for booking in BOOKINGS.values():
        if booking.status == Booking.STATUS_CHECKED_OUT:
            # Create turnover task for checked-out rooms
            due_date = datetime.combine(booking.check_out_date, datetime.min.time()) + timedelta(hours=2)
            
            task = HousekeepingTask(
                room_id=booking.room_id,
                assigned_to=random.choice(housekeeping_staff),
                task_type='turnover',
                description=f"Room turnover after checkout - Guest: {booking.guest_name}",
                status=random.choice(['completed', 'in_progress']) if booking.check_out_date < date.today() else 'pending',
                priority='high',
                due_date=due_date,
                notes=f"Checkout booking ID: {booking.id}"
            )
            
            if task.status == 'completed':
                task.completed_at = due_date + timedelta(hours=random.randint(1, 4))
                task.verified_by = USERS['manager_manager1'].id
                task.verified_at = task.completed_at + timedelta(minutes=random.randint(15, 60))
                # Update room status to available after cleaning
                booking.room.status = Room.STATUS_AVAILABLE
            
            db.session.add(task)
            task_count += 1
    
    # Create regular maintenance and cleaning tasks
    for room in list(ROOMS.values())[:30]:  # Create tasks for first 30 rooms
        # Regular cleaning task
        task = HousekeepingTask(
            room_id=room.id,
            assigned_to=random.choice(housekeeping_staff),
            task_type=random.choice(task_types),
            description=f"Routine {random.choice(task_types).replace('_', ' ')} for room {room.number}",
            status=random.choice(task_statuses),
            priority=random.choice(priorities),
            due_date=datetime.now() + timedelta(days=random.randint(-3, 7)),
            notes=f"Scheduled maintenance for room {room.number}"
        )
        
        if task.status == 'completed':
            task.completed_at = task.due_date - timedelta(hours=random.randint(1, 6))
            if random.random() < 0.8:  # 80% of completed tasks are verified
                task.verified_by = USERS['manager_manager1'].id
                task.verified_at = task.completed_at + timedelta(minutes=random.randint(15, 120))
        
        elif task.status == 'in_progress':
            # Task started but not completed
            task.notes += " - Task in progress"
        
        db.session.add(task)
        task_count += 1
    
    db.session.commit()
    print(f"✅ Created {task_count} housekeeping tasks")
    
    # Print task distribution
    for status in task_statuses:
        count = len([t for t in db.session.query(HousekeepingTask).all() if t.status == status])
        print(f"   {status}: {count} tasks")

def create_loyalty_transactions():
    """Create loyalty point transactions for customers."""
    print("\n🎁 Creating loyalty point transactions...")
    
    staff_id = USERS['receptionist_receptionist1'].id
    transaction_count = 0
    
    for customer in CUSTOMERS.values():
        # Create point earning transactions for completed bookings
        completed_bookings = [b for b in BOOKINGS.values() if b.customer_id == customer.id and b.status == Booking.STATUS_CHECKED_OUT]
        
        for booking in completed_bookings:
            if booking.loyalty_points_earned > 0:
                transaction = LoyaltyLedger(
                    customer_id=customer.id,
                    points=booking.loyalty_points_earned,
                    txn_type='earn',
                    reason=f"Stay completion - Booking #{booking.confirmation_code}",
                    booking_id=booking.id,
                    staff_id=staff_id,
                    txn_dt=datetime.combine(booking.check_out_date, datetime.min.time()) + timedelta(hours=1)
                )
                db.session.add(transaction)
                transaction_count += 1
        
        # Add some bonus point transactions
        if random.random() < 0.3:  # 30% of customers get bonus points
            bonus_transaction = LoyaltyLedger(
                customer_id=customer.id,
                points=random.randint(100, 500),
                txn_type='earn',
                reason="Birthday bonus points",
                staff_id=staff_id,
                txn_dt=fake.date_time_between(start_date='-1y', end_date='now')
            )
            db.session.add(bonus_transaction)
            transaction_count += 1
        
        # Add some redemption transactions for high-tier customers
        if customer.loyalty_tier in [Customer.TIER_GOLD, Customer.TIER_PLATINUM] and customer.loyalty_points > 1000:
            redemption_points = random.randint(500, min(1000, customer.loyalty_points // 2))
            redemption = LoyaltyLedger(
                customer_id=customer.id,
                points=-redemption_points,
                txn_type='redeem',
                reason="Room upgrade redemption",
                staff_id=staff_id,
                txn_dt=fake.date_time_between(start_date='-6m', end_date='now')
            )
            db.session.add(redemption)
            customer.loyalty_points -= redemption_points
            transaction_count += 1
    
    db.session.commit()
    print(f"✅ Created {transaction_count} loyalty transactions")

def update_room_statuses():
    """Update room statuses based on current bookings."""
    print("\n🚪 Updating room statuses based on bookings...")
    
    today = date.today()
    
    for room in ROOMS.values():
        # Find current booking for this room
        current_booking = None
        for booking in BOOKINGS.values():
            if (booking.room_id == room.id and 
                booking.status in [Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN] and
                booking.check_in_date <= today <= booking.check_out_date):
                current_booking = booking
                break
        
        # Update room status based on current booking
        if current_booking:
            if current_booking.status == Booking.STATUS_CHECKED_IN:
                room.status = Room.STATUS_OCCUPIED
            else:  # Reserved
                room.status = Room.STATUS_BOOKED
        else:
            # Check if room needs cleaning (recent checkout)
            recent_checkout = None
            for booking in BOOKINGS.values():
                if (booking.room_id == room.id and 
                    booking.status == Booking.STATUS_CHECKED_OUT and
                    booking.check_out_date >= today - timedelta(days=1)):
                    recent_checkout = booking
                    break
            
            if recent_checkout:
                # Check if cleaning task is completed
                cleaning_task = db.session.query(HousekeepingTask).filter_by(
                    room_id=room.id,
                    task_type='turnover'
                ).order_by(HousekeepingTask.created_at.desc()).first()
                
                if cleaning_task and cleaning_task.status == 'completed':
                    room.status = Room.STATUS_AVAILABLE
                else:
                    room.status = Room.STATUS_CLEANING
    
    db.session.commit()
    print("✅ Room statuses updated based on current bookings")

def print_summary():
    """Print a comprehensive summary of the seeded data."""
    print("\n" + "="*60)
    print("🎉 COMPREHENSIVE SEED DATA SUMMARY")
    print("="*60)
    
    # Users summary
    user_counts = {}
    for user in db.session.query(User).all():
        user_counts[user.role] = user_counts.get(user.role, 0) + 1
    
    print(f"\n👥 USERS CREATED:")
    for role, count in user_counts.items():
        print(f"   {role.upper()}: {count}")
    
    # Customers summary
    customer_count = db.session.query(Customer).count()
    print(f"\n👤 CUSTOMERS: {customer_count}")
    
    tier_counts = {}
    for customer in db.session.query(Customer).all():
        tier_counts[customer.loyalty_tier] = tier_counts.get(customer.loyalty_tier, 0) + 1
    
    for tier, count in tier_counts.items():
        print(f"   {tier}: {count}")
    
    # Room summary
    room_count = db.session.query(Room).count()
    print(f"\n🏨 ROOMS: {room_count}")
    
    room_status_counts = {}
    for room in db.session.query(Room).all():
        room_status_counts[room.status] = room_status_counts.get(room.status, 0) + 1
    
    for status, count in room_status_counts.items():
        print(f"   {status}: {count}")
    
    # Booking summary
    booking_count = db.session.query(Booking).count()
    print(f"\n📅 BOOKINGS: {booking_count}")
    
    booking_status_counts = {}
    for booking in db.session.query(Booking).all():
        booking_status_counts[booking.status] = booking_status_counts.get(booking.status, 0) + 1
    
    for status, count in booking_status_counts.items():
        print(f"   {status}: {count}")
    
    # Payment summary
    payment_count = db.session.query(Payment).count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(refunded=False).scalar() or 0
    print(f"\n💰 PAYMENTS: {payment_count}")
    print(f"   Total Revenue: ${total_revenue:.2f}")
    
    # Housekeeping summary
    task_count = db.session.query(HousekeepingTask).count()
    print(f"\n🧹 HOUSEKEEPING TASKS: {task_count}")
    
    # Loyalty summary
    loyalty_transactions = db.session.query(LoyaltyLedger).count()
    print(f"\n🎁 LOYALTY TRANSACTIONS: {loyalty_transactions}")
    
    print("\n" + "="*60)
    print("✅ ALL DATA SUCCESSFULLY SEEDED!")
    print("🔑 Customer login credentials are shown above")
    print("📊 All dashboards and metrics are populated with this data")
    print("="*60)

def seed_all():
    """Main function to seed all data in the correct order."""
    print("🚀 Starting comprehensive hotel management system data seeding...")
    print("⚠️  This will clear all existing data and create fresh seed data.")
    
    try:
        # Clear existing data
        clear_all_data()
        
        # Seed data in dependency order
        create_staff_users()
        create_customer_users()
        create_room_types()
        create_rooms()
        create_bookings_with_lifecycle()
        create_payments()
        create_housekeeping_tasks()
        create_loyalty_transactions()
        update_room_statuses()
        
        # Print comprehensive summary
        print_summary()
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_all()