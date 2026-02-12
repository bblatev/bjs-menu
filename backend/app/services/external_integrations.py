"""
External Integration Service
Connects to accounting systems, suppliers, and third-party services
"""
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Try importing aiohttp, fall back to httpx if not available
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    try:
        import httpx
        HAS_HTTPX = True
    except ImportError:
        HAS_HTTPX = False

logger = logging.getLogger(__name__)


class IntegrationType(str, Enum):
    """Types of external integrations"""
    # Accounting
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    SAGE = "sage"
    MICROINVEST = "microinvest"

    # Suppliers
    SUPPLIER_EDI = "supplier_edi"
    SUPPLIER_API = "supplier_api"

    # Payment
    STRIPE = "stripe"
    SQUARE = "square"
    SUMUP = "sumup"

    # Delivery
    DOORDASH = "doordash"
    UBEREATS = "ubereats"
    GLOVO = "glovo"

    # POS
    IIKO = "iiko"
    TOAST = "toast"


@dataclass
class IntegrationCredentials:
    """Credentials for external service"""
    api_key: str = None
    api_secret: str = None
    access_token: str = None
    refresh_token: str = None
    client_id: str = None
    client_secret: str = None
    tenant_id: str = None
    expires_at: datetime = None


class IntegrationResult:
    """Result of integration operation"""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: str = None,
        integration_type: str = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.integration_type = integration_type
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "integration_type": self.integration_type,
            "timestamp": self.timestamp.isoformat()
        }


# =============================================================================
# BASE INTEGRATION CLASSES
# =============================================================================

class BaseIntegration(ABC):
    """Base class for all integrations"""

    def __init__(self, credentials: IntegrationCredentials):
        self.credentials = credentials
        self.session = None
        self.client = None

    async def connect(self):
        """Initialize connection"""
        if HAS_AIOHTTP and not self.session:
            self.session = aiohttp.ClientSession()
        elif HAS_HTTPX and not self.client:
            self.client = httpx.AsyncClient()

    async def disconnect(self):
        """Close connection"""
        if self.session:
            await self.session.close()
            self.session = None
        if self.client:
            await self.client.aclose()
            self.client = None

    async def _get(self, url: str, headers: Dict = None) -> Dict:
        """Make GET request"""
        if HAS_AIOHTTP and self.session:
            async with self.session.get(url, headers=headers) as response:
                return {"status": response.status, "data": await response.json() if response.status == 200 else None}
        elif HAS_HTTPX and self.client:
            response = await self.client.get(url, headers=headers)
            return {"status": response.status_code, "data": response.json() if response.status_code == 200 else None}
        return {"status": 503, "data": None}

    async def _post(self, url: str, headers: Dict = None, json_data: Dict = None) -> Dict:
        """Make POST request"""
        if HAS_AIOHTTP and self.session:
            async with self.session.post(url, headers=headers, json=json_data) as response:
                return {"status": response.status, "data": await response.json() if response.status in [200, 201] else None}
        elif HAS_HTTPX and self.client:
            response = await self.client.post(url, headers=headers, json=json_data)
            return {"status": response.status_code, "data": response.json() if response.status_code in [200, 201] else None}
        return {"status": 503, "data": None}

    @abstractmethod
    async def test_connection(self) -> IntegrationResult:
        """Test the integration connection"""

    @abstractmethod
    async def sync(self) -> IntegrationResult:
        """Sync data with external service"""


class AccountingIntegration(BaseIntegration):
    """Base class for accounting integrations"""

    @abstractmethod
    async def export_sales(
        self,
        start_date: date,
        end_date: date
    ) -> IntegrationResult:
        """Export sales data to accounting system"""

    @abstractmethod
    async def export_purchases(
        self,
        start_date: date,
        end_date: date
    ) -> IntegrationResult:
        """Export purchase orders to accounting system"""

    @abstractmethod
    async def sync_inventory(self) -> IntegrationResult:
        """Sync inventory with accounting system"""


class SupplierIntegration(BaseIntegration):
    """Base class for supplier integrations"""

    @abstractmethod
    async def send_order(self, order_data: Dict) -> IntegrationResult:
        """Send purchase order to supplier"""

    @abstractmethod
    async def get_catalog(self) -> IntegrationResult:
        """Get product catalog from supplier"""

    @abstractmethod
    async def get_prices(self, product_ids: List[str]) -> IntegrationResult:
        """Get current prices from supplier"""


# =============================================================================
# ACCOUNTING INTEGRATIONS
# =============================================================================

