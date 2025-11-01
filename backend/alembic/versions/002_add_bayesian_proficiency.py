"""Add Bayesian proficiency tracking

Revision ID: 002
Revises: 001
Create Date: 2025-10-31 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Add student_proficiencies table for Bayesian tracking"""
    op.create_table(
        'student_proficiencies',
        sa.Column('proficiency_id', sa.String(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('level', sa.String(), nullable=False),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('module_id', sa.String(), nullable=True),
        sa.Column('item_id', sa.String(), nullable=True),
        sa.Column('alpha', sa.Float(), nullable=False, server_default='2.0'),
        sa.Column('beta', sa.Float(), nullable=False, server_default='2.0'),
        sa.Column('mean_ability', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('learning_rate', sa.Float(), nullable=False, server_default='0.1'),
        sa.Column('forgetting_rate', sa.Float(), nullable=False, server_default='0.05'),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('proficiency_id'),
        sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], )
    )
    
    # Create indexes for efficient queries
    op.create_index(
        'idx_student_level_module',
        'student_proficiencies',
        ['student_id', 'level', 'module_id']
    )
    
    op.create_index(
        'idx_student_module_item',
        'student_proficiencies',
        ['student_id', 'module_id', 'item_id']
    )
    
    op.create_index(
        'idx_proficiency_student_id',
        'student_proficiencies',
        ['student_id']
    )
    
    op.create_index(
        'idx_proficiency_level',
        'student_proficiencies',
        ['level']
    )
    
    op.create_index(
        'idx_proficiency_module_id',
        'student_proficiencies',
        ['module_id']
    )
    
    op.create_index(
        'idx_proficiency_item_id',
        'student_proficiencies',
        ['item_id']
    )


def downgrade():
    """Remove student_proficiencies table"""
    op.drop_index('idx_proficiency_item_id', table_name='student_proficiencies')
    op.drop_index('idx_proficiency_module_id', table_name='student_proficiencies')
    op.drop_index('idx_proficiency_level', table_name='student_proficiencies')
    op.drop_index('idx_proficiency_student_id', table_name='student_proficiencies')
    op.drop_index('idx_student_module_item', table_name='student_proficiencies')
    op.drop_index('idx_student_level_module', table_name='student_proficiencies')
    op.drop_table('student_proficiencies')
