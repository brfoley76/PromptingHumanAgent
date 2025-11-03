#!/usr/bin/env python3
"""
Simple script to run the activity_mastery migration.
This creates the activity_mastery table and backfills data.
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.database import engine, Base
from src.database.models import ActivityMastery
from sqlalchemy import text

def run_migration():
    """Run the activity_mastery migration"""
    print("=" * 60)
    print("Running Activity Mastery Migration")
    print("=" * 60)
    
    try:
        # Create the activity_mastery table
        print("\n1. Creating activity_mastery table...")
        Base.metadata.create_all(engine, tables=[ActivityMastery.__table__])
        print("✓ Table created successfully")
        
        # Backfill data from activity_attempts
        print("\n2. Backfilling data from activity_attempts...")
        with engine.connect() as conn:
            # First, check if there's already data
            existing = conn.execute(text("SELECT COUNT(*) FROM activity_mastery")).scalar()
            if existing > 0:
                print(f"  ℹ Table already has {existing} records, skipping backfill")
                print("  (Use 'DELETE FROM activity_mastery' to clear and re-run if needed)")
                conn.commit()
            else:
                result = conn.execute(text("""
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
            """))
                conn.commit()
                print(f"✓ Backfilled {result.rowcount} mastery records")
        
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print("\nThe activity_mastery table now tracks:")
        print("  - Highest difficulty completed per activity")
        print("  - Whether hard mode was completed with 80%+")
        print("  - Unlocking now requires hard mode completion")
        print("\n")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
