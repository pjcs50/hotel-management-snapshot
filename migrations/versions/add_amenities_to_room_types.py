"""
Add amenities and enhanced fields to room_types table.

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2024-05-19

Reason:
    Add missing columns to the room_types table to match the enhanced RoomType model.
    This migration addresses the "no such column: room_types.amenities_json" error.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '1a2b3c4d5e6f'
down_revision = None  # Update this if there are previous migrations
branch_labels = None
depends_on = None


def upgrade():
    # Add the missing columns to the room_types table
    op.add_column('room_types', sa.Column('amenities_json', sa.Text(), nullable=True, server_default='[]'))
    op.add_column('room_types', sa.Column('image_main', sa.String(255), nullable=True))
    op.add_column('room_types', sa.Column('image_gallery', sa.Text(), nullable=True, server_default='[]'))
    op.add_column('room_types', sa.Column('size_sqm', sa.Float(), nullable=True))
    op.add_column('room_types', sa.Column('bed_type', sa.String(100), nullable=True))
    op.add_column('room_types', sa.Column('max_occupants', sa.Integer(), nullable=True, server_default='2'))
    

def downgrade():
    # Remove the columns if needed
    op.drop_column('room_types', 'max_occupants')
    op.drop_column('room_types', 'bed_type')
    op.drop_column('room_types', 'size_sqm')
    op.drop_column('room_types', 'image_gallery')
    op.drop_column('room_types', 'image_main')
    op.drop_column('room_types', 'amenities_json') 