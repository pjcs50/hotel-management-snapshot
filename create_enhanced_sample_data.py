#!/usr/bin/env python3
"""
Create enhanced sample data for the hotel management system.

This script creates sample data for the enhanced features including:
- Room types with amenities and images
- Seasonal rates with day-of-week adjustments
- Customer profiles with loyalty data
- Bookings with payments and special requests
- Loyalty points transactions
"""

import sys
import os
import json
import random
import string
from datetime import datetime, date, timedelta

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.models.room_type import RoomType
from app.models.room import Room
from app.models.seasonal_rate import SeasonalRate
from app.models.customer import Customer
from app.models.user import User
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.booking_log import BookingLog
from app.models.loyalty_ledger import LoyaltyLedger
from app.models.room_status_log import RoomStatusLog

from db import db

def create_enhanced_room_types():
    """Create enhanced room types with amenities and images."""
    print("Creating enhanced room types...")
    
    # Define room types with detailed information
    room_types_data = [
        {
            'name': 'Standard Room',
            'description': 'Comfortable standard room with all basic amenities',
            'base_rate': 89.99,
            'capacity': 2,
            'size_sqm': 24,
            'bed_type': 'Queen',
            'max_occupants': 2,
            'has_view': False,
            'has_balcony': False,
            'smoking_allowed': False,
            'image_main': '/static/images/rooms/standard_main.jpg',
            'amenities': ['Free Wi-Fi', 'TV', 'Air Conditioning', 'Phone', 'Mini Fridge']
        },
        {
            'name': 'Deluxe Room',
            'description': 'Spacious deluxe room with premium furnishings and city view',
            'base_rate': 149.99,
            'capacity': 2,
            'size_sqm': 32,
            'bed_type': 'King',
            'max_occupants': 2,
            'has_view': True,
            'has_balcony': False,
            'smoking_allowed': False,
            'image_main': '/static/images/rooms/deluxe_main.jpg',
            'amenities': ['Free Wi-Fi', 'Smart TV', 'Premium Bedding', 'Desk', 'Coffee Maker', 'Mini Bar', 'Safe']
        },
        {
            'name': 'Suite',
            'description': 'Luxurious suite with separate living area and panoramic views',
            'base_rate': 249.99,
            'capacity': 3,
            'size_sqm': 48,
            'bed_type': 'King',
            'max_occupants': 4,
            'has_view': True,
            'has_balcony': True,
            'smoking_allowed': False,
            'image_main': '/static/images/rooms/suite_main.jpg',
            'amenities': ['Free Wi-Fi', 'Smart TV', 'Premium Bedding', 'Sofa', 'Dining Area', 'Coffee Maker', 'Mini Bar', 'Safe', 'Bathrobe', 'Slippers']
        },
        {
            'name': 'Family Room',
            'description': 'Spacious room for families with multiple beds',
            'base_rate': 179.99,
            'capacity': 4,
            'size_sqm': 40,
            'bed_type': 'Queen + Twin',
            'max_occupants': 5,
            'has_view': False,
            'has_balcony': False,
            'smoking_allowed': False,
            'image_main': '/static/images/rooms/family_main.jpg',
            'amenities': ['Free Wi-Fi', 'TV', 'Air Conditioning', 'Desk', 'Refrigerator', 'Microwave', 'Cribs Available']
        },
        {
            'name': 'Executive Suite',
            'description': 'Premium suite with separate bedroom, living room, and executive benefits',
            'base_rate': 349.99,
            'capacity': 2,
            'size_sqm': 60,
            'bed_type': 'King',
            'max_occupants': 3,
            'has_view': True,
            'has_balcony': True,
            'smoking_allowed': False,
            'image_main': '/static/images/rooms/executive_main.jpg',
            'amenities': ['Free Wi-Fi', 'Smart TV', 'Premium Bedding', 'Sofa', 'Dining Area', 'Coffee Maker', 'Mini Bar', 'Safe', 'Bathrobe', 'Slippers', 'Executive Lounge Access', 'Meeting Room Access']
        }
    ]
    
    # Create or update room types
    for room_type_data in room_types_data:
        amenities = room_type_data.pop('amenities', [])
        room_type = RoomType.query.filter_by(name=room_type_data['name']).first()
        
        if room_type:
            # Update existing room type
            for key, value in room_type_data.items():
                setattr(room_type, key, value)
            room_type.amenities = amenities
        else:
            # Create new room type
            room_type = RoomType(**room_type_data)
            room_type.amenities = amenities
            db.session.add(room_type)
    
    db.session.commit()
    print("Enhanced room types created successfully!")

