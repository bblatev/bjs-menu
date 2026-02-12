"""
IoT & Hardware Integration Service - Section W
Temperature monitoring, smart pour meters, scales, and device management
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid


class IoTService:
    """Service for IoT device management and sensor data processing."""
    
    # ==================== DEVICE MANAGEMENT ====================
    
    @staticmethod
    def register_device(
        db: Session,
        venue_id: int,
        device_type: str,  # "temperature_sensor", "pour_meter", "scale", "camera"
        device_name: str,
        serial_number: str,
        location: str,
        configuration: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Register a new IoT device."""
        from app.models.advanced_features_v9 import IoTDevice
        
        # Check if device already exists
        existing = db.query(IoTDevice).filter(
            IoTDevice.serial_number == serial_number
        ).first()
        
        if existing:
            raise ValueError(f"Device with serial {serial_number} already registered")
        
        device = IoTDevice(
            venue_id=venue_id,
            device_type=device_type,
            device_name=device_name,
            serial_number=serial_number,
            location=location,
            status="active",
            configuration=configuration or {},
            last_seen=datetime.utcnow(),
            firmware_version=None,
            battery_level=None
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        
        return {
            "id": device.id,
            "device_type": device.device_type,
            "device_name": device.device_name,
            "serial_number": device.serial_number,
            "location": device.location,
            "status": device.status,
            "configuration": device.configuration,
            "message": "Device registered successfully"
        }
    
    @staticmethod
    def update_device_status(
        db: Session,
        device_id: int,
        status: str,
        battery_level: Optional[int] = None,
        firmware_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update device status and metrics."""
        from app.models.advanced_features_v9 import IoTDevice
        
        device = db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        device.status = status
        device.last_seen = datetime.utcnow()
        
        if battery_level is not None:
            device.battery_level = battery_level
        if firmware_version:
            device.firmware_version = firmware_version
        
        device.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(device)
        
        return {
            "id": device.id,
            "status": device.status,
            "last_seen": device.last_seen.isoformat(),
            "battery_level": device.battery_level,
            "firmware_version": device.firmware_version
        }
    
    @staticmethod
    def get_devices(
        db: Session,
        venue_id: int,
        device_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all devices for a venue."""
        from app.models.advanced_features_v9 import IoTDevice
        
        query = db.query(IoTDevice).filter(IoTDevice.venue_id == venue_id)
        
        if device_type:
            query = query.filter(IoTDevice.device_type == device_type)
        if status:
            query = query.filter(IoTDevice.status == status)
        
        devices = query.all()
        
        return [{
            "id": d.id,
            "device_type": d.device_type,
            "device_name": d.device_name,
            "serial_number": d.serial_number,
            "location": d.location,
            "status": d.status,
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
            "battery_level": d.battery_level,
            "firmware_version": d.firmware_version,
            "is_online": (datetime.utcnow() - d.last_seen).seconds < 300 if d.last_seen else False
        } for d in devices]
    
    @staticmethod
    def get_offline_devices(
        db: Session,
        venue_id: int,
        offline_threshold_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """Get devices that haven't reported in recently."""
        from app.models.advanced_features_v9 import IoTDevice
        
        threshold = datetime.utcnow() - timedelta(minutes=offline_threshold_minutes)
        
        offline = db.query(IoTDevice).filter(
            IoTDevice.venue_id == venue_id,
            IoTDevice.status == "active",
            or_(
                IoTDevice.last_seen < threshold,
                IoTDevice.last_seen.is_(None)
            )
        ).all()
        
        return [{
            "id": d.id,
            "device_type": d.device_type,
            "device_name": d.device_name,
            "location": d.location,
            "last_seen": d.last_seen.isoformat() if d.last_seen else "Never",
            "minutes_offline": int((datetime.utcnow() - d.last_seen).seconds / 60) if d.last_seen else None
        } for d in offline]
    
    # ==================== TEMPERATURE MONITORING (HACCP) ====================
    
    @staticmethod
    def record_temperature(
        db: Session,
        device_id: int,
        temperature: Decimal,
        unit: str = "C",
        humidity: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Record temperature reading from a sensor."""
        from app.models.advanced_features_v9 import IoTDevice, TemperatureLog
        
        device = db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        if device.device_type != "temperature_sensor":
            raise ValueError(f"Device {device_id} is not a temperature sensor")
        
        # Get thresholds from device configuration
        config = device.configuration or {}
        min_temp = Decimal(str(config.get("min_temp", -25)))
        max_temp = Decimal(str(config.get("max_temp", 5)))
        
        # Determine if alert needed
        alert_triggered = temperature < min_temp or temperature > max_temp
        alert_type = None
        if temperature < min_temp:
            alert_type = "below_minimum"
        elif temperature > max_temp:
            alert_type = "above_maximum"
        
        log = TemperatureLog(
            device_id=device_id,
            venue_id=device.venue_id,
            location=device.location,
            temperature=temperature,
            temperature_unit=unit,
            humidity=humidity,
            min_threshold=min_temp,
            max_threshold=max_temp,
            alert_triggered=alert_triggered,
            alert_type=alert_type,
            acknowledged=False
        )
        db.add(log)
        
        # Update device last seen
        device.last_seen = datetime.utcnow()
        
        db.commit()
        db.refresh(log)
        
        result = {
            "id": log.id,
            "device_id": device_id,
            "location": device.location,
            "temperature": float(temperature),
            "unit": unit,
            "humidity": float(humidity) if humidity else None,
            "recorded_at": log.created_at.isoformat(),
            "within_range": not alert_triggered
        }
        
        if alert_triggered:
            result["alert"] = {
                "type": alert_type,
                "message": f"Temperature {temperature}°{unit} is outside safe range ({min_temp}-{max_temp}°{unit})",
                "severity": "critical",
                "requires_action": True
            }
        
        return result
    
    @staticmethod
    def get_temperature_history(
        db: Session,
        venue_id: int,
        device_id: Optional[int] = None,
        location: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        alerts_only: bool = False
    ) -> Dict[str, Any]:
        """Get temperature history for HACCP compliance."""
        from app.models.advanced_features_v9 import TemperatureLog
        
        query = db.query(TemperatureLog).filter(TemperatureLog.venue_id == venue_id)
        
        if device_id:
            query = query.filter(TemperatureLog.device_id == device_id)
        if location:
            query = query.filter(TemperatureLog.location == location)
        if start_date:
            query = query.filter(TemperatureLog.created_at >= start_date)
        if end_date:
            query = query.filter(TemperatureLog.created_at <= end_date)
        if alerts_only:
            query = query.filter(TemperatureLog.alert_triggered == True)
        
        logs = query.order_by(TemperatureLog.created_at.desc()).limit(1000).all()
        
        return {
            "venue_id": venue_id,
            "total_readings": len(logs),
            "alerts_count": sum(1 for l in logs if l.alert_triggered),
            "readings": [{
                "id": l.id,
                "device_id": l.device_id,
                "location": l.location,
                "temperature": float(l.temperature),
                "unit": l.temperature_unit,
                "humidity": float(l.humidity) if l.humidity else None,
                "recorded_at": l.created_at.isoformat(),
                "alert_triggered": l.alert_triggered,
                "alert_type": l.alert_type,
                "acknowledged": l.acknowledged
            } for l in logs]
        }
    
    @staticmethod
    def acknowledge_temperature_alert(
        db: Session,
        log_id: int,
        acknowledged_by: int,
        corrective_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """Acknowledge a temperature alert."""
        from app.models.advanced_features_v9 import TemperatureLog
        
        log = db.query(TemperatureLog).filter(TemperatureLog.id == log_id).first()
        if not log:
            raise ValueError(f"Temperature log {log_id} not found")
        
        log.acknowledged = True
        log.acknowledged_by = acknowledged_by
        log.acknowledged_at = datetime.utcnow()
        log.corrective_action = corrective_action
        log.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(log)
        
        return {
            "id": log.id,
            "acknowledged": True,
            "acknowledged_by": acknowledged_by,
            "acknowledged_at": log.acknowledged_at.isoformat(),
            "corrective_action": corrective_action
        }
    
    @staticmethod
    def get_haccp_compliance_report(
        db: Session,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Generate HACCP compliance report for inspections."""
        from app.models.advanced_features_v9 import TemperatureLog, IoTDevice
        
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        # Get all readings in period
        logs = db.query(TemperatureLog).filter(
            TemperatureLog.venue_id == venue_id,
            TemperatureLog.created_at >= start_dt,
            TemperatureLog.created_at <= end_dt
        ).all()
        
        # Group by location
        by_location = {}
        for log in logs:
            if log.location not in by_location:
                by_location[log.location] = {
                    "readings": 0,
                    "alerts": 0,
                    "acknowledged_alerts": 0,
                    "min_temp": float(log.temperature),
                    "max_temp": float(log.temperature),
                    "avg_temp": 0
                }
            
            loc = by_location[log.location]
            loc["readings"] += 1
            loc["min_temp"] = min(loc["min_temp"], float(log.temperature))
            loc["max_temp"] = max(loc["max_temp"], float(log.temperature))
            
            if log.alert_triggered:
                loc["alerts"] += 1
                if log.alert_acknowledged:
                    loc["acknowledged_alerts"] += 1
        
        # Calculate averages
        for loc in by_location.values():
            # Simplified - would calculate actual average
            loc["avg_temp"] = (loc["min_temp"] + loc["max_temp"]) / 2
        
        total_readings = len(logs)
        total_alerts = sum(1 for l in logs if l.alert_triggered)
        acknowledged_alerts = sum(1 for l in logs if l.alert_triggered and l.alert_acknowledged)
        
        compliance_score = 100
        if total_alerts > 0:
            compliance_score = max(0, 100 - (total_alerts / total_readings * 100))
        
        return {
            "venue_id": venue_id,
            "report_period": {"start": str(start_date), "end": str(end_date)},
            "summary": {
                "total_readings": total_readings,
                "total_alerts": total_alerts,
                "acknowledged_alerts": acknowledged_alerts,
                "unacknowledged_alerts": total_alerts - acknowledged_alerts,
                "compliance_score": round(compliance_score, 1)
            },
            "by_location": by_location,
            "compliance_status": "compliant" if compliance_score >= 95 else "needs_attention" if compliance_score >= 80 else "non_compliant",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # ==================== SMART POUR METERS ====================
    
    @staticmethod
    def record_pour(
        db: Session,
        device_id: int,
        product_id: int,
        poured_amount_ml: Decimal,
        expected_amount_ml: Decimal,
        staff_id: Optional[int] = None,
        order_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Record a pour reading from a smart pour meter."""
        from app.models.advanced_features_v9 import IoTDevice, PourReading
        
        device = db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        if device.device_type != "pour_meter":
            raise ValueError(f"Device {device_id} is not a pour meter")
        
        # Calculate variance
        variance_ml = poured_amount_ml - expected_amount_ml
        variance_percentage = (variance_ml / expected_amount_ml * 100) if expected_amount_ml > 0 else Decimal("0")
        
        # Determine if over/under pour
        config = device.configuration or {}
        tolerance = Decimal(str(config.get("tolerance_percentage", 5)))
        
        is_overpour = variance_percentage > tolerance
        is_underpour = variance_percentage < -tolerance
        
        reading = PourReading(
            device_id=device_id,
            venue_id=device.venue_id,
            product_id=product_id,
            staff_id=staff_id,
            order_id=order_id,
            poured_amount_ml=poured_amount_ml,
            expected_amount_ml=expected_amount_ml,
            variance_ml=variance_ml,
            variance_percentage=variance_percentage,
            is_overpour=is_overpour,
            is_underpour=is_underpour
        )
        db.add(reading)
        
        # Update device last seen
        device.last_seen = datetime.utcnow()
        
        db.commit()
        db.refresh(reading)
        
        result = {
            "id": reading.id,
            "product_id": product_id,
            "poured_ml": float(poured_amount_ml),
            "expected_ml": float(expected_amount_ml),
            "variance_ml": float(variance_ml),
            "variance_percentage": float(variance_percentage),
            "status": "accurate" if not (is_overpour or is_underpour) else "overpour" if is_overpour else "underpour"
        }
        
        if is_overpour:
            # Calculate cost of overpour (would need product cost data)
            result["alert"] = {
                "type": "overpour",
                "message": f"Overpour detected: {float(variance_ml):.1f}ml ({float(variance_percentage):.1f}%) over",
                "severity": "warning"
            }
        elif is_underpour:
            result["alert"] = {
                "type": "underpour",
                "message": f"Underpour detected: {abs(float(variance_ml)):.1f}ml ({abs(float(variance_percentage)):.1f}%) under",
                "severity": "info"
            }
        
        return result
    
    @staticmethod
    def get_pour_analytics(
        db: Session,
        venue_id: int,
        start_date: date,
        end_date: date,
        product_id: Optional[int] = None,
        staff_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get pour accuracy analytics."""
        from app.models.advanced_features_v9 import PourReading
        
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        query = db.query(PourReading).filter(
            PourReading.venue_id == venue_id,
            PourReading.created_at >= start_dt,
            PourReading.created_at <= end_dt
        )
        
        if product_id:
            query = query.filter(PourReading.product_id == product_id)
        if staff_id:
            query = query.filter(PourReading.staff_id == staff_id)
        
        readings = query.all()
        
        if not readings:
            return {
                "venue_id": venue_id,
                "period": {"start": str(start_date), "end": str(end_date)},
                "message": "No pour data for this period"
            }
        
        total_poured = sum(r.poured_amount_ml for r in readings)
        total_expected = sum(r.expected_amount_ml for r in readings)
        total_variance = sum(r.variance_ml for r in readings)
        
        overpours = [r for r in readings if r.is_overpour]
        underpours = [r for r in readings if r.is_underpour]
        
        # Group by staff
        by_staff = {}
        for r in readings:
            if r.staff_id:
                if r.staff_id not in by_staff:
                    by_staff[r.staff_id] = {"pours": 0, "overpours": 0, "underpours": 0, "total_variance": Decimal("0")}
                by_staff[r.staff_id]["pours"] += 1
                if r.is_overpour:
                    by_staff[r.staff_id]["overpours"] += 1
                if r.is_underpour:
                    by_staff[r.staff_id]["underpours"] += 1
                by_staff[r.staff_id]["total_variance"] += r.variance_ml
        
        return {
            "venue_id": venue_id,
            "period": {"start": str(start_date), "end": str(end_date)},
            "summary": {
                "total_pours": len(readings),
                "total_poured_ml": float(total_poured),
                "total_expected_ml": float(total_expected),
                "total_variance_ml": float(total_variance),
                "overpour_count": len(overpours),
                "underpour_count": len(underpours),
                "accuracy_rate": round((1 - (len(overpours) + len(underpours)) / len(readings)) * 100, 1)
            },
            "by_staff": {
                str(staff_id): {
                    "pours": data["pours"],
                    "overpours": data["overpours"],
                    "underpours": data["underpours"],
                    "variance_ml": float(data["total_variance"]),
                    "accuracy_rate": round((1 - (data["overpours"] + data["underpours"]) / data["pours"]) * 100, 1) if data["pours"] > 0 else 100
                }
                for staff_id, data in by_staff.items()
            },
            "estimated_loss_ml": float(sum(r.variance_ml for r in overpours))
        }
    
    # ==================== SCALE INTEGRATION ====================
    
    @staticmethod
    def record_weight(
        db: Session,
        device_id: int,
        item_id: int,
        weight_grams: Decimal,
        expected_weight_grams: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Record weight from a connected scale."""
        from app.models.advanced_features_v9 import IoTDevice
        
        device = db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        if device.device_type != "scale":
            raise ValueError(f"Device {device_id} is not a scale")
        
        # Update device last seen
        device.last_seen = datetime.utcnow()
        db.commit()
        
        result = {
            "device_id": device_id,
            "item_id": item_id,
            "weight_grams": float(weight_grams),
            "recorded_at": datetime.utcnow().isoformat()
        }
        
        if expected_weight_grams:
            variance = weight_grams - expected_weight_grams
            variance_pct = (variance / expected_weight_grams * 100) if expected_weight_grams > 0 else Decimal("0")
            result["expected_weight_grams"] = float(expected_weight_grams)
            result["variance_grams"] = float(variance)
            result["variance_percentage"] = float(variance_pct)
            result["within_tolerance"] = abs(variance_pct) <= 5
        
        return result

    # ==================== RFID INVENTORY TRACKING ====================

    @staticmethod
    def register_rfid_tag(
        db: Session,
        venue_id: int,
        tag_id: str,
        tag_type: str,
        tag_name: Optional[str] = None,
        stock_item_id: Optional[int] = None,
        quantity: float = 1.0,
        unit: Optional[str] = None,
        batch_number: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
        current_zone: Optional[str] = None,
        registered_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Register a new RFID tag for inventory tracking."""
        from app.models.advanced_features_v9 import RFIDTag

        # Check if tag already exists
        existing = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
        if existing:
            raise ValueError(f"RFID tag {tag_id} already registered")

        tag = RFIDTag(
            venue_id=venue_id,
            tag_id=tag_id,
            tag_type=tag_type,
            tag_name=tag_name or f"Tag-{tag_id[:8]}",
            stock_item_id=stock_item_id,
            quantity=quantity,
            unit=unit,
            batch_number=batch_number,
            expiry_date=expiry_date,
            current_zone=current_zone or "receiving",
            status="active",
            is_active=True,
            registered_by=registered_by
        )
        db.add(tag)
        db.commit()
        db.refresh(tag)

        return {
            "id": tag.id,
            "tag_id": tag.tag_id,
            "tag_type": tag.tag_type,
            "tag_name": tag.tag_name,
            "stock_item_id": tag.stock_item_id,
            "quantity": tag.quantity,
            "current_zone": tag.current_zone,
            "status": tag.status,
            "message": "RFID tag registered successfully"
        }

    @staticmethod
    def record_rfid_scan(
        db: Session,
        venue_id: int,
        reader_id: int,
        tag_id: str,
        read_type: str = "inventory_scan",
        location_zone: Optional[str] = None,
        staff_user_id: Optional[int] = None,
        order_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Record an RFID tag scan/read event."""
        from app.models.advanced_features_v9 import RFIDTag, RFIDReading, IoTDevice

        # Validate reader
        reader = db.query(IoTDevice).filter(
            IoTDevice.id == reader_id,
            IoTDevice.device_type == "rfid_reader"
        ).first()
        if not reader:
            raise ValueError(f"RFID reader {reader_id} not found")

        # Find tag
        tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
        if not tag:
            # Unknown tag - record for investigation
            return {
                "status": "unknown_tag",
                "tag_id": tag_id,
                "reader_id": reader_id,
                "message": "Unknown RFID tag detected",
                "alert": True
            }

        # Detect movement
        previous_zone = tag.current_zone
        movement_detected = location_zone and previous_zone and location_zone != previous_zone

        # Create reading record
        reading = RFIDReading(
            venue_id=venue_id,
            reader_id=reader_id,
            tag_id=tag.id,
            read_type=read_type,
            location_zone=location_zone,
            previous_zone=previous_zone if movement_detected else None,
            movement_detected=movement_detected,
            staff_user_id=staff_user_id,
            order_id=order_id
        )

        # Check for alerts
        alert_triggered = False
        alert_type = None

        # Check expiry warning (7 days before)
        if tag.expiry_date:
            days_to_expiry = (tag.expiry_date - datetime.utcnow()).days
            if days_to_expiry <= 7:
                alert_triggered = True
                alert_type = "expiry_warning"

        reading.alert_triggered = alert_triggered
        reading.alert_type = alert_type

        db.add(reading)

        # Update tag location
        if location_zone:
            tag.current_zone = location_zone
            tag.current_location = reader.location_description
            tag.last_reader_id = reader_id
        tag.last_seen = datetime.utcnow()

        # Update reader last seen
        reader.last_seen = datetime.utcnow()

        db.commit()
        db.refresh(reading)

        result = {
            "reading_id": reading.id,
            "tag_id": tag_id,
            "tag_name": tag.tag_name,
            "stock_item_id": tag.stock_item_id,
            "quantity": tag.quantity,
            "read_type": read_type,
            "location_zone": location_zone,
            "movement_detected": movement_detected,
            "read_at": reading.read_at.isoformat()
        }

        if movement_detected:
            result["previous_zone"] = previous_zone

        if alert_triggered:
            result["alert"] = {
                "type": alert_type,
                "message": f"Tag {tag_id} requires attention: {alert_type}"
            }

        return result

    @staticmethod
    def get_rfid_tags(
        db: Session,
        venue_id: int,
        tag_type: Optional[str] = None,
        zone: Optional[str] = None,
        stock_item_id: Optional[int] = None,
        status: Optional[str] = None,
        expiring_within_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get RFID tags with optional filtering."""
        from app.models.advanced_features_v9 import RFIDTag

        query = db.query(RFIDTag).filter(
            RFIDTag.venue_id == venue_id,
            RFIDTag.is_active == True
        )

        if tag_type:
            query = query.filter(RFIDTag.tag_type == tag_type)
        if zone:
            query = query.filter(RFIDTag.current_zone == zone)
        if stock_item_id:
            query = query.filter(RFIDTag.stock_item_id == stock_item_id)
        if status:
            query = query.filter(RFIDTag.status == status)
        if expiring_within_days:
            expiry_threshold = datetime.utcnow() + timedelta(days=expiring_within_days)
            query = query.filter(
                RFIDTag.expiry_date.isnot(None),
                RFIDTag.expiry_date <= expiry_threshold
            )

        tags = query.order_by(RFIDTag.last_seen.desc()).all()

        return {
            "venue_id": venue_id,
            "total_tags": len(tags),
            "tags": [{
                "id": t.id,
                "tag_id": t.tag_id,
                "tag_type": t.tag_type,
                "tag_name": t.tag_name,
                "stock_item_id": t.stock_item_id,
                "quantity": t.quantity,
                "unit": t.unit,
                "current_zone": t.current_zone,
                "current_location": t.current_location,
                "status": t.status,
                "batch_number": t.batch_number,
                "expiry_date": t.expiry_date.isoformat() if t.expiry_date else None,
                "last_seen": t.last_seen.isoformat() if t.last_seen else None,
                "days_to_expiry": (t.expiry_date - datetime.utcnow()).days if t.expiry_date else None
            } for t in tags]
        }

    @staticmethod
    def start_rfid_inventory_count(
        db: Session,
        venue_id: int,
        count_type: str,
        started_by: int,
        zone: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Start an RFID-based inventory count session."""
        from app.models.advanced_features_v9 import RFIDInventoryCount, RFIDTag

        count_id = f"RFID-CNT-{uuid.uuid4().hex[:8].upper()}"

        # Calculate expected tags
        expected_query = db.query(RFIDTag).filter(
            RFIDTag.venue_id == venue_id,
            RFIDTag.is_active == True,
            RFIDTag.status == "active"
        )
        if zone:
            expected_query = expected_query.filter(RFIDTag.current_zone == zone)

        tags_expected = expected_query.count()

        count = RFIDInventoryCount(
            venue_id=venue_id,
            count_id=count_id,
            count_type=count_type,
            zone=zone,
            category_id=category_id,
            status="in_progress",
            tags_expected=tags_expected,
            started_by=started_by
        )
        db.add(count)
        db.commit()
        db.refresh(count)

        return {
            "count_id": count_id,
            "count_type": count_type,
            "zone": zone,
            "tags_expected": tags_expected,
            "status": "in_progress",
            "started_at": count.started_at.isoformat(),
            "message": "RFID inventory count started"
        }

    @staticmethod
    def record_rfid_count_scan(
        db: Session,
        count_id: str,
        tag_ids: List[str]
    ) -> Dict[str, Any]:
        """Record tags found during an inventory count."""
        from app.models.advanced_features_v9 import RFIDInventoryCount, RFIDTag

        count = db.query(RFIDInventoryCount).filter(
            RFIDInventoryCount.count_id == count_id
        ).first()

        if not count:
            raise ValueError(f"Count session {count_id} not found")

        if count.status != "in_progress":
            raise ValueError(f"Count session {count_id} is not in progress")

        # Find tags
        found_tag_ids = []
        for tag_id in tag_ids:
            tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
            if tag:
                found_tag_ids.append(tag.id)

        # Update count
        existing_found = count.found_tags or []
        all_found = list(set(existing_found + found_tag_ids))
        count.found_tags = all_found
        count.tags_found = len(all_found)

        db.commit()

        return {
            "count_id": count_id,
            "tags_scanned": len(tag_ids),
            "tags_matched": len(found_tag_ids),
            "total_found": count.tags_found,
            "tags_expected": count.tags_expected
        }

    @staticmethod
    def complete_rfid_inventory_count(
        db: Session,
        count_id: str,
        completed_by: int,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Complete an RFID inventory count and calculate variances."""
        from app.models.advanced_features_v9 import RFIDInventoryCount, RFIDTag

        count = db.query(RFIDInventoryCount).filter(
            RFIDInventoryCount.count_id == count_id
        ).first()

        if not count:
            raise ValueError(f"Count session {count_id} not found")

        # Get expected tags
        expected_query = db.query(RFIDTag).filter(
            RFIDTag.venue_id == count.venue_id,
            RFIDTag.is_active == True,
            RFIDTag.status == "active"
        )
        if count.zone:
            expected_query = expected_query.filter(RFIDTag.current_zone == count.zone)

        expected_tags = {t.id for t in expected_query.all()}
        found_tags = set(count.found_tags or [])

        # Calculate missing and unexpected
        missing = expected_tags - found_tags
        unexpected = found_tags - expected_tags

        # Calculate value variance
        missing_tags_query = db.query(RFIDTag).filter(RFIDTag.id.in_(missing)) if missing else []
        variance_value = sum(t.current_value or 0 for t in missing_tags_query) if missing else 0

        # Update count
        count.status = "completed"
        count.completed_at = datetime.utcnow()
        count.completed_by = completed_by
        count.tags_missing = len(missing)
        count.tags_unexpected = len(unexpected)
        count.missing_tags = list(missing)
        count.unexpected_tags = list(unexpected)
        count.variance_value = variance_value
        count.variance_items = len(missing)
        count.notes = notes

        db.commit()
        db.refresh(count)

        return {
            "count_id": count_id,
            "status": "completed",
            "tags_expected": count.tags_expected,
            "tags_found": count.tags_found,
            "tags_missing": count.tags_missing,
            "tags_unexpected": count.tags_unexpected,
            "variance_value": variance_value,
            "accuracy_percentage": round((count.tags_found / count.tags_expected * 100), 1) if count.tags_expected > 0 else 100,
            "completed_at": count.completed_at.isoformat()
        }

    @staticmethod
    def update_tag_status(
        db: Session,
        tag_id: str,
        new_status: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update RFID tag status (consumed, expired, lost, etc.)."""
        from app.models.advanced_features_v9 import RFIDTag

        tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
        if not tag:
            raise ValueError(f"RFID tag {tag_id} not found")

        old_status = tag.status
        tag.status = new_status

        if new_status in ["consumed", "expired", "lost", "damaged"]:
            tag.is_active = False
            tag.deactivated_at = datetime.utcnow()
            tag.deactivation_reason = reason

        tag.updated_at = datetime.utcnow()
        db.commit()

        return {
            "tag_id": tag_id,
            "old_status": old_status,
            "new_status": new_status,
            "is_active": tag.is_active,
            "message": f"Tag status updated to {new_status}"
        }

    # ==================== FLOW METER - BULK LIQUIDS ====================

    @staticmethod
    def record_flow_meter_reading(
        db: Session,
        venue_id: int,
        device_id: int,
        meter_type: str,
        flow_volume_ml: float,
        container_id: Optional[str] = None,
        stock_item_id: Optional[int] = None,
        flow_rate_ml_per_sec: Optional[float] = None,
        temperature_celsius: Optional[float] = None,
        pressure_psi: Optional[float] = None,
        order_id: Optional[int] = None,
        staff_user_id: Optional[int] = None,
        tap_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Record a flow meter reading for bulk liquid tracking."""
        from app.models.advanced_features_v9 import FlowMeterReading, IoTDevice, KegTracking

        # Validate device
        device = db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")

        # Get current totals if tracking a container
        total_dispensed = flow_volume_ml
        remaining = None
        capacity = None
        fill_pct = None

        if container_id:
            # Get previous readings for this container
            prev_readings = db.query(func.sum(FlowMeterReading.flow_volume_ml)).filter(
                FlowMeterReading.container_id == container_id
            ).scalar() or 0
            total_dispensed = prev_readings + flow_volume_ml

            # Check for keg tracking
            keg = db.query(KegTracking).filter(KegTracking.keg_id == container_id).first()
            if keg:
                capacity = keg.initial_volume_ml
                remaining = capacity - total_dispensed
                fill_pct = (remaining / capacity * 100) if capacity > 0 else 0

                # Update keg tracking
                keg.current_volume_ml = max(0, remaining)
                keg.dispensed_volume_ml = total_dispensed
                keg.pours_count += 1

                if fill_pct <= 10:
                    keg.status = "low"
                if fill_pct <= 0:
                    keg.status = "empty"
                    keg.empty_date = datetime.utcnow()

        # Determine low/empty alerts
        is_low = fill_pct is not None and fill_pct <= 15
        is_empty = fill_pct is not None and fill_pct <= 2

        reading = FlowMeterReading(
            venue_id=venue_id,
            device_id=device_id,
            meter_type=meter_type,
            stock_item_id=stock_item_id,
            container_id=container_id,
            flow_volume_ml=flow_volume_ml,
            flow_rate_ml_per_sec=flow_rate_ml_per_sec,
            total_dispensed_ml=total_dispensed,
            remaining_volume_ml=remaining,
            container_capacity_ml=capacity,
            fill_percentage=fill_pct,
            temperature_celsius=temperature_celsius,
            pressure_psi=pressure_psi,
            order_id=order_id,
            staff_user_id=staff_user_id,
            tap_number=tap_number,
            is_low_level=is_low,
            is_empty=is_empty,
            alert_sent=False
        )
        db.add(reading)

        # Update device last seen
        device.last_seen = datetime.utcnow()

        db.commit()
        db.refresh(reading)

        result = {
            "reading_id": reading.id,
            "container_id": container_id,
            "flow_volume_ml": flow_volume_ml,
            "total_dispensed_ml": total_dispensed,
            "recorded_at": reading.recorded_at.isoformat()
        }

        if remaining is not None:
            result["remaining_ml"] = remaining
            result["fill_percentage"] = round(fill_pct, 1)

        if is_low or is_empty:
            result["alert"] = {
                "type": "empty" if is_empty else "low_level",
                "message": f"Container {container_id} is {'empty' if is_empty else 'running low'}",
                "fill_percentage": round(fill_pct, 1) if fill_pct else 0
            }

        return result

    @staticmethod
    def register_keg(
        db: Session,
        venue_id: int,
        keg_id: str,
        product_name: str,
        keg_size_liters: float,
        stock_item_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        rfid_tag_id: Optional[int] = None,
        flow_meter_id: Optional[int] = None,
        purchase_price: Optional[float] = None,
        expiry_date: Optional[datetime] = None,
        tap_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Register a new keg for tracking."""
        from app.models.advanced_features_v9 import KegTracking

        initial_volume = keg_size_liters * 1000  # Convert to ml

        keg = KegTracking(
            venue_id=venue_id,
            keg_id=keg_id,
            product_name=product_name,
            keg_size_liters=keg_size_liters,
            stock_item_id=stock_item_id,
            supplier_id=supplier_id,
            rfid_tag_id=rfid_tag_id,
            flow_meter_id=flow_meter_id,
            initial_volume_ml=initial_volume,
            current_volume_ml=initial_volume,
            dispensed_volume_ml=0,
            status="full",
            received_date=datetime.utcnow(),
            purchase_price=purchase_price,
            price_per_ml=purchase_price / initial_volume if purchase_price else None,
            expiry_date=expiry_date,
            tap_number=tap_number,
            current_location="storage"
        )
        db.add(keg)
        db.commit()
        db.refresh(keg)

        return {
            "id": keg.id,
            "keg_id": keg_id,
            "product_name": product_name,
            "size_liters": keg_size_liters,
            "status": "full",
            "current_volume_ml": initial_volume,
            "message": "Keg registered successfully"
        }

    @staticmethod
    def tap_keg(
        db: Session,
        keg_id: str,
        tap_number: int,
        location: str = "bar"
    ) -> Dict[str, Any]:
        """Mark a keg as tapped and assign to a tap."""
        from app.models.advanced_features_v9 import KegTracking

        keg = db.query(KegTracking).filter(KegTracking.keg_id == keg_id).first()
        if not keg:
            raise ValueError(f"Keg {keg_id} not found")

        keg.status = "tapped"
        keg.tapped_date = datetime.utcnow()
        keg.tap_number = tap_number
        keg.current_location = location

        db.commit()

        return {
            "keg_id": keg_id,
            "status": "tapped",
            "tap_number": tap_number,
            "location": location,
            "tapped_at": keg.tapped_date.isoformat()
        }

    @staticmethod
    def get_keg_status(
        db: Session,
        venue_id: int,
        status: Optional[str] = None,
        tap_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get keg status and inventory."""
        from app.models.advanced_features_v9 import KegTracking

        query = db.query(KegTracking).filter(KegTracking.venue_id == venue_id)

        if status:
            query = query.filter(KegTracking.status == status)
        if tap_number:
            query = query.filter(KegTracking.tap_number == tap_number)

        kegs = query.order_by(KegTracking.status, KegTracking.tap_number).all()

        return {
            "venue_id": venue_id,
            "total_kegs": len(kegs),
            "kegs": [{
                "keg_id": k.keg_id,
                "product_name": k.product_name,
                "size_liters": k.keg_size_liters,
                "status": k.status,
                "tap_number": k.tap_number,
                "current_volume_ml": k.current_volume_ml,
                "dispensed_ml": k.dispensed_volume_ml,
                "fill_percentage": round((k.current_volume_ml / k.initial_volume_ml * 100), 1) if k.initial_volume_ml > 0 else 0,
                "pours_count": k.pours_count,
                "yield_percentage": k.yield_percentage,
                "location": k.current_location,
                "tapped_date": k.tapped_date.isoformat() if k.tapped_date else None,
                "expiry_date": k.expiry_date.isoformat() if k.expiry_date else None
            } for k in kegs],
            "summary": {
                "full": sum(1 for k in kegs if k.status == "full"),
                "tapped": sum(1 for k in kegs if k.status == "tapped"),
                "low": sum(1 for k in kegs if k.status == "low"),
                "empty": sum(1 for k in kegs if k.status == "empty")
            }
        }

    @staticmethod
    def update_bulk_tank_level(
        db: Session,
        venue_id: int,
        tank_id: str,
        current_level_liters: float,
        flow_meter_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update bulk tank level reading."""
        from app.models.advanced_features_v9 import BulkTankLevel

        tank = db.query(BulkTankLevel).filter(
            BulkTankLevel.venue_id == venue_id,
            BulkTankLevel.tank_id == tank_id
        ).first()

        if not tank:
            raise ValueError(f"Tank {tank_id} not found")

        old_level = tank.current_level_liters
        tank.current_level_liters = current_level_liters
        tank.fill_percentage = (current_level_liters / tank.capacity_liters * 100) if tank.capacity_liters > 0 else 0
        tank.recorded_at = datetime.utcnow()

        # Calculate usage
        if old_level > current_level_liters:
            usage = old_level - current_level_liters
            # Could update daily average here
        elif current_level_liters > old_level:
            # Refill detected
            tank.last_refill_date = datetime.utcnow()
            tank.last_refill_amount = current_level_liters - old_level

        # Determine status
        if tank.fill_percentage <= 5:
            tank.status = "critical"
        elif tank.min_level_liters and current_level_liters <= tank.min_level_liters:
            tank.status = "low"
        else:
            tank.status = "normal"

        # Calculate days until empty
        if tank.daily_usage_avg_liters and tank.daily_usage_avg_liters > 0:
            tank.days_until_empty = current_level_liters / tank.daily_usage_avg_liters

        db.commit()

        result = {
            "tank_id": tank_id,
            "tank_name": tank.tank_name,
            "current_level_liters": current_level_liters,
            "capacity_liters": tank.capacity_liters,
            "fill_percentage": round(tank.fill_percentage, 1),
            "status": tank.status,
            "days_until_empty": round(tank.days_until_empty, 1) if tank.days_until_empty else None
        }

        if tank.status in ["low", "critical"]:
            result["alert"] = {
                "type": tank.status,
                "message": f"Tank {tank.tank_name} is at {round(tank.fill_percentage)}% capacity"
            }

        return result

    @staticmethod
    def register_bulk_tank(
        db: Session,
        venue_id: int,
        tank_id: str,
        tank_name: str,
        capacity_liters: float,
        product_type: str,
        stock_item_id: Optional[int] = None,
        min_level_liters: Optional[float] = None,
        flow_meter_id: Optional[int] = None,
        initial_level_liters: Optional[float] = None
    ) -> Dict[str, Any]:
        """Register a new bulk storage tank."""
        from app.models.advanced_features_v9 import BulkTankLevel

        current_level = initial_level_liters if initial_level_liters is not None else capacity_liters
        fill_pct = (current_level / capacity_liters * 100) if capacity_liters > 0 else 100

        tank = BulkTankLevel(
            venue_id=venue_id,
            tank_id=tank_id,
            tank_name=tank_name,
            flow_meter_id=flow_meter_id,
            stock_item_id=stock_item_id,
            product_type=product_type,
            capacity_liters=capacity_liters,
            min_level_liters=min_level_liters or (capacity_liters * 0.2),  # Default 20%
            current_level_liters=current_level,
            fill_percentage=fill_pct,
            status="normal"
        )
        db.add(tank)
        db.commit()
        db.refresh(tank)

        return {
            "id": tank.id,
            "tank_id": tank_id,
            "tank_name": tank_name,
            "capacity_liters": capacity_liters,
            "current_level_liters": current_level,
            "fill_percentage": round(fill_pct, 1),
            "product_type": product_type,
            "message": "Bulk tank registered successfully"
        }

    @staticmethod
    def get_flow_analytics(
        db: Session,
        venue_id: int,
        meter_type: Optional[str] = None,
        container_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get flow meter analytics and consumption data."""
        from app.models.advanced_features_v9 import FlowMeterReading

        query = db.query(FlowMeterReading).filter(FlowMeterReading.venue_id == venue_id)

        if meter_type:
            query = query.filter(FlowMeterReading.meter_type == meter_type)
        if container_id:
            query = query.filter(FlowMeterReading.container_id == container_id)
        if start_date:
            query = query.filter(FlowMeterReading.recorded_at >= start_date)
        if end_date:
            query = query.filter(FlowMeterReading.recorded_at <= end_date)

        readings = query.all()

        if not readings:
            return {
                "venue_id": venue_id,
                "message": "No flow data for the specified period"
            }

        total_flow = sum(r.flow_volume_ml for r in readings)

        # Group by container
        by_container = {}
        for r in readings:
            cid = r.container_id or "untracked"
            if cid not in by_container:
                by_container[cid] = {"total_ml": 0, "readings": 0}
            by_container[cid]["total_ml"] += r.flow_volume_ml
            by_container[cid]["readings"] += 1

        return {
            "venue_id": venue_id,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "summary": {
                "total_readings": len(readings),
                "total_flow_ml": total_flow,
                "total_flow_liters": round(total_flow / 1000, 2),
                "low_level_alerts": sum(1 for r in readings if r.is_low_level),
                "empty_alerts": sum(1 for r in readings if r.is_empty)
            },
            "by_container": {
                cid: {
                    "total_ml": data["total_ml"],
                    "total_liters": round(data["total_ml"] / 1000, 2),
                    "readings": data["readings"]
                }
                for cid, data in by_container.items()
            }
        }


# Class aliases for backwards compatibility with endpoint imports
IoTDeviceService = IoTService
TemperatureMonitoringService = IoTService
PourMeterService = IoTService
ScaleService = IoTService
RFIDService = IoTService
FlowMeterService = IoTService
KegTrackingService = IoTService

