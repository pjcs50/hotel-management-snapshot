"""
Migration script to create the loyalty rewards tables.

This script creates the loyalty_rewards and loyalty_redemptions tables.
"""

import sys
import os
import datetime

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app and models
from app_factory import create_app
from db import db
from app.models.customer import Customer
from app.models.user import User
from app.models.booking import Booking
from app.models.loyalty_reward import LoyaltyReward
from app.models.loyalty_redemption import LoyaltyRedemption

def create_sample_rewards():
    """Create sample loyalty rewards for testing."""
    
    rewards = [
        {
            'name': 'Room Upgrade',
            'description': 'Upgrade to the next room category for your stay.',
            'points_cost': 1000,
            'category': 'room_upgrade',
            'min_tier': 'Silver'
        },
        {
            'name': 'Late Checkout',
            'description': 'Extend your checkout time until 4:00 PM.',
            'points_cost': 500,
            'category': 'service',
            'min_tier': 'Standard'
        },
        {
            'name': 'Free Breakfast',
            'description': 'Enjoy a complimentary breakfast during your stay.',
            'points_cost': 800,
            'category': 'dining',
            'min_tier': 'Standard'
        },
        {
            'name': 'Executive Lounge Access',
            'description': 'Access the exclusive executive lounge for one day during your stay.',
            'points_cost': 1500,
            'category': 'amenity',
            'min_tier': 'Gold'
        },
        {
            'name': 'Spa Treatment',
            'description': '60-minute massage or facial treatment at our hotel spa.',
            'points_cost': 2000,
            'category': 'spa',
            'min_tier': 'Silver'
        },
        {
            'name': 'Airport Transfer',
            'description': 'One-way transfer between the hotel and airport.',
            'points_cost': 1200,
            'category': 'service',
            'min_tier': 'Standard'
        },
        {
            'name': 'Dinner for Two',
            'description': 'Complimentary dinner for two at our main restaurant (excluding alcoholic beverages).',
            'points_cost': 2500,
            'category': 'dining',
            'min_tier': 'Standard'
        },
        {
            'name': 'Welcome Amenity',
            'description': 'Special welcome amenity waiting in your room upon arrival.',
            'points_cost': 300,
            'category': 'amenity',
            'min_tier': 'Standard'
        },
        {
            'name': 'Premium Room Package',
            'description': 'One night stay in our premium suite with complimentary breakfast, spa treatment, and dinner.',
            'points_cost': 10000,
            'category': 'room_upgrade',
            'min_tier': 'Platinum'
        }
    ]
    
    for reward_data in rewards:
        reward = LoyaltyReward(**reward_data)
        db.session.add(reward)
    
    db.session.commit()
    print(f"Added {len(rewards)} sample loyalty rewards")


def main():
    """Create the loyalty rewards tables and add sample data."""
    
    # Create app
    app = create_app()
    
    # Use app context
    with app.app_context():
        try:
            # Add sample rewards
            create_sample_rewards()
            print("Migration completed successfully")
        except Exception as e:
            print(f"Error: {str(e)}")
            db.session.rollback()


if __name__ == "__main__":
    main() 