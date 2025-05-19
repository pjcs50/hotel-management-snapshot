"""
Customer service module.

This module provides services for customer profile management.
"""

from sqlalchemy.exc import IntegrityError

from app.models.customer import Customer
from app.models.user import User
from app.models.loyalty_ledger import LoyaltyLedger


class DuplicateUserError(Exception):
    """Exception raised when attempting to create a customer with an existing user ID."""
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
            List of LoyaltyLedger objects.
        """
        return LoyaltyLedger.query.filter_by(customer_id=customer_id)\
            .order_by(LoyaltyLedger.transaction_date.desc())\
            .limit(limit)\
            .all() 