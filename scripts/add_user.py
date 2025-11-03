#!/usr/bin/env python3
"""
Script to add a new user to the alert-manager system
"""
import asyncio
import sys

from core.database import init_database, close_database, get_session
from repositories.user_repository import UserRepository
from models.user import UserRole
from config.logging import configure_logging
from config import settings


async def add_user(phone: str, role: str = "admin", name: str = "User"):
    """Add a new user to the database"""
    try:
        # Configure logging
        configure_logging(settings.environment, settings.log_level)

        # Initialize database
        await init_database()

        # Create user
        async with get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(
                phone_number=phone,
                role=UserRole(role),
                full_name=name,
                is_active=True
            )

            print(f"\n[SUCCESS] User created successfully!")
            print(f"   Phone: {user.phone_number}")
            print(f"   Role: {user.role}")
            print(f"   Name: {user.full_name}")
            print(f"\nYou can now message the bot at @{settings.active_bot_username}")

        # Close database
        await close_database()

    except Exception as e:
        print(f"\n[ERROR] Failed to create user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_user.py <phone> [role] [name]")
        print("\nRoles: viewer, admin, super_admin")
        sys.exit(1)

    phone = sys.argv[1]
    role = sys.argv[2] if len(sys.argv) > 2 else "admin"
    name = sys.argv[3] if len(sys.argv) > 3 else "User"

    asyncio.run(add_user(phone, role, name))
