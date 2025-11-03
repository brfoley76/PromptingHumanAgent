-- Reset Bob's proficiency data to use new Beta(1,1) prior
-- This clears corrupted old data and allows fresh learning with the new system

UPDATE student_proficiencies
SET 
    alpha = 1.0,
    beta = 1.0,
    mean_ability = 0.5,
    confidence = 0.0,
    sample_count = 0,
    last_updated = CURRENT_TIMESTAMP
WHERE student_id = '140d959c-19a4-4d5d-81af-701a279b8aaf';

-- Verify the reset
SELECT 
    level,
    COALESCE(item_id, module_id, domain) as identifier,
    alpha,
    beta,
    mean_ability,
    sample_count
FROM student_proficiencies
WHERE student_id = '140d959c-19a4-4d5d-81af-701a279b8aaf'
ORDER BY level, identifier;
