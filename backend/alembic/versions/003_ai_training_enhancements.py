"""Add AI training enhancements - augmented features, image hash, recognition logs

Revision ID: 003
Revises: 002
Create Date: 2025-01-08

Adds:
- augmented_features column to training_images
- image_hash column for duplicate detection
- image dimensions columns
- feature_version tracking
- extraction_error for debugging
- updated_at timestamp
- product_feature_cache table for faster lookups
- recognition_logs table for analytics
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to training_images table
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('training_images', schema=None) as batch_op:
        # Augmented features from data augmentation
        batch_op.add_column(
            sa.Column('augmented_features', sa.LargeBinary(), nullable=True)
        )
        # MD5 hash for duplicate detection
        batch_op.add_column(
            sa.Column('image_hash', sa.String(32), nullable=True)
        )
        # Original image dimensions
        batch_op.add_column(
            sa.Column('image_width', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('image_height', sa.Integer(), nullable=True)
        )
        # Feature extraction metadata
        batch_op.add_column(
            sa.Column('feature_version', sa.String(20), nullable=True, server_default='v2')
        )
        batch_op.add_column(
            sa.Column('extraction_error', sa.Text(), nullable=True)
        )
        # Updated timestamp
        batch_op.add_column(
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
        )
        # Create index on image_hash for duplicate lookups
        batch_op.create_index('ix_training_images_image_hash', ['image_hash'])

    # Create product_feature_cache table
    op.create_table(
        'product_feature_cache',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('aggregated_features', sa.LargeBinary(), nullable=True),
        sa.Column('image_count', sa.Integer(), default=0, nullable=False),
        sa.Column('feature_version', sa.String(20), nullable=True, server_default='v2'),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create recognition_logs table for analytics
    op.create_table(
        'recognition_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        # Result
        sa.Column('matched_product_id', sa.Integer(), nullable=True, index=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('is_match', sa.Boolean(), default=False, nullable=False),
        # Metadata
        sa.Column('inference_time_ms', sa.Float(), nullable=True),
        sa.Column('top_5_results', sa.Text(), nullable=True),
        # Request info
        sa.Column('image_hash', sa.String(32), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        # User feedback
        sa.Column('user_confirmed', sa.Boolean(), nullable=True),
        sa.Column('user_correction_id', sa.Integer(), nullable=True),
        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes for recognition_logs queries
    op.create_index('ix_recognition_logs_created_at', 'recognition_logs', ['created_at'])
    op.create_index('ix_recognition_logs_source', 'recognition_logs', ['source'])


def downgrade() -> None:
    # Drop recognition_logs table
    op.drop_index('ix_recognition_logs_source', table_name='recognition_logs')
    op.drop_index('ix_recognition_logs_created_at', table_name='recognition_logs')
    op.drop_table('recognition_logs')

    # Drop product_feature_cache table
    op.drop_table('product_feature_cache')

    # Remove new columns from training_images
    with op.batch_alter_table('training_images', schema=None) as batch_op:
        batch_op.drop_index('ix_training_images_image_hash')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('extraction_error')
        batch_op.drop_column('feature_version')
        batch_op.drop_column('image_height')
        batch_op.drop_column('image_width')
        batch_op.drop_column('image_hash')
        batch_op.drop_column('augmented_features')
