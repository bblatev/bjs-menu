"""
Cryptocurrency Payment API Endpoints
Square 2025 feature: Bitcoin payments with zero transaction fees
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
import secrets

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rate_limit import limiter
from app.models import StaffUser, Order


router = APIRouter()


def require_admin(current_user = Depends(get_current_user)):
    """Require admin/owner role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# =============================================================================
# SCHEMAS
# =============================================================================

class CryptoWalletConfig(BaseModel):
    """Cryptocurrency wallet configuration"""
    currency: str = Field(..., description="Cryptocurrency: BTC, ETH, USDT, USDC")
    wallet_address: str = Field(..., description="Wallet address for receiving payments")
    payment_provider: str = Field("coinbase_commerce", description="Provider: coinbase_commerce, bitpay, btcpay_server, custom")

    # Provider settings
    api_key: Optional[str] = None
    webhook_secret: Optional[str] = None

    # Settlement
    auto_convert_to_fiat: bool = Field(True, description="Auto-convert to BGN/EUR")
    fiat_currency: str = Field("BGN", description="Settlement currency")


class CryptoWalletResponse(BaseModel):
    id: int
    venue_id: int
    currency: str
    wallet_address: str
    payment_provider: str
    auto_convert_to_fiat: bool
    fiat_currency: str
    is_active: bool
    total_received: float
    total_transactions: int
    created_at: datetime


class CryptoPaymentRequest(BaseModel):
    order_id: int
    currency: str = Field(..., description="BTC, ETH, USDT, USDC")
    amount_fiat: float = Field(..., description="Amount in fiat currency (BGN/EUR)")


class CryptoPaymentResponse(BaseModel):
    payment_id: str
    order_id: int
    currency: str
    amount_crypto: float
    amount_fiat: float
    exchange_rate: float
    wallet_address: str
    payment_uri: str  # For QR code generation
    expires_at: datetime
    status: str  # pending, confirmed, expired, failed


class CryptoPaymentStatus(BaseModel):
    payment_id: str
    status: str
    confirmations: int
    required_confirmations: int
    transaction_hash: Optional[str]
    amount_received: Optional[float]
    received_at: Optional[datetime]


class CryptoRates(BaseModel):
    """Current cryptocurrency exchange rates"""
    base_currency: str = "BGN"
    rates: Dict[str, float]
    updated_at: datetime


# =============================================================================
# IN-MEMORY STATE (Production: Use database + Redis)
# =============================================================================

crypto_wallets: Dict[int, Dict[str, Any]] = {}
wallet_counter = 1

crypto_payments: Dict[str, Dict[str, Any]] = {}

