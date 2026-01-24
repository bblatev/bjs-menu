"""CSV POS connector.

This connector imports sales data from CSV files exported from
various POS systems. It supports a flexible column mapping to
accommodate different CSV formats.
"""

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.pos.connector_base import (
    NormalizedSalesLine,
    POSConnector,
    POSConnectorFactory,
)


@POSConnectorFactory.register
class CSVConnector(POSConnector):
    """
    CSV-based POS data connector.

    Expected CSV format:
    timestamp,item_id,item_name,qty,is_refund

    Supports various date formats and optional columns.
    """

    @property
    def name(self) -> str:
        return "csv"

    # Supported timestamp formats
    TIMESTAMP_FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y/%m/%d %H:%M:%S",
    ]

    # Column name mappings (various names that map to our normalized fields)
    COLUMN_MAPPINGS = {
        "timestamp": ["timestamp", "date", "datetime", "time", "sale_date", "transaction_date"],
        "item_id": ["item_id", "product_id", "sku", "pos_id", "id"],
        "item_name": ["item_name", "name", "product_name", "description", "item"],
        "qty": ["qty", "quantity", "amount", "count"],
        "is_refund": ["is_refund", "refund", "void", "is_void", "type"],
    }

    def parse_data(self, raw_data: str) -> list[NormalizedSalesLine]:
        """Parse CSV data into normalized sales lines."""
        reader = csv.DictReader(io.StringIO(raw_data))

        # Find column mappings
        columns = self._map_columns(reader.fieldnames or [])

        lines = []
        for row in reader:
            try:
                line = self._parse_row(row, columns)
                if line:
                    lines.append(line)
            except Exception:
                # Skip invalid rows (validation will catch these)
                continue

        return lines

    def validate_data(self, raw_data: str) -> tuple[bool, list[str]]:
        """Validate CSV data format."""
        errors = []

        try:
            reader = csv.DictReader(io.StringIO(raw_data))
            fieldnames = reader.fieldnames or []

            if not fieldnames:
                errors.append("CSV file has no headers")
                return False, errors

            # Check for required columns
            columns = self._map_columns(fieldnames)

            if "timestamp" not in columns:
                errors.append("Missing timestamp column (tried: timestamp, date, datetime, etc.)")

            if "item_name" not in columns:
                errors.append("Missing item_name column (tried: item_name, name, product_name, etc.)")

            # Validate some rows
            row_count = 0
            for i, row in enumerate(reader):
                row_count += 1
                if i < 10:  # Validate first 10 rows
                    row_errors = self._validate_row(row, columns, i + 2)
                    errors.extend(row_errors)

            if row_count == 0:
                errors.append("CSV file has no data rows")

        except csv.Error as e:
            errors.append(f"CSV parsing error: {str(e)}")

        return len(errors) == 0, errors

    def _map_columns(self, fieldnames: list[str]) -> dict[str, str]:
        """Map CSV column names to normalized field names."""
        columns = {}
        lower_fields = {f.lower().strip(): f for f in fieldnames}

        for norm_name, variations in self.COLUMN_MAPPINGS.items():
            for variation in variations:
                if variation.lower() in lower_fields:
                    columns[norm_name] = lower_fields[variation.lower()]
                    break

        return columns

    def _parse_row(
        self, row: dict[str, str], columns: dict[str, str]
    ) -> NormalizedSalesLine | None:
        """Parse a single CSV row."""
        # Parse timestamp
        ts_col = columns.get("timestamp")
        if not ts_col or not row.get(ts_col):
            return None

        timestamp = self._parse_timestamp(row[ts_col])
        if not timestamp:
            return None

        # Parse item name (required)
        name_col = columns.get("item_name")
        item_name = row.get(name_col, "").strip() if name_col else ""
        if not item_name:
            return None

        # Parse optional fields
        item_id = None
        if id_col := columns.get("item_id"):
            item_id = row.get(id_col, "").strip() or None

        qty = Decimal("1")
        if qty_col := columns.get("qty"):
            try:
                qty = Decimal(row.get(qty_col, "1") or "1")
            except InvalidOperation:
                qty = Decimal("1")

        is_refund = False
        if refund_col := columns.get("is_refund"):
            refund_val = row.get(refund_col, "").lower().strip()
            is_refund = refund_val in ("true", "1", "yes", "refund", "void")

        return NormalizedSalesLine(
            timestamp=timestamp,
            pos_item_id=item_id,
            item_name=item_name,
            qty=qty,
            is_refund=is_refund,
            raw_data=dict(row),
        )

    def _validate_row(
        self, row: dict[str, str], columns: dict[str, str], row_num: int
    ) -> list[str]:
        """Validate a single row and return errors."""
        errors = []

        # Check timestamp
        ts_col = columns.get("timestamp")
        if ts_col:
            ts_val = row.get(ts_col, "")
            if not ts_val:
                errors.append(f"Row {row_num}: Empty timestamp")
            elif not self._parse_timestamp(ts_val):
                errors.append(f"Row {row_num}: Invalid timestamp format: {ts_val}")

        # Check item name
        name_col = columns.get("item_name")
        if name_col:
            name_val = row.get(name_col, "").strip()
            if not name_val:
                errors.append(f"Row {row_num}: Empty item_name")

        # Check qty
        qty_col = columns.get("qty")
        if qty_col:
            qty_val = row.get(qty_col, "")
            if qty_val:
                try:
                    Decimal(qty_val)
                except InvalidOperation:
                    errors.append(f"Row {row_num}: Invalid qty: {qty_val}")

        return errors

    def _parse_timestamp(self, ts_str: str) -> datetime | None:
        """Parse a timestamp string in various formats."""
        ts_str = ts_str.strip()
        if not ts_str:
            return None

        # Try ISO format first
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Try other formats
        for fmt in self.TIMESTAMP_FORMATS:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue

        return None