def create_seasonal_rates():
    """Create seasonal rates with dynamic pricing."""
    print("Creating seasonal rates...")
    
    # Get all room types
    room_types = RoomType.query.all()
    
    # Define seasonal periods
    today = date.today()
    current_year = today.year
    
    seasonal_periods = [
        {
            'name': 'Summer Season',
            'start_date': date(current_year, 6, 1),
            'end_date': date(current_year, 8, 31),
            'rate_multiplier': 1.25,
            'rate_type': SeasonalRate.TYPE_SEASONAL,
            'description': 'Peak summer season rates',
            'day_adjustments': {
                'friday': 1.2,
                'saturday': 1.2
            }
        },
        {
            'name': 'Winter Holidays',
            'start_date': date(current_year, 12, 15),
            'end_date': date(current_year, 1, 5) if today.month > 6 else date(current_year-1, 1, 5),
            'rate_multiplier': 1.35,
            'rate_type': SeasonalRate.TYPE_HOLIDAY,
            'description': 'Holiday season rates',
            'priority': 120,
            'day_adjustments': {
                'friday': 1.1,
                'saturday': 1.1
            }
        },
        {
            'name': 'Weekend Rate',
            'start_date': date(current_year, 1, 1),
            'end_date': date(current_year, 12, 31),
            'rate_multiplier': 1.15,
            'rate_type': SeasonalRate.TYPE_WEEKEND,
            'description': 'Standard weekend rates',
            'priority': 50
        },
        {
            'name': 'Spring Break',
            'start_date': date(current_year, 3, 15),
            'end_date': date(current_year, 4, 15),
            'rate_multiplier': 1.20,
            'rate_type': SeasonalRate.TYPE_SEASONAL,
            'description': 'Spring break season rates'
        },
        {
            'name': 'Off-Peak Season',
            'start_date': date(current_year, 1, 6),
            'end_date': date(current_year, 2, 28),
            'rate_multiplier': 0.85,
            'rate_type': SeasonalRate.TYPE_SEASONAL,
            'description': 'Off-peak season discounted rates'
        },
        {
            'name': 'Annual Conference',
            'start_date': today + timedelta(days=30),
            'end_date': today + timedelta(days=35),
            'rate_multiplier': 1.40,
            'rate_type': SeasonalRate.TYPE_EVENT,
            'description': 'Annual business conference',
            'is_special_event': True,
            'priority': 150
        }
    ]
    
    # Create seasonal rates for each room type
    for room_type in room_types:
        for period in seasonal_periods:
            # Skip weekend rates for existing room types (to avoid duplicates)
            if period['rate_type'] == SeasonalRate.TYPE_WEEKEND:
                if SeasonalRate.query.filter_by(
                    room_type_id=room_type.id,
                    rate_type=SeasonalRate.TYPE_WEEKEND
                ).first():
                    continue
            
            # Create seasonal rate
            rate_data = {
                'room_type_id': room_type.id,
                'name': period['name'],
                'start_date': period['start_date'],
                'end_date': period['end_date'],
                'rate_multiplier': period['rate_multiplier'],
                'rate_type': period['rate_type'],
                'description': period['description'],
                'priority': period.get('priority', 100),
                'is_special_event': period.get('is_special_event', False)
            }
            
            seasonal_rate = SeasonalRate(**rate_data)
            
            # Add day-of-week adjustments if specified
            if 'day_adjustments' in period:
                seasonal_rate.day_adjustments = period['day_adjustments']
            
            db.session.add(seasonal_rate)
    
    db.session.commit()
    print("Seasonal rates created successfully!")