# Mock exchange rates (Production: Use CoinGecko/CoinMarketCap API)
mock_rates = {
    "BTC": 0.000012,  # 1 BGN = 0.000012 BTC
    "ETH": 0.00019,   # 1 BGN = 0.00019 ETH
    "USDT": 0.55,     # 1 BGN = 0.55 USDT
    "USDC": 0.55      # 1 BGN = 0.55 USDC
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_payment_id() -> str:
    """Generate unique payment ID"""
    return f"CRYPTO_{secrets.token_hex(8).upper()}"


def get_exchange_rate(currency: str, fiat: str = "BGN") -> float:
    """Get current exchange rate for cryptocurrency"""
    if currency in mock_rates:
        return mock_rates[currency]
    raise ValueError(f"Unsupported cryptocurrency: {currency}")


def calculate_crypto_amount(fiat_amount: float, currency: str) -> float:
    """Convert fiat amount to cryptocurrency"""
    rate = get_exchange_rate(currency)
    return round(fiat_amount * rate, 8)


def generate_payment_uri(currency: str, address: str, amount: float, payment_id: str) -> str:
    """Generate payment URI for QR code"""
    if currency == "BTC":
        return f"bitcoin:{address}?amount={amount}&message={payment_id}"
    elif currency == "ETH":
        return f"ethereum:{address}?value={amount}&data={payment_id}"
    elif currency in ["USDT", "USDC"]:
        # ERC-20 tokens
        return f"ethereum:{address}?value={amount}&token={currency}&message={payment_id}"
    return f"{currency.lower()}:{address}?amount={amount}"


# =============================================================================
# WALLET CONFIGURATION
# =============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_crypto_payments_root(request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_manager)):
    """Crypto payments overview."""
    return await list_crypto_wallets(request=request, db=db, current_user=current_user)


@router.post("/wallets", response_model=CryptoWalletResponse)
@limiter.limit("30/minute")
async def create_crypto_wallet(
    request: Request,
    data: CryptoWalletConfig,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Configure cryptocurrency wallet for receiving payments"""
    global wallet_counter

    wallet = {
        "id": wallet_counter,
        "venue_id": current_user.venue_id,
        "currency": data.currency.upper(),
        "wallet_address": data.wallet_address,
        "payment_provider": data.payment_provider,
        "api_key": data.api_key,
        "webhook_secret": data.webhook_secret,
        "auto_convert_to_fiat": data.auto_convert_to_fiat,
        "fiat_currency": data.fiat_currency,
        "is_active": True,
        "total_received": 0.0,
        "total_transactions": 0,
        "created_at": datetime.now(timezone.utc)
    }

    crypto_wallets[wallet_counter] = wallet
    wallet_counter += 1

    return CryptoWalletResponse(**{k: v for k, v in wallet.items() if k != "api_key" and k != "webhook_secret"})


@router.get("/wallets", response_model=List[CryptoWalletResponse])
@limiter.limit("60/minute")
async def list_crypto_wallets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """List configured cryptocurrency wallets"""
    venue_wallets = [
        CryptoWalletResponse(**{k: v for k, v in w.items() if k != "api_key" and k != "webhook_secret"})
        for w in crypto_wallets.values()
        if w.get("venue_id") == current_user.venue_id
    ]
    return venue_wallets


@router.put("/wallets/{wallet_id}", response_model=CryptoWalletResponse)
@limiter.limit("30/minute")
async def update_crypto_wallet(
    request: Request,
    wallet_id: int,
    data: CryptoWalletConfig,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Update cryptocurrency wallet configuration"""
    if wallet_id not in crypto_wallets:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet = crypto_wallets[wallet_id]
    if wallet["venue_id"] != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Access denied")

    wallet.update(data.model_dump())

    return CryptoWalletResponse(**{k: v for k, v in wallet.items() if k != "api_key" and k != "webhook_secret"})


@router.delete("/wallets/{wallet_id}")
@limiter.limit("30/minute")
async def delete_crypto_wallet(
    request: Request,
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Remove cryptocurrency wallet"""
    if wallet_id not in crypto_wallets:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet = crypto_wallets[wallet_id]
    if wallet["venue_id"] != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Access denied")

    del crypto_wallets[wallet_id]

    return {"message": "Wallet removed"}


@router.put("/wallets/{wallet_id}/toggle")
@limiter.limit("30/minute")
async def toggle_crypto_wallet(
    request: Request,
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Enable/disable cryptocurrency wallet"""
    if wallet_id not in crypto_wallets:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet = crypto_wallets[wallet_id]
    if wallet["venue_id"] != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Access denied")

    wallet["is_active"] = not wallet["is_active"]

    return {"is_active": wallet["is_active"]}


# =============================================================================
# EXCHANGE RATES
# =============================================================================

@router.get("/rates", response_model=CryptoRates)
@limiter.limit("60/minute")
async def get_crypto_rates(
    request: Request,
    base_currency: str = "BGN",
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get current cryptocurrency exchange rates

    In production, this would fetch from CoinGecko, CoinMarketCap, or provider API.
    """
    # Mock rates (production: fetch from API)
    rates = {
        "BTC": 0.000012,  # ~83,333 BGN per BTC
        "ETH": 0.00019,   # ~5,263 BGN per ETH
        "USDT": 0.55,     # ~1.82 BGN per USDT
        "USDC": 0.55,     # ~1.82 BGN per USDC
        "LTC": 0.0006,    # Litecoin
        "DOGE": 0.15      # Dogecoin
    }

    return CryptoRates(
        base_currency=base_currency,
        rates=rates,
        updated_at=datetime.now(timezone.utc)
    )


@router.get("/convert")
@limiter.limit("60/minute")
async def convert_currency(
    request: Request,
    amount: float = Query(0.0, description="Amount to convert"),
    from_currency: str = Query("BGN", description="Source currency"),
    to_currency: str = Query("BTC", description="Target currency"),
    current_user: StaffUser = Depends(get_current_user)
):
    """Convert between fiat and cryptocurrency"""
    if from_currency == "BGN":
        crypto_amount = calculate_crypto_amount(amount, to_currency)
        return {
            "from_amount": amount,
            "from_currency": from_currency,
            "to_amount": crypto_amount,
            "to_currency": to_currency,
            "rate": get_exchange_rate(to_currency)
        }
    else:
        # Crypto to fiat
        rate = get_exchange_rate(from_currency)
        fiat_amount = amount / rate if rate > 0 else 0
        return {
            "from_amount": amount,
            "from_currency": from_currency,
            "to_amount": round(fiat_amount, 2),
            "to_currency": to_currency,
            "rate": 1 / rate if rate > 0 else 0
        }


# =============================================================================
# PAYMENT CREATION
# =============================================================================

@router.post("/payments", response_model=CryptoPaymentResponse)
@limiter.limit("30/minute")
async def create_crypto_payment(
    request: Request,
    data: CryptoPaymentRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Create a cryptocurrency payment request

    Generates payment details including QR code-compatible URI.
    """
    # Verify order exists
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Find wallet for this currency
    wallet = None
    for w in crypto_wallets.values():
        if w["currency"] == data.currency.upper() and w["is_active"]:
            wallet = w
            break

    if not wallet:
        raise HTTPException(
            status_code=400,
            detail=f"No active wallet configured for {data.currency}"
        )

    # Calculate crypto amount
    crypto_amount = calculate_crypto_amount(data.amount_fiat, data.currency)
    exchange_rate = get_exchange_rate(data.currency)

    payment_id = generate_payment_id()

    payment = {
        "payment_id": payment_id,
        "order_id": data.order_id,
        "venue_id": current_user.venue_id,
        "currency": data.currency.upper(),
        "amount_crypto": crypto_amount,
        "amount_fiat": data.amount_fiat,
        "fiat_currency": "BGN",
        "exchange_rate": exchange_rate,
        "wallet_address": wallet["wallet_address"],
        "wallet_id": wallet["id"],
        "payment_uri": generate_payment_uri(
            data.currency, wallet["wallet_address"], crypto_amount, payment_id
        ),
        "status": "pending",
        "confirmations": 0,
        "required_confirmations": 1 if data.currency in ["USDT", "USDC"] else 3,
        "transaction_hash": None,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
        "received_at": None,
        "created_by": current_user.id
    }

    crypto_payments[payment_id] = payment

    return CryptoPaymentResponse(
        payment_id=payment_id,
        order_id=data.order_id,
        currency=data.currency.upper(),
        amount_crypto=crypto_amount,
        amount_fiat=data.amount_fiat,
        exchange_rate=exchange_rate,
        wallet_address=wallet["wallet_address"],
        payment_uri=payment["payment_uri"],
        expires_at=payment["expires_at"],
        status="pending"
    )


@router.get("/payments/{payment_id}", response_model=CryptoPaymentStatus)
@limiter.limit("60/minute")
async def get_payment_status(
    request: Request,
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get cryptocurrency payment status"""
    if payment_id not in crypto_payments:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment = crypto_payments[payment_id]

    # Check if expired
    if payment["status"] == "pending" and datetime.now(timezone.utc) > payment["expires_at"]:
        payment["status"] = "expired"

    return CryptoPaymentStatus(
        payment_id=payment_id,
        status=payment["status"],
        confirmations=payment["confirmations"],
        required_confirmations=payment["required_confirmations"],
        transaction_hash=payment["transaction_hash"],
        amount_received=payment.get("amount_received"),
        received_at=payment["received_at"]
    )


@router.post("/payments/{payment_id}/check")
@limiter.limit("30/minute")
async def check_payment_status(
    request: Request,
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Manually check payment status on blockchain

    In production, this would query the blockchain or payment provider API.
    """
    if payment_id not in crypto_payments:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment = crypto_payments[payment_id]

    # Mock: Check blockchain (production: actual blockchain query)
    # For demo, we'll simulate confirmation after a few checks
    import random
    if payment["status"] == "pending" and random.random() > 0.7:
        payment["status"] = "confirmed"
        payment["confirmations"] = payment["required_confirmations"]
        payment["transaction_hash"] = f"0x{secrets.token_hex(32)}"
        payment["amount_received"] = payment["amount_crypto"]
        payment["received_at"] = datetime.now(timezone.utc)

        # Update wallet stats
        wallet = crypto_wallets.get(payment["wallet_id"])
        if wallet:
            wallet["total_received"] += payment["amount_crypto"]
            wallet["total_transactions"] += 1

        # Update order
        order = db.query(Order).filter(Order.id == payment["order_id"]).first()
        if order:
            order.paid_amount = (order.paid_amount or 0) + payment["amount_fiat"]
            order.payment_method = f"crypto_{payment['currency'].lower()}"
            db.commit()

    return CryptoPaymentStatus(
        payment_id=payment_id,
        status=payment["status"],
        confirmations=payment["confirmations"],
        required_confirmations=payment["required_confirmations"],
        transaction_hash=payment["transaction_hash"],
        amount_received=payment.get("amount_received"),
        received_at=payment["received_at"]
    )


@router.post("/payments/{payment_id}/cancel")
@limiter.limit("30/minute")
async def cancel_payment(
    request: Request,
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Cancel a pending payment"""
    if payment_id not in crypto_payments:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment = crypto_payments[payment_id]

    if payment["status"] != "pending":
        raise HTTPException(status_code=400, detail="Cannot cancel non-pending payment")

    payment["status"] = "cancelled"

    return {"message": "Payment cancelled"}


# =============================================================================
# WEBHOOK HANDLING
# =============================================================================

@router.post("/webhook/{provider}")
@limiter.limit("30/minute")
async def handle_payment_webhook(
    request: Request,
    provider: str,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Handle payment notifications from crypto payment providers

    Supports: coinbase_commerce, bitpay, btcpay_server
    """
    if provider == "coinbase_commerce":
        # Coinbase Commerce webhook
        event_type = payload.get("event", {}).get("type")
        payment_id = payload.get("event", {}).get("data", {}).get("metadata", {}).get("payment_id")

        if event_type == "charge:confirmed" and payment_id in crypto_payments:
            payment = crypto_payments[payment_id]
            payment["status"] = "confirmed"
            payment["confirmations"] = payment["required_confirmations"]
            payment["received_at"] = datetime.now(timezone.utc)

    elif provider == "bitpay":
        # BitPay webhook
        payment_id = payload.get("posData", {}).get("payment_id")
        status = payload.get("status")

        if payment_id in crypto_payments:
            if status == "confirmed":
                crypto_payments[payment_id]["status"] = "confirmed"
            elif status == "expired":
                crypto_payments[payment_id]["status"] = "expired"

    elif provider == "btcpay_server":
        # BTCPay Server webhook
        payment_id = payload.get("orderId")
        status = payload.get("status")

        if payment_id in crypto_payments:
            if status in ["settled", "confirmed"]:
                crypto_payments[payment_id]["status"] = "confirmed"

    return {"received": True}


# =============================================================================
# REPORTS & ANALYTICS
# =============================================================================

@router.get("/transactions")
@limiter.limit("60/minute")
async def list_crypto_transactions(
    request: Request,
    currency: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """List cryptocurrency transactions"""
    transactions = [
        p for p in crypto_payments.values()
        if p.get("venue_id") == current_user.venue_id
    ]

    if currency:
        transactions = [t for t in transactions if t["currency"] == currency.upper()]

    if status:
        transactions = [t for t in transactions if t["status"] == status]

    # Sort by created_at descending
    transactions.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "transactions": transactions[skip:skip + limit],
        "total": len(transactions)
    }


@router.get("/stats")
@limiter.limit("60/minute")
async def get_crypto_stats(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get cryptocurrency payment statistics"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    venue_payments = [
        p for p in crypto_payments.values()
        if p.get("venue_id") == current_user.venue_id and p.get("created_at") > cutoff
    ]

    total = len(venue_payments)
    confirmed = len([p for p in venue_payments if p["status"] == "confirmed"])
    expired = len([p for p in venue_payments if p["status"] == "expired"])

    # By currency
    by_currency = {}
    for p in venue_payments:
        currency = p["currency"]
        if currency not in by_currency:
            by_currency[currency] = {"count": 0, "amount_fiat": 0, "amount_crypto": 0}
        by_currency[currency]["count"] += 1
        if p["status"] == "confirmed":
            by_currency[currency]["amount_fiat"] += p["amount_fiat"]
            by_currency[currency]["amount_crypto"] += p["amount_crypto"]

    total_fiat = sum(p["amount_fiat"] for p in venue_payments if p["status"] == "confirmed")

    return {
        "period_days": days,
        "total_payments": total,
        "confirmed": confirmed,
        "expired": expired,
        "conversion_rate": round(confirmed / total * 100, 2) if total > 0 else 0,
        "total_fiat_received": round(total_fiat, 2),
        "by_currency": by_currency,
        "transaction_fee": 0.0  # Zero fees through 2026 (Square feature)
    }


# =============================================================================
# QR CODE GENERATION
# =============================================================================

@router.get("/payments/{payment_id}/qr")
@limiter.limit("60/minute")
async def get_payment_qr_code(
    request: Request,
    payment_id: str,
    size: int = 300,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Generate QR code for cryptocurrency payment

    Returns PNG image of QR code that can be scanned by crypto wallets.
    """
    if payment_id not in crypto_payments:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment = crypto_payments[payment_id]

    try:
        import qrcode
        from io import BytesIO
        from fastapi.responses import StreamingResponse

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(payment["payment_uri"])
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size))

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return StreamingResponse(buffer, media_type="image/png")

    except ImportError:
        # If qrcode library not installed, return payment info
        return {
            "payment_uri": payment["payment_uri"],
            "message": "Install qrcode library for QR image generation"
        }


# =============================================================================
# SUPPORTED CRYPTOCURRENCIES
# =============================================================================

@router.get("/currencies")
@limiter.limit("60/minute")
async def get_supported_currencies(request: Request):
    """Get list of supported cryptocurrencies"""
    return {
        "currencies": [
            {
                "symbol": "BTC",
                "name": "Bitcoin",
                "network": "bitcoin",
                "confirmations_required": 3,
                "transaction_fee": 0.0,
                "min_amount": 0.00001
            },
            {
                "symbol": "ETH",
                "name": "Ethereum",
                "network": "ethereum",
                "confirmations_required": 12,
                "transaction_fee": 0.0,
                "min_amount": 0.0001
            },
            {
                "symbol": "USDT",
                "name": "Tether USD",
                "network": "ethereum",
                "type": "ERC-20",
                "confirmations_required": 1,
                "transaction_fee": 0.0,
                "min_amount": 1.0
            },
            {
                "symbol": "USDC",
                "name": "USD Coin",
                "network": "ethereum",
                "type": "ERC-20",
                "confirmations_required": 1,
                "transaction_fee": 0.0,
                "min_amount": 1.0
            },
            {
                "symbol": "LTC",
                "name": "Litecoin",
                "network": "litecoin",
                "confirmations_required": 6,
                "transaction_fee": 0.0,
                "min_amount": 0.001
            }
        ],
        "note": "Zero transaction fees through December 2026"
    }
