"""
Unit tests for health checker
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from monitoring.health_checker import HealthChecker, HealthCheckResult
from models.service import Service


@pytest.fixture
def health_checker():
    """Create health checker instance"""
    return HealthChecker()


@pytest.fixture
def sample_service():
    """Create sample service for testing"""
    service = Mock(spec=Service)
    service.id = 1
    service.name = "test-service"
    service.endpoint_url = "https://example.com/health"
    service.expected_status_code = 200
    service.timeout_seconds = 10
    service.max_retries = 3
    service.retry_delay_seconds = 1  # Short delay for tests
    return service


@pytest.mark.asyncio
async def test_successful_health_check(health_checker, sample_service):
    """Test successful health check on first attempt"""
    with patch("httpx.AsyncClient") as mock_client:
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200

        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # Perform check
        result = await health_checker._perform_health_check(sample_service)

        # Assertions
        assert result.success is True
        assert result.status_code == 200
        assert result.response_time_ms is not None
        assert result.response_time_ms > 0
        assert result.error_message is None


@pytest.mark.asyncio
async def test_health_check_timeout(health_checker, sample_service):
    """Test health check timeout"""
    with patch("httpx.AsyncClient") as mock_client:
        import httpx

        # Mock timeout
        mock_get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # Perform check
        result = await health_checker._perform_health_check(sample_service)

        # Assertions
        assert result.success is False
        assert result.error_message is not None
        assert "Timeout" in result.error_message


@pytest.mark.asyncio
async def test_health_check_unexpected_status(health_checker, sample_service):
    """Test health check with unexpected status code"""
    with patch("httpx.AsyncClient") as mock_client:
        # Mock unexpected status code
        mock_response = Mock()
        mock_response.status_code = 500

        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # Perform check
        result = await health_checker._perform_health_check(sample_service)

        # Assertions
        assert result.success is False
        assert result.status_code == 500
        assert "Unexpected status code" in result.error_message


@pytest.mark.asyncio
async def test_health_check_with_retries(health_checker, sample_service):
    """Test health check retry logic"""
    with patch("httpx.AsyncClient") as mock_client:
        # Mock: fail twice, then succeed
        call_count = [0]

        async def mock_get(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                import httpx

                raise httpx.ConnectError("Connection failed")
            else:
                mock_response = Mock()
                mock_response.status_code = 200
                return mock_response

        mock_client.return_value.__aenter__.return_value.get = mock_get

        with patch.object(health_checker, "_store_health_check", new=AsyncMock()):
            # Perform check with retries
            result = await health_checker.check_service(sample_service)

            # Assertions
            assert result.success is True
            assert call_count[0] == 3  # Should have tried 3 times