def enhance_customer_profiles():
    """Enhance existing customer profiles with loyalty and preferences data."""
    print("Enhancing customer profiles...")
    
    # Get all customers
    customers = Customer.query.all()
    
    if not customers:
        print("No customers found. Please run the basic sample data creation first.")
        return
    
    # Sample preferences and nationalities
    room_preferences = [
        {'floor': 'high', 'near_elevator': False, 'bed_type': 'king'},
        {'floor': 'low', 'near_elevator': True, 'bed_type': 'queen'},
        {'floor': 'middle', 'near_elevator': False, 'bed_type': 'twin'},
        {'floor': 'high', 'near_elevator': True, 'quiet_room': True}
    ]
    
    nationalities = ['US', 'UK', 'Canada', 'Australia', 'Germany', 'France', 'Japan', 'China', 'India', 'Brazil']
    
    # Enhance each customer
    for customer in customers:
        # Add email if missing
        if not hasattr(customer, 'email') or not customer.email:
            username = customer.name.lower().replace(' ', '.')
            customer.email = f"{username}@example.com"
        
        # Set random nationality
        customer.nationality = random.choice(nationalities)
        
        # Set random date of birth (adults between 21-75 years old)
        years_ago = random.randint(21, 75)
        days_variation = random.randint(0, 365)
        customer.date_of_birth = date.today() - timedelta(days=years_ago*365 + days_variation)
        
        # Set random stay count and spend
        customer.stay_count = random.randint(0, 20)
        customer.total_spent = customer.stay_count * random.uniform(100, 500)
        
        # Calculate loyalty points (roughly 10 points per dollar spent)
        customer.loyalty_points = int(customer.total_spent * 10)
        
        # Set some customers as VIP
        customer.vip = random.random() < 0.15  # 15% chance
        
        # Set random preferences
        customer.preferences = random.choice(room_preferences)
        
        # Update loyalty tier based on points
        customer.update_loyalty_tier()
    
    db.session.commit()
    print("Customer profiles enhanced successfully!")

def create_loyalty_transactions():
    """Create sample loyalty point transactions."""
    print("Creating loyalty transactions...")
    
    # Get all customers with loyalty points
    customers = Customer.query.filter(Customer.loyalty_points > 0).all()
    
    if not customers:
        print("No customers with loyalty points found.")
        return
    
    # Transaction reasons
    earn_reasons = ['Stay completion', 'Welcome bonus', 'Promotion', 'Dining purchase', 'Referral bonus']
    redeem_reasons = ['Room upgrade', 'Free night', 'Spa service', 'Restaurant voucher', 'Airport transfer']
    
    # Create transactions for each customer
    for customer in customers:
        # Reset loyalty points to zero as we'll recalculate
        total_points = 0
        
        # Generate 2-8 random transactions per customer
        num_transactions = random.randint(2, 8)
        
        for i in range(num_transactions):
            # 80% earning transactions, 20% redemption
            is_earning = random.random() < 0.8
            
            if is_earning:
                points = random.randint(100, 2000)
                reason = random.choice(earn_reasons)
                
                LoyaltyLedger.earn_points(
                    customer_id=customer.id,
                    points=points,
                    reason=reason
                )
                
                total_points += points
            else:
                # Can only redeem if they have points
                if total_points > 0:
                    points = min(random.randint(100, 1000), total_points)
                    reason = random.choice(redeem_reasons)
                    
                    LoyaltyLedger.redeem_points(
                        customer_id=customer.id,
                        points=points,
                        reason=reason
                    )
                    
                    total_points -= points
        
        # Update customer's loyalty points to match ledger
        customer.loyalty_points = LoyaltyLedger.get_customer_balance(customer.id)
        customer.update_loyalty_tier()
    
    db.session.commit()
    print("Loyalty transactions created successfully!")

