"""
Database Constraints Migration Script.

This script adds comprehensive database constraints including foreign key constraints,
check constraints for business rules, and indexes for performance.
"""

import logging
from sqlalchemy import text
from db import db

logger = logging.getLogger(__name__)


def add_foreign_key_constraints():
    """Add proper foreign key constraints with cascade settings."""
    
    constraints = [
        # User-related constraints
        {
            'table': 'customers',
            'constraint': 'fk_customers_user_id',
            'sql': 'ALTER TABLE customers ADD CONSTRAINT fk_customers_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE'
        },
        {
            'table': 'notifications',
            'constraint': 'fk_notifications_user_id',
            'sql': 'ALTER TABLE notifications ADD CONSTRAINT fk_notifications_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE'
        },
        {
            'table': 'staff_requests',
            'constraint': 'fk_staff_requests_user_id',
            'sql': 'ALTER TABLE staff_requests ADD CONSTRAINT fk_staff_requests_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE'
        },
        {
            'table': 'staff_requests',
            'constraint': 'fk_staff_requests_handled_by',
            'sql': 'ALTER TABLE staff_requests ADD CONSTRAINT fk_staff_requests_handled_by FOREIGN KEY (handled_by) REFERENCES users(id) ON DELETE SET NULL'
        },
        
        # Booking-related constraints
        {
            'table': 'bookings',
            'constraint': 'fk_bookings_customer_id',
            'sql': 'ALTER TABLE bookings ADD CONSTRAINT fk_bookings_customer_id FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE'
        },
        {
            'table': 'bookings',
            'constraint': 'fk_bookings_room_id',
            'sql': 'ALTER TABLE bookings ADD CONSTRAINT fk_bookings_room_id FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE RESTRICT'
        },
        {
            'table': 'bookings',
            'constraint': 'fk_bookings_cancelled_by',
            'sql': 'ALTER TABLE bookings ADD CONSTRAINT fk_bookings_cancelled_by FOREIGN KEY (cancelled_by) REFERENCES users(id) ON DELETE SET NULL'
        },
        
        # Payment-related constraints
        {
            'table': 'payments',
            'constraint': 'fk_payments_booking_id',
            'sql': 'ALTER TABLE payments ADD CONSTRAINT fk_payments_booking_id FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE'
        },
        {
            'table': 'payments',
            'constraint': 'fk_payments_processed_by',
            'sql': 'ALTER TABLE payments ADD CONSTRAINT fk_payments_processed_by FOREIGN KEY (processed_by) REFERENCES users(id) ON DELETE SET NULL'
        },
        {
            'table': 'payments',
            'constraint': 'fk_payments_refunded_by',
            'sql': 'ALTER TABLE payments ADD CONSTRAINT fk_payments_refunded_by FOREIGN KEY (refunded_by) REFERENCES users(id) ON DELETE SET NULL'
        },
        
        # Room-related constraints
        {
            'table': 'rooms',
            'constraint': 'fk_rooms_room_type_id',
            'sql': 'ALTER TABLE rooms ADD CONSTRAINT fk_rooms_room_type_id FOREIGN KEY (room_type_id) REFERENCES room_types(id) ON DELETE RESTRICT'
        },
        {
            'table': 'room_status_logs',
            'constraint': 'fk_room_status_logs_room_id',
            'sql': 'ALTER TABLE room_status_logs ADD CONSTRAINT fk_room_status_logs_room_id FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE'
        },
        {
            'table': 'room_status_logs',
            'constraint': 'fk_room_status_logs_changed_by',
            'sql': 'ALTER TABLE room_status_logs ADD CONSTRAINT fk_room_status_logs_changed_by FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL'
        },
        {
            'table': 'room_status_logs',
            'constraint': 'fk_room_status_logs_booking_id',
            'sql': 'ALTER TABLE room_status_logs ADD CONSTRAINT fk_room_status_logs_booking_id FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE SET NULL'
        },
        
        # Housekeeping constraints
        {
            'table': 'housekeeping_tasks',
            'constraint': 'fk_housekeeping_tasks_room_id',
            'sql': 'ALTER TABLE housekeeping_tasks ADD CONSTRAINT fk_housekeeping_tasks_room_id FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE'
        },
        {
            'table': 'housekeeping_tasks',
            'constraint': 'fk_housekeeping_tasks_assigned_to',
            'sql': 'ALTER TABLE housekeeping_tasks ADD CONSTRAINT fk_housekeeping_tasks_assigned_to FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL'
        },
        {
            'table': 'housekeeping_tasks',
            'constraint': 'fk_housekeeping_tasks_verified_by',
            'sql': 'ALTER TABLE housekeeping_tasks ADD CONSTRAINT fk_housekeeping_tasks_verified_by FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL'
        },
        
        # Maintenance constraints
        {
            'table': 'maintenance_requests',
            'constraint': 'fk_maintenance_requests_room_id',
            'sql': 'ALTER TABLE maintenance_requests ADD CONSTRAINT fk_maintenance_requests_room_id FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE'
        },
        {
            'table': 'maintenance_requests',
            'constraint': 'fk_maintenance_requests_reported_by',
            'sql': 'ALTER TABLE maintenance_requests ADD CONSTRAINT fk_maintenance_requests_reported_by FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE SET NULL'
        },
        {
            'table': 'maintenance_requests',
            'constraint': 'fk_maintenance_requests_assigned_to',
            'sql': 'ALTER TABLE maintenance_requests ADD CONSTRAINT fk_maintenance_requests_assigned_to FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL'
        },
        
        # Loyalty constraints
        {
            'table': 'loyalty_ledger',
            'constraint': 'fk_loyalty_ledger_customer_id',
            'sql': 'ALTER TABLE loyalty_ledger ADD CONSTRAINT fk_loyalty_ledger_customer_id FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE'
        },
        {
            'table': 'loyalty_ledger',
            'constraint': 'fk_loyalty_ledger_booking_id',
            'sql': 'ALTER TABLE loyalty_ledger ADD CONSTRAINT fk_loyalty_ledger_booking_id FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE'
        },
        {
            'table': 'loyalty_ledger',
            'constraint': 'fk_loyalty_ledger_staff_id',
            'sql': 'ALTER TABLE loyalty_ledger ADD CONSTRAINT fk_loyalty_ledger_staff_id FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE SET NULL'
        }
    ]
    
    for constraint in constraints:
        try:
            db.session.execute(text(constraint['sql']))
            logger.info(f"Added constraint {constraint['constraint']} to {constraint['table']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.debug(f"Constraint {constraint['constraint']} already exists")
            else:
                logger.error(f"Failed to add constraint {constraint['constraint']}: {str(e)}")


def add_check_constraints():
    """Add check constraints for business rules."""
    
    constraints = [
        # Booking constraints
        {
            'table': 'bookings',
            'constraint': 'chk_bookings_dates',
            'sql': 'ALTER TABLE bookings ADD CONSTRAINT chk_bookings_dates CHECK (check_in_date < check_out_date)'
        },
        {
            'table': 'bookings',
            'constraint': 'chk_bookings_num_guests',
            'sql': 'ALTER TABLE bookings ADD CONSTRAINT chk_bookings_num_guests CHECK (num_guests > 0)'
        },
        {
            'table': 'bookings',
            'constraint': 'chk_bookings_total_price',
            'sql': 'ALTER TABLE bookings ADD CONSTRAINT chk_bookings_total_price CHECK (total_price >= 0)'
        },
        {
            'table': 'bookings',
            'constraint': 'chk_bookings_payment_amount',
            'sql': 'ALTER TABLE bookings ADD CONSTRAINT chk_bookings_payment_amount CHECK (payment_amount >= 0)'
        },
        {
            'table': 'bookings',
            'constraint': 'chk_bookings_deposit_amount',
            'sql': 'ALTER TABLE bookings ADD CONSTRAINT chk_bookings_deposit_amount CHECK (deposit_amount >= 0)'
        },
        {
            'table': 'bookings',
            'constraint': 'chk_bookings_cancellation_fee',
            'sql': 'ALTER TABLE bookings ADD CONSTRAINT chk_bookings_cancellation_fee CHECK (cancellation_fee >= 0)'
        },
        {
            'table': 'bookings',
            'constraint': 'chk_bookings_status',
            'sql': "ALTER TABLE bookings ADD CONSTRAINT chk_bookings_status CHECK (status IN ('Reserved', 'Checked In', 'Checked Out', 'Cancelled', 'No Show'))"
        },
        {
            'table': 'bookings',
            'constraint': 'chk_bookings_payment_status',
            'sql': "ALTER TABLE bookings ADD CONSTRAINT chk_bookings_payment_status CHECK (payment_status IN ('Not Paid', 'Deposit Paid', 'Fully Paid', 'Refunded'))"
        },
        
        # Payment constraints
        {
            'table': 'payments',
            'constraint': 'chk_payments_amount',
            'sql': 'ALTER TABLE payments ADD CONSTRAINT chk_payments_amount CHECK (amount > 0)'
        },
        {
            'table': 'payments',
            'constraint': 'chk_payments_refunded',
            'sql': 'ALTER TABLE payments ADD CONSTRAINT chk_payments_refunded CHECK (refunded IN (0, 1))'
        },
        
        # Room constraints
        {
            'table': 'rooms',
            'constraint': 'chk_rooms_floor',
            'sql': 'ALTER TABLE rooms ADD CONSTRAINT chk_rooms_floor CHECK (floor > 0)'
        },
        {
            'table': 'rooms',
            'constraint': 'chk_rooms_status',
            'sql': "ALTER TABLE rooms ADD CONSTRAINT chk_rooms_status CHECK (status IN ('Available', 'Booked', 'Occupied', 'Checkout', 'Needs Cleaning', 'Under Maintenance', 'Out of Service'))"
        },
        
        # Room type constraints
        {
            'table': 'room_types',
            'constraint': 'chk_room_types_base_rate',
            'sql': 'ALTER TABLE room_types ADD CONSTRAINT chk_room_types_base_rate CHECK (base_rate > 0)'
        },
        {
            'table': 'room_types',
            'constraint': 'chk_room_types_max_occupancy',
            'sql': 'ALTER TABLE room_types ADD CONSTRAINT chk_room_types_max_occupancy CHECK (max_occupancy > 0)'
        },
        
        # Seasonal rate constraints
        {
            'table': 'seasonal_rates',
            'constraint': 'chk_seasonal_rates_rate',
            'sql': 'ALTER TABLE seasonal_rates ADD CONSTRAINT chk_seasonal_rates_rate CHECK (rate > 0)'
        },
        {
            'table': 'seasonal_rates',
            'constraint': 'chk_seasonal_rates_dates',
            'sql': 'ALTER TABLE seasonal_rates ADD CONSTRAINT chk_seasonal_rates_dates CHECK (start_date <= end_date)'
        },
        
        # Loyalty constraints
        {
            'table': 'loyalty_ledger',
            'constraint': 'chk_loyalty_ledger_points',
            'sql': 'ALTER TABLE loyalty_ledger ADD CONSTRAINT chk_loyalty_ledger_points CHECK (points != 0)'
        },
        {
            'table': 'loyalty_ledger',
            'constraint': 'chk_loyalty_ledger_txn_type',
            'sql': "ALTER TABLE loyalty_ledger ADD CONSTRAINT chk_loyalty_ledger_txn_type CHECK (txn_type IN ('earn', 'redeem', 'adjust', 'expire'))"
        },
        
        # Maintenance constraints
        {
            'table': 'maintenance_requests',
            'constraint': 'chk_maintenance_requests_priority',
            'sql': "ALTER TABLE maintenance_requests ADD CONSTRAINT chk_maintenance_requests_priority CHECK (priority IN ('low', 'medium', 'high', 'urgent'))"
        },
        {
            'table': 'maintenance_requests',
            'constraint': 'chk_maintenance_requests_status',
            'sql': "ALTER TABLE maintenance_requests ADD CONSTRAINT chk_maintenance_requests_status CHECK (status IN ('open', 'assigned', 'in_progress', 'resolved', 'closed'))"
        },
        
        # Housekeeping constraints
        {
            'table': 'housekeeping_tasks',
            'constraint': 'chk_housekeeping_tasks_priority',
            'sql': "ALTER TABLE housekeeping_tasks ADD CONSTRAINT chk_housekeeping_tasks_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent'))"
        },
        {
            'table': 'housekeeping_tasks',
            'constraint': 'chk_housekeeping_tasks_status',
            'sql': "ALTER TABLE housekeeping_tasks ADD CONSTRAINT chk_housekeeping_tasks_status CHECK (status IN ('pending', 'in_progress', 'completed', 'verified'))"
        },
        
        # Customer constraints
        {
            'table': 'customers',
            'constraint': 'chk_customers_loyalty_points',
            'sql': 'ALTER TABLE customers ADD CONSTRAINT chk_customers_loyalty_points CHECK (loyalty_points >= 0)'
        },
        {
            'table': 'customers',
            'constraint': 'chk_customers_total_spent',
            'sql': 'ALTER TABLE customers ADD CONSTRAINT chk_customers_total_spent CHECK (total_spent >= 0)'
        }
    ]
    
    for constraint in constraints:
        try:
            db.session.execute(text(constraint['sql']))
            logger.info(f"Added check constraint {constraint['constraint']} to {constraint['table']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.debug(f"Check constraint {constraint['constraint']} already exists")
            else:
                logger.error(f"Failed to add check constraint {constraint['constraint']}: {str(e)}")


def add_performance_indexes():
    """Add indexes for better query performance."""
    
    indexes = [
        # Booking indexes
        {
            'name': 'idx_bookings_customer_status',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_bookings_customer_status ON bookings(customer_id, status)'
        },
        {
            'name': 'idx_bookings_room_dates',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_bookings_room_dates ON bookings(room_id, check_in_date, check_out_date)'
        },
        {
            'name': 'idx_bookings_dates_status',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_bookings_dates_status ON bookings(check_in_date, check_out_date, status)'
        },
        
        # Payment indexes
        {
            'name': 'idx_payments_booking_date',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_payments_booking_date ON payments(booking_id, payment_date)'
        },
        
        # Room status log indexes
        {
            'name': 'idx_room_status_logs_room_time',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_room_status_logs_room_time ON room_status_logs(room_id, change_time)'
        },
        
        # Housekeeping task indexes
        {
            'name': 'idx_housekeeping_tasks_assigned_status',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_housekeeping_tasks_assigned_status ON housekeeping_tasks(assigned_to, status)'
        },
        {
            'name': 'idx_housekeeping_tasks_room_due',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_housekeeping_tasks_room_due ON housekeeping_tasks(room_id, due_date)'
        },
        
        # Maintenance request indexes
        {
            'name': 'idx_maintenance_requests_assigned_status',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_maintenance_requests_assigned_status ON maintenance_requests(assigned_to, status)'
        },
        {
            'name': 'idx_maintenance_requests_room_priority',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_maintenance_requests_room_priority ON maintenance_requests(room_id, priority)'
        },
        
        # Loyalty ledger indexes
        {
            'name': 'idx_loyalty_ledger_customer_date',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_loyalty_ledger_customer_date ON loyalty_ledger(customer_id, txn_dt)'
        },
        
        # Notification indexes
        {
            'name': 'idx_notifications_user_read',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read)'
        }
    ]
    
    for index in indexes:
        try:
            db.session.execute(text(index['sql']))
            logger.info(f"Added index {index['name']}")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.debug(f"Index {index['name']} already exists")
            else:
                logger.error(f"Failed to add index {index['name']}: {str(e)}")


def run_migration():
    """Run the complete database constraints migration."""
    try:
        logger.info("Starting database constraints migration...")
        
        # Add foreign key constraints
        logger.info("Adding foreign key constraints...")
        add_foreign_key_constraints()
        
        # Add check constraints
        logger.info("Adding check constraints...")
        add_check_constraints()
        
        # Add performance indexes
        logger.info("Adding performance indexes...")
        add_performance_indexes()
        
        # Commit all changes
        db.session.commit()
        logger.info("Database constraints migration completed successfully")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database constraints migration failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run migration
    success = run_migration()
    
    if success:
        print("✅ Database constraints migration completed successfully")
    else:
        print("❌ Database constraints migration failed")
        exit(1) 