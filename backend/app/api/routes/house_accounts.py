"""
House Accounts API Endpoints
Corporate account management for restaurants
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.services.house_account_service import HouseAccountService


router = APIRouter()


# ========== SCHEMAS ==========

class CreateAccountRequest(BaseModel):
    account_name: str
    account_type: str = "corporate"
    contact_name: str
    contact_email: str
    contact_phone: str
    billing_address: str
    credit_limit: float = 5000.0
    payment_terms: str = "net_30"
    discount_percentage: float = 0.0
    tax_id: Optional[str] = None
    notes: Optional[str] = None
    authorized_users: Optional[List[dict]] = None


class ChargeToAccountRequest(BaseModel):
    order_id: int
    amount: float
    description: str
    authorized_by: str
    signature: Optional[str] = None
    table_id: Optional[int] = None


class RecordPaymentRequest(BaseModel):
    amount: float
    payment_method: str
    reference: Optional[str] = None
    notes: Optional[str] = None


class AddAuthorizedUserRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    spending_limit: Optional[float] = None


class SuspendAccountRequest(BaseModel):
    reason: str


# ========== ENDPOINTS ==========

@router.post("/")
async def create_house_account(
    request: CreateAccountRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new house account for a company/VIP
    
    - **account_name**: Company or VIP name
    - **credit_limit**: Maximum credit allowed
    - **payment_terms**: net_7, net_15, net_30, net_45, on_demand
    - **discount_percentage**: Automatic discount for this account
    """
    service = HouseAccountService(db)
    
    result = service.create_account(
        venue_id=1,  # Would come from current_user
        account_name=request.account_name,
        account_type=request.account_type,
        contact_name=request.contact_name,
        contact_email=request.contact_email,
        contact_phone=request.contact_phone,
        billing_address=request.billing_address,
        credit_limit=request.credit_limit,
        payment_terms=request.payment_terms,
        discount_percentage=request.discount_percentage,
        tax_id=request.tax_id,
        notes=request.notes,
        authorized_users=request.authorized_users,
        created_by=current_user.id if current_user else None
    )
    
    return result


@router.post("/{account_id}/charge")
async def charge_to_account(
    account_id: str,
    request: ChargeToAccountRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Charge an order to a house account
    
    - **order_id**: Order being charged
    - **amount**: Total amount
    - **authorized_by**: Name of person authorizing
    """
    service = HouseAccountService(db)
    
    result = service.charge_to_account(
        account_id=account_id,
        order_id=request.order_id,
        amount=request.amount,
        description=request.description,
        authorized_by=request.authorized_by,
        staff_id=current_user.id if current_user else None,
        signature=request.signature,
        table_id=request.table_id
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to charge account")
        )
    
    return result


@router.post("/{account_id}/payment")
async def record_payment(
    account_id: str,
    request: RecordPaymentRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Record a payment received on a house account
    
    - **amount**: Payment amount
    - **payment_method**: check, bank_transfer, card, cash
    - **reference**: Check number, transfer reference, etc.
    """
    service = HouseAccountService(db)
    
    result = service.record_payment(
        account_id=account_id,
        amount=request.amount,
        payment_method=request.payment_method,
        reference=request.reference,
        notes=request.notes,
        staff_id=current_user.id if current_user else None
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to record payment")
        )
    
    return result


@router.get("/{account_id}/statement")
async def get_statement(
    account_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Generate an account statement"""
    service = HouseAccountService(db)
    result = service.generate_statement(account_id, start_date, end_date)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Account not found")
        )
    
    return result


@router.get("/aging-report")
async def get_aging_report(
    db: Session = Depends(get_db)
):
    """Get accounts receivable aging report"""
    service = HouseAccountService(db)
    return service.get_aging_report(venue_id=1)


@router.post("/{account_id}/authorized-users")
async def add_authorized_user(
    account_id: str,
    request: AddAuthorizedUserRequest,
    db: Session = Depends(get_db)
):
    """Add an authorized user to a house account"""
    service = HouseAccountService(db)
    
    result = service.add_authorized_user(
        account_id=account_id,
        name=request.name,
        email=request.email,
        phone=request.phone,
        spending_limit=request.spending_limit
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to add user")
        )
    
    return result


@router.post("/{account_id}/suspend")
async def suspend_account(
    account_id: str,
    request: SuspendAccountRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Suspend a house account"""
    service = HouseAccountService(db)
    
    result = service.suspend_account(
        account_id=account_id,
        reason=request.reason,
        staff_id=current_user.id if current_user else None
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to suspend account")
        )
    
    return result


@router.post("/{account_id}/reactivate")
async def reactivate_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Reactivate a suspended house account"""
    service = HouseAccountService(db)
    
    result = service.reactivate_account(
        account_id=account_id,
        staff_id=current_user.id if current_user else None
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to reactivate account")
        )
    
    return result


@router.get("/{account_id}")
async def get_account(
    account_id: str,
    db: Session = Depends(get_db)
):
    """Get account details"""
    service = HouseAccountService(db)
    result = service.get_account(account_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Account not found")
        )
    
    return result


@router.get("/")
async def list_accounts(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all house accounts"""
    service = HouseAccountService(db)
    return service.list_accounts(venue_id=1, status=status)


# ========== UPDATE OPERATION ==========

class UpdateAccountRequest(BaseModel):
    account_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    billing_address: Optional[str] = None
    credit_limit: Optional[float] = None
    payment_terms: Optional[str] = None
    discount_percentage: Optional[float] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None


@router.put("/{account_id}")
async def update_account(
    account_id: str,
    request: UpdateAccountRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update a house account

    - Only non-null fields will be updated
    - credit_limit changes are tracked in audit log
    """
    service = HouseAccountService(db)

    # Check if account exists
    existing = service.get_account(account_id)
    if not existing.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Build update dict from non-None values
    update_data = {k: v for k, v in request.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    result = service.update_account(
        account_id=account_id,
        update_data=update_data,
        staff_id=current_user.id if current_user else None
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to update account")
        )

    return result


# ========== DELETE OPERATION ==========

@router.delete("/{account_id}")
async def delete_account(
    account_id: str,
    permanent: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a house account

    - **permanent**: If False (default), soft deletes (marks as closed)
    - **permanent**: If True, permanently removes the account (admin only)
    - Cannot delete accounts with outstanding balance
    """
    service = HouseAccountService(db)

    # Check if account exists
    existing = service.get_account(account_id)
    if not existing.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Check for outstanding balance
    account_data = existing.get("account", {})
    if account_data.get("current_balance", 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete account with outstanding balance of {account_data.get('current_balance')}"
        )

    result = service.delete_account(
        account_id=account_id,
        permanent=permanent,
        staff_id=current_user.id if current_user else None
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to delete account")
        )

    return result


@router.delete("/{account_id}/authorized-users/{user_id}")
async def remove_authorized_user(
    account_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove an authorized user from a house account"""
    service = HouseAccountService(db)

    result = service.remove_authorized_user(
        account_id=account_id,
        user_id=user_id,
        staff_id=current_user.id if current_user else None
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to remove user")
        )

    return result