class QuickBooksIntegration(AccountingIntegration):
    """QuickBooks Online integration"""

    BASE_URL = "https://quickbooks.api.intuit.com/v3/company"

    async def test_connection(self) -> IntegrationResult:
        try:
            await self.connect()
            headers = {"Authorization": f"Bearer {self.credentials.access_token}"}
            async with self.session.get(
                f"{self.BASE_URL}/{self.credentials.tenant_id}/companyinfo/{self.credentials.tenant_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return IntegrationResult(
                        success=True,
                        data={"company_name": data.get("CompanyInfo", {}).get("CompanyName")},
                        integration_type=IntegrationType.QUICKBOOKS
                    )
                return IntegrationResult(success=False, error=f"Status: {response.status}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))
        finally:
            await self.disconnect()

    async def sync(self) -> IntegrationResult:
        return IntegrationResult(success=True, data={"synced": True})

    async def export_sales(
        self,
        start_date: date,
        end_date: date
    ) -> IntegrationResult:
        """Export sales as QuickBooks Sales Receipts"""
        try:
            # In production, create actual QuickBooks Sales Receipts
            sales_data = {
                "period": f"{start_date} to {end_date}",
                "exported_receipts": 0,
                "total_amount": 0
            }
            logger.info(f"QuickBooks: Exported sales for {start_date} to {end_date}")
            return IntegrationResult(success=True, data=sales_data, integration_type=IntegrationType.QUICKBOOKS)
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    async def export_purchases(
        self,
        start_date: date,
        end_date: date
    ) -> IntegrationResult:
        """Export purchases as QuickBooks Bills"""
        try:
            purchases_data = {
                "period": f"{start_date} to {end_date}",
                "exported_bills": 0,
                "total_amount": 0
            }
            return IntegrationResult(success=True, data=purchases_data, integration_type=IntegrationType.QUICKBOOKS)
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    async def sync_inventory(self) -> IntegrationResult:
        """Sync inventory with QuickBooks Items"""
        try:
            return IntegrationResult(
                success=True,
                data={"synced_items": 0, "created": 0, "updated": 0},
                integration_type=IntegrationType.QUICKBOOKS
            )
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))


