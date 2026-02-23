"""
Multi-Tenant Administration API Routes
Manages tenant provisioning, configuration, and usage.
"""
from fastapi import APIRouter, Query, Request
from app.db.session import DbSession
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
def get_all_tenants(request: Request, db: DbSession):
    """List all tenants."""
    from app.services.multi_tenant_service import MultiTenantService
    return MultiTenantService.get_all_tenants(db)


@router.post("/")
@limiter.limit("30/minute")
def create_tenant(request: Request, db: DbSession, data: dict = {}):
    """Provision a new tenant."""
    from app.services.multi_tenant_service import MultiTenantService
    return MultiTenantService.create_tenant(db, data)


@router.get("/{tenant_id}")
@limiter.limit("60/minute")
def get_tenant_details(request: Request, db: DbSession, tenant_id: int):
    """Get tenant details."""
    from app.services.multi_tenant_service import MultiTenantService
    return MultiTenantService.get_tenant_config(db, tenant_id)


@router.put("/{tenant_id}/suspend")
@limiter.limit("30/minute")
def suspend_tenant(request: Request, db: DbSession, tenant_id: int, data: dict = {}):
    """Suspend a tenant."""
    from app.services.multi_tenant_service import MultiTenantService
    return MultiTenantService.suspend_tenant(db, tenant_id, data.get("reason", ""))


@router.get("/{tenant_id}/usage")
@limiter.limit("60/minute")
def get_tenant_usage(request: Request, db: DbSession, tenant_id: int):
    """Get tenant resource usage."""
    from app.services.multi_tenant_service import MultiTenantService
    return MultiTenantService.get_tenant_usage(db, tenant_id)
