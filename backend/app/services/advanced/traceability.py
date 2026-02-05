"""Blockchain Supply Chain Traceability Service."""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
import hashlib
import secrets

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import SupplyChainTrace


class TraceabilityService:
    """Service for supply chain traceability."""

    def __init__(self, db: Session):
        self.db = db

    def _generate_trace_id(self) -> str:
        """Generate a unique trace ID."""
        return f"TRC-{secrets.token_hex(8).upper()}"

    def _generate_blockchain_hash(
        self,
        trace_data: Dict[str, Any],
    ) -> str:
        """Generate a blockchain hash for trace data."""
        # Simplified hash - in production would use actual blockchain
        data_str = str(sorted(trace_data.items()))
        return hashlib.sha256(data_str.encode()).hexdigest()

    def create_trace(
        self,
        product_id: int,
        batch_id: Optional[int] = None,
        trace_id: Optional[str] = None,
        farm_name: Optional[str] = None,
        farm_location: Optional[str] = None,
        harvest_date: Optional[date] = None,
        processor_name: Optional[str] = None,
        processing_date: Optional[date] = None,
        distributor_name: Optional[str] = None,
        ship_date: Optional[date] = None,
        received_date: Optional[date] = None,
        certifications: Optional[List[str]] = None,
    ) -> SupplyChainTrace:
        """Create a supply chain trace record."""
        if not trace_id:
            trace_id = self._generate_trace_id()

        # Generate blockchain hash
        trace_data = {
            "trace_id": trace_id,
            "product_id": product_id,
            "farm": farm_name,
            "harvest": str(harvest_date) if harvest_date else None,
            "processor": processor_name,
            "distributor": distributor_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
        blockchain_hash = self._generate_blockchain_hash(trace_data)

        trace = SupplyChainTrace(
            product_id=product_id,
            batch_id=batch_id,
            trace_id=trace_id,
            farm_name=farm_name,
            farm_location=farm_location,
            harvest_date=harvest_date,
            processor_name=processor_name,
            processing_date=processing_date,
            distributor_name=distributor_name,
            ship_date=ship_date,
            received_date=received_date,
            certifications=certifications,
            blockchain_hash=blockchain_hash,
            blockchain_verified=True,  # Auto-verified on creation
        )
        self.db.add(trace)
        self.db.commit()
        self.db.refresh(trace)

        # Generate QR code URL
        trace.qr_code_url = f"/api/v1/traceability/qr/{trace_id}"
        self.db.commit()

        return trace

    def get_trace(
        self,
        trace_id: str,
    ) -> Optional[SupplyChainTrace]:
        """Get a trace by ID."""
        query = select(SupplyChainTrace).where(SupplyChainTrace.trace_id == trace_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_product_traces(
        self,
        product_id: int,
    ) -> List[SupplyChainTrace]:
        """Get all traces for a product."""
        query = select(SupplyChainTrace).where(
            SupplyChainTrace.product_id == product_id
        ).order_by(SupplyChainTrace.created_at.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_batch_trace(
        self,
        batch_id: int,
    ) -> Optional[SupplyChainTrace]:
        """Get trace for a specific batch."""
        query = select(SupplyChainTrace).where(SupplyChainTrace.batch_id == batch_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def verify_trace(
        self,
        trace_id: str,
    ) -> Dict[str, Any]:
        """Verify a trace on the blockchain."""
        trace = self.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")

        # Recalculate hash
        trace_data = {
            "trace_id": trace.trace_id,
            "product_id": trace.product_id,
            "farm": trace.farm_name,
            "harvest": str(trace.harvest_date) if trace.harvest_date else None,
            "processor": trace.processor_name,
            "distributor": trace.distributor_name,
            "timestamp": trace.created_at.isoformat() if trace.created_at else None,
        }
        expected_hash = self._generate_blockchain_hash(trace_data)

        is_verified = expected_hash == trace.blockchain_hash

        return {
            "trace_id": trace_id,
            "is_verified": is_verified,
            "blockchain_hash": trace.blockchain_hash,
            "verification_timestamp": datetime.utcnow().isoformat(),
            "chain_integrity": is_verified,
        }

    def get_chain_of_custody(
        self,
        trace_id: str,
    ) -> List[Dict[str, Any]]:
        """Get chain of custody for a trace."""
        trace = self.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")

        chain = []

        if trace.farm_name:
            chain.append({
                "step": 1,
                "entity": trace.farm_name,
                "type": "farm",
                "location": trace.farm_location,
                "date": trace.harvest_date.isoformat() if trace.harvest_date else None,
                "action": "Harvested",
            })

        if trace.processor_name:
            chain.append({
                "step": 2,
                "entity": trace.processor_name,
                "type": "processor",
                "date": trace.processing_date.isoformat() if trace.processing_date else None,
                "action": "Processed",
            })

        if trace.distributor_name:
            chain.append({
                "step": 3,
                "entity": trace.distributor_name,
                "type": "distributor",
                "date": trace.ship_date.isoformat() if trace.ship_date else None,
                "action": "Shipped",
            })

        if trace.received_date:
            chain.append({
                "step": 4,
                "entity": "Restaurant",
                "type": "destination",
                "date": trace.received_date.isoformat(),
                "action": "Received",
            })

        return chain

    def query_traceability(
        self,
        trace_id: str,
    ) -> Dict[str, Any]:
        """Full traceability query for customer-facing display."""
        trace = self.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")

        chain = self.get_chain_of_custody(trace_id)
        verification = self.verify_trace(trace_id)

        # Calculate days from farm
        days_from_farm = None
        if trace.harvest_date and trace.received_date:
            days_from_farm = (trace.received_date - trace.harvest_date).days

        # Calculate sustainability score (simplified)
        sustainability_score = 70  # Base
        if trace.certifications:
            if "organic" in trace.certifications:
                sustainability_score += 15
            if "fair_trade" in trace.certifications:
                sustainability_score += 10
            if "sustainable" in trace.certifications:
                sustainability_score += 5

        return {
            "product_name": f"Product #{trace.product_id}",  # Would lookup actual name
            "trace": trace,
            "chain_of_custody": chain,
            "certifications": trace.certifications or [],
            "days_from_farm": days_from_farm,
            "sustainability_score": min(100, sustainability_score),
            "blockchain_verified": verification["is_verified"],
        }

    def update_trace(
        self,
        trace_id: str,
        **updates,
    ) -> SupplyChainTrace:
        """Update a trace record."""
        trace = self.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")

        for key, value in updates.items():
            if hasattr(trace, key) and key not in ["id", "trace_id", "blockchain_hash"]:
                setattr(trace, key, value)

        # Regenerate blockchain hash after update
        trace_data = {
            "trace_id": trace.trace_id,
            "product_id": trace.product_id,
            "farm": trace.farm_name,
            "harvest": str(trace.harvest_date) if trace.harvest_date else None,
            "processor": trace.processor_name,
            "distributor": trace.distributor_name,
            "timestamp": trace.created_at.isoformat() if trace.created_at else None,
        }
        trace.blockchain_hash = self._generate_blockchain_hash(trace_data)

        self.db.commit()
        self.db.refresh(trace)
        return trace

    def add_certification(
        self,
        trace_id: str,
        certification: str,
    ) -> SupplyChainTrace:
        """Add a certification to a trace."""
        trace = self.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")

        certs = trace.certifications or []
        if certification not in certs:
            trace.certifications = certs + [certification]
            self.db.commit()
            self.db.refresh(trace)

        return trace
