"""Pytest configuration and fixtures."""

import os
import pytest
from decimal import Decimal
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rbac import UserRole
from app.core.security import get_password_hash, create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
# Import all models to ensure they're registered with Base.metadata
from app.models import *
from app.models.user import User
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.location import Location

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Disable rate limiters during tests to avoid flaky failures
    from app.core.rate_limit import limiter as global_limiter
    from app.api.routes.auth import limiter as auth_limiter
    global_limiter.enabled = False
    auth_limiter.enabled = False
    # Don't raise server exceptions so we can test error status codes
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    global_limiter.enabled = True
    auth_limiter.enabled = True
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.OWNER,
        name="Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    """Get an authentication token for the test user."""
    return create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email, "role": test_user.role.value}
    )


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Get authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def test_supplier(db_session: Session) -> Supplier:
    """Create a test supplier."""
    supplier = Supplier(
        name="Test Supplier",
        contact_phone="+1234567890",
        contact_email="supplier@example.com",
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier


@pytest.fixture
def test_location(db_session: Session) -> Location:
    """Create a test location."""
    location = Location(
        name="Main Bar",
        description="Main bar location",
        is_default=True,
        active=True,
    )
    db_session.add(location)
    db_session.commit()
    db_session.refresh(location)
    return location


@pytest.fixture
def test_product(db_session: Session, test_supplier: Supplier) -> Product:
    """Create a test product."""
    product = Product(
        name="Test Beer",
        barcode="1234567890123",
        supplier_id=test_supplier.id,
        pack_size=24,
        unit="pcs",
        min_stock=Decimal("10"),
        target_stock=Decimal("50"),
        lead_time_days=3,
        cost_price=Decimal("1.50"),
        active=True,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product
