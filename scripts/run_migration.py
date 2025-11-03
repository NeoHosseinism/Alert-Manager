#!/usr/bin/env python3
"""
Script to run SQL migration for adding name columns
"""
import asyncio
import sys

from sqlalchemy import text
from core.database import init_database, close_database, get_session
from config.logging import configure_logging
from config import settings


async def run_migration():
    """Run the migration to add first_name and last_name columns"""
    try:
        configure_logging(settings.environment, settings.log_level)
        await init_database()

        async with get_session() as session:
            # Add first_name column
            await session.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(255)")
            )

            # Add last_name column
            await session.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(255)")
            )

            await session.commit()

        print("\n[SUCCESS] Migration completed!")
        print("   - Added first_name column to users table")
        print("   - Added last_name column to users table")
        print("\nYou can now restart the bot with: make dev\n")

        await close_database()
        return 0

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    exit_code = asyncio.run(run_migration())
    sys.exit(exit_code)
