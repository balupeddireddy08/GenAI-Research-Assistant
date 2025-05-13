# Database Rollback Functionality

This document describes the database rollback functionality of the GenAI Research Assistant application.

## Overview

The GenAI Research Assistant uses PostgreSQL as its primary database but includes a rollback feature that creates an SQLite database in the system's temporary directory if PostgreSQL is unavailable. This ensures that the application can continue to operate even when the primary database is down.

## How It Works

1. **Database Connection Check**: On application startup, the system checks if PostgreSQL is available.
2. **Automatic Fallback**: If PostgreSQL is unavailable, the system automatically creates an SQLite database in the system's temporary directory.
3. **Seamless Integration**: All database operations use the same SQLAlchemy models and APIs, regardless of whether PostgreSQL or SQLite is being used.
4. **Data Transfer**: When PostgreSQL becomes available again, you can transfer data from the SQLite database back to PostgreSQL.

## Directory Structure

The SQLite database is stored in a temporary directory specific to the application:

```
{temp_dir}/genai_research_assistant/research_assistant.db
```

Where `{temp_dir}` is the system's temporary directory, which can be determined by:
- Windows: Typically `C:\Users\{username}\AppData\Local\Temp`
- Linux/macOS: Typically `/tmp`

## Available Scripts

### Initializing the Database

```bash
python -m app.scripts.init_db
```

This script checks if PostgreSQL is available and sets up the appropriate database.

### Transferring Data between Databases

```bash
# Transfer from PostgreSQL to SQLite
python -m app.scripts.transfer_data --direction pg_to_sqlite

# Transfer from SQLite to PostgreSQL
python -m app.scripts.transfer_data --direction sqlite_to_pg
```

These commands allow you to transfer data between the PostgreSQL and SQLite databases.

## Implementation Details

The rollback functionality is implemented through several key components:

1. **db_fallback.py**: Provides utility functions for checking database availability and setting up fallbacks.
2. **database.py**: Modified to use the fallback utilities and handle database connections.
3. **init_db.py**: Script for initializing the database with rollback support.
4. **transfer_data.py**: Script for transferring data between PostgreSQL and SQLite.

## PostgreSQL to SQLite Compatibility

Note that while most functionality works the same between PostgreSQL and SQLite, there are some differences:

1. **JSON Support**: PostgreSQL has native JSON/JSONB types, while SQLite stores these as TEXT.
2. **Concurrent Access**: SQLite has limitations for concurrent writes compared to PostgreSQL.
3. **Performance**: PostgreSQL generally offers better performance for larger datasets and concurrent access.

Despite these differences, the application is designed to work correctly with either database backend.

## Limitations

1. The SQLite fallback is intended for temporary use when PostgreSQL is unavailable.
2. Some advanced PostgreSQL features (e.g., full-text search) may not be available in SQLite mode.
3. Data created during SQLite fallback mode needs to be manually transferred back to PostgreSQL when it becomes available. 