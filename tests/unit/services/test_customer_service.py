"""
Test cases for the CustomerService class.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date

from app.services.customer_service import CustomerService, DuplicateUserError, InsufficientPointsError, RewardNotAvailableError
from app.models.customer import Customer
from app.models.user import User
from app.models.loyalty_ledger import LoyaltyLedger
from app.models.loyalty_reward import LoyaltyReward
from app.models.loyalty_redemption import LoyaltyRedemption


class TestCustomerService(unittest.TestCase):
    """Test case for the CustomerService class."""

    def setUp(self):
        """Set up the test case."""
        self.db_session = MagicMock()
        self.customer_service = CustomerService(self.db_session)

    def test_get_customer_by_user_id(self):
        """Test get_customer_by_user_id method."""
        # Mock the Customer.query.filter_by().first() call
        mock_customer = MagicMock(spec=Customer)
        mock_query = MagicMock()
        mock_filter_by = MagicMock()
        mock_filter_by.first.return_value = mock_customer

        with patch('app.services.customer_service.Customer.query') as mock_query_cls:
            mock_query_cls.filter_by.return_value = mock_filter_by
            
            # Call the method
            result = self.customer_service.get_customer_by_user_id(1)
            
            # Assert the result
            self.assertEqual(result, mock_customer)
            mock_query_cls.filter_by.assert_called_once_with(user_id=1)
            mock_filter_by.first.assert_called_once()

    def test_get_customer_by_id(self):
        """Test get_customer_by_id method."""
        # Mock the Customer.query.get() call
        mock_customer = MagicMock(spec=Customer)

        with patch('app.services.customer_service.Customer.query') as mock_query_cls:
            mock_query_cls.get.return_value = mock_customer
            
            # Call the method
            result = self.customer_service.get_customer_by_id(1)
            
            # Assert the result
            self.assertEqual(result, mock_customer)
            mock_query_cls.get.assert_called_once_with(1)

    def test_create_customer_success(self):
        """Test create_customer method with a successful creation."""
        # Mock the User.query.get() call
        mock_user = MagicMock(spec=User)

        # Mock the Customer.query.filter_by().first() call to return None (no existing customer)
        mock_filter_by = MagicMock()
        mock_filter_by.first.return_value = None

        with patch('app.services.customer_service.User.query') as mock_user_query:
            mock_user_query.get.return_value = mock_user
            
            with patch('app.services.customer_service.Customer.query') as mock_customer_query:
                mock_customer_query.filter_by.return_value = mock_filter_by
                
                with patch('app.services.customer_service.Customer') as mock_customer_cls:
                    mock_customer = MagicMock(spec=Customer)
                    mock_customer_cls.return_value = mock_customer
                    
                    # Call the method
                    result = self.customer_service.create_customer(
                        user_id=1,
                        name='Test Customer',
                        phone='1234567890',
                        address='123 Test St',
                        emergency_contact='Emergency Contact'
                    )
                    
                    # Assert the result
                    self.assertEqual(result, mock_customer)
                    mock_user_query.get.assert_called_once_with(1)
                    mock_customer_query.filter_by.assert_called_once_with(user_id=1)
                    mock_customer_cls.assert_called_once_with(
                        user_id=1,
                        name='Test Customer',
                        phone='1234567890',
                        address='123 Test St',
                        emergency_contact='Emergency Contact',
                        profile_complete=True
                    )
                    self.db_session.add.assert_called_once_with(mock_customer)
                    self.db_session.commit.assert_called_once()

    def test_create_customer_user_not_found(self):
        """Test create_customer method when the user is not found."""
        # Mock the User.query.get() call to return None
        with patch('app.services.customer_service.User.query') as mock_user_query:
            mock_user_query.get.return_value = None
            
            # Call the method and assert that it raises ValueError
            with self.assertRaises(ValueError):
                self.customer_service.create_customer(
                    user_id=1,
                    name='Test Customer',
                    phone='1234567890'
                )
                
            mock_user_query.get.assert_called_once_with(1)

    def test_create_customer_duplicate_user(self):
        """Test create_customer method when a customer with the user ID already exists."""
        # Mock the User.query.get() call
        mock_user = MagicMock(spec=User)

        # Mock the Customer.query.filter_by().first() call to return a customer
        mock_customer = MagicMock(spec=Customer)
        mock_filter_by = MagicMock()
        mock_filter_by.first.return_value = mock_customer

        with patch('app.services.customer_service.User.query') as mock_user_query:
            mock_user_query.get.return_value = mock_user
            
            with patch('app.services.customer_service.Customer.query') as mock_customer_query:
                mock_customer_query.filter_by.return_value = mock_filter_by
                
                # Call the method and assert that it raises DuplicateUserError
                with self.assertRaises(DuplicateUserError):
                    self.customer_service.create_customer(
                        user_id=1,
                        name='Test Customer',
                        phone='1234567890'
                    )
                    
                mock_user_query.get.assert_called_once_with(1)
                mock_customer_query.filter_by.assert_called_once_with(user_id=1)

    def test_update_customer_success(self):
        """Test update_customer method with a successful update."""
        # Mock the Customer.query.get() call
        mock_customer = MagicMock(spec=Customer)

        with patch('app.services.customer_service.Customer.query') as mock_query_cls:
            mock_query_cls.get.return_value = mock_customer
            
            # Call the method
            result = self.customer_service.update_customer(
                customer_id=1,
                name='Updated Name',
                phone='9876543210'
            )
            
            # Assert the result
            self.assertEqual(result, mock_customer)
            mock_query_cls.get.assert_called_once_with(1)
            self.assertEqual(mock_customer.name, 'Updated Name')
            self.assertEqual(mock_customer.phone, '9876543210')
            self.db_session.commit.assert_called_once()

    def test_update_customer_not_found(self):
        """Test update_customer method when the customer is not found."""
        # Mock the Customer.query.get() call to return None
        with patch('app.services.customer_service.Customer.query') as mock_query_cls:
            mock_query_cls.get.return_value = None
            
            # Call the method and assert that it raises ValueError
            with self.assertRaises(ValueError):
                self.customer_service.update_customer(
                    customer_id=1,
                    name='Updated Name'
                )
                
            mock_query_cls.get.assert_called_once_with(1)

    def test_get_all_customers(self):
        """Test get_all_customers method."""
        # Mock the Customer.query.all() call
        mock_customers = [MagicMock(spec=Customer), MagicMock(spec=Customer)]

        with patch('app.services.customer_service.Customer.query') as mock_query_cls:
            mock_query_cls.all.return_value = mock_customers
            
            # Call the method
            result = self.customer_service.get_all_customers()
            
            # Assert the result
            self.assertEqual(result, mock_customers)
            mock_query_cls.all.assert_called_once()

    def test_get_loyalty_history(self):
        """Test get_loyalty_history method."""
        # Mock the LoyaltyLedger.query.filter_by().order_by().limit().all() call
        mock_transactions = [
            MagicMock(
                txn_dt=datetime(2023, 5, 1),
                reason='Welcome bonus',
                points=100,
                txn_type='earn',
                booking_id=None
            ),
            MagicMock(
                txn_dt=datetime(2023, 5, 2),
                reason='Stay #1',
                points=200,
                txn_type='earn',
                booking_id=1
            )
        ]
        
        mock_query = MagicMock()
        mock_filter_by = MagicMock()
        mock_order_by = MagicMock()
        mock_limit = MagicMock()
        
        mock_filter_by.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_transactions

        with patch('app.services.customer_service.LoyaltyLedger.query') as mock_query_cls:
            mock_query_cls.filter_by.return_value = mock_filter_by
            
            # Mock the get_customer_balance method
            with patch('app.services.customer_service.LoyaltyLedger.get_customer_balance') as mock_get_balance:
                mock_get_balance.return_value = 300  # Current balance after both transactions
                
                # Call the method
                result = self.customer_service.get_loyalty_history(1, limit=10)
                
                # Assert the result
                self.assertEqual(len(result), 2)
                
                # Check first transaction
                self.assertEqual(result[0]['transaction_date'], mock_transactions[0].txn_dt)
                self.assertEqual(result[0]['description'], mock_transactions[0].reason)
                self.assertEqual(result[0]['points_change'], mock_transactions[0].points)
                self.assertEqual(result[0]['balance_after_transaction'], 300)  # Current balance
                self.assertEqual(result[0]['transaction_type'], mock_transactions[0].txn_type)
                self.assertEqual(result[0]['booking_id'], mock_transactions[0].booking_id)
                
                # Check second transaction
                self.assertEqual(result[1]['transaction_date'], mock_transactions[1].txn_dt)
                self.assertEqual(result[1]['description'], mock_transactions[1].reason)
                self.assertEqual(result[1]['points_change'], mock_transactions[1].points)
                self.assertEqual(result[1]['balance_after_transaction'], 200)  # Balance after first transaction
                self.assertEqual(result[1]['transaction_type'], mock_transactions[1].txn_type)
                self.assertEqual(result[1]['booking_id'], mock_transactions[1].booking_id)
                
                mock_query_cls.filter_by.assert_called_once_with(customer_id=1)
                mock_filter_by.order_by.assert_called_once()
                mock_order_by.limit.assert_called_once_with(10)
                mock_limit.all.assert_called_once()
                mock_get_balance.assert_called_once_with(1)

    def test_get_available_rewards(self):
        """Test get_available_rewards method."""
        # Mock customer with Gold tier
        mock_customer = MagicMock(spec=Customer)
        mock_customer.loyalty_tier = 'Gold'
        
        # Mock the get_customer_by_id method
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = mock_customer
            
            # Mock the LoyaltyReward.get_available_rewards method
            mock_rewards = [MagicMock(spec=LoyaltyReward), MagicMock(spec=LoyaltyReward)]
            
            with patch('app.services.customer_service.LoyaltyReward.get_available_rewards') as mock_get_rewards:
                mock_get_rewards.return_value = mock_rewards
                
                # Call the method
                result = self.customer_service.get_available_rewards(1, category='dining')
                
                # Assert the result
                self.assertEqual(result, mock_rewards)
                mock_get_customer.assert_called_once_with(1)
                mock_get_rewards.assert_called_once_with('Gold', 'dining')
    
    def test_get_available_rewards_customer_not_found(self):
        """Test get_available_rewards method when customer is not found."""
        # Mock the get_customer_by_id method to return None
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = None
            
            # Call the method
            result = self.customer_service.get_available_rewards(1)
            
            # Assert that an empty list is returned
            self.assertEqual(result, [])
            mock_get_customer.assert_called_once_with(1)

    def test_get_customer_redemptions(self):
        """Test get_customer_redemptions method."""
        # Mock the LoyaltyRedemption.query.filter_by()
        mock_redemptions = [MagicMock(spec=LoyaltyRedemption), MagicMock(spec=LoyaltyRedemption)]
        
        mock_query = MagicMock()
        mock_filter_by = MagicMock()
        mock_order_by = MagicMock()
        mock_limit = MagicMock()
        
        mock_filter_by.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_redemptions
        mock_filter_by.filter_by.return_value = mock_filter_by
        
        with patch('app.services.customer_service.LoyaltyRedemption.query') as mock_query_cls:
            mock_query_cls.filter_by.return_value = mock_filter_by
            
            # Call the method with status and limit
            result = self.customer_service.get_customer_redemptions(1, status='pending', limit=5)
            
            # Assert the result
            self.assertEqual(result, mock_redemptions)
            mock_query_cls.filter_by.assert_called_once_with(customer_id=1)
            mock_filter_by.filter_by.assert_called_once_with(status='pending')
            mock_filter_by.order_by.assert_called_once()
            mock_order_by.limit.assert_called_once_with(5)
            mock_limit.all.assert_called_once()

    def test_redeem_reward_success(self):
        """Test redeem_reward method with a successful redemption."""
        # Mock customer with enough points
        mock_customer = MagicMock(spec=Customer)
        mock_customer.id = 1
        mock_customer.loyalty_points = 1000
        
        # Mock reward
        mock_reward = MagicMock(spec=LoyaltyReward)
        mock_reward.id = 2
        mock_reward.name = 'Test Reward'
        mock_reward.points_cost = 500
        mock_reward.is_available_for_customer.return_value = True
        
        # Mock the get_customer_by_id method
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = mock_customer
            
            # Mock the LoyaltyReward.query.get method
            with patch('app.services.customer_service.LoyaltyReward.query') as mock_reward_query:
                mock_reward_query.get.return_value = mock_reward
                
                # Mock the LoyaltyRedemption constructor
                mock_redemption = MagicMock(spec=LoyaltyRedemption)
                
                with patch('app.services.customer_service.LoyaltyRedemption') as mock_redemption_cls:
                    mock_redemption_cls.return_value = mock_redemption
                    
                    # Mock the LoyaltyLedger constructor
                    mock_ledger = MagicMock(spec=LoyaltyLedger)
                    
                    with patch('app.services.customer_service.LoyaltyLedger') as mock_ledger_cls:
                        mock_ledger_cls.return_value = mock_ledger
                        
                        # Call the method
                        result = self.customer_service.redeem_reward(
                            customer_id=1,
                            reward_id=2,
                            booking_id=3,
                            notes='Test notes'
                        )
                        
                        # Assert the result
                        self.assertEqual(result, mock_redemption)
                        
                        # Verify method calls
                        mock_get_customer.assert_called_once_with(1)
                        mock_reward_query.get.assert_called_once_with(2)
                        mock_reward.is_available_for_customer.assert_called_once_with(mock_customer)
                        
                        # Verify redemption creation
                        mock_redemption_cls.assert_called_once_with(
                            customer_id=1,
                            reward_id=2,
                            points_spent=500,
                            booking_id=3,
                            notes='Test notes'
                        )
                        
                        # Verify ledger creation
                        mock_ledger_cls.assert_called_once_with(
                            customer_id=1,
                            points=-500,
                            reason='Redemption: Test Reward',
                            booking_id=3,
                            txn_type='redeem'
                        )
                        
                        # Verify points deduction
                        self.assertEqual(mock_customer.loyalty_points, 500)
                        
                        # Verify session operations
                        self.db_session.add.assert_any_call(mock_redemption)
                        self.db_session.add.assert_any_call(mock_ledger)
                        self.db_session.commit.assert_called_once()

    def test_redeem_reward_customer_not_found(self):
        """Test redeem_reward method when customer is not found."""
        # Mock the get_customer_by_id method to return None
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = None
            
            # Call the method and assert that it raises ValueError
            with self.assertRaises(ValueError):
                self.customer_service.redeem_reward(
                    customer_id=1,
                    reward_id=2
                )
                
            mock_get_customer.assert_called_once_with(1)

    def test_redeem_reward_reward_not_found(self):
        """Test redeem_reward method when reward is not found."""
        # Mock customer
        mock_customer = MagicMock(spec=Customer)
        
        # Mock the get_customer_by_id method
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = mock_customer
            
            # Mock the LoyaltyReward.query.get method to return None
            with patch('app.services.customer_service.LoyaltyReward.query') as mock_reward_query:
                mock_reward_query.get.return_value = None
                
                # Call the method and assert that it raises ValueError
                with self.assertRaises(ValueError):
                    self.customer_service.redeem_reward(
                        customer_id=1,
                        reward_id=2
                    )
                    
                mock_get_customer.assert_called_once_with(1)
                mock_reward_query.get.assert_called_once_with(2)

    def test_redeem_reward_insufficient_points(self):
        """Test redeem_reward method when customer has insufficient points."""
        # Mock customer with insufficient points
        mock_customer = MagicMock(spec=Customer)
        mock_customer.loyalty_points = 300
        
        # Mock reward with higher point cost
        mock_reward = MagicMock(spec=LoyaltyReward)
        mock_reward.points_cost = 500
        
        # Mock the get_customer_by_id method
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = mock_customer
            
            # Mock the LoyaltyReward.query.get method
            with patch('app.services.customer_service.LoyaltyReward.query') as mock_reward_query:
                mock_reward_query.get.return_value = mock_reward
                
                # Call the method and assert that it raises InsufficientPointsError
                with self.assertRaises(InsufficientPointsError):
                    self.customer_service.redeem_reward(
                        customer_id=1,
                        reward_id=2
                    )
                    
                mock_get_customer.assert_called_once_with(1)
                mock_reward_query.get.assert_called_once_with(2)

    def test_redeem_reward_not_available(self):
        """Test redeem_reward method when reward is not available to customer."""
        # Mock customer with enough points
        mock_customer = MagicMock(spec=Customer)
        mock_customer.loyalty_points = 1000
        
        # Mock reward that's not available to the customer
        mock_reward = MagicMock(spec=LoyaltyReward)
        mock_reward.points_cost = 500
        mock_reward.name = 'Test Reward'
        mock_reward.is_available_for_customer.return_value = False
        
        # Mock the get_customer_by_id method
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = mock_customer
            
            # Mock the LoyaltyReward.query.get method
            with patch('app.services.customer_service.LoyaltyReward.query') as mock_reward_query:
                mock_reward_query.get.return_value = mock_reward
                
                # Call the method and assert that it raises RewardNotAvailableError
                with self.assertRaises(RewardNotAvailableError):
                    self.customer_service.redeem_reward(
                        customer_id=1,
                        reward_id=2
                    )
                    
                mock_get_customer.assert_called_once_with(1)
                mock_reward_query.get.assert_called_once_with(2)
                mock_reward.is_available_for_customer.assert_called_once_with(mock_customer)

    def test_get_tier_benefits(self):
        """Test get_tier_benefits method."""
        # Call the method for different tiers
        standard_benefits = self.customer_service.get_tier_benefits('Standard')
        silver_benefits = self.customer_service.get_tier_benefits('Silver')
        gold_benefits = self.customer_service.get_tier_benefits('Gold')
        platinum_benefits = self.customer_service.get_tier_benefits('Platinum')
        
        # Assert the results
        self.assertEqual(standard_benefits['name'], 'Standard')
        self.assertEqual(standard_benefits['point_multiplier'], 1.0)
        self.assertFalse(standard_benefits['late_checkout'])
        self.assertTrue(standard_benefits['free_wifi'])
        self.assertEqual(standard_benefits['next_tier_points'], 1000)
        
        self.assertEqual(silver_benefits['name'], 'Silver')
        self.assertEqual(silver_benefits['point_multiplier'], 1.25)
        self.assertTrue(silver_benefits['late_checkout'])
        self.assertTrue(silver_benefits['exclusive_offers'])
        self.assertEqual(silver_benefits['next_tier_points'], 5000)
        
        self.assertEqual(gold_benefits['name'], 'Gold')
        self.assertEqual(gold_benefits['point_multiplier'], 1.5)
        self.assertTrue(gold_benefits['room_upgrades'])
        self.assertTrue(gold_benefits['welcome_gift'])
        self.assertEqual(gold_benefits['next_tier_points'], 10000)
        
        self.assertEqual(platinum_benefits['name'], 'Platinum')
        self.assertEqual(platinum_benefits['point_multiplier'], 2.0)
        self.assertTrue(platinum_benefits['free_breakfast'])
        self.assertTrue(platinum_benefits['lounge_access'])
        self.assertTrue(platinum_benefits['guaranteed_availability'])
        self.assertIsNone(platinum_benefits['next_tier_points'])
        
        # Also test with an invalid tier
        invalid_benefits = self.customer_service.get_tier_benefits('Invalid')
        self.assertEqual(invalid_benefits, standard_benefits)  # Should default to Standard

    def test_get_tier_progress(self):
        """Test get_tier_progress method."""
        # Test case 1: Customer with Standard tier
        mock_standard_customer = MagicMock(spec=Customer)
        mock_standard_customer.loyalty_tier = 'Standard'
        mock_standard_customer.loyalty_points = 500
        
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = mock_standard_customer
            
            progress = self.customer_service.get_tier_progress(1)
            
            self.assertEqual(progress['current_tier'], 'Standard')
            self.assertEqual(progress['next_tier'], 'Silver')
            self.assertEqual(progress['points'], 500)
            self.assertEqual(progress['points_to_next_tier'], 500)  # Need 500 more to reach 1000
            self.assertEqual(progress['progress_percent'], 50)  # 500/1000 = 50%
            
            mock_get_customer.assert_called_once_with(1)
            
        # Test case 2: Customer with Gold tier
        mock_gold_customer = MagicMock(spec=Customer)
        mock_gold_customer.loyalty_tier = 'Gold'
        mock_gold_customer.loyalty_points = 7500
        
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = mock_gold_customer
            
            progress = self.customer_service.get_tier_progress(1)
            
            self.assertEqual(progress['current_tier'], 'Gold')
            self.assertEqual(progress['next_tier'], 'Platinum')
            self.assertEqual(progress['points'], 7500)
            self.assertEqual(progress['points_to_next_tier'], 2500)  # Need 2500 more to reach 10000
            self.assertEqual(progress['progress_percent'], 50)  # 2500/5000 = 50%
            
            mock_get_customer.assert_called_once_with(1)
            
        # Test case 3: Customer with Platinum tier (highest tier)
        mock_platinum_customer = MagicMock(spec=Customer)
        mock_platinum_customer.loyalty_tier = 'Platinum'
        mock_platinum_customer.loyalty_points = 15000
        
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = mock_platinum_customer
            
            progress = self.customer_service.get_tier_progress(1)
            
            self.assertEqual(progress['current_tier'], 'Platinum')
            self.assertIsNone(progress['next_tier'])  # No next tier
            self.assertEqual(progress['points'], 15000)
            self.assertEqual(progress['points_to_next_tier'], 0)  # Already at highest tier
            self.assertEqual(progress['progress_percent'], 100)  # 100% progress
            
            mock_get_customer.assert_called_once_with(1)
            
        # Test case 4: Customer not found
        with patch.object(self.customer_service, 'get_customer_by_id') as mock_get_customer:
            mock_get_customer.return_value = None
            
            progress = self.customer_service.get_tier_progress(1)
            
            self.assertIsNone(progress)
            mock_get_customer.assert_called_once_with(1) 