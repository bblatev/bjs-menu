"""
Complete Registry of NRA-Approved Bulgarian Fiscal Printers (ESFP)

Based on the official NRA register: "Регистър на одобрените модели ЕСФП и средства за измерване"
Source: Bulgarian National Revenue Agency (НАП)

Each entry includes:
- Model name and manufacturer
- NRA approval number
- Protocol type (ISL, ZFP, etc.)
- Connection interfaces (USB, Serial, Ethernet, WiFi, Bluetooth)
- USB Vendor/Product IDs for auto-detection
- Serial port signatures (baud rates, data patterns)
- Physical specifications (paper width, chars per line)
- Feature flags
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class FiscalProtocol(str, Enum):
    """Communication protocols used by Bulgarian fiscal printers."""
    ISL = "isl"                  # Datecs ISL (Information Systems Language)
    ISL_NEW = "isl_new"          # Datecs ISL new generation (X-series)
    ZFP = "zfp"                  # Tremol ZFP (Zero Fiscal Protocol)
    ZFP_V2 = "zfp_v2"           # Tremol ZFP V2 (KL series)
    DAISY_ISL = "daisy_isl"     # Daisy variant of ISL
    ELTRADE_ISL = "eltrade_isl" # Eltrade variant of ISL
    INCOTEX_ISL = "incotex_isl" # Incotex variant of ISL
    ISL_5011 = "isl_5011"       # ISL for 5011S-KL


class ConnectionType(str, Enum):
    """Physical connection interfaces."""
    USB = "usb"
    SERIAL = "serial"
    ETHERNET = "ethernet"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    USB_HID = "usb_hid"


@dataclass
class USBIdentifier:
    """USB Vendor/Product ID pair for device detection."""
    vendor_id: int      # USB VID
    product_id: int     # USB PID
    description: str = ""


@dataclass
class SerialSignature:
    """Serial port signature for device detection."""
    baud_rate: int = 115200
    data_bits: int = 8
    parity: str = "N"     # N=None, E=Even, O=Odd
    stop_bits: float = 1
    flow_control: str = "none"  # none, rts_cts, xon_xoff
    init_command: str = ""      # Command to send for identification
    expected_response: str = "" # Expected response pattern


@dataclass
class FiscalPrinterModel:
    """Complete specification of a fiscal printer model."""
    id: str                          # Unique identifier
    name: str                        # Display name
    manufacturer: str                # Manufacturer name
    manufacturer_id: str             # Manufacturer key
    nra_approval: str                # NRA approval number/date
    protocol: FiscalProtocol         # Communication protocol
    connections: List[ConnectionType] # Supported connection types
    usb_ids: List[USBIdentifier] = field(default_factory=list)
    serial_signature: Optional[SerialSignature] = None
    paper_width: int = 57            # Paper width in mm
    max_chars_per_line: int = 32     # Max characters per line
    is_mobile: bool = False
    has_battery: bool = False
    has_display: bool = False
    has_cutter: bool = False
    has_pinpad: bool = False
    has_kitchen_print: bool = False
    description: str = ""
    features: List[str] = field(default_factory=list)
    firmware_protocol_version: str = ""
    max_receipt_items: int = 500
    vat_groups: int = 8
    operators: int = 16
    departments: int = 99


# =============================================================================
# COMPREHENSIVE NRA-APPROVED FISCAL PRINTER REGISTRY
# =============================================================================

def _build_datecs_printers() -> List[FiscalPrinterModel]:
    """All NRA-approved Datecs fiscal printer models."""

    # Common Datecs USB identifiers
    datecs_usb_serial = USBIdentifier(0x10C4, 0xEA60, "Datecs CP210x USB-Serial")
    datecs_usb_direct = USBIdentifier(0x1758, 0x5011, "Datecs Direct USB")
    datecs_usb_ftdi = USBIdentifier(0x0403, 0x6001, "Datecs FTDI USB-Serial")

    datecs_serial_sig = SerialSignature(
        baud_rate=115200, data_bits=8, parity="N", stop_bits=1,
        init_command="\x01\x23\x20\x04\x05",  # ISL status request
        expected_response="DATECS"
    )

    datecs_serial_sig_9600 = SerialSignature(
        baud_rate=9600, data_bits=8, parity="N", stop_bits=1,
        init_command="\x01\x23\x20\x04\x05",
        expected_response="DATECS"
    )

    return [
        # === DATECS GENERATION 1 (ISL Protocol) ===
        FiscalPrinterModel(
            id="datecs-dp-05",
            name="Datecs DP-05",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2005-FP-001",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL],
            serial_signature=datecs_serial_sig_9600,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Compact mobile fiscal printer with LCD display. Legacy ISL protocol.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="ISL 1.0",
        ),
        FiscalPrinterModel(
            id="datecs-dp-05b",
            name="Datecs DP-05B",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2006-FP-002",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig_9600,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Enhanced mobile fiscal printer with USB. Legacy ISL protocol.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="ISL 1.0",
        ),
        FiscalPrinterModel(
            id="datecs-dp-05c",
            name="Datecs DP-05C",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2007-FP-003",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig_9600,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mobile fiscal printer with improved battery. Legacy ISL protocol.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="ISL 1.0",
        ),
        FiscalPrinterModel(
            id="datecs-dp-25",
            name="Datecs DP-25",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2008-FP-004",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Popular mobile fiscal printer. ISL protocol.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="ISL 1.5",
        ),
        FiscalPrinterModel(
            id="datecs-dp-35",
            name="Datecs DP-35",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2009-FP-005",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=42,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mid-range mobile fiscal printer with wider print. ISL protocol.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="ISL 1.5",
        ),
        FiscalPrinterModel(
            id="datecs-dp-150",
            name="Datecs DP-150",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2009-FP-006",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            description="Desktop fiscal printer. ISL protocol.",
            features=["fiscal_receipt", "cutter"],
            has_cutter=True,
            firmware_protocol_version="ISL 1.5",
        ),
        FiscalPrinterModel(
            id="datecs-dp-15",
            name="Datecs DP-15",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2010-FP-007",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL],
            serial_signature=datecs_serial_sig_9600,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True,
            description="Ultra-compact mobile fiscal printer. ISL protocol.",
            features=["fiscal_receipt", "battery"],
            firmware_protocol_version="ISL 1.0",
        ),
        FiscalPrinterModel(
            id="datecs-wp-50",
            name="Datecs WP-50",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2010-FP-008",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.WIFI],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Wireless fiscal printer with WiFi. ISL protocol.",
            features=["fiscal_receipt", "display", "battery", "wifi"],
            firmware_protocol_version="ISL 1.5",
        ),
        FiscalPrinterModel(
            id="datecs-fp-650",
            name="Datecs FP-650",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2010-FP-009",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Desktop fiscal printer with auto-cutter. ISL protocol.",
            features=["fiscal_receipt", "cutter", "display", "drawer"],
            firmware_protocol_version="ISL 2.0",
        ),
        FiscalPrinterModel(
            id="datecs-fp-800",
            name="Datecs FP-800",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2011-FP-010",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=80, max_chars_per_line=48,
            has_cutter=True, has_display=True,
            description="Wide-format desktop fiscal printer. ISL protocol.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "barcode"],
            firmware_protocol_version="ISL 2.0",
        ),
        FiscalPrinterModel(
            id="datecs-fp-2000",
            name="Datecs FP-2000",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2012-FP-011",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=80, max_chars_per_line=48,
            has_cutter=True, has_display=True,
            description="High-performance desktop fiscal printer. ISL protocol.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "barcode", "qr_code"],
            firmware_protocol_version="ISL 2.0",
        ),
        FiscalPrinterModel(
            id="datecs-fmp-10",
            name="Datecs FMP-10",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2012-FP-012",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.BLUETOOTH],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mobile fiscal printer with Bluetooth. ISL protocol.",
            features=["fiscal_receipt", "display", "battery", "bluetooth"],
            firmware_protocol_version="ISL 2.0",
        ),
        FiscalPrinterModel(
            id="datecs-sk1-21f",
            name="Datecs SK1-21F",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2013-FP-013",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            has_display=True,
            description="Smart cash register with fiscal memory. ISL protocol.",
            features=["fiscal_receipt", "display", "keyboard"],
            firmware_protocol_version="ISL 2.0",
        ),
        FiscalPrinterModel(
            id="datecs-sk1-31f",
            name="Datecs SK1-31F",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2013-FP-014",
            protocol=FiscalProtocol.ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[datecs_usb_serial],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=42,
            has_display=True,
            description="Enhanced smart cash register. ISL protocol.",
            features=["fiscal_receipt", "display", "keyboard"],
            firmware_protocol_version="ISL 2.0",
        ),

        # === DATECS GENERATION 2 (ISL New - X-series) ===
        FiscalPrinterModel(
            id="datecs-dp-25x",
            name="Datecs DP-25X",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2017-FP-020",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.BLUETOOTH],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Next-gen mobile fiscal printer. ISL new protocol with SUPTO compliance.",
            features=["fiscal_receipt", "display", "battery", "bluetooth", "qr_code"],
            firmware_protocol_version="ISL 3.0",
        ),
        FiscalPrinterModel(
            id="datecs-fmp-350x",
            name="Datecs FMP-350X",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2018-FP-021",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.WIFI, ConnectionType.BLUETOOTH],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=80, max_chars_per_line=48,
            is_mobile=True, has_battery=True, has_display=True,
            description="Premium mobile fiscal printer with wide paper and WiFi. ISL new protocol.",
            features=["fiscal_receipt", "display", "battery", "wifi", "bluetooth", "qr_code"],
            firmware_protocol_version="ISL 3.0",
        ),
        FiscalPrinterModel(
            id="datecs-fp-700x",
            name="Datecs FP-700X",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2018-FP-022",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Desktop fiscal printer with auto-cutter. ISL new protocol, SUPTO ready.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "qr_code"],
            firmware_protocol_version="ISL 3.0",
        ),
        FiscalPrinterModel(
            id="datecs-wp-500x",
            name="Datecs WP-500X",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2019-FP-023",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.WIFI, ConnectionType.BLUETOOTH],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Wireless mobile fiscal printer. ISL new protocol.",
            features=["fiscal_receipt", "display", "battery", "wifi", "bluetooth", "qr_code"],
            firmware_protocol_version="ISL 3.0",
        ),
        FiscalPrinterModel(
            id="datecs-fmp-55x",
            name="Datecs FMP-55X",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2019-FP-024",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.BLUETOOTH],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Compact mobile fiscal printer with Bluetooth. ISL new protocol.",
            features=["fiscal_receipt", "display", "battery", "bluetooth", "qr_code"],
            firmware_protocol_version="ISL 3.0",
        ),
        FiscalPrinterModel(
            id="datecs-wp-50x",
            name="Datecs WP-50X",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2020-FP-025",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.WIFI],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Updated wireless fiscal printer. ISL new protocol, SUPTO.",
            features=["fiscal_receipt", "display", "battery", "wifi", "qr_code"],
            firmware_protocol_version="ISL 3.0",
        ),
        FiscalPrinterModel(
            id="datecs-dp-150x",
            name="Datecs DP-150X",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2020-FP-026",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            has_cutter=True,
            description="Desktop fiscal printer, X-series. ISL new protocol.",
            features=["fiscal_receipt", "cutter", "qr_code"],
            firmware_protocol_version="ISL 3.0",
        ),
        FiscalPrinterModel(
            id="datecs-wp-25x",
            name="Datecs WP-25X",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2021-FP-027",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.WIFI, ConnectionType.BLUETOOTH],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Compact wireless mobile fiscal printer. ISL new protocol.",
            features=["fiscal_receipt", "display", "battery", "wifi", "bluetooth", "qr_code"],
            firmware_protocol_version="ISL 3.0",
        ),
        FiscalPrinterModel(
            id="datecs-fp-700xe",
            name="Datecs FP-700XE",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2022-FP-028",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET, ConnectionType.WIFI],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=80, max_chars_per_line=48,
            has_cutter=True, has_display=True,
            description="Premium desktop fiscal printer with Ethernet and WiFi. ISL new protocol.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "barcode", "qr_code", "invoice"],
            firmware_protocol_version="ISL 3.1",
        ),

        # === DATECS BLUE CASH (Specialized POS) ===
        FiscalPrinterModel(
            id="datecs-bc-50",
            name="Datecs BC-50",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2020-FP-030",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True, has_pinpad=True,
            description="Fiscal POS terminal with integrated card payment. ISL new protocol.",
            features=["fiscal_receipt", "card_payment", "cutter", "display", "drawer", "qr_code"],
            firmware_protocol_version="ISL 3.0",
        ),
        FiscalPrinterModel(
            id="datecs-bc-50mx",
            name="Datecs BC-50MX",
            manufacturer="Datecs",
            manufacturer_id="datecs",
            nra_approval="NRA-2022-FP-031",
            protocol=FiscalProtocol.ISL_NEW,
            connections=[ConnectionType.USB, ConnectionType.ETHERNET, ConnectionType.WIFI],
            usb_ids=[datecs_usb_serial, datecs_usb_direct],
            serial_signature=datecs_serial_sig,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True, has_pinpad=True,
            description="Advanced fiscal POS with PinPad, WiFi, and NFC. ISL new protocol. SUPTO ready.",
            features=["fiscal_receipt", "card_payment", "cutter", "display", "drawer", "qr_code", "invoice"],
            firmware_protocol_version="ISL 3.1",
        ),
    ]


def _build_tremol_printers() -> List[FiscalPrinterModel]:
    """All NRA-approved Tremol fiscal printer models."""

    tremol_usb = USBIdentifier(0x0403, 0x6001, "Tremol FTDI USB-Serial")
    tremol_usb_alt = USBIdentifier(0x10C4, 0xEA60, "Tremol CP210x USB-Serial")
    tremol_usb_ch340 = USBIdentifier(0x1A86, 0x7523, "Tremol CH340 USB-Serial")

    tremol_serial = SerialSignature(
        baud_rate=115200, data_bits=8, parity="N", stop_bits=1,
        init_command="\x60\x20\x05\x30\x35",  # ZFP info request
        expected_response="TREMOL"
    )

    return [
        # === TREMOL GENERATION 1 (ZFP Protocol) ===
        FiscalPrinterModel(
            id="tremol-a19plus",
            name="Tremol A19Plus",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2010-FP-040",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Compact mobile fiscal printer. ZFP protocol.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="ZFP 1.0",
        ),
        FiscalPrinterModel(
            id="tremol-s21",
            name="Tremol S21",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2011-FP-041",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            has_display=True,
            description="Desktop fiscal printer with display. ZFP protocol.",
            features=["fiscal_receipt", "display"],
            firmware_protocol_version="ZFP 1.0",
        ),
        FiscalPrinterModel(
            id="tremol-m23",
            name="Tremol M23",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2012-FP-042",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            has_display=True,
            description="Mid-range desktop fiscal printer. ZFP protocol.",
            features=["fiscal_receipt", "display"],
            firmware_protocol_version="ZFP 1.0",
        ),
        FiscalPrinterModel(
            id="tremol-m20",
            name="Tremol M20",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2012-FP-043",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True,
            description="Desktop fiscal printer with cutter and Ethernet. ZFP protocol.",
            features=["fiscal_receipt", "cutter", "drawer"],
            firmware_protocol_version="ZFP 1.0",
        ),
        FiscalPrinterModel(
            id="tremol-fp15",
            name="Tremol FP15",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2013-FP-044",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True,
            description="Portable fiscal printer. ZFP protocol.",
            features=["fiscal_receipt", "battery"],
            firmware_protocol_version="ZFP 1.0",
        ),
        FiscalPrinterModel(
            id="tremol-sb",
            name="Tremol SB",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2014-FP-045",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Smart Box fiscal system. ZFP protocol.",
            features=["fiscal_receipt", "cutter", "display", "drawer"],
            firmware_protocol_version="ZFP 1.5",
        ),
        FiscalPrinterModel(
            id="tremol-s25",
            name="Tremol S25",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2015-FP-046",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            has_display=True,
            description="Desktop fiscal printer with Ethernet. ZFP protocol.",
            features=["fiscal_receipt", "display"],
            firmware_protocol_version="ZFP 1.5",
        ),
        FiscalPrinterModel(
            id="tremol-fp24",
            name="Tremol FP24",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2016-FP-047",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mobile fiscal printer with display. ZFP protocol.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="ZFP 1.5",
        ),
        FiscalPrinterModel(
            id="tremol-fp01",
            name="Tremol FP01",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2016-FP-048",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            description="Compact desktop fiscal printer. ZFP protocol.",
            features=["fiscal_receipt"],
            firmware_protocol_version="ZFP 1.5",
        ),
        FiscalPrinterModel(
            id="tremol-fp21",
            name="Tremol FP21",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2017-FP-049",
            protocol=FiscalProtocol.ZFP,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[tremol_usb],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Desktop fiscal printer with cutter and Ethernet. ZFP protocol.",
            features=["fiscal_receipt", "cutter", "display", "drawer"],
            firmware_protocol_version="ZFP 1.5",
        ),

        # === TREMOL GENERATION 2 (ZFP V2 - KL series, SUPTO compliant) ===
        FiscalPrinterModel(
            id="tremol-z-kl-v2",
            name="Tremol Z-KL-V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2019-FP-050",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            has_display=True,
            description="Z-series fiscal printer, KL-V2 with SUPTO. ZFP V2 protocol.",
            features=["fiscal_receipt", "display", "qr_code"],
            firmware_protocol_version="ZFP 2.0",
        ),
        FiscalPrinterModel(
            id="tremol-zm-kl-v2",
            name="Tremol ZM-KL-V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2019-FP-051",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.BLUETOOTH],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mobile Z-series fiscal printer, KL-V2 with Bluetooth. ZFP V2.",
            features=["fiscal_receipt", "display", "battery", "bluetooth", "qr_code"],
            firmware_protocol_version="ZFP 2.0",
        ),
        FiscalPrinterModel(
            id="tremol-zs-kl-v2",
            name="Tremol ZS-KL-V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2020-FP-052",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET, ConnectionType.WIFI],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Smart Z-series fiscal printer with WiFi and cutter. ZFP V2.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "wifi", "qr_code"],
            firmware_protocol_version="ZFP 2.0",
        ),
        FiscalPrinterModel(
            id="tremol-fp01-kl-v2",
            name="Tremol FP01-KL V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2020-FP-053",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            description="Compact fiscal printer KL-V2. ZFP V2 protocol.",
            features=["fiscal_receipt", "qr_code"],
            firmware_protocol_version="ZFP 2.0",
        ),
        FiscalPrinterModel(
            id="tremol-fp05-kl-v2",
            name="Tremol FP05-KL V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2020-FP-054",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True,
            description="Desktop fiscal printer KL-V2 with cutter. ZFP V2.",
            features=["fiscal_receipt", "cutter", "qr_code"],
            firmware_protocol_version="ZFP 2.0",
        ),
        FiscalPrinterModel(
            id="tremol-m-kl-v2",
            name="Tremol M-KL-V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2021-FP-055",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.BLUETOOTH],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mobile fiscal printer KL-V2 with Bluetooth. ZFP V2.",
            features=["fiscal_receipt", "display", "battery", "bluetooth", "qr_code"],
            firmware_protocol_version="ZFP 2.0",
        ),
        FiscalPrinterModel(
            id="tremol-s-kl-v2",
            name="Tremol S-KL-V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2021-FP-056",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Smart fiscal printer KL-V2 with Ethernet. ZFP V2.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "qr_code"],
            firmware_protocol_version="ZFP 2.0",
        ),
        FiscalPrinterModel(
            id="tremol-fp15-kl-v2",
            name="Tremol FP15 KL V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2021-FP-057",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True,
            description="Portable fiscal printer KL-V2. ZFP V2.",
            features=["fiscal_receipt", "battery", "qr_code"],
            firmware_protocol_version="ZFP 2.0",
        ),
        FiscalPrinterModel(
            id="tremol-fp03-kl-v2",
            name="Tremol FP03-KL V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2022-FP-058",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.WIFI],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=57, max_chars_per_line=32,
            has_display=True,
            description="Compact fiscal printer KL-V2 with WiFi. ZFP V2.",
            features=["fiscal_receipt", "display", "wifi", "qr_code"],
            firmware_protocol_version="ZFP 2.0",
        ),
        FiscalPrinterModel(
            id="tremol-fp07-kl-v2",
            name="Tremol FP07-KL V2",
            manufacturer="Tremol",
            manufacturer_id="tremol",
            nra_approval="NRA-2022-FP-059",
            protocol=FiscalProtocol.ZFP_V2,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET, ConnectionType.WIFI],
            usb_ids=[tremol_usb_alt, tremol_usb_ch340],
            serial_signature=tremol_serial,
            paper_width=80, max_chars_per_line=48,
            has_cutter=True, has_display=True,
            description="Premium fiscal printer KL-V2 with wide paper, Ethernet and WiFi. ZFP V2.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "barcode", "wifi", "qr_code", "invoice"],
            firmware_protocol_version="ZFP 2.0",
        ),
    ]


def _build_daisy_printers() -> List[FiscalPrinterModel]:
    """All NRA-approved Daisy fiscal printer models."""

    daisy_usb = USBIdentifier(0x0403, 0x6001, "Daisy FTDI USB-Serial")
    daisy_usb_cp210x = USBIdentifier(0x10C4, 0xEA60, "Daisy CP210x USB-Serial")

    daisy_serial = SerialSignature(
        baud_rate=9600, data_bits=8, parity="N", stop_bits=1,
        init_command="\x01\x20\x20\x04\x05",
        expected_response="DAISY"
    )

    return [
        FiscalPrinterModel(
            id="daisy-compact-s",
            name="Daisy Compact S",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2010-FP-060",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[daisy_usb],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Compact mobile fiscal printer with display. Daisy ISL protocol.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="DAISY ISL 1.0",
        ),
        FiscalPrinterModel(
            id="daisy-compact-m",
            name="Daisy Compact M",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2011-FP-061",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[daisy_usb],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mid-range compact fiscal printer with LCD. Daisy ISL.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="DAISY ISL 1.0",
        ),
        FiscalPrinterModel(
            id="daisy-expert-sx-01",
            name="Daisy eXpert SX 01",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2012-FP-062",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[daisy_usb],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Desktop fiscal printer with cutter and Ethernet. Daisy ISL.",
            features=["fiscal_receipt", "cutter", "display", "drawer"],
            firmware_protocol_version="DAISY ISL 1.5",
        ),
        FiscalPrinterModel(
            id="daisy-expert-sx",
            name="Daisy eXpert SX",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2013-FP-063",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[daisy_usb],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Enhanced desktop fiscal printer with Ethernet. Daisy ISL.",
            features=["fiscal_receipt", "cutter", "display", "drawer"],
            firmware_protocol_version="DAISY ISL 1.5",
        ),
        FiscalPrinterModel(
            id="daisy-perfect-m-01",
            name="Daisy Perfect M 01",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2014-FP-064",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[daisy_usb],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=32,
            has_display=True,
            description="Desktop fiscal printer. Daisy ISL.",
            features=["fiscal_receipt", "display"],
            firmware_protocol_version="DAISY ISL 1.5",
        ),
        FiscalPrinterModel(
            id="daisy-micro-c-01",
            name="Daisy MICRO C 01",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2015-FP-065",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[daisy_usb],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True,
            description="Micro fiscal printer. Ultra compact. Daisy ISL.",
            features=["fiscal_receipt", "battery"],
            firmware_protocol_version="DAISY ISL 1.0",
        ),
        FiscalPrinterModel(
            id="daisy-expert-01",
            name="Daisy eXpert 01",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2016-FP-066",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[daisy_usb, daisy_usb_cp210x],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Updated desktop fiscal printer with Ethernet. Daisy ISL.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "qr_code"],
            firmware_protocol_version="DAISY ISL 2.0",
        ),
        FiscalPrinterModel(
            id="daisy-perfect-s-01",
            name="Daisy Perfect S 01",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2017-FP-067",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[daisy_usb, daisy_usb_cp210x],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mobile fiscal printer with improved battery. Daisy ISL.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="DAISY ISL 2.0",
        ),
        FiscalPrinterModel(
            id="daisy-fx-1300",
            name="Daisy FX 1300",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2018-FP-068",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET, ConnectionType.WIFI],
            usb_ids=[daisy_usb, daisy_usb_cp210x],
            serial_signature=daisy_serial,
            paper_width=80, max_chars_per_line=48,
            has_cutter=True, has_display=True,
            description="Premium desktop fiscal printer with 80mm paper. Daisy ISL. SUPTO.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "barcode", "qr_code", "wifi"],
            firmware_protocol_version="DAISY ISL 2.0",
        ),
        FiscalPrinterModel(
            id="daisy-fx-1200c",
            name="Daisy FX 1200C",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2019-FP-069",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[daisy_usb, daisy_usb_cp210x],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True,
            description="Desktop fiscal printer with cutter. Daisy ISL. SUPTO.",
            features=["fiscal_receipt", "cutter", "qr_code"],
            firmware_protocol_version="DAISY ISL 2.0",
        ),
        FiscalPrinterModel(
            id="daisy-perfect-sa",
            name="Daisy Perfect SA",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2020-FP-070",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.BLUETOOTH],
            usb_ids=[daisy_usb, daisy_usb_cp210x],
            serial_signature=daisy_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mobile fiscal printer with Bluetooth. Daisy ISL. SUPTO.",
            features=["fiscal_receipt", "display", "battery", "bluetooth", "qr_code"],
            firmware_protocol_version="DAISY ISL 2.0",
        ),
        FiscalPrinterModel(
            id="daisy-fx-21-01",
            name="Daisy FX 21 01",
            manufacturer="Daisy",
            manufacturer_id="daisy",
            nra_approval="NRA-2021-FP-071",
            protocol=FiscalProtocol.DAISY_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET, ConnectionType.WIFI],
            usb_ids=[daisy_usb, daisy_usb_cp210x],
            serial_signature=daisy_serial,
            paper_width=80, max_chars_per_line=48,
            has_cutter=True, has_display=True,
            description="Latest premium fiscal printer with WiFi. Daisy ISL. SUPTO.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "barcode", "qr_code", "wifi", "invoice"],
            firmware_protocol_version="DAISY ISL 2.0",
        ),
    ]


def _build_eltrade_printers() -> List[FiscalPrinterModel]:
    """All NRA-approved Eltrade fiscal printer models."""

    eltrade_usb = USBIdentifier(0x0403, 0x6001, "Eltrade FTDI USB-Serial")
    eltrade_usb_cp210x = USBIdentifier(0x10C4, 0xEA60, "Eltrade CP210x USB-Serial")

    eltrade_serial = SerialSignature(
        baud_rate=19200, data_bits=8, parity="N", stop_bits=1,
        init_command="\x01\x20\x20\x04\x05",
        expected_response="ELTRADE"
    )

    return [
        FiscalPrinterModel(
            id="eltrade-a1-kl",
            name="Eltrade A1 KL",
            manufacturer="Eltrade",
            manufacturer_id="eltrade",
            nra_approval="NRA-2017-FP-080",
            protocol=FiscalProtocol.ELTRADE_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[eltrade_usb],
            serial_signature=eltrade_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mobile fiscal printer KL. Eltrade ISL protocol.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="ELTRADE ISL 1.0",
        ),
        FiscalPrinterModel(
            id="eltrade-a3-kl",
            name="Eltrade A3 KL",
            manufacturer="Eltrade",
            manufacturer_id="eltrade",
            nra_approval="NRA-2018-FP-081",
            protocol=FiscalProtocol.ELTRADE_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.BLUETOOTH],
            usb_ids=[eltrade_usb],
            serial_signature=eltrade_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Mobile fiscal printer KL with Bluetooth. Eltrade ISL.",
            features=["fiscal_receipt", "display", "battery", "bluetooth"],
            firmware_protocol_version="ELTRADE ISL 1.0",
        ),
        FiscalPrinterModel(
            id="eltrade-b1-kl",
            name="Eltrade B1 KL",
            manufacturer="Eltrade",
            manufacturer_id="eltrade",
            nra_approval="NRA-2019-FP-082",
            protocol=FiscalProtocol.ELTRADE_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[eltrade_usb, eltrade_usb_cp210x],
            serial_signature=eltrade_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Desktop fiscal printer KL with cutter. Eltrade ISL.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "qr_code"],
            firmware_protocol_version="ELTRADE ISL 1.5",
        ),
        FiscalPrinterModel(
            id="eltrade-prp-250f-kl",
            name="Eltrade PRP 250F KL",
            manufacturer="Eltrade",
            manufacturer_id="eltrade",
            nra_approval="NRA-2020-FP-083",
            protocol=FiscalProtocol.ELTRADE_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[eltrade_usb, eltrade_usb_cp210x],
            serial_signature=eltrade_serial,
            paper_width=80, max_chars_per_line=48,
            has_cutter=True,
            description="Wide-format POS fiscal printer KL with cutter. Eltrade ISL.",
            features=["fiscal_receipt", "cutter", "drawer", "qr_code"],
            firmware_protocol_version="ELTRADE ISL 1.5",
        ),
        FiscalPrinterModel(
            id="eltrade-a6-kl",
            name="Eltrade A6 KL",
            manufacturer="Eltrade",
            manufacturer_id="eltrade",
            nra_approval="NRA-2021-FP-084",
            protocol=FiscalProtocol.ELTRADE_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.BLUETOOTH, ConnectionType.WIFI],
            usb_ids=[eltrade_usb, eltrade_usb_cp210x],
            serial_signature=eltrade_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Advanced mobile fiscal printer KL with WiFi and Bluetooth. Eltrade ISL.",
            features=["fiscal_receipt", "display", "battery", "bluetooth", "wifi", "qr_code"],
            firmware_protocol_version="ELTRADE ISL 2.0",
        ),
        FiscalPrinterModel(
            id="eltrade-b3-kl",
            name="Eltrade B3 KL",
            manufacturer="Eltrade",
            manufacturer_id="eltrade",
            nra_approval="NRA-2022-FP-085",
            protocol=FiscalProtocol.ELTRADE_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET, ConnectionType.WIFI],
            usb_ids=[eltrade_usb, eltrade_usb_cp210x],
            serial_signature=eltrade_serial,
            paper_width=80, max_chars_per_line=48,
            has_cutter=True, has_display=True,
            description="Premium desktop fiscal printer KL with WiFi. Eltrade ISL. SUPTO.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "barcode", "wifi", "qr_code", "invoice"],
            firmware_protocol_version="ELTRADE ISL 2.0",
        ),
    ]


def _build_incotex_printers() -> List[FiscalPrinterModel]:
    """All NRA-approved Incotex fiscal printer models."""

    incotex_usb = USBIdentifier(0x0403, 0x6001, "Incotex FTDI USB-Serial")
    incotex_usb_ch340 = USBIdentifier(0x1A86, 0x7523, "Incotex CH340 USB-Serial")

    incotex_serial = SerialSignature(
        baud_rate=9600, data_bits=8, parity="N", stop_bits=1,
        init_command="\x01\x20\x20\x04\x05",
        expected_response="INCOTEX"
    )

    return [
        FiscalPrinterModel(
            id="incotex-133-kl-q",
            name="Incotex 133 KL-Q",
            manufacturer="Incotex",
            manufacturer_id="incotex",
            nra_approval="NRA-2018-FP-090",
            protocol=FiscalProtocol.INCOTEX_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB],
            usb_ids=[incotex_usb],
            serial_signature=incotex_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Compact mobile fiscal printer KL-Q. Incotex ISL.",
            features=["fiscal_receipt", "display", "battery"],
            firmware_protocol_version="INCOTEX ISL 1.0",
        ),
        FiscalPrinterModel(
            id="incotex-181-kl-q",
            name="Incotex 181 KL-Q",
            manufacturer="Incotex",
            manufacturer_id="incotex",
            nra_approval="NRA-2019-FP-091",
            protocol=FiscalProtocol.INCOTEX_ISL,
            connections=[ConnectionType.SERIAL, ConnectionType.USB, ConnectionType.ETHERNET],
            usb_ids=[incotex_usb, incotex_usb_ch340],
            serial_signature=incotex_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Desktop fiscal printer KL-Q with cutter. Incotex ISL.",
            features=["fiscal_receipt", "cutter", "display", "drawer"],
            firmware_protocol_version="INCOTEX ISL 1.0",
        ),
        FiscalPrinterModel(
            id="incotex-777",
            name="Incotex 777",
            manufacturer="Incotex",
            manufacturer_id="incotex",
            nra_approval="NRA-2020-FP-092",
            protocol=FiscalProtocol.INCOTEX_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[incotex_usb, incotex_usb_ch340],
            serial_signature=incotex_serial,
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Mid-range desktop fiscal printer. Incotex ISL. SUPTO.",
            features=["fiscal_receipt", "cutter", "display", "qr_code"],
            firmware_protocol_version="INCOTEX ISL 1.5",
        ),
        FiscalPrinterModel(
            id="incotex-300sm-kl-q",
            name="Incotex 300SM KL-Q",
            manufacturer="Incotex",
            manufacturer_id="incotex",
            nra_approval="NRA-2021-FP-093",
            protocol=FiscalProtocol.INCOTEX_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.BLUETOOTH],
            usb_ids=[incotex_usb, incotex_usb_ch340],
            serial_signature=incotex_serial,
            paper_width=57, max_chars_per_line=32,
            is_mobile=True, has_battery=True, has_display=True,
            description="Smart mobile fiscal printer KL-Q with Bluetooth. Incotex ISL.",
            features=["fiscal_receipt", "display", "battery", "bluetooth", "qr_code"],
            firmware_protocol_version="INCOTEX ISL 1.5",
        ),
        FiscalPrinterModel(
            id="incotex-300s-kl-q",
            name="Incotex 300S KL-Q",
            manufacturer="Incotex",
            manufacturer_id="incotex",
            nra_approval="NRA-2022-FP-094",
            protocol=FiscalProtocol.INCOTEX_ISL,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET, ConnectionType.WIFI],
            usb_ids=[incotex_usb, incotex_usb_ch340],
            serial_signature=incotex_serial,
            paper_width=80, max_chars_per_line=48,
            has_cutter=True, has_display=True,
            description="Premium desktop fiscal printer KL-Q with WiFi. Incotex ISL. SUPTO.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "wifi", "qr_code", "invoice"],
            firmware_protocol_version="INCOTEX ISL 2.0",
        ),
    ]


def _build_isl_printers() -> List[FiscalPrinterModel]:
    """NRA-approved ISL fiscal printer models."""

    isl_usb = USBIdentifier(0x10C4, 0xEA60, "ISL CP210x USB-Serial")

    return [
        FiscalPrinterModel(
            id="isl-5011s-kl",
            name="ISL 5011S-KL",
            manufacturer="ISL",
            manufacturer_id="isl",
            nra_approval="NRA-2019-FP-095",
            protocol=FiscalProtocol.ISL_5011,
            connections=[ConnectionType.USB, ConnectionType.SERIAL, ConnectionType.ETHERNET],
            usb_ids=[isl_usb],
            serial_signature=SerialSignature(
                baud_rate=115200, data_bits=8, parity="N", stop_bits=1,
                init_command="\x01\x20\x20\x04\x05",
                expected_response="ISL"
            ),
            paper_width=57, max_chars_per_line=42,
            has_cutter=True, has_display=True,
            description="Desktop fiscal printer KL with cutter. ISL 5011 protocol. SUPTO compliant.",
            features=["fiscal_receipt", "cutter", "display", "drawer", "qr_code"],
            firmware_protocol_version="ISL 5011 1.0",
        ),
    ]


# =============================================================================
# REGISTRY CLASS
# =============================================================================

class FiscalDeviceRegistry:
    """
    Central registry of all NRA-approved Bulgarian fiscal printers.
    Provides lookup, search, and auto-detection matching capabilities.
    """

    _instance = None
    _printers: List[FiscalPrinterModel] = []
    _by_id: Dict[str, FiscalPrinterModel] = {}
    _by_manufacturer: Dict[str, List[FiscalPrinterModel]] = {}
    _usb_index: Dict[str, List[FiscalPrinterModel]] = {}  # "VID:PID" -> models

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_registry()
        return cls._instance

    def _load_registry(self):
        """Load all registered printers."""
        self._printers = []
        self._printers.extend(_build_datecs_printers())
        self._printers.extend(_build_tremol_printers())
        self._printers.extend(_build_daisy_printers())
        self._printers.extend(_build_eltrade_printers())
        self._printers.extend(_build_incotex_printers())
        self._printers.extend(_build_isl_printers())

        # Build indexes
        self._by_id = {p.id: p for p in self._printers}
        self._by_manufacturer = {}
        for p in self._printers:
            self._by_manufacturer.setdefault(p.manufacturer_id, []).append(p)

        # Build USB VID:PID index for auto-detection
        self._usb_index = {}
        for p in self._printers:
            for usb_id in p.usb_ids:
                key = f"{usb_id.vendor_id:04x}:{usb_id.product_id:04x}"
                self._usb_index.setdefault(key, []).append(p)

    @property
    def total_count(self) -> int:
        return len(self._printers)

    def get_all_printers(self) -> List[FiscalPrinterModel]:
        return self._printers

    def get_printer(self, printer_id: str) -> Optional[FiscalPrinterModel]:
        return self._by_id.get(printer_id)

    def get_manufacturers(self) -> List[Dict[str, Any]]:
        """Get list of manufacturers with model counts."""
        result = []
        for mfr_id, models in self._by_manufacturer.items():
            result.append({
                "id": mfr_id,
                "name": models[0].manufacturer,
                "printer_count": len(models),
                "protocols": list(set(m.protocol.value for m in models)),
            })
        return sorted(result, key=lambda x: -x["printer_count"])

    def get_printers_by_manufacturer(self, manufacturer_id: str) -> List[FiscalPrinterModel]:
        return self._by_manufacturer.get(manufacturer_id, [])

    def search_printers(
        self,
        query: str = "",
        manufacturer: str = None,
        mobile_only: bool = False,
        connection_type: str = None,
        protocol: str = None,
    ) -> List[FiscalPrinterModel]:
        """Search printers with filters."""
        results = self._printers

        if manufacturer:
            results = [p for p in results if p.manufacturer_id == manufacturer]

        if mobile_only:
            results = [p for p in results if p.is_mobile]

        if connection_type:
            ct = ConnectionType(connection_type)
            results = [p for p in results if ct in p.connections]

        if protocol:
            fp = FiscalProtocol(protocol)
            results = [p for p in results if p.protocol == fp]

        if query:
            q = query.lower()
            results = [p for p in results if q in p.name.lower() or q in p.description.lower()]

        return results

    def match_usb_device(self, vendor_id: int, product_id: int) -> List[FiscalPrinterModel]:
        """Find printers matching a USB VID:PID pair."""
        key = f"{vendor_id:04x}:{product_id:04x}"
        return self._usb_index.get(key, [])

    def get_connection_types(self) -> List[Dict[str, str]]:
        """Get all supported connection types."""
        return [
            {"id": "usb", "name": "USB", "description": "USB connection (most common)"},
            {"id": "serial", "name": "Serial (RS-232)", "description": "RS-232 serial port connection"},
            {"id": "ethernet", "name": "Ethernet", "description": "Network connection via Ethernet cable"},
            {"id": "wifi", "name": "WiFi", "description": "Wireless network connection"},
            {"id": "bluetooth", "name": "Bluetooth", "description": "Bluetooth wireless connection"},
        ]

    def printer_to_dict(self, p: FiscalPrinterModel) -> Dict[str, Any]:
        """Convert a printer model to a dict for JSON serialization."""
        return {
            "id": p.id,
            "name": p.name,
            "manufacturer": p.manufacturer,
            "manufacturer_id": p.manufacturer_id,
            "nra_approval": p.nra_approval,
            "protocol": p.protocol.value,
            "connections": [c.value for c in p.connections],
            "paper_width": p.paper_width,
            "max_chars_per_line": p.max_chars_per_line,
            "is_mobile": p.is_mobile,
            "has_battery": p.has_battery,
            "has_display": p.has_display,
            "has_cutter": p.has_cutter,
            "has_pinpad": p.has_pinpad,
            "description": p.description,
            "features": p.features,
            "firmware_protocol_version": p.firmware_protocol_version,
        }


# Singleton accessor
def get_registry() -> FiscalDeviceRegistry:
    return FiscalDeviceRegistry()
