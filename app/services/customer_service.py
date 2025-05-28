"""
Customer service module.

This module provides services for customer profile management.
"""

from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.models.customer import Customer
from app.models.user import User
from app.models.loyalty_ledger import LoyaltyLedger
from app.models.loyalty_reward import LoyaltyReward
from app.models.loyalty_redemption import LoyaltyRedemption


class DuplicateUserError(Exception):
    """Exception raised when attempting to create a customer with an existing user ID."""
    pass


class InsufficientPointsError(Exception):
    """Exception raised when a customer has insufficient points for a redemption."""
    pass


class RewardNotAvailableError(Exception):
    """Exception raised when a reward is not available to a customer."""
    pass


class CustomerService:
    """
    Service for customer profile management.
    
    This service handles customer CRUD operations and profile completeness.
    """

    def __init__(self, db_session):
        """Initialize the service with a database session."""
        self.db_session = db_session
    
    def get_customer_by_user_id(self, user_id):
        """
        Get a customer by user ID.
        
        Args:
            user_id: ID of the user associated with the customer
            
        Returns:
            The customer object or None if not found
        """
        return Customer.query.filter_by(user_id=user_id).first()
    
    def get_customer_by_id(self, customer_id):
        """
        Get a customer by customer ID.
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            The customer object or None if not found
        """
        return Customer.query.get(customer_id)
    
    def create_customer(self, user_id, name=None, phone=None, address=None, emergency_contact=None):
        """
        Create a new customer profile.
        
        Args:
            user_id: ID of the user to associate with the customer
            name: Customer's full name
            phone: Customer's phone number
            address: Customer's address
            emergency_contact: Customer's emergency contact information
            
        Returns:
            The newly created customer
            
        Raises:
            DuplicateUserError: If a customer with the given user ID already exists
            ValueError: If the user does not exist
        """
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} does not exist")
        
        # Check if customer already exists
        if Customer.query.filter_by(user_id=user_id).first():
            raise DuplicateUserError(f"Customer with user ID {user_id} already exists")
        
        # Check profile completeness
        profile_complete = bool(name and phone)
        
        # Create new customer
        customer = Customer(
            user_id=user_id,
            name=name or "",
            phone=phone or "",
            address=address or "",
            emergency_contact=emergency_contact or "",
            profile_complete=profile_complete
        )
        
        try:
            self.db_session.add(customer)
            self.db_session.commit()
            return customer
        except IntegrityError:
            self.db_session.rollback()
            # Final check in case of race condition
            if Customer.query.filter_by(user_id=user_id).first():
                raise DuplicateUserError(f"Customer with user ID {user_id} already exists")
            raise  # Re-raise if it's another kind of integrity error
    
    def update_customer(self, customer_id, **kwargs):
        """
        Update a customer profile.
        
        Args:
            customer_id: ID of the customer to update
            **kwargs: Attributes to update
            
        Returns:
            The updated customer
            
        Raises:
            ValueError: If the customer does not exist
        """
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist")
        
        # Update customer attributes
        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        
        # Update profile completeness
        customer.profile_complete = bool(customer.name and customer.phone)
        
        try:
            self.db_session.commit()
            return customer
        except IntegrityError:
            self.db_session.rollback()
            raise  # Re-raise if there's an integrity error
    
    def get_all_customers(self):
        """
        Get all customers.
        
        Returns:
            List of all customers
        """
        return Customer.query.all()
    
    def get_loyalty_history(self, customer_id, limit=20):
        """
        Get loyalty ledger entries for a customer, most recent first.

        Args:
            customer_id: ID of the customer.
            limit: Maximum number of history entries to return.

        Returns:
            List of loyalty transactions formatted as dictionaries.
        """
        transactions = LoyaltyLedger.query.filter_by(customer_id=customer_id)\
            .order_by(LoyaltyLedger.txn_dt.desc())\
            .limit(limit)\
            .all() 
            
        # Format transactions for the template
        history = []
        running_balance = 0
        
        # Get current balance first
        current_balance = LoyaltyLedger.get_customer_balance(customer_id)
        
        # Calculate running balance backwards from current balance
        for transaction in transactions:
            history.append({
                'transaction_date': transaction.txn_dt,
                'description': transaction.reason,
                'points_change': transaction.points,
                'balance_after_transaction': current_balance,
                'transaction_type': transaction.txn_type,
                'booking_id': transaction.booking_id
            })
            current_balance -= transaction.points
            
        return history
    
    def get_available_rewards(self, customer_id, category=None):
        """
        Get rewards available to a customer.
        
        Args:
            customer_id: ID of the customer
            category: Optional category filter
            
        Returns:
            List of available rewards
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            return []
            
        return LoyaltyReward.get_available_rewards(customer.loyalty_tier, category)
    
    def get_customer_redemptions(self, customer_id, status=None, limit=None):
        """
        Get a customer's reward redemptions.
        
        Args:
            customer_id: ID of the customer
            status: Optional status filter
            limit: Maximum number of redemptions to return
            
        Returns:
            List of redemptions
        """
        query = LoyaltyRedemption.query.filter_by(customer_id=customer_id)
        
        if status:
            query = query.filter_by(status=status)
            
        query = query.order_by(LoyaltyRedemption.redemption_date.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def redeem_reward(self, customer_id, reward_id, booking_id=None, notes=None):
        """
        Redeem a loyalty reward for a customer.
        
        Args:
            customer_id: ID of the customer
            reward_id: ID of the reward to redeem
            booking_id: Optional booking ID to associate with the redemption
            notes: Optional notes about the redemption
            
        Returns:
            The created redemption
            
        Raises:
            ValueError: If the customer or reward does not exist
            InsufficientPointsError: If the customer has insufficient points
            RewardNotAvailableError: If the reward is not available to the customer
        """
        # Get customer and reward
        customer = self.get_customer_by_id(customer_id)
        reward = LoyaltyReward.query.get(reward_id)
        
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist")
            
        if not reward:
            raise ValueError(f"Reward with ID {reward_id} does not exist")
            
        # Check if customer has enough points
        if customer.loyalty_points < reward.points_cost:
            raise InsufficientPointsError(f"Insufficient points. Required: {reward.points_cost}, Available: {customer.loyalty_points}")
            
        # Check if reward is available to customer
        if not reward.is_available_for_customer(customer):
            raise RewardNotAvailableError(f"Reward {reward.name} is not available to this customer")
            
        # Create redemption
        redemption = LoyaltyRedemption(
            customer_id=customer_id,
            reward_id=reward_id,
            points_spent=reward.points_cost,
            booking_id=booking_id,
            notes=notes
        )
        
        # Deduct points through loyalty ledger
        ledger = LoyaltyLedger(
            customer_id=customer_id,
            points=-reward.points_cost,  # Negative for deduction
            reason=f"Redemption: {reward.name}",
            booking_id=booking_id,
            txn_type=LoyaltyLedger.TYPE_REDEEM
        )
        
        # Update customer loyalty points
        customer.loyalty_points -= reward.points_cost
        
        # Update reward quantity if limited
        if reward.limited_quantity and reward.quantity_remaining is not None:
            reward.quantity_remaining -= 1
            
        self.db_session.add(redemption)
        self.db_session.add(ledger)
        self.db_session.commit()
        
        return redemption
    
    def get_tier_benefits(self, tier):
        """
        Get benefits for a specific loyalty tier.
        
        Args:
            tier: Loyalty tier name
            
        Returns:
            Dictionary of tier benefits
        """
        benefits = {
            Customer.TIER_STANDARD: {
                'name': 'Standard',
                'point_multiplier': 1.0,
                'late_checkout': False,
                'room_upgrades': False,
                'welcome_gift': False,
                'free_breakfast': False,
                'free_wifi': True,
                'exclusive_offers': False,
                'lounge_access': False,
                'guaranteed_availability': False,
                'next_tier_points': 1000
            },
            Customer.TIER_SILVER: {
                'name': 'Silver',
                'point_multiplier': 1.25,
                'late_checkout': True,
                'room_upgrades': False,
                'welcome_gift': False,
                'free_breakfast': False,
                'free_wifi': True,
                'exclusive_offers': True,
                'lounge_access': False,
                'guaranteed_availability': False,
                'next_tier_points': 5000
            },
            Customer.TIER_GOLD: {
                'name': 'Gold',
                'point_multiplier': 1.5,
                'late_checkout': True,
                'room_upgrades': True,
                'welcome_gift': True,
                'free_breakfast': False,
                'free_wifi': True,
                'exclusive_offers': True,
                'lounge_access': False,
                'guaranteed_availability': False,
                'next_tier_points': 10000
            },
            Customer.TIER_PLATINUM: {
                'name': 'Platinum',
                'point_multiplier': 2.0,
                'late_checkout': True,
                'room_upgrades': True,
                'welcome_gift': True,
                'free_breakfast': True,
                'free_wifi': True,
                'exclusive_offers': True,
                'lounge_access': True,
                'guaranteed_availability': True,
                'next_tier_points': None
            }
        }
        
        return benefits.get(tier, benefits[Customer.TIER_STANDARD])
    
    def get_tier_progress(self, customer_id):
        """
        Get a customer's progress toward the next loyalty tier.
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            Dictionary with tier progress information
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            return None
            
        tier_thresholds = {
            Customer.TIER_STANDARD: 0,
            Customer.TIER_SILVER: 1000,
            Customer.TIER_GOLD: 5000,
            Customer.TIER_PLATINUM: 10000
        }
        
        # Get next tier
        current_tier = customer.loyalty_tier
        tier_order = [Customer.TIER_STANDARD, Customer.TIER_SILVER, Customer.TIER_GOLD, Customer.TIER_PLATINUM]
        current_index = tier_order.index(current_tier)
        
        if current_index < len(tier_order) - 1:
            next_tier = tier_order[current_index + 1]
            points_needed = tier_thresholds[next_tier] - customer.loyalty_points
            progress_percent = min(100, max(0, (customer.loyalty_points - tier_thresholds[current_tier]) / 
                                         (tier_thresholds[next_tier] - tier_thresholds[current_tier]) * 100))
            
            return {
                'current_tier': current_tier,
                'next_tier': next_tier,
                'points': customer.loyalty_points,
                'points_to_next_tier': points_needed if points_needed > 0 else 0,
                'progress_percent': progress_percent
            }
        else:
            # Already at highest tier
            return {
                'current_tier': current_tier,
                'next_tier': None,
                'points': customer.loyalty_points,
                'points_to_next_tier': 0,
                'progress_percent': 100
            } 