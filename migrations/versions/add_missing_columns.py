"""Add missing columns to room_types table

This migration adds the has_view, has_balcony, and smoking_allowed columns to the room_types table.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_missing_cols'
down_revision = None  # Set to the previous migration if needed
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to room_types table if they don't exist
    op.execute("""
    ALTER TABLE room_types ADD COLUMN IF NOT EXISTS has_view BOOLEAN DEFAULT FALSE;
    ALTER TABLE room_types ADD COLUMN IF NOT EXISTS has_balcony BOOLEAN DEFAULT FALSE;
    ALTER TABLE room_types ADD COLUMN IF NOT EXISTS smoking_allowed BOOLEAN DEFAULT FALSE;
    """)


def downgrade():
    # SQLite doesn't support dropping columns without recreating the table
    pass 