"""
Serial/Batch Tracking Service
Complete implementation for item tracking, warranty, and expiry management
"""

from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
import logging

from app.models.complete_modules import (
    SerialNumber, BatchTracking, SerialHistory
)
from app.models import StockItem

logger = logging.getLogger(__name__)


class SerialBatchService:
    """Service for serial number and batch tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== SERIAL NUMBER MANAGEMENT ====================
    
    def register_serial_number(
        self,
        stock_item_id: int,
        serial_number: str,
        batch_number: Optional[str] = None,
        manufacture_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
        supplier_id: Optional[int] = None,
        purchase_order_id: Optional[int] = None,
        warranty_months: Optional[int] = None,
        current_location: Optional[str] = None,
        notes: Optional[str] = None
    ) -> SerialNumber:
        """Register a new serial number"""
        
        # Check if serial number already exists
        existing = self.db.query(SerialNumber).filter(
            SerialNumber.serial_number == serial_number
        ).first()
        
        if existing:
            raise ValueError(f"Serial number {serial_number} already exists")
        
        # Verify stock item exists
        stock_item = self.db.query(StockItem).filter(
            StockItem.id == stock_item_id
        ).first()
        
        if not stock_item:
            raise ValueError(f"Stock item {stock_item_id} not found")
        
        # Calculate warranty expiry
        warranty_expires = None
        if warranty_months:
            received_date = datetime.now()
            warranty_expires = (
                received_date + timedelta(days=warranty_months * 30)
            ).date()
        
        # Create serial number record
        serial = SerialNumber(
            stock_item_id=stock_item_id,
            serial_number=serial_number,
            batch_number=batch_number,
            manufacture_date=manufacture_date,
            expiry_date=expiry_date,
            supplier_id=supplier_id,
            purchase_order_id=purchase_order_id,
            received_date=datetime.now(),
            warranty_months=warranty_months,
            warranty_expires=warranty_expires,
            status='in_stock',
            current_location=current_location or 'Main Warehouse',
            notes=notes
        )
        
        self.db.add(serial)
        
        # Create history entry
        history = SerialHistory(
            serial_number_id=serial.id,
            event_type='received',
            to_location=current_location or 'Main Warehouse',
            notes=f"Registered serial number from supplier"
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(serial)
        
        logger.info(f"Registered serial number {serial_number}")
        
        return serial
    
    def get_serial_number(self, serial_number: str) -> Optional[Dict]:
        """Get serial number details"""
        
        serial = self.db.query(SerialNumber).filter(
            SerialNumber.serial_number == serial_number
        ).first()
        
        if not serial:
            return None
        
        # Build response
        result = {
            'id': serial.id,
            'stock_item_id': serial.stock_item_id,
            'stock_item_name': serial.stock_item.name if serial.stock_item else None,
            'serial_number': serial.serial_number,
            'batch_number': serial.batch_number,
            'manufacture_date': serial.manufacture_date,
            'expiry_date': serial.expiry_date,
            'supplier_name': serial.supplier.name if serial.supplier else None,
            'warranty_months': serial.warranty_months,
            'warranty_expires': serial.warranty_expires,
            'status': serial.status,
            'current_location': serial.current_location,
            'sold_to_customer': serial.customer.name if serial.customer else None,
            'sold_date': serial.sold_date,
            'created_at': serial.created_at
        }
        
        return result
    
    def get_serial_history(self, serial_number: str) -> Optional[List[Dict]]:
        """Get complete history for serial number"""
        
        serial = self.db.query(SerialNumber).filter(
            SerialNumber.serial_number == serial_number
        ).first()
        
        if not serial:
            return None
        
        history = self.db.query(SerialHistory).filter(
            SerialHistory.serial_number_id == serial.id
        ).order_by(SerialHistory.event_date.desc()).all()
        
        result = []
        for entry in history:
            result.append({
                'id': entry.id,
                'event_type': entry.event_type,
                'event_date': entry.event_date,
                'from_location': entry.from_location,
                'to_location': entry.to_location,
                'staff_name': entry.staff.full_name if entry.staff else None,
                'customer_name': entry.customer.name if entry.customer else None,
                'notes': entry.notes
            })
        
        return result
    
    def list_serial_numbers(
        self,
        stock_item_id: Optional[int] = None,
        status: Optional[str] = None,
        expiring_days: Optional[int] = None,
        warranty_expiring_days: Optional[int] = None,
        supplier_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict]:
        """List serial numbers with filters"""
        
        query = self.db.query(SerialNumber)
        
        if stock_item_id:
            query = query.filter(SerialNumber.stock_item_id == stock_item_id)
        
        if status:
            query = query.filter(SerialNumber.status == status)
        
        if expiring_days:
            expiry_threshold = date.today() + timedelta(days=expiring_days)
            query = query.filter(
                SerialNumber.expiry_date <= expiry_threshold,
                SerialNumber.expiry_date >= date.today(),
                SerialNumber.status == 'in_stock'
            )
        
        if warranty_expiring_days:
            warranty_threshold = date.today() + timedelta(days=warranty_expiring_days)
            query = query.filter(
                SerialNumber.warranty_expires <= warranty_threshold,
                SerialNumber.warranty_expires >= date.today()
            )
        
        if supplier_id:
            query = query.filter(SerialNumber.supplier_id == supplier_id)
        
        serials = query.offset(skip).limit(limit).all()
        
        result = []
        for serial in serials:
            result.append(self.get_serial_number(serial.serial_number))
        
        return result
    
    def update_serial_status(
        self,
        serial_number: str,
        new_status: str,
        reason: Optional[str] = None
    ) -> Dict:
        """Update serial number status"""
        
        serial = self.db.query(SerialNumber).filter(
            SerialNumber.serial_number == serial_number
        ).first()
        
        if not serial:
            raise ValueError(f"Serial number {serial_number} not found")
        
        old_status = serial.status
        serial.status = new_status
        
        # Create history entry
        history = SerialHistory(
            serial_number_id=serial.id,
            event_type='status_change',
            notes=f"Status changed from {old_status} to {new_status}. {reason or ''}"
        )
        self.db.add(history)
        
        self.db.commit()
        
        logger.info(f"Updated serial {serial_number} status: {old_status} -> {new_status}")
        
        return self.get_serial_number(serial_number)
    
    def move_serial_number(
        self,
        serial_number: str,
        to_location: str,
        staff_id: int,
        notes: Optional[str] = None
    ) -> Dict:
        """Move serial number to new location"""
        
        serial = self.db.query(SerialNumber).filter(
            SerialNumber.serial_number == serial_number
        ).first()
        
        if not serial:
            raise ValueError(f"Serial number {serial_number} not found")
        
        from_location = serial.current_location
        serial.current_location = to_location
        
        # Create history entry
        history = SerialHistory(
            serial_number_id=serial.id,
            event_type='moved',
            from_location=from_location,
            to_location=to_location,
            staff_id=staff_id,
            notes=notes
        )
        self.db.add(history)
        
        self.db.commit()
        
        logger.info(f"Moved serial {serial_number}: {from_location} -> {to_location}")
        
        return self.get_serial_number(serial_number)
    
    # ==================== BATCH TRACKING ====================
    
    def create_batch(
        self,
        batch_number: str,
        stock_item_id: int,
        quantity_received: int,
        manufacture_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
        supplier_id: Optional[int] = None,
        auto_writeoff: bool = True
    ) -> Dict:
        """Create new batch"""
        
        # Check if batch exists
        existing = self.db.query(BatchTracking).filter(
            BatchTracking.batch_number == batch_number,
            BatchTracking.stock_item_id == stock_item_id
        ).first()
        
        if existing:
            raise ValueError(f"Batch {batch_number} already exists for this item")
        
        # Verify stock item
        stock_item = self.db.query(StockItem).filter(
            StockItem.id == stock_item_id
        ).first()
        
        if not stock_item:
            raise ValueError(f"Stock item {stock_item_id} not found")
        
        # Create batch
        batch = BatchTracking(
            batch_number=batch_number,
            stock_item_id=stock_item_id,
            quantity_received=quantity_received,
            quantity_remaining=quantity_received,
            manufacture_date=manufacture_date,
            expiry_date=expiry_date,
            supplier_id=supplier_id,
            received_date=datetime.now(),
            status='active',
            auto_writeoff=auto_writeoff
        )
        
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        
        logger.info(f"Created batch {batch_number} with {quantity_received} units")
        
        return self._batch_to_dict(batch)
    
    def list_batches(
        self,
        stock_item_id: Optional[int] = None,
        status: Optional[str] = None,
        expiring_days: Optional[int] = None,
        supplier_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict]:
        """List batches with filters"""
        
        query = self.db.query(BatchTracking)
        
        if stock_item_id:
            query = query.filter(BatchTracking.stock_item_id == stock_item_id)
        
        if status:
            query = query.filter(BatchTracking.status == status)
        
        if expiring_days:
            expiry_threshold = date.today() + timedelta(days=expiring_days)
            query = query.filter(
                BatchTracking.expiry_date <= expiry_threshold,
                BatchTracking.expiry_date >= date.today(),
                BatchTracking.status == 'active'
            )
        
        if supplier_id:
            query = query.filter(BatchTracking.supplier_id == supplier_id)
        
        batches = query.offset(skip).limit(limit).all()
        
        return [self._batch_to_dict(b) for b in batches]
    
    def get_expiring_batches(
        self,
        days: int = 7,
        venue_id: Optional[int] = None
    ) -> List[Dict]:
        """Get batches expiring soon"""
        
        expiry_threshold = date.today() + timedelta(days=days)
        
        query = self.db.query(BatchTracking).filter(
            BatchTracking.expiry_date <= expiry_threshold,
            BatchTracking.expiry_date >= date.today(),
            BatchTracking.status == 'active',
            BatchTracking.quantity_remaining > 0
        ).order_by(BatchTracking.expiry_date.asc())
        
        batches = query.all()
        
        return [self._batch_to_dict(b) for b in batches]
    
    def writeoff_batch(
        self,
        batch_id: int,
        quantity: Optional[int],
        reason: str,
        staff_id: int
    ) -> Dict:
        """Writeoff batch (manual)"""
        
        batch = self.db.query(BatchTracking).filter(
            BatchTracking.id == batch_id
        ).first()
        
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        # Determine writeoff quantity
        writeoff_qty = quantity if quantity else batch.quantity_remaining
        
        if writeoff_qty > batch.quantity_remaining:
            raise ValueError(
                f"Cannot writeoff {writeoff_qty}: only {batch.quantity_remaining} remaining"
            )
        
        # Update batch
        batch.quantity_remaining -= writeoff_qty
        
        if batch.quantity_remaining == 0:
            batch.status = 'depleted'
        
        self.db.commit()
        
        logger.info(
            f"Written off {writeoff_qty} units from batch {batch.batch_number}. "
            f"Reason: {reason}"
        )
        
        return {
            'batch_number': batch.batch_number,
            'quantity': writeoff_qty,
            'remaining': batch.quantity_remaining,
            'reason': reason
        }
    
    def auto_expire_batches(self) -> Dict:
        """Automatically expire batches past expiry date"""
        
        today = date.today()
        
        expired = self.db.query(BatchTracking).filter(
            BatchTracking.expiry_date < today,
            BatchTracking.status == 'active',
            BatchTracking.auto_writeoff == True
        ).all()
        
        expired_list = []
        for batch in expired:
            batch.status = 'expired'
            expired_list.append({
                'batch_number': batch.batch_number,
                'stock_item': batch.stock_item.name if batch.stock_item else None,
                'quantity_remaining': batch.quantity_remaining,
                'expiry_date': batch.expiry_date
            })
            
            logger.warning(
                f"Auto-expired batch {batch.batch_number}: "
                f"{batch.quantity_remaining} units lost"
            )
        
        self.db.commit()
        
        return {
            'count': len(expired),
            'batches': expired_list
        }
    
    def get_batch_items(self, batch_number: str) -> Optional[List[str]]:
        """Get serial numbers in a batch"""
        
        batch = self.db.query(BatchTracking).filter(
            BatchTracking.batch_number == batch_number
        ).first()
        
        if not batch:
            return None
        
        # Get serial numbers associated with this batch
        serials = self.db.query(SerialNumber).filter(
            SerialNumber.batch_number == batch_number
        ).all()
        
        return [s.serial_number for s in serials]
    
    # ==================== REPORTING ====================
    
    def get_expiring_warranties(self, days: int = 30) -> List[Dict]:
        """Get items with warranties expiring soon"""
        
        threshold = date.today() + timedelta(days=days)
        
        serials = self.db.query(SerialNumber).filter(
            SerialNumber.warranty_expires <= threshold,
            SerialNumber.warranty_expires >= date.today(),
            SerialNumber.status == 'sold'
        ).all()
        
        result = []
        for serial in serials:
            result.append({
                'serial_number': serial.serial_number,
                'stock_item': serial.stock_item.name if serial.stock_item else None,
                'customer': serial.customer.name if serial.customer else None,
                'warranty_expires': serial.warranty_expires,
                'days_remaining': (serial.warranty_expires - date.today()).days
            })
        
        return result
    
    def get_batch_report(
        self,
        venue_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """Get comprehensive batch report"""
        
        query = self.db.query(BatchTracking)
        
        if start_date and end_date:
            query = query.filter(
                BatchTracking.received_date >= start_date,
                BatchTracking.received_date <= end_date
            )
        
        all_batches = query.all()
        
        active = [b for b in all_batches if b.status == 'active']
        expired = [b for b in all_batches if b.status == 'expired']
        depleted = [b for b in all_batches if b.status == 'depleted']
        
        # Calculate expiring soon
        expiring_7 = self.get_expiring_batches(days=7, venue_id=venue_id)
        expiring_30 = self.get_expiring_batches(days=30, venue_id=venue_id)
        
        return {
            'total_batches': len(all_batches),
            'active': len(active),
            'expired': len(expired),
            'depleted': len(depleted),
            'expiring_7_days': len(expiring_7),
            'expiring_30_days': len(expiring_30),
            'total_units_active': sum(b.quantity_remaining for b in active),
            'total_units_expired': sum(b.quantity_remaining for b in expired if b.quantity_remaining > 0)
        }
    
    # ==================== HELPER METHODS ====================
    
    def _batch_to_dict(self, batch: BatchTracking) -> Dict:
        """Convert batch to dictionary"""
        
        days_until_expiry = None
        if batch.expiry_date:
            days_until_expiry = (batch.expiry_date - date.today()).days
        
        return {
            'id': batch.id,
            'batch_number': batch.batch_number,
            'stock_item_id': batch.stock_item_id,
            'stock_item_name': batch.stock_item.name if batch.stock_item else None,
            'quantity_received': batch.quantity_received,
            'quantity_remaining': batch.quantity_remaining,
            'manufacture_date': batch.manufacture_date,
            'expiry_date': batch.expiry_date,
            'days_until_expiry': days_until_expiry,
            'supplier_name': batch.supplier.name if batch.supplier else None,
            'status': batch.status,
            'auto_writeoff': batch.auto_writeoff,
            'received_date': batch.received_date
        }
