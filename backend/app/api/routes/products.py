"""Product routes."""

import csv
import io
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from app.core.rate_limit import limiter

from app.core.file_utils import sanitize_filename
from app.core.rbac import CurrentUser, OptionalCurrentUser, RequireManager
from app.db.session import DbSession
from app.models.product import Product
from app.models.supplier import Supplier
from app.schemas.pagination import paginate_query
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.sku_mapping_service import SKUMappingService

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
def list_products(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    active_only: bool = Query(True, description="Only show active products"),
    supplier_id: Optional[int] = Query(None, description="Filter by supplier"),
    search: Optional[str] = Query(None, description="Search by name or barcode"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
):
    """List products with optional filters and pagination."""
    query = db.query(Product)

    if active_only:
        query = query.filter(Product.active == True)
    if supplier_id:
        query = query.filter(Product.supplier_id == supplier_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) | (Product.barcode.ilike(search_term))
        )

    query = query.order_by(Product.name)
    items, total = paginate_query(query, skip, limit)

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(items)) < total,
    }


@router.get("/by-barcode/{barcode}", response_model=ProductResponse)
@limiter.limit("60/minute")
def get_product_by_barcode(request: Request, barcode: str, db: DbSession, current_user: CurrentUser):
    """Get a product by barcode (EAN/UPC)."""
    product = db.query(Product).filter(Product.barcode == barcode, Product.active == True).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.get("/{product_id}", response_model=ProductResponse)
@limiter.limit("60/minute")
def get_product(request: Request, product_id: int, db: DbSession, current_user: CurrentUser):
    """Get a specific product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_product(request: Request, product_data: ProductCreate, db: DbSession, current_user: RequireManager):
    """Create a new product (requires Manager role)."""
    # Check for duplicate barcode
    if product_data.barcode:
        existing = db.query(Product).filter(Product.barcode == product_data.barcode).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with barcode {product_data.barcode} already exists",
            )

    product = Product(**product_data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
@limiter.limit("30/minute")
def update_product(
    request: Request, product_id: int, product_data: ProductUpdate, db: DbSession, current_user: RequireManager
):
    """Update a product (requires Manager role)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Check for duplicate barcode if updating
    if product_data.barcode and product_data.barcode != product.barcode:
        existing = db.query(Product).filter(Product.barcode == product_data.barcode).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with barcode {product_data.barcode} already exists",
            )

    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.post("/import")
@limiter.limit("5/minute")
def import_products(
    request: Request,
    file: UploadFile = File(...),
    db: DbSession = None,
    current_user: RequireManager = None,
):
    """
    Import products from CSV file.

    CSV format: name,barcode,supplier_name,pack_size,unit,min_stock,target_stock,lead_time_days,cost_price,sku,ai_label
    """
    # Validate file extension with sanitized filename
    safe_filename = sanitize_filename(file.filename) if file.filename else "upload.csv"
    if not safe_filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV",
        )

    content = file.file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10MB",
        )
    try:
        decoded_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File encoding error. Please ensure the CSV file is UTF-8 encoded.",
        )
    try:
        reader = csv.DictReader(io.StringIO(decoded_content))
        # Validate that required columns exist
        if reader.fieldnames is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file appears to be empty or has no header row.",
            )
        required_columns = {"name"}
        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV is missing required columns: {', '.join(sorted(missing_columns))}. "
                       f"Found columns: {', '.join(reader.fieldnames)}",
            )
    except csv.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}",
        )

    created = 0
    updated = 0
    errors = []

    # Cache suppliers by name
    supplier_cache = {}

    for row_num, row in enumerate(reader, start=2):
        try:
            # Get or create supplier
            supplier_id = None
            supplier_name = row.get("supplier_name", "").strip()
            if supplier_name:
                if supplier_name not in supplier_cache:
                    supplier = db.query(Supplier).filter(Supplier.name == supplier_name).first()
                    if not supplier:
                        supplier = Supplier(name=supplier_name)
                        db.add(supplier)
                        db.flush()
                    supplier_cache[supplier_name] = supplier.id
                supplier_id = supplier_cache[supplier_name]

            # Check if product exists by barcode
            barcode = row.get("barcode", "").strip() or None
            product = None
            if barcode:
                product = db.query(Product).filter(Product.barcode == barcode).first()

            product_data = {
                "name": row["name"].strip(),
                "barcode": barcode,
                "supplier_id": supplier_id,
                "pack_size": int(row.get("pack_size", 1) or 1),
                "unit": row.get("unit", "pcs").strip() or "pcs",
                "min_stock": Decimal(row.get("min_stock", 0) or 0),
                "target_stock": Decimal(row.get("target_stock", 0) or 0),
                "lead_time_days": int(row.get("lead_time_days", 1) or 1),
                "cost_price": Decimal(row["cost_price"]) if row.get("cost_price") else None,
                "sku": row.get("sku", "").strip() or None,
                "ai_label": row.get("ai_label", "").strip() or None,
            }

            if product:
                # Update existing
                for field, value in product_data.items():
                    setattr(product, field, value)
                updated += 1
            else:
                # Create new
                product = Product(**product_data)
                db.add(product)
                created += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    db.commit()

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "total_processed": created + updated,
    }


@router.get("/search/smart")
@limiter.limit("60/minute")
def smart_search_products(
    request: Request,
    q: Optional[str] = Query(None, min_length=2, description="Search query (barcode, SKU, or name)"),
    limit: int = Query(10, ge=1, le=50),
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """
    Smart product search using multiple matching strategies.

    Searches by:
    1. Exact barcode match
    2. Exact SKU match
    3. Name substring match
    4. Fuzzy name matching

    Returns products sorted by match confidence.
    """
    if q is None:
        return {
            "query": None,
            "count": 0,
            "results": [],
        }
    service = SKUMappingService(db)
    results = service.search_products(q, limit=limit)

    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@router.post("/match")
@limiter.limit("30/minute")
def match_product(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    barcode: Optional[str] = Query(None, description="Product barcode"),
    sku: Optional[str] = Query(None, description="Product SKU"),
    name: Optional[str] = Query(None, description="Product name for fuzzy matching"),
    ai_product_id: Optional[int] = Query(None, description="Product ID from AI recognition"),
    ai_confidence: Optional[float] = Query(None, ge=0, le=1, description="AI recognition confidence"),
):
    """
    Match a product using various strategies.

    Tries matching in priority order:
    1. Barcode (exact)
    2. SKU (exact)
    3. AI recognition (if confidence above threshold)
    4. Fuzzy name matching

    Returns the best match and any alternatives.
    """
    service = SKUMappingService(db)
    result = service.match_product(
        barcode=barcode,
        sku=sku,
        name=name,
        ai_product_id=ai_product_id,
        ai_confidence=ai_confidence,
    )

    return {
        "product_id": result.product_id,
        "product_name": result.product_name,
        "match_method": result.method.value,
        "confidence": result.confidence,
        "alternatives": result.alternatives,
    }