def enhance_bookings():
    """Enhance existing bookings with payment records and special requests."""
    print("Enhancing bookings...")
    
    # Get all bookings
    bookings = Booking.query.all()
    
    if not bookings:
        print("No bookings found. Please run the basic sample data creation first.")
        return
    
    # Sample special requests
    special_requests = [
        ['Early check-in', 'Extra pillows'],
        ['Late check-out', 'Quiet room'],
        ['Airport shuttle', 'Champagne in room'],
        ['Baby crib', 'High floor'],
        ['Extra towels', 'Feather-free bedding'],
        ['Anniversary celebration', 'King bed']
    ]
    
    # Sample booking sources
    sources = ['Website', 'Phone', 'Walk-in', 'Travel Agent', 'Booking.com', 'Expedia']
    
    # Sample user IDs for staff
    staff_user_ids = [user.id for user in User.query.all() if user.id <= 5]
    
    # Enhance each booking
    for booking in bookings:
        # Skip if booking already has enhanced data
        if booking.payment_amount > 0 or booking.special_requests_json:
            continue
        
        # Generate confirmation code if missing
        if not booking.confirmation_code:
            booking.generate_confirmation_code()
        
        # Add number of guests
        booking.num_guests = random.randint(1, booking.room.room_type.max_occupants)
        
        # Add source
        booking.source = random.choice(sources)
        
        # Add random special requests for some bookings
        if random.random() < 0.7:  # 70% chance
            booking.special_requests = random.choice(special_requests)
        
        # Calculate total price if missing
        if not booking.total_price:
            booking.calculate_price()
        
        # Set payment status
        if booking.status in [Booking.STATUS_CHECKED_OUT, Booking.STATUS_CANCELLED]:
            # Completed or cancelled bookings
            payment_status = Booking.PAYMENT_FULL
            payment_amount = booking.total_price
        elif booking.status in [Booking.STATUS_CHECKED_IN, Booking.STATUS_RESERVED]:
            # Current or future bookings
            if random.random() < 0.7:  # 70% chance
                payment_status = Booking.PAYMENT_DEPOSIT
                payment_amount = booking.total_price * 0.3  # 30% deposit
            else:
                payment_status = Booking.PAYMENT_FULL
                payment_amount = booking.total_price
        else:
            payment_status = Booking.PAYMENT_NOT_PAID
            payment_amount = 0
        
        booking.payment_status = payment_status
        booking.payment_amount = payment_amount
        
        # Create payment record if payment was made
        if payment_amount > 0:
            payment_type = random.choice([
                Payment.TYPE_CREDIT_CARD,
                Payment.TYPE_DEBIT_CARD,
                Payment.TYPE_BANK_TRANSFER
            ])
            
            reference = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # Create payment record
            Payment.create(
                booking_id=booking.id,
                amount=payment_amount,
                payment_type=payment_type,
                reference=reference,
                processed_by=random.choice(staff_user_ids) if staff_user_ids else None
            )
        
        # Create booking log entries
        BookingLog.log_booking_action(
            booking_id=booking.id,
            action=BookingLog.ACTION_CREATE,
            notes="Booking created"
        )
        
        if booking.status == Booking.STATUS_CHECKED_IN:
            BookingLog.log_booking_action(
                booking_id=booking.id,
                action=BookingLog.ACTION_CHECK_IN,
                user_id=random.choice(staff_user_ids) if staff_user_ids else None,
                notes=f"Checked in on {booking.check_in_date.strftime('%Y-%m-%d')}"
            )
        elif booking.status == Booking.STATUS_CHECKED_OUT:
            BookingLog.log_booking_action(
                booking_id=booking.id,
                action=BookingLog.ACTION_CHECK_IN,
                user_id=random.choice(staff_user_ids) if staff_user_ids else None,
                notes=f"Checked in on {booking.check_in_date.strftime('%Y-%m-%d')}"
            )
            BookingLog.log_booking_action(
                booking_id=booking.id,
                action=BookingLog.ACTION_CHECK_OUT,
                user_id=random.choice(staff_user_ids) if staff_user_ids else None,
                notes=f"Checked out on {booking.check_out_date.strftime('%Y-%m-%d')}"
            )
        elif booking.status == Booking.STATUS_CANCELLED:
            BookingLog.log_booking_action(
                booking_id=booking.id,
                action=BookingLog.ACTION_CANCEL,
                user_id=random.choice(staff_user_ids) if staff_user_ids else None,
                notes="Booking cancelled"
            )
        
        # For completed stays, add loyalty points
        if booking.status == Booking.STATUS_CHECKED_OUT and booking.customer:
            points_earned = int(booking.total_price * 10)  # 10 points per dollar
            booking.loyalty_points_earned = points_earned
            
            # Add loyalty points if they don't already exist
            existing_points = LoyaltyLedger.query.filter_by(
                customer_id=booking.customer_id,
                booking_id=booking.id
            ).first()
            
            if not existing_points and points_earned > 0:
                LoyaltyLedger.earn_points(
                    customer_id=booking.customer_id,
                    points=points_earned,
                    reason=f"Stay at {booking.room.room_type.name}",
                    booking_id=booking.id
                )
    
    db.session.commit()
    print("Bookings enhanced successfully!")

def create_sample_data():
    """Create all sample data for enhanced features."""
    app = create_app()
    
    with app.app_context():
        # Create or enhance data in the proper order
        create_enhanced_room_types()
        create_seasonal_rates()
        enhance_customer_profiles()
        create_loyalty_transactions()
        enhance_bookings()
        
        print("All enhanced sample data created successfully!")

if __name__ == '__main__':
    create_sample_data() 