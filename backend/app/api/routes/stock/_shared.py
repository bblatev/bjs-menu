"""Stock routes - Comprehensive stock management endpoints.

Consolidated from stock.py + stock_management.py. Provides all stock
management functionality: items, movements, alerts, transfers, adjustments,
waste, counts, par levels, variance, cost analysis, shrinkage detection,
AI shelf scanning, availability checks, reservations, and multi-location
aggregation.

Business Logic Flows (merged from stock_management):
- Transfer: TRANSFER_OUT from source + TRANSFER_IN to destination (paired movements)
- Adjustment: ADJUSTMENT movement with reason tracking
- Shrinkage: Theoretical (recipe x sales) vs Actual (inventory counts) analysis
- Cost: FIFO, weighted average, and last cost tracking per product
- AI Scanner: Camera-based shelf scanning -> inventory count sessions
- Reservation: Reserve stock for in-progress orders
- Multi-location: Aggregate view and transfer suggestions
"""

import logging
import random
import uuid
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, UploadFile

from app.core.rate_limit import limiter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, and_, or_

from app.db.session import DbSession
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.product import Product
from app.models.location import Location
from app.models.order import PurchaseOrder, PurchaseOrderLine
from app.models.inventory import InventorySession, InventoryLine, SessionStatus
from app.services.stock_deduction_service import StockDeductionService
from app.services.stock_alert_service import StockAlertService
from app.services.stock_count_service import StockCountService
from app.models.menu_inventory_complete import (
    StockItemBarcode, StockBatchFIFO, ShrinkageRecord,
    CycleCountSchedule, CycleCountTask, CycleCountItem, UnitConversion,
    ReconciliationSession, ReconciliationItem, SupplierPerformanceRecord,
    ReorderPriority, CountType, ShrinkageReason, ReconciliationStatus
)
from app.models.feature_models import AutoReorderRule

logger = logging.getLogger(__name__)



