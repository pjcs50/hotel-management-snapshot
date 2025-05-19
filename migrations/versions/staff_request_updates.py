"""Staff requests table updates

Revision ID: 202310181234
Revises: 
Create Date: 2023-10-18 12:34:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '202310181234'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Check if the staff_requests table exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    if 'staff_requests' not in tables:
        # Create the table if it doesn't exist
        op.create_table(
            'staff_requests',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('role_requested', sa.String(50), nullable=False),
            sa.Column('status', sa.String(20), default='pending'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
            sa.Column('handled_at', sa.DateTime(), nullable=True),
            sa.Column('handled_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.ForeignKeyConstraint(['handled_by'], ['users.id'])
        )
        return
    
    # Get the columns in the staff_requests table
    columns = [c['name'] for c in inspector.get_columns('staff_requests')]
    
    # Add any missing columns
    if 'notes' not in columns:
        op.add_column('staff_requests', sa.Column('notes', sa.Text(), nullable=True))
    
    if 'created_at' not in columns:
        op.add_column('staff_requests', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()))
    
    if 'handled_at' not in columns and 'processed_at' not in columns:
        op.add_column('staff_requests', sa.Column('handled_at', sa.DateTime(), nullable=True))
    
    if 'handled_by' not in columns and 'processed_by' not in columns:
        op.add_column('staff_requests', sa.Column('handled_by', sa.Integer(), nullable=True))
        # Add foreign key constraint
        op.create_foreign_key(
            'fk_staff_requests_handled_by_users', 
            'staff_requests', 'users', 
            ['handled_by'], ['id']
        )
    
    # Handle column renames if necessary
    if 'processed_at' in columns and 'handled_at' not in columns:
        op.alter_column('staff_requests', 'processed_at', new_column_name='handled_at')
    
    if 'processed_by' in columns and 'handled_by' not in columns:
        op.alter_column('staff_requests', 'processed_by', new_column_name='handled_by')


def downgrade():
    # No downgrade implementation needed for this migration
    pass 