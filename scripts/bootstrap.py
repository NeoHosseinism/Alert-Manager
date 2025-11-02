"""
Bootstrap script to initialize database with sample data
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monitoring_system.config import settings
from monitoring_system.config.logging import configure_logging, get_logger
from monitoring_system.core.database import init_database, get_session
from monitoring_system.core.encryption import encrypt_api_key
from monitoring_system.repositories.user_repository import UserRepository
from monitoring_system.repositories.service_repository import ServiceRepository
from monitoring_system.models.user import UserRole

configure_logging(settings.environment, settings.log_level)
log = get_logger(__name__)


async def bootstrap():
    """Bootstrap database with initial data"""
    log.info("starting_bootstrap", environment=settings.environment)

    try:
        # Initialize database
        await init_database()
        log.info("database_initialized")

        async with get_session() as session:
            user_repo = UserRepository(session)
            service_repo = ServiceRepository(session)

            # Create super admin user
            admin_phone = "+989123456789"
            existing_admin = await user_repo.get_by_phone(admin_phone)

            if not existing_admin:
                admin = await user_repo.create(
                    phone_number=admin_phone,
                    role=UserRole.SUPER_ADMIN.value,
                    is_active=True,
                )
                log.info("created_super_admin", phone=admin_phone)
            else:
                log.info("super_admin_exists", phone=admin_phone)

            # Create sample viewer user
            viewer_phone = "+989987654321"
            existing_viewer = await user_repo.get_by_phone(viewer_phone)

            if not existing_viewer:
                viewer = await user_repo.create(
                    phone_number=viewer_phone,
                    role=UserRole.VIEWER.value,
                    is_active=True,
                )
                log.info("created_viewer", phone=viewer_phone)
            else:
                log.info("viewer_exists", phone=viewer_phone)

            # Create sample health check service
            service_name = "example-api"
            existing_service = await service_repo.get_by_name(service_name, settings.environment)

            if not existing_service:
                health_service = await service_repo.create(
                    name=service_name,
                    service_type="health_check",
                    endpoint_url="https://httpbin.org/status/200",
                    expected_status_code=200,
                    timeout_seconds=10,
                    check_interval_seconds=300,
                    max_retries=3,
                    retry_delay_seconds=30,
                    is_active=True,
                    environment=settings.environment,
                    metadata={"description": "Example health check service"},
                )
                log.info("created_health_check_service", name=service_name)
            else:
                log.info("service_exists", name=service_name)

            # Create sample API credit service (with placeholder key)
            credit_service_name = "openrouter-credits"
            existing_credit = await service_repo.get_by_name(
                credit_service_name, settings.environment
            )

            if not existing_credit:
                # Note: This is a placeholder. Users need to set real API key via /edit_service
                placeholder_key = encrypt_api_key("placeholder-api-key-replace-me")

                credit_service = await service_repo.create(
                    name=credit_service_name,
                    service_type="api_credit",
                    api_provider="openrouter",
                    api_key_encrypted=placeholder_key,
                    credit_threshold=20.00,
                    credit_check_interval_hours=24,
                    check_interval_seconds=86400,
                    is_active=False,  # Disabled until real key is set
                    environment=settings.environment,
                    metadata={"description": "OpenRouter API credit monitoring"},
                )
                log.info("created_credit_service", name=credit_service_name)
            else:
                log.info("credit_service_exists", name=credit_service_name)

            await session.commit()

        log.info(
            "bootstrap_complete",
            message="Database initialized with sample data. "
            "Update API keys and activate services as needed.",
        )

        print("\n" + "=" * 60)
        print("Bootstrap Complete!")
        print("=" * 60)
        print(f"\nSuper Admin: {admin_phone}")
        print(f"Viewer: {viewer_phone}")
        print(f"\nServices created:")
        print(f"  - {service_name} (health_check, active)")
        print(f"  - {credit_service_name} (api_credit, inactive)")
        print(f"\nNext steps:")
        print(f"1. Link your Telegram account to one of the phone numbers")
        print(f"2. Message your Telegram bot with /start")
        print(f"3. Configure API keys for credit monitoring")
        print("=" * 60 + "\n")

    except Exception as e:
        log.error("bootstrap_failed", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(bootstrap())
