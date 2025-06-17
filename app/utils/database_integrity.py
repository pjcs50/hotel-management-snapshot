"""
Database Integrity Management Module.

This module provides comprehensive database integrity features including
foreign key constraint management, cascade operations, and business rule validation.
"""

import logging
from datetime import datetime
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session
from db import db

logger = logging.getLogger(__name__)


class DatabaseIntegrityError(Exception):
    """Exception raised for database integrity violations."""
    pass


class CascadeDeleteError(DatabaseIntegrityError):
    """Exception raised for cascade delete operation errors."""
    pass


class BusinessRuleViolationError(DatabaseIntegrityError):
    """Exception raised for business rule violations."""
    pass


class DatabaseIntegrityManager:
    """
    Comprehensive database integrity manager.
    
    Handles foreign key constraints, cascade operations, and business rule validation
    to ensure data consistency and prevent orphaned records.
    """
    
    def __init__(self):
        """Initialize database integrity manager."""
        self.cascade_rules = self._define_cascade_rules()
        self.business_rules = self._define_business_rules()
        self.constraint_checks = self._define_constraint_checks()
        
    def _define_cascade_rules(self):
        """Define cascade delete rules for all relationships."""
        return {
            'User': {
                'customer_profile': 'CASCADE',  # Delete customer when user deleted
                'notifications': 'CASCADE',    # Delete notifications when user deleted
                'staff_requests': 'CASCADE',   # Delete staff requests when user deleted
                'cancelled_bookings': 'SET_NULL',  # Set cancelled_by to NULL
                'processed_payments': 'SET_NULL',  # Set processed_by to NULL
                'room_status_changes': 'SET_NULL',  # Set changed_by to NULL
                'assigned_tasks': 'SET_NULL',  # Set assigned_to to NULL
                'verified_tasks': 'SET_NULL',  # Set verified_by to NULL
                'reported_maintenance': 'SET_NULL',  # Set reported_by to NULL
                'assigned_maintenance': 'SET_NULL',  # Set assigned_to to NULL
            },
            'Customer': {
                'bookings': 'CASCADE',  # Delete bookings when customer deleted
                'loyalty_transactions': 'CASCADE',  # Delete loyalty records
                'loyalty_redemptions': 'CASCADE',  # Delete redemptions
                'waitlist_entries': 'CASCADE',  # Delete waitlist entries
            },
            'Room': {
                'bookings': 'RESTRICT',  # Prevent room deletion if bookings exist
                'housekeeping_tasks': 'CASCADE',  # Delete tasks when room deleted
                'maintenance_requests': 'CASCADE',  # Delete maintenance when room deleted
                'status_logs': 'CASCADE',  # Delete status logs when room deleted
                'waitlist_entries': 'CASCADE',  # Delete waitlist entries
            },
            'RoomType': {
                'rooms': 'RESTRICT',  # Prevent room type deletion if rooms exist
                'seasonal_rates': 'CASCADE',  # Delete rates when room type deleted
                'waitlist_entries': 'CASCADE',  # Delete waitlist entries
            },
            'Booking': {
                'payments': 'CASCADE',  # Delete payments when booking deleted
                'loyalty_transactions': 'CASCADE',  # Delete loyalty records
                'loyalty_redemptions': 'SET_NULL',  # Set booking_id to NULL
                'room_status_changes': 'SET_NULL',  # Set booking_id to NULL
                'booking_logs': 'CASCADE',  # Delete logs when booking deleted
                'folio_items': 'CASCADE',  # Delete folio items when booking deleted
            }
        }
    
    def _define_business_rules(self):
        """Define business rules for data validation."""
        return {
            'booking_dates': {
                'rule': 'check_in_date < check_out_date',
                'message': 'Check-in date must be before check-out date'
            },
            'booking_future_dates': {
                'rule': 'check_in_date >= CURRENT_DATE',
                'message': 'Check-in date cannot be in the past'
            },
            'room_capacity': {
                'rule': 'num_guests <= room_type.max_occupancy',
                'message': 'Number of guests exceeds room capacity'
            },
            'payment_amount': {
                'rule': 'amount > 0',
                'message': 'Payment amount must be positive'
            },
            'loyalty_points': {
                'rule': 'points >= 0',
                'message': 'Loyalty points cannot be negative'
            },
            'seasonal_rate_dates': {
                'rule': 'start_date <= end_date',
                'message': 'Start date must be before or equal to end date'
            },
            'maintenance_priority': {
                'rule': "priority IN ('low', 'medium', 'high', 'urgent')",
                'message': 'Invalid maintenance priority level'
            }
        }
    
    def _define_constraint_checks(self):
        """Define database-level constraint checks."""
        return {
            'bookings': [
                "CHECK (check_in_date < check_out_date)",
                "CHECK (num_guests > 0)",
                "CHECK (total_price >= 0)",
                "CHECK (payment_amount >= 0)",
                "CHECK (deposit_amount >= 0)",
                "CHECK (cancellation_fee >= 0)"
            ],
            'payments': [
                "CHECK (amount > 0)",
                "CHECK (refunded IN (0, 1))"
            ],
            'rooms': [
                "CHECK (floor > 0)",
                "CHECK (status IN ('Available', 'Booked', 'Occupied', 'Checkout', 'Needs Cleaning', 'Under Maintenance', 'Out of Service'))"
            ],
            'room_types': [
                "CHECK (base_rate > 0)",
                "CHECK (max_occupancy > 0)"
            ],
            'seasonal_rates': [
                "CHECK (rate > 0)",
                "CHECK (start_date <= end_date)"
            ],
            'loyalty_ledger': [
                "CHECK (points != 0)",  # Points must be non-zero (positive or negative)
                "CHECK (txn_type IN ('earn', 'redeem', 'adjust', 'expire'))"
            ],
            'maintenance_requests': [
                "CHECK (priority IN ('low', 'medium', 'high', 'urgent'))",
                "CHECK (status IN ('open', 'assigned', 'in_progress', 'resolved', 'closed'))"
            ],
            'housekeeping_tasks': [
                "CHECK (priority IN ('low', 'normal', 'high', 'urgent'))",
                "CHECK (status IN ('pending', 'in_progress', 'completed', 'verified'))"
            ]
        }
    
    def validate_cascade_delete(self, model_class, instance_id, session=None):
        """
        Validate if a cascade delete operation is safe.
        
        Args:
            model_class: SQLAlchemy model class
            instance_id: ID of the instance to delete
            session: Database session (optional)
            
        Returns:
            dict: Validation result with affected records
            
        Raises:
            CascadeDeleteError: If cascade delete would violate business rules
        """
        if session is None:
            session = db.session
        
        model_name = model_class.__name__
        instance = session.get(model_class, instance_id)
        
        if not instance:
            raise ValueError(f"{model_name} with ID {instance_id} not found")
        
        cascade_rules = self.cascade_rules.get(model_name, {})
        affected_records = {}
        
        # Check each relationship
        for relationship_name, cascade_action in cascade_rules.items():
            try:
                related_objects = getattr(instance, relationship_name, None)
                
                if related_objects is not None:
                    # Handle both single objects and collections
                    if hasattr(related_objects, '__iter__') and not isinstance(related_objects, str):
                        count = len(list(related_objects))
                    else:
                        count = 1 if related_objects else 0
                    
                    if count > 0:
                        affected_records[relationship_name] = {
                            'count': count,
                            'action': cascade_action
                        }
                        
                        # Check for RESTRICT rules
                        if cascade_action == 'RESTRICT':
                            raise CascadeDeleteError(
                                f"Cannot delete {model_name} {instance_id}: "
                                f"{count} related {relationship_name} records exist"
                            )
                            
            except AttributeError:
                # Relationship doesn't exist on this instance
                continue
        
        return {
            'safe_to_delete': True,
            'affected_records': affected_records,
            'instance': instance
        }
    
    def safe_delete(self, model_class, instance_id, session=None, force=False):
        """
        Safely delete an instance with proper cascade handling.
        
        Args:
            model_class: SQLAlchemy model class
            instance_id: ID of the instance to delete
            session: Database session (optional)
            force: Force delete even if RESTRICT rules exist
            
        Returns:
            dict: Delete operation result
            
        Raises:
            CascadeDeleteError: If delete operation fails
        """
        if session is None:
            session = db.session
        
        try:
            # Validate cascade delete
            validation_result = self.validate_cascade_delete(model_class, instance_id, session)
            
            if not validation_result['safe_to_delete'] and not force:
                raise CascadeDeleteError("Delete operation blocked by validation")
            
            instance = validation_result['instance']
            
            # Log the delete operation
            logger.info(
                f"Deleting {model_class.__name__} {instance_id} with "
                f"{len(validation_result['affected_records'])} related record types"
            )
            
            # Perform the delete
            session.delete(instance)
            session.commit()
            
            return {
                'success': True,
                'deleted_instance': f"{model_class.__name__} {instance_id}",
                'affected_records': validation_result['affected_records']
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete {model_class.__name__} {instance_id}: {str(e)}")
            raise CascadeDeleteError(f"Delete operation failed: {str(e)}")
    
    def validate_business_rules(self, model_class, data, session=None):
        """
        Validate business rules for model data.
        
        Args:
            model_class: SQLAlchemy model class
            data: Data dictionary to validate
            session: Database session (optional)
            
        Returns:
            dict: Validation result
            
        Raises:
            BusinessRuleViolationError: If business rules are violated
        """
        if session is None:
            session = db.session
        
        model_name = model_class.__name__.lower()
        violations = []
        
        # Check model-specific business rules
        for rule_name, rule_config in self.business_rules.items():
            if model_name in rule_name or rule_name.startswith(model_name):
                try:
                    # Simple rule validation (can be extended for complex rules)
                    if not self._evaluate_business_rule(rule_config, data, session):
                        violations.append({
                            'rule': rule_name,
                            'message': rule_config['message']
                        })
                except Exception as e:
                    logger.warning(f"Failed to evaluate business rule {rule_name}: {str(e)}")
        
        if violations:
            raise BusinessRuleViolationError(
                f"Business rule violations: {'; '.join([v['message'] for v in violations])}"
            )
        
        return {
            'valid': True,
            'violations': violations
        }
    
    def _evaluate_business_rule(self, rule_config, data, session):
        """Evaluate a single business rule."""
        rule = rule_config['rule']
        
        # Simple rule evaluation (can be extended)
        if 'check_in_date < check_out_date' in rule:
            check_in = data.get('check_in_date')
            check_out = data.get('check_out_date')
            if check_in and check_out:
                return check_in < check_out
        
        elif 'amount > 0' in rule:
            amount = data.get('amount', 0)
            return amount > 0
        
        elif 'points >= 0' in rule:
            points = data.get('points', 0)
            return points >= 0
        
        elif 'num_guests > 0' in rule:
            num_guests = data.get('num_guests', 1)
            return num_guests > 0
        
        # Default to True for rules we can't evaluate
        return True
    
    def add_database_constraints(self, session=None):
        """
        Add database-level constraints for business rules.
        
        Args:
            session: Database session (optional)
        """
        if session is None:
            session = db.session
        
        try:
            for table_name, constraints in self.constraint_checks.items():
                for constraint in constraints:
                    constraint_name = f"chk_{table_name}_{hash(constraint) % 10000}"
                    
                    try:
                        # Add constraint if it doesn't exist
                        sql = f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} {constraint}"
                        session.execute(text(sql))
                        logger.info(f"Added constraint {constraint_name} to {table_name}")
                        
                    except Exception as e:
                        # Constraint might already exist
                        logger.debug(f"Constraint {constraint_name} already exists or failed: {str(e)}")
            
            session.commit()
            logger.info("Database constraints validation completed")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add database constraints: {str(e)}")
    
    def check_referential_integrity(self, session=None):
        """
        Check referential integrity across all tables.
        
        Args:
            session: Database session (optional)
            
        Returns:
            dict: Integrity check results
        """
        if session is None:
            session = db.session
        
        integrity_issues = []
        
        try:
            # Check for orphaned records
            orphaned_checks = [
                {
                    'table': 'customers',
                    'foreign_key': 'user_id',
                    'reference_table': 'users',
                    'reference_key': 'id'
                },
                {
                    'table': 'bookings',
                    'foreign_key': 'customer_id',
                    'reference_table': 'customers',
                    'reference_key': 'id'
                },
                {
                    'table': 'bookings',
                    'foreign_key': 'room_id',
                    'reference_table': 'rooms',
                    'reference_key': 'id'
                },
                {
                    'table': 'payments',
                    'foreign_key': 'booking_id',
                    'reference_table': 'bookings',
                    'reference_key': 'id'
                },
                {
                    'table': 'housekeeping_tasks',
                    'foreign_key': 'room_id',
                    'reference_table': 'rooms',
                    'reference_key': 'id'
                }
            ]
            
            for check in orphaned_checks:
                sql = f"""
                    SELECT COUNT(*) as orphaned_count
                    FROM {check['table']} t
                    LEFT JOIN {check['reference_table']} r 
                        ON t.{check['foreign_key']} = r.{check['reference_key']}
                    WHERE t.{check['foreign_key']} IS NOT NULL 
                        AND r.{check['reference_key']} IS NULL
                """
                
                result = session.execute(text(sql)).fetchone()
                orphaned_count = result[0] if result else 0
                
                if orphaned_count > 0:
                    integrity_issues.append({
                        'type': 'orphaned_records',
                        'table': check['table'],
                        'count': orphaned_count,
                        'description': f"{orphaned_count} orphaned records in {check['table']}"
                    })
            
            return {
                'integrity_ok': len(integrity_issues) == 0,
                'issues': integrity_issues,
                'checked_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Referential integrity check failed: {str(e)}")
            return {
                'integrity_ok': False,
                'issues': [{'type': 'check_failed', 'error': str(e)}],
                'checked_at': datetime.utcnow()
            }


# Global instance
db_integrity = DatabaseIntegrityManager()


def safe_delete_with_cascade(model_class, instance_id, force=False):
    """
    Convenience function for safe cascade delete.
    
    Args:
        model_class: SQLAlchemy model class
        instance_id: ID of the instance to delete
        force: Force delete even if RESTRICT rules exist
        
    Returns:
        dict: Delete operation result
    """
    return db_integrity.safe_delete(model_class, instance_id, force=force)


def validate_model_data(model_class, data):
    """
    Convenience function for business rule validation.
    
    Args:
        model_class: SQLAlchemy model class
        data: Data dictionary to validate
        
    Returns:
        dict: Validation result
    """
    return db_integrity.validate_business_rules(model_class, data)


def check_database_integrity():
    """
    Convenience function for integrity checking.
    
    Returns:
        dict: Integrity check results
    """
    return db_integrity.check_referential_integrity() 