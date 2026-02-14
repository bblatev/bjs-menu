"""Restricted pickle unpickler that only allows safe types.

Standard pickle.loads() can execute arbitrary code during deserialization.
This module provides a restricted alternative that only allows numpy arrays,
basic Python types, and common data structures.

Usage:
    from app.core.safe_pickle import safe_loads
    data = safe_loads(raw_bytes)
"""

import io
import pickle
from typing import Any


# Allowlist of safe modules and classes
_SAFE_CLASSES = {
    ("numpy", "ndarray"),
    ("numpy", "dtype"),
    ("numpy", "float64"),
    ("numpy", "float32"),
    ("numpy", "int64"),
    ("numpy", "int32"),
    ("numpy", "uint8"),
    ("numpy.core.multiarray", "_reconstruct"),
    ("numpy.core.numeric", "_frombuffer"),  # numpy >= 1.24
    ("builtins", "dict"),
    ("builtins", "list"),
    ("builtins", "tuple"),
    ("builtins", "set"),
    ("builtins", "frozenset"),
    ("builtins", "bytes"),
    ("builtins", "bytearray"),
    ("builtins", "complex"),
    ("builtins", "float"),
    ("builtins", "int"),
    ("builtins", "str"),
    ("builtins", "True"),
    ("builtins", "False"),
    ("builtins", "None"),
    ("collections", "OrderedDict"),
    ("datetime", "datetime"),
    ("datetime", "date"),
    ("datetime", "time"),
    ("datetime", "timedelta"),
    ("decimal", "Decimal"),
}


class RestrictedUnpickler(pickle.Unpickler):
    """Unpickler that only allows a safe set of classes."""

    def find_class(self, module: str, name: str) -> Any:
        if (module, name) in _SAFE_CLASSES:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(
            f"Blocked unsafe pickle class: {module}.{name}"
        )


def safe_loads(data: bytes) -> Any:
    """Safely deserialize pickle data, allowing only whitelisted types."""
    return RestrictedUnpickler(io.BytesIO(data)).load()
