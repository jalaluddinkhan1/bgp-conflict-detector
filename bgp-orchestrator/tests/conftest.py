"""
Pytest configuration and fixtures for BGP Orchestrator tests.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.config import settings
from app.dependencies import get_db, get_redis
from app.main import app
from models.peering import Base as ModelBase
from security.auth import User, jwt_manager


# Pytest-asyncio configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """Create test database engine."""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def async_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create async database session for tests.

    Usage:
        async def test_something(async_db_session):
            result = await async_db_session.execute(select(...))
    """
    async_session_factory = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Override get_db dependency
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        yield session
        app.dependency_overrides.clear()


@pytest.fixture
def test_client(async_db_session) -> TestClient:
    """
    Create test client for FastAPI app.

    Usage:
        def test_endpoint(test_client):
            response = test_client.get("/api/v1/bgp-peerings/")
    """
    return TestClient(app)


@pytest.fixture
async def async_test_client(async_db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    Create async test client for FastAPI app.

    Usage:
        async def test_endpoint(async_test_client):
            response = await async_test_client.get("/api/v1/bgp-peerings/")
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_user() -> User:
    """Create test user."""
    return User(
        id="test-user-id",
        email="test@example.com",
        roles=[],
        is_active=True,
    )


@pytest.fixture
def test_user_token(test_user) -> str:
    """
    Create JWT token for test user.

    Usage:
        def test_protected_endpoint(test_client, test_user_token):
            response = test_client.get(
                "/api/v1/bgp-peerings/",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
    """
    token_pair = jwt_manager.create_token_pair(
        user_id=test_user.id,
        email=test_user.email,
        roles=["admin", "operator"],
    )
    return token_pair.access_token


@pytest.fixture
def admin_user_token(test_user) -> str:
    """Create JWT token for admin user."""
    token_pair = jwt_manager.create_token_pair(
        user_id=test_user.id,
        email=test_user.email,
        roles=["admin"],
    )
    return token_pair.access_token


@pytest.fixture
async def mock_redis():
    """Create mock Redis client."""
    from fakeredis import FakeRedis

    redis_client = FakeRedis(decode_responses=True)

    # Override get_redis dependency
    def override_get_redis():
        return redis_client

    app.dependency_overrides[get_redis] = override_get_redis
    yield redis_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_batfish_client():
    """Create mock Batfish client."""
    from unittest.mock import AsyncMock, MagicMock
    from services.batfish_client import BatfishClient, ValidationResult

    mock_client = MagicMock(spec=BatfishClient)
    mock_client.validate_bgp_config = AsyncMock(
        return_value=ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            issues=[],
            loops=[],
            summary="Validation passed",
        )
    )
    mock_client.check_session_compatibility = AsyncMock(return_value=[])
    mock_client.detect_routing_loops = AsyncMock(return_value=[])
    mock_client._ensure_running = AsyncMock(return_value=None)

    return mock_client


@pytest.fixture
def mock_ripe_ris_client():
    """Create mock RIPE RIS client."""
    from unittest.mock import AsyncMock, MagicMock
    from services.ripe_ris_client import RIPEClient

    mock_client = MagicMock(spec=RIPEClient)
    mock_client.validate_prefix_origin = AsyncMock(return_value=True)
    mock_client.get_historical_data = AsyncMock(return_value=[])
    mock_client.get_live_updates = AsyncMock()

    return mock_client


@pytest.fixture
def mock_suzieq_client():
    """Create mock SuzieQ client."""
    from unittest.mock import AsyncMock, MagicMock
    from services.suzieq_client import SuzieQClient

    mock_client = MagicMock(spec=SuzieQClient)
    mock_client.poll_bgp_sessions = AsyncMock(return_value=[])
    mock_client.get_device_inventory = AsyncMock(return_value=[])

    return mock_client


@pytest.fixture
def sample_bgp_peering_data():
    """Sample BGP peering data for tests."""
    return {
        "name": "test-peering-1",
        "local_asn": 65000,
        "peer_asn": 65001,
        "peer_ip": "10.0.0.1",
        "hold_time": 180,
        "keepalive": 60,
        "device": "router01",
        "interface": "eth0",
        "status": "pending",
        "address_families": ["ipv4"],
        "routing_policy": {},
    }


@pytest.fixture(autouse=True)
async def cleanup_database(async_db_session):
    """Clean up database after each test."""
    yield
    # Clean up all tables
    async with async_db_session.begin():
        for table in reversed(ModelBase.metadata.sorted_tables):
            await async_db_session.execute(table.delete())


@pytest.fixture
def event_loop_policy():
    """Set event loop policy for asyncio tests."""
    policy = asyncio.get_event_loop_policy()
    return policy

