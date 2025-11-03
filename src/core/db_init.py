"""
Database initialization and auto-setup utilities
Handles database creation and Alembic migrations automatically
"""
import asyncio
from typing import Optional
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import command
from alembic.config import Config

from alert_manager.config import settings
from alert_manager.config.logging import get_logger

log = get_logger(__name__)


async def check_database_exists() -> bool:
    """
    Check if the database exists

    Returns:
        True if database exists, False otherwise
    """
    try:
        # Connect to postgres database to check if our database exists
        engine = create_async_engine(
            f"postgresql+asyncpg://{settings.database_user}:{settings.database_password}@{settings.database_host}:{settings.database_port}/postgres",
            isolation_level="AUTOCOMMIT",
        )

        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    f"SELECT 1 FROM pg_database WHERE datname = '{settings.database_name}'"
                )
            )
            exists = result.scalar() is not None

        await engine.dispose()
        return exists

    except Exception as e:
        log.error("database_check_failed", error=str(e))
        return False


def create_database_sync() -> bool:
    """
    Create the database using synchronous psycopg2 (required for CREATE DATABASE)

    Returns:
        True if database was created, False otherwise
    """
    try:
        # Connect to postgres database
        conn = psycopg2.connect(
            host=settings.database_host,
            port=settings.database_port,
            user=settings.database_user,
            password=settings.database_password,
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            f"SELECT 1 FROM pg_database WHERE datname = '{settings.database_name}'"
        )
        exists = cursor.fetchone() is not None

        if not exists:
            log.info("creating_database", database=settings.database_name)
            cursor.execute(f'CREATE DATABASE "{settings.database_name}"')
            log.info("database_created", database=settings.database_name)
            created = True
        else:
            log.info("database_already_exists", database=settings.database_name)
            created = False

        cursor.close()
        conn.close()

        return created

    except psycopg2.OperationalError as e:
        log.error(
            "database_creation_failed",
            error=str(e),
            hint="Check database credentials and server connectivity",
        )
        raise
    except Exception as e:
        log.error("unexpected_database_error", error=str(e))
        raise


def run_migrations() -> None:
    """
    Run Alembic migrations to create/update tables

    This runs 'alembic upgrade head' programmatically
    """
    try:
        log.info("running_database_migrations")

        # Create Alembic config
        alembic_cfg = Config("alembic.ini")

        # Override sqlalchemy.url with current settings
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_sync_url)

        # Run migrations
        command.upgrade(alembic_cfg, "head")

        log.info("migrations_completed_successfully")

    except Exception as e:
        log.error("migration_failed", error=str(e), exc_info=True)
        raise


async def initialize_database() -> None:
    """
    Auto-initialize database from scratch if needed

    This function:
    1. Checks if database exists
    2. Creates database if it doesn't exist
    3. Runs Alembic migrations to create/update tables
    4. Handles all edge cases gracefully

    This makes the app work out of the box without manual setup
    """
    log.info(
        "initializing_database",
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database_name,
    )

    try:
        # Step 1: Check if database exists
        db_exists = await check_database_exists()

        # Step 2: Create database if it doesn't exist
        if not db_exists:
            log.warning(
                "database_not_found_creating",
                database=settings.database_name,
            )
            create_database_sync()
        else:
            log.info("database_found", database=settings.database_name)

        # Step 3: Run migrations to ensure tables exist
        log.info("ensuring_tables_exist")
        run_migrations()

        log.info(
            "database_initialization_complete",
            database=settings.database_name,
        )

    except psycopg2.OperationalError as e:
        log.error(
            "database_connection_failed",
            error=str(e),
            host=settings.database_host,
            port=settings.database_port,
            user=settings.database_user,
        )
        raise RuntimeError(
            f"Cannot connect to PostgreSQL server at {settings.database_host}:{settings.database_port}. "
            "Please ensure PostgreSQL is running and credentials are correct."
        )
    except Exception as e:
        log.error("database_initialization_failed", error=str(e), exc_info=True)
        raise
