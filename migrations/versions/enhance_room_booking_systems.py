"""
Enhance room and booking systems.

This migration adds enhanced functionality to the room, booking, and customer management systems,
including loyalty points, payments, booking logs, and room status tracking.

Revision ID: enhance_room_booking_systems
Revises: staff_request_updates
Create Date: 2023-05-20 08:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import json
from datetime import datetime


# revision identifiers, used by Alembic
revision = 'enhance_room_booking_systems'
down_revision = 'staff_request_updates'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Enhance room_types table
    op.add_column('room_types', sa.Column('amenities_json', sa.Text(), nullable=True))
    op.add_column('room_types', sa.Column('image_main', sa.String(255), nullable=True))
    op.add_column('room_types', sa.Column('image_gallery', sa.Text(), nullable=True))
    op.add_column('room_types', sa.Column('size_sqm', sa.Float(), nullable=True))
    op.add_column('room_types', sa.Column('bed_type', sa.String(100), nullable=True))
    op.add_column('room_types', sa.Column('max_occupants', sa.Integer(), nullable=False, server_default='2'))
    op.add_column('room_types', sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')))
    op.add_column('room_types', sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')))
    
    # Set default values for amenities_json and image_gallery
    op.execute("UPDATE room_types SET amenities_json = '[]', image_gallery = '[]'")
    
    # 2. Enhance seasonal_rates table
    op.add_column('seasonal_rates', sa.Column('rate_type', sa.String(20), nullable=False, server_default='seasonal'))
    op.add_column('seasonal_rates', sa.Column('day_of_week_adjustments', sa.Text(), nullable=True))
    op.add_column('seasonal_rates', sa.Column('is_special_event', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('seasonal_rates', sa.Column('min_stay_nights', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('seasonal_rates', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('seasonal_rates', sa.Column('priority', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('seasonal_rates', sa.Column('active', sa.Boolean(), nullable=False, server_default='1'))
    
    # 3. Enhance customers table
    op.add_column('customers', sa.Column('email', sa.String(120), nullable=True))
    op.add_column('customers', sa.Column('preferences_json', sa.Text(), nullable=True))
    op.add_column('customers', sa.Column('documents_json', sa.Text(), nullable=True))
    op.add_column('customers', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('customers', sa.Column('loyalty_points', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('customers', sa.Column('loyalty_tier', sa.String(20), nullable=False, server_default='Standard'))
    op.add_column('customers', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('customers', sa.Column('nationality', sa.String(50), nullable=True))
    op.add_column('customers', sa.Column('vip', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('customers', sa.Column('stay_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('customers', sa.Column('total_spent', sa.Float(), nullable=False, server_default='0.0'))
    
    # Create an index on loyalty tier and points
    op.create_index('idx_customers_loyalty', 'customers', ['loyalty_tier', 'loyalty_points'])
    
    # 4. Enhance bookings table
    op.add_column('bookings', sa.Column('num_guests', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('bookings', sa.Column('payment_status', sa.String(20), nullable=False, server_default='Not Paid'))
    op.add_column('bookings', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('bookings', sa.Column('special_requests_json', sa.Text(), nullable=True))
    op.add_column('bookings', sa.Column('room_preferences_json', sa.Text(), nullable=True))
    op.add_column('bookings', sa.Column('confirmation_code', sa.String(20), nullable=True, unique=True))
    op.add_column('bookings', sa.Column('payment_amount', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('bookings', sa.Column('deposit_amount', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('bookings', sa.Column('source', sa.String(50), nullable=True))
    op.add_column('bookings', sa.Column('booking_date', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')))
    op.add_column('bookings', sa.Column('loyalty_points_earned', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('bookings', sa.Column('guest_name', sa.String(100), nullable=True))
    op.add_column('bookings', sa.Column('cancellation_reason', sa.Text(), nullable=True))
    op.add_column('bookings', sa.Column('cancelled_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('bookings', sa.Column('cancellation_date', sa.DateTime(), nullable=True))
    op.add_column('bookings', sa.Column('cancellation_fee', sa.Float(), nullable=False, server_default='0.0'))
    
    # Create an index on customer_id and status
    op.create_index('idx_bookings_customer', 'bookings', ['customer_id', 'status'])
    
    # 5. Create loyalty_ledger table
    op.create_table('loyalty_ledger',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False, index=True),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('txn_dt', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('txn_type', sa.String(20), nullable=False, server_default='earn'),
        sa.Column('staff_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'))
    )
    
    # 6. Create payments table
    op.create_table('payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=False, index=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('payment_date', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('payment_type', sa.String(50), nullable=True),
        sa.Column('reference', sa.String(100), nullable=True),
        sa.Column('processed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('refunded', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('refund_date', sa.DateTime(), nullable=True),
        sa.Column('refund_reason', sa.Text(), nullable=True),
        sa.Column('refund_reference', sa.String(100), nullable=True),
        sa.Column('refunded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'))
    )
    
    # 7. Create booking_logs table
    op.create_table('booking_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=False, index=True),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('action_time', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('prev_status', sa.String(20), nullable=True),
        sa.Column('new_status', sa.String(20), nullable=True),
        sa.Column('prev_room_id', sa.Integer(), nullable=True),
        sa.Column('new_room_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('reference', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'))
    )
    
    # 8. Create room_status_logs table if it doesn't exist already
    if not op.get_bind().engine.dialect.has_table(op.get_bind(), 'room_status_logs'):
        op.create_table('room_status_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('room_id', sa.Integer(), sa.ForeignKey('rooms.id'), nullable=False, index=True),
            sa.Column('old_status', sa.String(20), nullable=True),
            sa.Column('new_status', sa.String(20), nullable=False),
            sa.Column('changed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('change_time', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'))
        )
    else:
        # Make sure existing room_status_logs table has all needed columns
        op.add_column('room_status_logs', sa.Column('change_time', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')))
        op.add_column('room_status_logs', sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=True))
        
        # Update existing rows to have change_time
        op.execute("UPDATE room_status_logs SET change_time = created_at WHERE change_time IS NULL")
        op.alter_column('room_status_logs', 'change_time', nullable=False)


def downgrade():
    # This is a complex migration with many changes, so we'll provide a basic downgrade
    # that removes the added tables and columns
    
    # Dropping tables in reverse order
    op.drop_table('booking_logs')
    op.drop_table('payments')
    op.drop_table('loyalty_ledger')
    
    # Remove added columns from existing tables
    # Bookings
    columns_to_remove = [
        'num_guests', 'payment_status', 'notes', 'special_requests_json',
        'room_preferences_json', 'confirmation_code', 'payment_amount',
        'deposit_amount', 'source', 'booking_date', 'loyalty_points_earned',
        'guest_name', 'cancellation_reason', 'cancelled_by',
        'cancellation_date', 'cancellation_fee'
    ]
    for column in columns_to_remove:
        op.drop_column('bookings', column)
    
    # Remove index
    op.drop_index('idx_bookings_customer', table_name='bookings')
    
    # Customers
    columns_to_remove = [
        'email', 'preferences_json', 'documents_json', 'notes',
        'loyalty_points', 'loyalty_tier', 'date_of_birth', 'nationality',
        'vip', 'stay_count', 'total_spent'
    ]
    for column in columns_to_remove:
        op.drop_column('customers', column)
    
    # Remove index
    op.drop_index('idx_customers_loyalty', table_name='customers')
    
    # Seasonal rates
    columns_to_remove = [
        'rate_type', 'day_of_week_adjustments', 'is_special_event', 
        'min_stay_nights', 'description', 'priority', 'active'
    ]
    for column in columns_to_remove:
        op.drop_column('seasonal_rates', column)
    
    # Room types
    columns_to_remove = [
        'amenities_json', 'image_main', 'image_gallery', 'size_sqm',
        'bed_type', 'max_occupants', 'created_at', 'updated_at'
    ]
    for column in columns_to_remove:
        op.drop_column('room_types', column) 