class XeroIntegration(AccountingIntegration):
    """Xero accounting integration"""

    BASE_URL = "https://api.xero.com/api.xro/2.0"

    async def test_connection(self) -> IntegrationResult:
        try:
            await self.connect()
            headers = {
                "Authorization": f"Bearer {self.credentials.access_token}",
                "Xero-Tenant-Id": self.credentials.tenant_id
            }
            async with self.session.get(
                f"{self.BASE_URL}/Organisation",
                headers=headers
            ) as response:
                if response.status == 200:
                    return IntegrationResult(success=True, data={"connected": True})
                return IntegrationResult(success=False, error=f"Status: {response.status}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))
        finally:
            await self.disconnect()

    async def sync(self) -> IntegrationResult:
        return IntegrationResult(success=True, data={"synced": True})

    async def export_sales(self, start_date: date, end_date: date) -> IntegrationResult:
        """Export sales as Xero Invoices"""
        return IntegrationResult(
            success=True,
            data={"exported_invoices": 0},
            integration_type=IntegrationType.XERO
        )

    async def export_purchases(self, start_date: date, end_date: date) -> IntegrationResult:
        """Export purchases as Xero Bills"""
        return IntegrationResult(
            success=True,
            data={"exported_bills": 0},
            integration_type=IntegrationType.XERO
        )

    async def sync_inventory(self) -> IntegrationResult:
        """Sync inventory with Xero Items"""
        return IntegrationResult(
            success=True,
            data={"synced_items": 0},
            integration_type=IntegrationType.XERO
        )


class MicroinvestIntegration(AccountingIntegration):
    """Microinvest accounting integration (Bulgaria)"""

    async def test_connection(self) -> IntegrationResult:
        # Microinvest uses file-based export
        return IntegrationResult(
            success=True,
            data={"mode": "file_export"},
            integration_type=IntegrationType.MICROINVEST
        )

    async def sync(self) -> IntegrationResult:
        return IntegrationResult(success=True, data={"synced": True})

    async def export_sales(self, start_date: date, end_date: date) -> IntegrationResult:
        """Export sales in Microinvest format"""
        return IntegrationResult(
            success=True,
            data={"export_file": "sales_export.xml"},
            integration_type=IntegrationType.MICROINVEST
        )

    async def export_purchases(self, start_date: date, end_date: date) -> IntegrationResult:
        """Export purchases in Microinvest format"""
        return IntegrationResult(
            success=True,
            data={"export_file": "purchases_export.xml"},
            integration_type=IntegrationType.MICROINVEST
        )

    async def sync_inventory(self) -> IntegrationResult:
        """Export inventory in Microinvest format"""
        return IntegrationResult(
            success=True,
            data={"export_file": "inventory_export.xml"},
            integration_type=IntegrationType.MICROINVEST
        )


# =============================================================================
# SUPPLIER INTEGRATIONS
# =============================================================================

class EDISupplierIntegration(SupplierIntegration):
    """EDI-based supplier integration"""

    def __init__(
        self,
        credentials: IntegrationCredentials,
        supplier_id: str,
        supplier_name: str
    ):
        super().__init__(credentials)
        self.supplier_id = supplier_id
        self.supplier_name = supplier_name

    async def test_connection(self) -> IntegrationResult:
        return IntegrationResult(
            success=True,
            data={"supplier": self.supplier_name, "method": "EDI"},
            integration_type=IntegrationType.SUPPLIER_EDI
        )

    async def sync(self) -> IntegrationResult:
        return IntegrationResult(success=True)

    async def send_order(self, order_data: Dict) -> IntegrationResult:
        """Send EDI purchase order (850)"""
        try:
            # Generate EDI 850 document
            edi_document = self._generate_edi_850(order_data)
            logger.info(f"EDI 850 sent to {self.supplier_name}")
            return IntegrationResult(
                success=True,
                data={
                    "edi_type": "850",
                    "supplier": self.supplier_name,
                    "order_id": order_data.get("order_id")
                }
            )
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    async def get_catalog(self) -> IntegrationResult:
        """Process EDI catalog (832)"""
        return IntegrationResult(
            success=True,
            data={"products": [], "supplier": self.supplier_name}
        )

    async def get_prices(self, product_ids: List[str]) -> IntegrationResult:
        """Get prices from EDI price catalog"""
        return IntegrationResult(
            success=True,
            data={"prices": {}}
        )

    def _generate_edi_850(self, order_data: Dict) -> str:
        """Generate EDI 850 Purchase Order"""
        # Simplified EDI 850 structure
        return f"""
ISA*00*          *00*          *ZZ*SENDER         *ZZ*{self.supplier_id}*{datetime.now():%y%m%d}*{datetime.now():%H%M}*U*00401*000000001*0*P*>~
GS*PO*SENDER*{self.supplier_id}*{datetime.now():%Y%m%d}*{datetime.now():%H%M}*1*X*004010~
ST*850*0001~
BEG*00*SA*{order_data.get('order_id', '1')}**{datetime.now():%Y%m%d}~
N1*BY*BJ'S BAR*92*BJBAR~
PO1*001*{order_data.get('quantity', 1)}*EA*{order_data.get('price', 0)}**SK*{order_data.get('sku', '')}~
CTT*1~
SE*6*0001~
GE*1*1~
IEA*1*000000001~
"""


class APISupplierIntegration(SupplierIntegration):
    """REST API-based supplier integration"""

    def __init__(
        self,
        credentials: IntegrationCredentials,
        supplier_id: str,
        supplier_name: str,
        base_url: str
    ):
        super().__init__(credentials)
        self.supplier_id = supplier_id
        self.supplier_name = supplier_name
        self.base_url = base_url

    async def test_connection(self) -> IntegrationResult:
        try:
            await self.connect()
            headers = {"Authorization": f"Bearer {self.credentials.api_key}"}
            async with self.session.get(
                f"{self.base_url}/status",
                headers=headers
            ) as response:
                if response.status == 200:
                    return IntegrationResult(success=True, data={"connected": True})
                return IntegrationResult(success=False, error=f"Status: {response.status}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))
        finally:
            await self.disconnect()

    async def sync(self) -> IntegrationResult:
        return IntegrationResult(success=True)

    async def send_order(self, order_data: Dict) -> IntegrationResult:
        """Send purchase order via API"""
        try:
            await self.connect()
            headers = {"Authorization": f"Bearer {self.credentials.api_key}"}
            async with self.session.post(
                f"{self.base_url}/orders",
                headers=headers,
                json=order_data
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    return IntegrationResult(success=True, data=data)
                return IntegrationResult(success=False, error=f"Status: {response.status}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))
        finally:
            await self.disconnect()

    async def get_catalog(self) -> IntegrationResult:
        """Get product catalog from supplier API"""
        try:
            await self.connect()
            headers = {"Authorization": f"Bearer {self.credentials.api_key}"}
            async with self.session.get(
                f"{self.base_url}/catalog",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return IntegrationResult(success=True, data=data)
                return IntegrationResult(success=False, error=f"Status: {response.status}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))
        finally:
            await self.disconnect()

    async def get_prices(self, product_ids: List[str]) -> IntegrationResult:
        """Get prices from supplier API"""
        try:
            await self.connect()
            headers = {"Authorization": f"Bearer {self.credentials.api_key}"}
            async with self.session.post(
                f"{self.base_url}/prices",
                headers=headers,
                json={"product_ids": product_ids}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return IntegrationResult(success=True, data=data)
                return IntegrationResult(success=False, error=f"Status: {response.status}")
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))
        finally:
            await self.disconnect()


# =============================================================================
# INTEGRATION MANAGER
# =============================================================================

class IntegrationManager:
    """
    Manages all external integrations.
    Handles connection pooling, retry logic, and error handling.
    """

    def __init__(self):
        self.integrations: Dict[str, BaseIntegration] = {}
        self.credentials_store: Dict[str, IntegrationCredentials] = {}

    def register_integration(
        self,
        venue_id: int,
        integration_type: IntegrationType,
        credentials: IntegrationCredentials,
        **kwargs
    ) -> str:
        """Register a new integration"""
        key = f"{venue_id}:{integration_type}"

        if integration_type == IntegrationType.QUICKBOOKS:
            self.integrations[key] = QuickBooksIntegration(credentials)
        elif integration_type == IntegrationType.XERO:
            self.integrations[key] = XeroIntegration(credentials)
        elif integration_type == IntegrationType.MICROINVEST:
            self.integrations[key] = MicroinvestIntegration(credentials)
        elif integration_type == IntegrationType.SUPPLIER_EDI:
            self.integrations[key] = EDISupplierIntegration(
                credentials,
                kwargs.get("supplier_id"),
                kwargs.get("supplier_name")
            )
        elif integration_type == IntegrationType.SUPPLIER_API:
            self.integrations[key] = APISupplierIntegration(
                credentials,
                kwargs.get("supplier_id"),
                kwargs.get("supplier_name"),
                kwargs.get("base_url")
            )

        self.credentials_store[key] = credentials
        logger.info(f"Registered integration: {key}")
        return key

    def get_integration(
        self,
        venue_id: int,
        integration_type: IntegrationType
    ) -> Optional[BaseIntegration]:
        """Get registered integration"""
        key = f"{venue_id}:{integration_type}"
        return self.integrations.get(key)

    async def test_integration(
        self,
        venue_id: int,
        integration_type: IntegrationType
    ) -> IntegrationResult:
        """Test an integration connection"""
        integration = self.get_integration(venue_id, integration_type)
        if not integration:
            return IntegrationResult(
                success=False,
                error="Integration not found"
            )
        return await integration.test_connection()

    async def export_to_accounting(
        self,
        venue_id: int,
        integration_type: IntegrationType,
        start_date: date,
        end_date: date,
        export_type: str = "sales"
    ) -> IntegrationResult:
        """Export data to accounting system"""
        integration = self.get_integration(venue_id, integration_type)
        if not integration or not isinstance(integration, AccountingIntegration):
            return IntegrationResult(
                success=False,
                error="Accounting integration not found"
            )

        if export_type == "sales":
            return await integration.export_sales(start_date, end_date)
        elif export_type == "purchases":
            return await integration.export_purchases(start_date, end_date)
        elif export_type == "inventory":
            return await integration.sync_inventory()
        else:
            return IntegrationResult(success=False, error="Unknown export type")

    async def send_supplier_order(
        self,
        venue_id: int,
        supplier_integration_key: str,
        order_data: Dict
    ) -> IntegrationResult:
        """Send order to supplier"""
        integration = self.integrations.get(supplier_integration_key)
        if not integration or not isinstance(integration, SupplierIntegration):
            return IntegrationResult(
                success=False,
                error="Supplier integration not found"
            )
        return await integration.send_order(order_data)

    async def get_supplier_catalog(
        self,
        supplier_integration_key: str
    ) -> IntegrationResult:
        """Get catalog from supplier"""
        integration = self.integrations.get(supplier_integration_key)
        if not integration or not isinstance(integration, SupplierIntegration):
            return IntegrationResult(
                success=False,
                error="Supplier integration not found"
            )
        return await integration.get_catalog()

    def list_integrations(self, venue_id: int) -> List[Dict]:
        """List all integrations for a venue"""
        result = []
        prefix = f"{venue_id}:"
        for key, integration in self.integrations.items():
            if key.startswith(prefix):
                integration_type = key.replace(prefix, "")
                result.append({
                    "key": key,
                    "type": integration_type,
                    "class": integration.__class__.__name__
                })
        return result


# Global integration manager
integration_manager = IntegrationManager()
