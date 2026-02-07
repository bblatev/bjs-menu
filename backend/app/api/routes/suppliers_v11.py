"""Supplier Management v11 - DEPRECATED, consolidated into suppliers.py.

All endpoints now live in suppliers.py. This file is kept only for any
direct imports that may reference `suppliers_v11.router`.
"""

from app.api.routes.suppliers import router  # noqa: F401
