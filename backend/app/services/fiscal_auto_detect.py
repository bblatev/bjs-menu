"""
Fiscal Printer Auto-Detection Service

Automatically detects connected Bulgarian fiscal printers via:
1. USB device enumeration (matching VID:PID against the NRA registry)
2. Serial port scanning (probing for known fiscal printer responses)
3. Network discovery (scanning for FPGate/ErpNet.FP services)

Works with all NRA-approved manufacturers:
- Datecs (ISL protocol)
- Tremol (ZFP protocol)
- Daisy (ISL variant)
- Eltrade (ISL variant)
- Incotex (ISL variant)
- ISL (ISL 5011 protocol)
"""

import asyncio
import logging
import os
import re
import glob as glob_module
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DetectedDevice:
    """A detected fiscal printer device."""
    port: str                      # e.g., /dev/ttyUSB0, COM3
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    serial_number: str = ""
    manufacturer_hint: str = ""    # From USB descriptor
    product_hint: str = ""         # From USB descriptor
    matched_printer_ids: List[str] = field(default_factory=list)
    matched_manufacturer: str = ""
    matched_protocol: str = ""
    connection_type: str = "usb"   # usb, serial, network
    confidence: float = 0.0        # 0.0 to 1.0


class FiscalAutoDetectService:
    """Service for automatically detecting connected fiscal printers."""

    # Known USB VID:PID mappings for fiscal printer USB-to-Serial bridges
    KNOWN_USB_CHIPS = {
        # Silicon Labs CP210x (very common in Datecs, Daisy, Eltrade)
        (0x10C4, 0xEA60): {
            "chip": "CP210x",
            "manufacturers": ["datecs", "daisy", "eltrade", "isl", "tremol"],
            "confidence": 0.6,
        },
        # FTDI FT232 (common in Tremol, Daisy, Eltrade, Incotex)
        (0x0403, 0x6001): {
            "chip": "FTDI FT232",
            "manufacturers": ["tremol", "daisy", "eltrade", "incotex"],
            "confidence": 0.6,
        },
        # CH340/CH341 (common in Tremol KL-V2, Incotex)
        (0x1A86, 0x7523): {
            "chip": "CH340",
            "manufacturers": ["tremol", "incotex"],
            "confidence": 0.6,
        },
        # Datecs direct USB
        (0x1758, 0x5011): {
            "chip": "Datecs Direct",
            "manufacturers": ["datecs"],
            "confidence": 0.9,
        },
        # Prolific PL2303 (legacy printers)
        (0x067B, 0x2303): {
            "chip": "PL2303",
            "manufacturers": ["datecs", "daisy", "tremol"],
            "confidence": 0.5,
        },
    }

    # Baud rates to probe in order of likelihood
    PROBE_BAUD_RATES = [115200, 9600, 19200, 38400, 57600]

    # Protocol identification patterns
    PROTOCOL_PATTERNS = {
        "datecs_isl": {
            "probe_cmd": b"\x01\x24\x20\x04\x05",  # ISL: read diagnostic info
            "response_patterns": [
                rb"DATECS",
                rb"FP-\d+",
                rb"DP-\d+",
                rb"WP-\d+",
                rb"BC-\d+",
                rb"FMP-\d+",
                rb"SK1-\d+",
            ],
            "manufacturer": "datecs",
            "protocol": "isl",
        },
        "tremol_zfp": {
            "probe_cmd": b"\x60\x20\x05\x30\x35",  # ZFP: read device info
            "response_patterns": [
                rb"TREMOL",
                rb"ZFP",
                rb"FP\d+",
            ],
            "manufacturer": "tremol",
            "protocol": "zfp",
        },
        "daisy_isl": {
            "probe_cmd": b"\x01\x24\x20\x04\x05",
            "response_patterns": [
                rb"DAISY",
                rb"eXpert",
                rb"Compact",
                rb"Perfect",
                rb"FX\s*\d+",
            ],
            "manufacturer": "daisy",
            "protocol": "daisy_isl",
        },
        "eltrade_isl": {
            "probe_cmd": b"\x01\x24\x20\x04\x05",
            "response_patterns": [
                rb"ELTRADE",
                rb"ELT",
            ],
            "manufacturer": "eltrade",
            "protocol": "eltrade_isl",
        },
        "incotex_isl": {
            "probe_cmd": b"\x01\x24\x20\x04\x05",
            "response_patterns": [
                rb"INCOTEX",
                rb"INC",
            ],
            "manufacturer": "incotex",
            "protocol": "incotex_isl",
        },
    }

    def __init__(self):
        from app.services.fiscal_device_registry import get_registry
        self.registry = get_registry()

    async def detect_all(self) -> Dict[str, Any]:
        """
        Run full auto-detection: USB scan + serial probe + network scan.
        Returns list of detected devices with matched printer models.
        """
        detected = []

        # Step 1: USB device enumeration
        usb_devices = await self._scan_usb_devices()
        detected.extend(usb_devices)

        # Step 2: Serial port probe (for devices found via USB or listed serial ports)
        serial_devices = await self._scan_serial_ports(
            exclude_ports=[d.port for d in usb_devices]
        )
        detected.extend(serial_devices)

        # Step 3: Try to identify devices via serial protocol probing
        for device in detected:
            if device.confidence < 0.8:
                probe_result = await self._probe_serial_protocol(device.port)
                if probe_result:
                    device.matched_manufacturer = probe_result["manufacturer"]
                    device.matched_protocol = probe_result["protocol"]
                    device.confidence = max(device.confidence, probe_result["confidence"])

        # Step 4: Match detected devices against registry
        for device in detected:
            self._match_registry(device)

        # Step 5: Network scan for FPGate/ErpNet.FP
        network_devices = await self._scan_network()
        detected.extend(network_devices)

        return {
            "success": True,
            "devices": [self._device_to_dict(d) for d in detected],
            "total_detected": len(detected),
            "scan_methods": ["usb", "serial", "network"],
        }

    async def _scan_usb_devices(self) -> List[DetectedDevice]:
        """Scan USB devices by reading sysfs on Linux."""
        detected = []

        try:
            # Linux: scan /sys/bus/usb/devices for USB-serial devices
            usb_serial_devices = glob_module.glob("/sys/bus/usb-serial/devices/*")

            for dev_path in usb_serial_devices:
                tty_name = os.path.basename(dev_path)
                port = f"/dev/{tty_name}"

                if not os.path.exists(port):
                    continue

                # Read USB device info from sysfs
                vid, pid, serial, mfr, product = self._read_usb_sysfs(dev_path)

                if vid is not None and pid is not None:
                    device = DetectedDevice(
                        port=port,
                        vendor_id=vid,
                        product_id=pid,
                        serial_number=serial or "",
                        manufacturer_hint=mfr or "",
                        product_hint=product or "",
                        connection_type="usb",
                    )

                    # Match against known USB chips
                    chip_info = self.KNOWN_USB_CHIPS.get((vid, pid))
                    if chip_info:
                        device.confidence = chip_info["confidence"]
                        if len(chip_info["manufacturers"]) == 1:
                            device.matched_manufacturer = chip_info["manufacturers"][0]

                    # Match against registry USB IDs
                    matches = self.registry.match_usb_device(vid, pid)
                    if matches:
                        device.matched_printer_ids = [m.id for m in matches]
                        if not device.matched_manufacturer and matches:
                            device.matched_manufacturer = matches[0].manufacturer_id
                        device.confidence = max(device.confidence, 0.7)

                    detected.append(device)

            # Also check /dev/ttyUSB* and /dev/ttyACM* that might not be in sysfs
            for pattern in ["/dev/ttyUSB*", "/dev/ttyACM*"]:
                for port in glob_module.glob(pattern):
                    if not any(d.port == port for d in detected):
                        detected.append(DetectedDevice(
                            port=port,
                            connection_type="usb",
                            confidence=0.3,
                        ))

        except Exception as e:
            logger.warning(f"USB scan error: {e}")

        return detected

    def _read_usb_sysfs(self, dev_path: str):
        """Read USB device info from Linux sysfs."""
        vid = pid = serial = mfr = product = None

        try:
            # Navigate up to the USB device directory
            real_path = os.path.realpath(dev_path)
            usb_device = real_path

            # Walk up to find the USB device with idVendor
            for _ in range(10):
                vid_path = os.path.join(usb_device, "idVendor")
                if os.path.exists(vid_path):
                    break
                usb_device = os.path.dirname(usb_device)
            else:
                return vid, pid, serial, mfr, product

            # Read VID/PID
            vid_file = os.path.join(usb_device, "idVendor")
            pid_file = os.path.join(usb_device, "idProduct")

            if os.path.exists(vid_file) and os.path.exists(pid_file):
                with open(vid_file) as f:
                    vid = int(f.read().strip(), 16)
                with open(pid_file) as f:
                    pid = int(f.read().strip(), 16)

            # Read serial number
            serial_file = os.path.join(usb_device, "serial")
            if os.path.exists(serial_file):
                with open(serial_file) as f:
                    serial = f.read().strip()

            # Read manufacturer
            mfr_file = os.path.join(usb_device, "manufacturer")
            if os.path.exists(mfr_file):
                with open(mfr_file) as f:
                    mfr = f.read().strip()

            # Read product
            product_file = os.path.join(usb_device, "product")
            if os.path.exists(product_file):
                with open(product_file) as f:
                    product = f.read().strip()

        except Exception as e:
            logger.debug(f"sysfs read error for {dev_path}: {e}")

        return vid, pid, serial, mfr, product

    async def _scan_serial_ports(self, exclude_ports: List[str] = None) -> List[DetectedDevice]:
        """Scan standard serial ports (RS-232). Only include ports that appear to be real hardware."""
        detected = []
        exclude = set(exclude_ports or [])

        try:
            # Skip generic ttyS ports (ttyS0-31 are usually virtual on modern systems)
            # Only scan for real serial devices like ttyAMA, specific ttyS with real hardware
            # The primary detection is via USB (ttyUSB*, ttyACM*) which is handled by _scan_usb_devices
            for pattern in ["/dev/ttyAMA*"]:
                for port in glob_module.glob(pattern):
                    if port in exclude:
                        continue

                    try:
                        fd = os.open(port, os.O_RDWR | os.O_NONBLOCK | os.O_NOCTTY)
                        os.close(fd)

                        detected.append(DetectedDevice(
                            port=port,
                            connection_type="serial",
                            confidence=0.3,
                        ))
                    except OSError:
                        pass

        except Exception as e:
            logger.debug(f"Serial port scan error: {e}")

        return detected

    async def _probe_serial_protocol(self, port: str) -> Optional[Dict[str, Any]]:
        """
        Probe a serial port to identify the connected fiscal printer protocol.
        Sends identification commands and analyzes responses.
        """
        try:
            import serial
        except ImportError:
            logger.debug("pyserial not installed, skipping serial probe")
            return None

        for baud_rate in self.PROBE_BAUD_RATES:
            for proto_name, proto_info in self.PROTOCOL_PATTERNS.items():
                try:
                    ser = serial.Serial(
                        port=port,
                        baudrate=baud_rate,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1.0,
                        write_timeout=1.0,
                    )

                    # Clear buffers
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()

                    # Send probe command
                    ser.write(proto_info["probe_cmd"])

                    # Wait for response
                    await asyncio.sleep(0.3)
                    response = ser.read(256)
                    ser.close()

                    if response:
                        # Check response patterns
                        for pattern in proto_info["response_patterns"]:
                            if re.search(pattern, response):
                                return {
                                    "manufacturer": proto_info["manufacturer"],
                                    "protocol": proto_info["protocol"],
                                    "confidence": 0.9,
                                    "baud_rate": baud_rate,
                                    "response_data": response.hex(),
                                }

                except Exception as e:
                    logger.debug(f"Probe {port} at {baud_rate} ({proto_name}): {e}")
                    continue

        return None

    async def _scan_network(self) -> List[DetectedDevice]:
        """Scan for network-accessible fiscal printer services."""
        detected = []

        # Check common FPGate ports
        fpgate_ports = [4444, 8080, 8443]
        for port in fpgate_ports:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=2.0) as client:
                    try:
                        response = await client.get(f"http://localhost:{port}/")
                        if response.status_code in [200, 404]:
                            detected.append(DetectedDevice(
                                port=f"localhost:{port}",
                                connection_type="network",
                                manufacturer_hint="FPGate",
                                product_hint="FPGate REST API",
                                confidence=0.7,
                                matched_protocol="fpgate",
                            ))
                    except Exception as e:
                        logger.debug("Fiscal device probe failed: %s", e)
            except ImportError:
                break

        # Check ErpNet.FP port
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                try:
                    response = await client.get("http://localhost:8001/printers")
                    if response.status_code == 200:
                        detected.append(DetectedDevice(
                            port="localhost:8001",
                            connection_type="network",
                            manufacturer_hint="ErpNet.FP",
                            product_hint="ErpNet.FP REST API",
                            confidence=0.7,
                            matched_protocol="erpnet_fp",
                        ))
                except Exception as e:
                    logger.debug("ErpNet.FP probe failed: %s", e)
        except ImportError:
            pass

        return detected

    def _match_registry(self, device: DetectedDevice):
        """Match a detected device against the registry to refine identification."""
        if device.vendor_id and device.product_id:
            matches = self.registry.match_usb_device(device.vendor_id, device.product_id)
            if matches:
                # If we know the manufacturer, filter to that
                if device.matched_manufacturer:
                    matches = [m for m in matches if m.manufacturer_id == device.matched_manufacturer]
                device.matched_printer_ids = [m.id for m in matches]

                if len(matches) == 1:
                    device.confidence = min(device.confidence + 0.2, 1.0)
                elif matches:
                    device.confidence = min(device.confidence + 0.1, 0.95)

        # If we have a serial number with a known prefix, try to narrow down
        if device.serial_number:
            sn_upper = device.serial_number.upper()
            mfr_prefixes = {
                "DT": "datecs",
                "TR": "tremol",
                "DS": "daisy",
                "EL": "eltrade",
                "IN": "incotex",
            }
            for prefix, mfr in mfr_prefixes.items():
                if sn_upper.startswith(prefix):
                    device.matched_manufacturer = mfr
                    device.confidence = min(device.confidence + 0.15, 1.0)
                    break

    def _device_to_dict(self, device: DetectedDevice) -> Dict[str, Any]:
        """Convert a detected device to a JSON-serializable dict."""
        result = {
            "port": device.port,
            "connection_type": device.connection_type,
            "confidence": round(device.confidence, 2),
            "manufacturer_hint": device.manufacturer_hint,
            "product_hint": device.product_hint,
            "serial_number": device.serial_number,
            "matched_manufacturer": device.matched_manufacturer,
            "matched_protocol": device.matched_protocol,
            "matched_printer_ids": device.matched_printer_ids,
        }

        if device.vendor_id is not None:
            result["vendor_id"] = f"0x{device.vendor_id:04X}"
        if device.product_id is not None:
            result["product_id"] = f"0x{device.product_id:04X}"

        # Add matched printer details from registry
        if device.matched_printer_ids:
            result["matched_printers"] = []
            for pid in device.matched_printer_ids[:5]:  # Top 5 matches
                printer = self.registry.get_printer(pid)
                if printer:
                    result["matched_printers"].append({
                        "id": printer.id,
                        "name": printer.name,
                        "manufacturer": printer.manufacturer,
                        "protocol": printer.protocol.value,
                    })

        return result


# Singleton accessor
_auto_detect_service = None


def get_auto_detect_service() -> FiscalAutoDetectService:
    global _auto_detect_service
    if _auto_detect_service is None:
        _auto_detect_service = FiscalAutoDetectService()
    return _auto_detect_service
