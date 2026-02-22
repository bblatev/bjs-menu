"""QuickBooks Online Integration Service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class QBOEnvironment(str, Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


@dataclass
class QBOTokens:
    """OAuth2 tokens for QuickBooks."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    realm_id: Optional[str] = None  # Company ID


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    synced_count: int = 0
    error_count: int = 0
    errors: List[str] = None
    last_sync: Optional[datetime] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def _qb_escape(value: str) -> str:
    """Escape a string for QuickBooks query language.

    QBO queries use single-quoted strings with '' as the escape for literal quotes.
    Also strips control characters that could alter query semantics.
    """
    import re
    if not isinstance(value, str):
        value = str(value)
    # Truncate to prevent oversized query payloads
    value = value[:200]
    # Remove control characters, null bytes, backslashes, and semicolons
    cleaned = re.sub(r'[\x00-\x1f\x7f\\;]', '', value)
    # Escape single quotes (QBO standard)
    return cleaned.replace("'", "''")


class QuickBooksService:
    """Service for QuickBooks Online integration."""

    OAUTH_BASE = "https://oauth.platform.intuit.com/oauth2/v1"
    API_BASE_SANDBOX = "https://sandbox-quickbooks.api.intuit.com/v3/company"
    API_BASE_PRODUCTION = "https://quickbooks.api.intuit.com/v3/company"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        environment: QBOEnvironment = QBOEnvironment.SANDBOX,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.environment = environment
        self.api_base = (
            self.API_BASE_PRODUCTION
            if environment == QBOEnvironment.PRODUCTION
            else self.API_BASE_SANDBOX
        )

        self._tokens: Optional[QBOTokens] = None
        self._client: Optional[httpx.AsyncClient] = None

    def get_authorization_url(self, state: str = "random_state") -> str:
        """Get the OAuth2 authorization URL."""
        import urllib.parse

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "com.intuit.quickbooks.accounting",
            "state": state,
        }

        return f"https://appcenter.intuit.com/connect/oauth2?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_tokens(
        self,
        authorization_code: str,
        realm_id: str,
    ) -> Optional[QBOTokens]:
        """Exchange authorization code for access tokens."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                import base64
                credentials = base64.b64encode(
                    f"{self.client_id}:{self.client_secret}".encode()
                ).decode()

                response = await client.post(
                    f"{self.OAUTH_BASE}/tokens/bearer",
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                    data={
                        "grant_type": "authorization_code",
                        "code": authorization_code,
                        "redirect_uri": self.redirect_uri,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self._tokens = QBOTokens(
                        access_token=data["access_token"],
                        refresh_token=data["refresh_token"],
                        token_type=data.get("token_type", "Bearer"),
                        expires_at=datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600)),
                        realm_id=realm_id,
                    )
                    return self._tokens
                else:
                    logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                    return None

            except Exception as e:
                logger.error(f"Token exchange error: {e}")
                return None

    async def refresh_tokens(self) -> bool:
        """Refresh access tokens."""
        if not self._tokens or not self._tokens.refresh_token:
            return False

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                import base64
                credentials = base64.b64encode(
                    f"{self.client_id}:{self.client_secret}".encode()
                ).decode()

                response = await client.post(
                    f"{self.OAUTH_BASE}/tokens/bearer",
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self._tokens.refresh_token,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self._tokens = QBOTokens(
                        access_token=data["access_token"],
                        refresh_token=data["refresh_token"],
                        token_type=data.get("token_type", "Bearer"),
                        expires_at=datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600)),
                        realm_id=self._tokens.realm_id,
                    )
                    return True
                else:
                    logger.error(f"Token refresh failed: {response.status_code}")
                    return False

            except Exception as e:
                logger.error(f"Token refresh error: {e}")
                return False

    def set_tokens(self, tokens: QBOTokens):
        """Set tokens (loaded from database)."""
        self._tokens = tokens

    def get_tokens(self) -> Optional[QBOTokens]:
        """Get current tokens (for saving to database)."""
        return self._tokens

    async def _get_client(self) -> httpx.AsyncClient:
        """Get authenticated HTTP client."""
        if not self._tokens:
            raise ValueError("Not authenticated. Call exchange_code_for_tokens first.")

        # Check if token needs refresh
        if self._tokens.expires_at and datetime.now(timezone.utc) >= self._tokens.expires_at - timedelta(minutes=5):
            await self.refresh_tokens()

        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{self.api_base}/{self._tokens.realm_id}",
                headers={
                    "Authorization": f"Bearer {self._tokens.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        else:
            # Update authorization header
            self._client.headers["Authorization"] = f"Bearer {self._tokens.access_token}"

        return self._client

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        client = await self._get_client()

        try:
            if method == "GET":
                response = await client.get(endpoint, params=params)
            elif method == "POST":
                response = await client.post(endpoint, json=data, params=params)
            elif method == "DELETE":
                response = await client.post(endpoint, json=data, params={"operation": "delete"})
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code in (200, 201):
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }

        except Exception as e:
            logger.error(f"QBO API error: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Company Info
    # =========================================================================

    async def get_company_info(self) -> Dict[str, Any]:
        """Get company information."""
        result = await self._api_request(
            "GET",
            f"/companyinfo/{self._tokens.realm_id}",
        )

        if result["success"]:
            info = result["data"].get("CompanyInfo", {})
            return {
                "success": True,
                "company_name": info.get("CompanyName"),
                "legal_name": info.get("LegalName"),
                "country": info.get("Country"),
                "email": info.get("Email", {}).get("Address"),
                "fiscal_year_start_month": info.get("FiscalYearStartMonth"),
            }
        return result

    # =========================================================================
    # Customers
    # =========================================================================

    async def sync_customer(
        self,
        display_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company_name: Optional[str] = None,
        notes: Optional[str] = None,
        internal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a customer in QuickBooks."""
        # First check if customer exists
        safe_name = _qb_escape(display_name)
        query = f"SELECT * FROM Customer WHERE DisplayName = '{safe_name}'"
        existing = await self._api_request("GET", "/query", params={"query": query})

        customer_data = {
            "DisplayName": display_name,
        }
        if email:
            customer_data["PrimaryEmailAddr"] = {"Address": email}
        if phone:
            customer_data["PrimaryPhone"] = {"FreeFormNumber": phone}
        if company_name:
            customer_data["CompanyName"] = company_name
        if notes:
            customer_data["Notes"] = notes

        if existing["success"] and existing["data"].get("QueryResponse", {}).get("Customer"):
            # Update existing
            existing_customer = existing["data"]["QueryResponse"]["Customer"][0]
            customer_data["Id"] = existing_customer["Id"]
            customer_data["SyncToken"] = existing_customer["SyncToken"]

        result = await self._api_request("POST", "/customer", data=customer_data)

        if result["success"]:
            customer = result["data"].get("Customer", {})
            return {
                "success": True,
                "qbo_customer_id": customer.get("Id"),
                "display_name": customer.get("DisplayName"),
            }
        return result

    async def get_customers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all customers from QuickBooks."""
        # Validate and clamp limit
        limit = max(1, min(int(limit), 1000))
        query = f"SELECT * FROM Customer MAXRESULTS {limit}"
        result = await self._api_request("GET", "/query", params={"query": query})

        if result["success"]:
            customers = result["data"].get("QueryResponse", {}).get("Customer", [])
            return [
                {
                    "id": c.get("Id"),
                    "display_name": c.get("DisplayName"),
                    "email": c.get("PrimaryEmailAddr", {}).get("Address"),
                    "phone": c.get("PrimaryPhone", {}).get("FreeFormNumber"),
                    "balance": c.get("Balance", 0),
                }
                for c in customers
            ]
        return []

    # =========================================================================
    # Sales Receipts (for POS sales)
    # =========================================================================

    async def create_sales_receipt(
        self,
        customer_id: Optional[str],
        line_items: List[Dict[str, Any]],
        payment_method: str = "Cash",
        txn_date: Optional[str] = None,
        memo: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a sales receipt in QuickBooks.

        line_items format:
        [
            {
                "description": "Item name",
                "amount": 10.00,
                "quantity": 2,
                "item_id": "optional_qbo_item_id",
            }
        ]
        """
        lines = []
        for i, item in enumerate(line_items):
            line = {
                "Id": str(i + 1),
                "LineNum": i + 1,
                "Amount": item.get("amount", 0) * item.get("quantity", 1),
                "DetailType": "SalesItemLineDetail",
                "SalesItemLineDetail": {
                    "Qty": item.get("quantity", 1),
                    "UnitPrice": item.get("amount", 0),
                },
            }

            if item.get("item_id"):
                line["SalesItemLineDetail"]["ItemRef"] = {"value": item["item_id"]}
            if item.get("description"):
                line["Description"] = item["description"]

            lines.append(line)

        receipt_data = {
            "Line": lines,
        }

        if customer_id:
            receipt_data["CustomerRef"] = {"value": customer_id}
        if txn_date:
            receipt_data["TxnDate"] = txn_date
        if memo:
            receipt_data["PrivateNote"] = memo
        if order_id:
            receipt_data["DocNumber"] = order_id

        # Payment method reference (need to query for actual payment method ID)
        # For simplicity, we'll use deposit to undeposited funds

        result = await self._api_request("POST", "/salesreceipt", data=receipt_data)

        if result["success"]:
            receipt = result["data"].get("SalesReceipt", {})
            return {
                "success": True,
                "qbo_receipt_id": receipt.get("Id"),
                "doc_number": receipt.get("DocNumber"),
                "total": receipt.get("TotalAmt"),
            }
        return result

    # =========================================================================
    # Invoices
    # =========================================================================

    async def create_invoice(
        self,
        customer_id: str,
        line_items: List[Dict[str, Any]],
        due_date: Optional[str] = None,
        txn_date: Optional[str] = None,
        memo: Optional[str] = None,
        invoice_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an invoice in QuickBooks."""
        lines = []
        for i, item in enumerate(line_items):
            line = {
                "Id": str(i + 1),
                "LineNum": i + 1,
                "Amount": item.get("amount", 0) * item.get("quantity", 1),
                "DetailType": "SalesItemLineDetail",
                "SalesItemLineDetail": {
                    "Qty": item.get("quantity", 1),
                    "UnitPrice": item.get("amount", 0),
                },
            }

            if item.get("item_id"):
                line["SalesItemLineDetail"]["ItemRef"] = {"value": item["item_id"]}
            if item.get("description"):
                line["Description"] = item["description"]

            lines.append(line)

        invoice_data = {
            "CustomerRef": {"value": customer_id},
            "Line": lines,
        }

        if due_date:
            invoice_data["DueDate"] = due_date
        if txn_date:
            invoice_data["TxnDate"] = txn_date
        if memo:
            invoice_data["PrivateNote"] = memo
        if invoice_number:
            invoice_data["DocNumber"] = invoice_number

        result = await self._api_request("POST", "/invoice", data=invoice_data)

        if result["success"]:
            invoice = result["data"].get("Invoice", {})
            return {
                "success": True,
                "qbo_invoice_id": invoice.get("Id"),
                "doc_number": invoice.get("DocNumber"),
                "total": invoice.get("TotalAmt"),
                "balance": invoice.get("Balance"),
            }
        return result

    # =========================================================================
    # Vendors (Suppliers)
    # =========================================================================

    async def sync_vendor(
        self,
        display_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a vendor in QuickBooks."""
        # Check if vendor exists
        safe_name = _qb_escape(display_name)
        query = f"SELECT * FROM Vendor WHERE DisplayName = '{safe_name}'"
        existing = await self._api_request("GET", "/query", params={"query": query})

        vendor_data = {
            "DisplayName": display_name,
        }
        if email:
            vendor_data["PrimaryEmailAddr"] = {"Address": email}
        if phone:
            vendor_data["PrimaryPhone"] = {"FreeFormNumber": phone}
        if company_name:
            vendor_data["CompanyName"] = company_name

        if existing["success"] and existing["data"].get("QueryResponse", {}).get("Vendor"):
            existing_vendor = existing["data"]["QueryResponse"]["Vendor"][0]
            vendor_data["Id"] = existing_vendor["Id"]
            vendor_data["SyncToken"] = existing_vendor["SyncToken"]

        result = await self._api_request("POST", "/vendor", data=vendor_data)

        if result["success"]:
            vendor = result["data"].get("Vendor", {})
            return {
                "success": True,
                "qbo_vendor_id": vendor.get("Id"),
                "display_name": vendor.get("DisplayName"),
            }
        return result

    # =========================================================================
    # Bills (Purchase Orders / Invoices from Vendors)
    # =========================================================================

    async def create_bill(
        self,
        vendor_id: str,
        line_items: List[Dict[str, Any]],
        due_date: Optional[str] = None,
        txn_date: Optional[str] = None,
        memo: Optional[str] = None,
        ref_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a bill (vendor invoice) in QuickBooks."""
        lines = []
        for i, item in enumerate(line_items):
            line = {
                "Id": str(i + 1),
                "LineNum": i + 1,
                "Amount": item.get("amount", 0) * item.get("quantity", 1),
                "DetailType": "AccountBasedExpenseLineDetail",
                "AccountBasedExpenseLineDetail": {},
            }

            if item.get("account_id"):
                line["AccountBasedExpenseLineDetail"]["AccountRef"] = {"value": item["account_id"]}
            if item.get("description"):
                line["Description"] = item["description"]

            lines.append(line)

        bill_data = {
            "VendorRef": {"value": vendor_id},
            "Line": lines,
        }

        if due_date:
            bill_data["DueDate"] = due_date
        if txn_date:
            bill_data["TxnDate"] = txn_date
        if memo:
            bill_data["PrivateNote"] = memo
        if ref_number:
            bill_data["DocNumber"] = ref_number

        result = await self._api_request("POST", "/bill", data=bill_data)

        if result["success"]:
            bill = result["data"].get("Bill", {})
            return {
                "success": True,
                "qbo_bill_id": bill.get("Id"),
                "doc_number": bill.get("DocNumber"),
                "total": bill.get("TotalAmt"),
            }
        return result

    # =========================================================================
    # Accounts (Chart of Accounts)
    # =========================================================================

    async def get_accounts(self, account_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get chart of accounts."""
        query = "SELECT * FROM Account"
        if account_type:
            safe_type = _qb_escape(account_type)
            query += f" WHERE AccountType = '{safe_type}'"
        query += " MAXRESULTS 1000"

        result = await self._api_request("GET", "/query", params={"query": query})

        if result["success"]:
            accounts = result["data"].get("QueryResponse", {}).get("Account", [])
            return [
                {
                    "id": a.get("Id"),
                    "name": a.get("Name"),
                    "full_name": a.get("FullyQualifiedName"),
                    "type": a.get("AccountType"),
                    "sub_type": a.get("AccountSubType"),
                    "current_balance": a.get("CurrentBalance", 0),
                    "active": a.get("Active", True),
                }
                for a in accounts
            ]
        return []

    # =========================================================================
    # Items (Products/Services)
    # =========================================================================

    async def sync_item(
        self,
        name: str,
        description: Optional[str] = None,
        unit_price: Optional[float] = None,
        purchase_cost: Optional[float] = None,
        item_type: str = "Service",  # Service, Inventory, NonInventory
        income_account_id: Optional[str] = None,
        expense_account_id: Optional[str] = None,
        sku: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update an item in QuickBooks."""
        # Check if item exists
        safe_name = _qb_escape(name)
        query = f"SELECT * FROM Item WHERE Name = '{safe_name}'"
        existing = await self._api_request("GET", "/query", params={"query": query})

        item_data = {
            "Name": name,
            "Type": item_type,
        }

        if description:
            item_data["Description"] = description
        if unit_price is not None:
            item_data["UnitPrice"] = unit_price
        if purchase_cost is not None:
            item_data["PurchaseCost"] = purchase_cost
        if sku:
            item_data["Sku"] = sku
        if income_account_id:
            item_data["IncomeAccountRef"] = {"value": income_account_id}
        if expense_account_id:
            item_data["ExpenseAccountRef"] = {"value": expense_account_id}

        if existing["success"] and existing["data"].get("QueryResponse", {}).get("Item"):
            existing_item = existing["data"]["QueryResponse"]["Item"][0]
            item_data["Id"] = existing_item["Id"]
            item_data["SyncToken"] = existing_item["SyncToken"]

        result = await self._api_request("POST", "/item", data=item_data)

        if result["success"]:
            item = result["data"].get("Item", {})
            return {
                "success": True,
                "qbo_item_id": item.get("Id"),
                "name": item.get("Name"),
            }
        return result

    async def get_items(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all items from QuickBooks."""
        # Validate and clamp limit
        limit = max(1, min(int(limit), 1000))
        query = f"SELECT * FROM Item MAXRESULTS {limit}"
        result = await self._api_request("GET", "/query", params={"query": query})

        if result["success"]:
            items = result["data"].get("QueryResponse", {}).get("Item", [])
            return [
                {
                    "id": i.get("Id"),
                    "name": i.get("Name"),
                    "description": i.get("Description"),
                    "type": i.get("Type"),
                    "unit_price": i.get("UnitPrice", 0),
                    "purchase_cost": i.get("PurchaseCost", 0),
                    "sku": i.get("Sku"),
                    "active": i.get("Active", True),
                }
                for i in items
            ]
        return []

    # =========================================================================
    # Reports
    # =========================================================================

    async def get_profit_and_loss(
        self,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Get profit and loss report."""
        result = await self._api_request(
            "GET",
            "/reports/ProfitAndLoss",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        return result

    async def get_balance_sheet(self, as_of_date: str) -> Dict[str, Any]:
        """Get balance sheet report."""
        result = await self._api_request(
            "GET",
            "/reports/BalanceSheet",
            params={"as_of_date": as_of_date},
        )
        return result

    # =========================================================================
    # Bulk Sync Operations
    # =========================================================================

    async def sync_daily_sales(
        self,
        sales: List[Dict[str, Any]],
    ) -> SyncResult:
        """
        Sync daily sales to QuickBooks.

        sales format:
        [
            {
                "order_id": "123",
                "customer_name": "Walk-in Customer",
                "items": [{"description": "Item", "amount": 10.00, "quantity": 1}],
                "total": 10.00,
                "payment_method": "Cash",
                "date": "2026-02-04",
            }
        ]
        """
        result = SyncResult(success=True, last_sync=datetime.now(timezone.utc))

        for sale in sales:
            try:
                receipt_result = await self.create_sales_receipt(
                    customer_id=None,  # Walk-in customer
                    line_items=sale.get("items", []),
                    payment_method=sale.get("payment_method", "Cash"),
                    txn_date=sale.get("date"),
                    memo=f"POS Order #{sale.get('order_id')}",
                    order_id=sale.get("order_id"),
                )

                if receipt_result.get("success"):
                    result.synced_count += 1
                else:
                    result.error_count += 1
                    result.errors.append(
                        f"Order {sale.get('order_id')}: {receipt_result.get('error')}"
                    )

            except Exception as e:
                result.error_count += 1
                result.errors.append(f"Order {sale.get('order_id')}: {str(e)}")

        result.success = result.error_count == 0
        return result

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_qbo_service: Optional[QuickBooksService] = None


def get_quickbooks_service() -> Optional[QuickBooksService]:
    """Get or create the QuickBooks service singleton."""
    global _qbo_service
    if _qbo_service is None:
        client_id = settings.qbo_client_id
        client_secret = settings.qbo_client_secret
        redirect_uri = settings.qbo_redirect_uri

        if client_id and client_secret:
            env = QBOEnvironment.PRODUCTION if settings.qbo_production else QBOEnvironment.SANDBOX
            _qbo_service = QuickBooksService(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                environment=env,
            )
    return _qbo_service
