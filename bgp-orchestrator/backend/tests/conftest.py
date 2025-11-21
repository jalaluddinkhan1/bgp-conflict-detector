"""
Pytest configuration and fixtures.
"""
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_application
from app.config import settings
from app.dependencies import get_db_engine


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create FastAPI application instance."""
    return create_application()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_db_url():
    """Get test database URL."""
    return "postgresql+asyncpg://test:test@localhost:5432/test_db"


@pytest_asyncio.fixture
async def db_session(test_db_url) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for testing."""
    engine = create_async_engine(test_db_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
def redis_client():
    """Create Redis client for testing."""
    import fakeredis
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def sample_bgp_update():
    """Sample BGP update data for testing."""
    return {
        "type": "announce",
        "peer_ip": "192.0.2.1",
        "peer_asn": 65001,
        "prefix": "192.0.2.0/24",
        "as_path": [65001, 65002, 65003],
        "origin": "IGP",
        "next_hop": "192.0.2.1",
        "communities": ["65001:100"],
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_conflict():
    """Sample conflict data for testing."""
    from core.conflict_detector import Conflict, ConflictType, ConflictSeverity
    
    return Conflict(
        type=ConflictType.ASN_COLLISION,
        severity=ConflictSeverity.HIGH,
        description="ASN collision detected",
        affected_peers=[1, 2],
        recommended_action="Resolve ASN collision",
        metadata={"asn": 65001},
    )


@pytest.fixture
def sample_peering():
    """Sample BGP peering data for testing."""
    return {
        "id": 1,
        "local_asn": 65000,
        "peer_asn": 65001,
        "peer_ip": "192.0.2.1",
        "local_ip": "192.0.2.2",
        "state": "established",
        "import_policy": "accept-all",
        "export_policy": "default",
    }

