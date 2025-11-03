"""Add activity_mastery table for hard mode tracking

Revision ID: 003_add_activity_mastery
Revises: 002_add_bayesian_proficiency
Create Date: 2025-11-02 12:23:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '003_add_activity_mastery'
down_revision = '002_add_bayesian_proficiency'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add activity_mastery table to track highest difficulty completed per activity.
    This enforces hard-mode completion before unlocking next activity.
    """
    # Create activity_mastery table
    op.create_table(
        'activity_mastery',
        sa.Column('mastery_id', sa.String(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('module_id', sa.String(), nullable=False),
        sa.Column('activity_type', sa.String(), nullable=False),
        sa.Column('highest_difficulty', sa.String(), nullable=False),
        sa.Column('highest_difficulty_score', sa.Float(), nullable=False),
        sa.Column('highest_difficulty_date', sa.DateTime(), nullable=False),
        sa.Column('completed_hard_mode', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
        sa.PrimaryKeyConstraint('mastery_id'),
        sa.ForeignKeyConstraint(['student_id'], ['students.student_id'])
    )
    
    # Create indexes for efficient queries
    op.create_index('idx_student_activity', 'activity_mastery', ['student_id'])
    op.create_index('idx_module_activity', 'activity_mastery', ['module_id'])
    op.create_index('idx_activity_type', 'activity_mastery', ['activity_type'])
    op.create_index(
        'idx_student_module_activity', 
        'activity_mastery', 
        ['student_id', 'module_id', 'activity_type'],
        unique=True
    )
    
    # Backfill data from existing activity_attempts
    # This finds the highest difficulty completed for each student/module/activity combination
    op.execute("""
        INSERT INTO activity_mastery (
            mastery_id,
            student_id,
            module_id,
            activity_type,
            highest_difficulty,
            highest_difficulty_score,
            highest_difficulty_date,
            completed_hard_mode,
            created_at,
            updated_at
        )
        SELECT 
            lower(hex(randomblob(16))) as mastery_id,
            student_id,
            module as module_id,
            activity as activity_type,
            difficulty as highest_difficulty,
            CAST(score AS FLOAT) / CAST(total AS FLOAT) * 100 as highest_difficulty_score,
            date as highest_difficulty_date,
            CASE 
                WHEN (activity = 'multiple_choice' AND difficulty = '5' AND CAST(score AS FLOAT) / CAST(total AS FLOAT) >= 0.80)
                  OR (activity = 'fill_in_the_blank' AND difficulty = 'moderate' AND CAST(score AS FLOAT) / CAST(total AS FLOAT) >= 0.80)
                  OR (activity NOT IN ('multiple_choice', 'fill_in_the_blank') AND difficulty = 'hard' AND CAST(score AS FLOAT) / CAST(total AS FLOAT) >= 0.80)
                THEN 1
                ELSE 0
            END as completed_hard_mode,
            datetime('now') as created_at,
            datetime('now') as updated_at
        FROM (
            SELECT 
                student_id,
                module,
                activity,
                difficulty,
                score,
                total,
                date,
                ROW_NUMBER() OVER (
                    PARTITION BY student_id, module, activity 
                    ORDER BY 
                        CASE 
                            WHEN activity = 'multiple_choice' THEN CAST(difficulty AS INTEGER)
                            WHEN difficulty = 'hard' THEN 3
                            WHEN difficulty = 'moderate' OR difficulty = 'medium' THEN 2
                            ELSE 1
                        END DESC,
                        CAST(score AS FLOAT) / CAST(total AS FLOAT) DESC,
                        date DESC
                ) as rn
            FROM activity_attempts
            WHERE total > 0
        ) ranked
        WHERE rn = 1
    """)


def downgrade():
    """Remove activity_mastery table"""
    op.drop_index('idx_student_module_activity', table_name='activity_mastery')
    op.drop_index('idx_activity_type', table_name='activity_mastery')
    op.drop_index('idx_module_activity', table_name='activity_mastery')
    op.drop_index('idx_student_activity', table_name='activity_mastery')
    op.drop_table('activity_mastery')
