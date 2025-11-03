# Backend Utility Scripts

This directory contains utility scripts for the backend application.

## Available Scripts

### run_migration.py

Database migration utility script for running Alembic migrations.

**Usage:**
```bash
python scripts/run_migration.py
```

**What it does:**
- Runs pending Alembic database migrations
- Handles migration errors gracefully
- Provides migration status feedback

### test_terminal.py

Terminal testing utility for debugging and development.

**Usage:**
```bash
python scripts/test_terminal.py
```

## SQL Scripts

### sql/reset_bob_proficiency.sql

SQL script to reset proficiency data for the test user "Bob".

**Usage:**
```bash
# Using psql
psql -d your_database -f scripts/sql/reset_bob_proficiency.sql

# Or using the database client of your choice
```

**What it does:**
- Resets proficiency scores for test user
- Useful for development and testing
- Safe to run multiple times

---

*For more information about the backend architecture, see [../README.md](../README.md)*
