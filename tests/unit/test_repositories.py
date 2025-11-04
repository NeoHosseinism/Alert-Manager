"""
Tests for repository layer (database access)
"""
import pytest
from datetime import datetime
from repositories.user_repository import UserRepository
from repositories.service_repository import ServiceRepository
from repositories.alert_repository import AlertRepository
from models.user import User
from models.service import Service
from models.alert import Alert, AlertSeverity, AlertStatus


class TestUserRepository:
    """Test UserRepository"""

    @pytest.fixture
    async def user_repo(self, test_session):
        """Create user repository"""
        return UserRepository(test_session)

    @pytest.mark.asyncio
    async def test_create_user(self, user_repo, sample_user_data):
        """Test creating a new user"""
        user = await user_repo.create(**sample_user_data)

        assert user.id is not None
        assert user.phone_number == sample_user_data["phone_number"]
        assert user.role == sample_user_data["role"]
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_repo, sample_user_data):
        """Test retrieving user by ID"""
        created_user = await user_repo.create(**sample_user_data)
        retrieved_user = await user_repo.get_by_id(created_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.phone_number == created_user.phone_number

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id(self, user_repo, sample_user_data):
        """Test retrieving user by Telegram ID"""
        created_user = await user_repo.create(**sample_user_data)
        retrieved_user = await user_repo.get_by_telegram_id(
            sample_user_data["telegram_user_id"]
        )

        assert retrieved_user is not None
        assert retrieved_user.telegram_user_id == sample_user_data["telegram_user_id"]

    @pytest.mark.asyncio
    async def test_get_user_by_phone(self, user_repo, sample_user_data):
        """Test retrieving user by phone number"""
        created_user = await user_repo.create(**sample_user_data)
        retrieved_user = await user_repo.get_by_phone(sample_user_data["phone_number"])

        assert retrieved_user is not None
        assert retrieved_user.phone_number == sample_user_data["phone_number"]

    @pytest.mark.asyncio
    async def test_update_user(self, user_repo, sample_user_data):
        """Test updating user"""
        user = await user_repo.create(**sample_user_data)

        updated = await user_repo.update(user.id, role="admin")

        assert updated.role == "admin"
        assert updated.phone_number == sample_user_data["phone_number"]

    @pytest.mark.asyncio
    async def test_list_active_users(self, user_repo, sample_user_data):
        """Test listing active users"""
        # Create active user
        await user_repo.create(**sample_user_data)

        # Create inactive user
        inactive_data = sample_user_data.copy()
        inactive_data["phone_number"] = "+989123456790"
        inactive_data["telegram_user_id"] = 987654321
        inactive_data["is_active"] = False
        await user_repo.create(**inactive_data)

        # List active users
        active_users = await user_repo.list_active()

        assert len(active_users) == 1
        assert active_users[0].is_active is True

    @pytest.mark.asyncio
    async def test_delete_user(self, user_repo, sample_user_data):
        """Test deleting user"""
        user = await user_repo.create(**sample_user_data)

        await user_repo.delete(user.id)

        deleted_user = await user_repo.get_by_id(user.id)
        assert deleted_user is None


class TestServiceRepository:
    """Test ServiceRepository"""

    @pytest.fixture
    async def service_repo(self, test_session):
        """Create service repository"""
        return ServiceRepository(test_session)

    @pytest.fixture
    async def test_user(self, test_session, sample_user_data):
        """Create a test user for services"""
        user_repo = UserRepository(test_session)
        return await user_repo.create(**sample_user_data)

    @pytest.mark.asyncio
    async def test_create_service(self, service_repo, test_user, sample_service_data):
        """Test creating a new service"""
        sample_service_data["user_id"] = test_user.id

        service = await service_repo.create(**sample_service_data)

        assert service.id is not None
        assert service.name == sample_service_data["name"]
        assert service.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_get_service_by_id(self, service_repo, test_user, sample_service_data):
        """Test retrieving service by ID"""
        sample_service_data["user_id"] = test_user.id
        created = await service_repo.create(**sample_service_data)

        retrieved = await service_repo.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    @pytest.mark.asyncio
    async def test_list_user_services(self, service_repo, test_user, sample_service_data):
        """Test listing services for a user"""
        sample_service_data["user_id"] = test_user.id

        # Create multiple services
        await service_repo.create(**sample_service_data)
        sample_service_data["name"] = "test-service-2"
        await service_repo.create(**sample_service_data)

        services = await service_repo.list_by_user(test_user.id)

        assert len(services) == 2

    @pytest.mark.asyncio
    async def test_list_active_services(self, service_repo, test_user, sample_service_data):
        """Test listing only active services"""
        sample_service_data["user_id"] = test_user.id

        # Create active service
        await service_repo.create(**sample_service_data)

        # Create inactive service
        sample_service_data["name"] = "inactive-service"
        sample_service_data["is_active"] = False
        await service_repo.create(**sample_service_data)

        active_services = await service_repo.list_active()

        assert len(active_services) == 1
        assert active_services[0].is_active is True

    @pytest.mark.asyncio
    async def test_update_service(self, service_repo, test_user, sample_service_data):
        """Test updating service"""
        sample_service_data["user_id"] = test_user.id
        service = await service_repo.create(**sample_service_data)

        updated = await service_repo.update(
            service.id,
            timeout_seconds=30,
            check_interval_seconds=600
        )

        assert updated.timeout_seconds == 30
        assert updated.check_interval_seconds == 600


class TestAlertRepository:
    """Test AlertRepository"""

    @pytest.fixture
    async def alert_repo(self, test_session):
        """Create alert repository"""
        return AlertRepository(test_session)

    @pytest.fixture
    async def test_service(self, test_session, test_user, sample_service_data):
        """Create a test service for alerts"""
        service_repo = ServiceRepository(test_session)
        sample_service_data["user_id"] = test_user.id
        return await service_repo.create(**sample_service_data)

    @pytest.fixture
    async def test_user(self, test_session, sample_user_data):
        """Create a test user"""
        user_repo = UserRepository(test_session)
        return await user_repo.create(**sample_user_data)

    @pytest.mark.asyncio
    async def test_create_alert(self, alert_repo, test_service):
        """Test creating an alert"""
        alert_data = {
            "service_id": test_service.id,
            "severity": AlertSeverity.WARNING,
            "message": "High response time detected",
            "details": {"response_time_ms": 5000},
        }

        alert = await alert_repo.create(**alert_data)

        assert alert.id is not None
        assert alert.service_id == test_service.id
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_alert_by_id(self, alert_repo, test_service):
        """Test retrieving alert by ID"""
        alert_data = {
            "service_id": test_service.id,
            "severity": AlertSeverity.CRITICAL,
            "message": "Service down",
        }

        created = await alert_repo.create(**alert_data)
        retrieved = await alert_repo.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.severity == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_list_pending_alerts(self, alert_repo, test_service):
        """Test listing pending alerts"""
        # Create pending alert
        await alert_repo.create(
            service_id=test_service.id,
            severity=AlertSeverity.WARNING,
            message="Pending alert"
        )

        # Create resolved alert
        resolved = await alert_repo.create(
            service_id=test_service.id,
            severity=AlertSeverity.INFO,
            message="Resolved alert"
        )
        await alert_repo.update(resolved.id, status=AlertStatus.RESOLVED)

        pending = await alert_repo.list_pending()

        assert len(pending) == 1
        assert pending[0].status == AlertStatus.PENDING

    @pytest.mark.asyncio
    async def test_resolve_alert(self, alert_repo, test_service):
        """Test resolving an alert"""
        alert = await alert_repo.create(
            service_id=test_service.id,
            severity=AlertSeverity.CRITICAL,
            message="Critical issue"
        )

        resolved = await alert_repo.resolve(alert.id)

        assert resolved.status == AlertStatus.RESOLVED
        assert resolved.resolved_at is not None

    @pytest.mark.asyncio
    async def test_list_alerts_by_service(self, alert_repo, test_service):
        """Test listing alerts for a specific service"""
        # Create multiple alerts
        for i in range(3):
            await alert_repo.create(
                service_id=test_service.id,
                severity=AlertSeverity.INFO,
                message=f"Alert {i}"
            )

        alerts = await alert_repo.list_by_service(test_service.id)

        assert len(alerts) == 3
        assert all(a.service_id == test_service.id for a in alerts)
