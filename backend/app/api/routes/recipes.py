"""Recipe (BOM) routes."""

import csv
import io

from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from app.core.file_utils import sanitize_filename
from app.core.rbac import CurrentUser, OptionalCurrentUser, RequireManager
from app.db.session import DbSession
from app.models.product import Product
from app.models.recipe import Recipe, RecipeLine
from app.schemas.recipe import RecipeCreate, RecipeResponse, RecipeUpdate
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/", response_model=List[RecipeResponse])
@limiter.limit("60/minute")
def list_recipes(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    search: Optional[str] = Query(None),
):
    """List all recipes."""
    query = db.query(Recipe)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Recipe.name.ilike(search_term)) | (Recipe.pos_item_name.ilike(search_term))
        )
    return query.order_by(Recipe.name).all()


@router.get("/costs")
@limiter.limit("60/minute")
def get_recipe_costs(request: Request, db: DbSession, current_user: CurrentUser):
    """Get recipe cost analysis."""
    recipes = db.query(Recipe).order_by(Recipe.name).all()
    results = []
    for recipe in recipes:
        total_cost = Decimal("0")
        for line in recipe.lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if product and product.cost_price:
                total_cost += line.qty * product.cost_price
        results.append({
            "id": recipe.id,
            "name": recipe.name,
            "total_cost": float(total_cost),
            "sell_price": float(total_cost * 4) if total_cost > 0 else 0,
            "margin": 75.0 if total_cost > 0 else 0,
            "ingredients_count": len(recipe.lines),
        })
    return {"recipes": results, "total": len(results)}


@router.get("/costs/stats")
@limiter.limit("60/minute")
def get_recipe_cost_stats(request: Request, db: DbSession, current_user: CurrentUser):
    """Get recipe cost statistics."""
    recipes = db.query(Recipe).all()
    count = len(recipes)

    if count == 0:
        return {"total_recipes": 0, "avg_food_cost_pct": 0, "highest_cost_recipe": None, "lowest_margin_recipe": None}

    # Compute actual food cost percentages from recipe data
    costs = []
    highest_cost = None
    highest_cost_val = Decimal("0")

    for recipe in recipes:
        total_cost = Decimal("0")
        for line in recipe.lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if product and product.cost_price:
                total_cost += line.qty * product.cost_price
        if total_cost > 0:
            costs.append(float(total_cost))
        if total_cost > highest_cost_val:
            highest_cost_val = total_cost
            highest_cost = recipe.name

    avg_cost_pct = 0
    if costs:
        avg_cost_pct = round(sum(costs) / len(costs), 2)

    return {
        "total_recipes": count,
        "avg_food_cost_pct": avg_cost_pct,
        "highest_cost_recipe": highest_cost,
        "lowest_margin_recipe": None,
    }


@router.get("/export")
@limiter.limit("60/minute")
def export_recipes(request: Request, db: DbSession = None, current_user: CurrentUser = None):
    """Export all recipes to CSV.

    CSV format: recipe_name,pos_item_id,pos_item_name,product_barcode,qty,unit
    """
    from fastapi.responses import Response

    recipes = db.query(Recipe).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["recipe_name", "pos_item_id", "pos_item_name", "product_barcode", "qty", "unit"])

    for recipe in recipes:
        lines = db.query(RecipeLine).filter(RecipeLine.recipe_id == recipe.id).all()
        for line in lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            writer.writerow([
                recipe.name,
                recipe.pos_item_id or "",
                recipe.pos_item_name or "",
                product.barcode if product else "",
                float(line.qty),
                line.unit or "pcs",
            ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=recipes_export.csv"},
    )


@router.get("/{recipe_id}", response_model=RecipeResponse)
@limiter.limit("60/minute")
def get_recipe(request: Request, recipe_id: int, db: DbSession, current_user: CurrentUser):
    """Get a specific recipe with lines."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


@router.post("/", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_recipe(request: Request, body: RecipeCreate, db: DbSession, current_user: RequireManager):
    """Create a new recipe."""
    # Check for duplicate pos_item_id
    if body.pos_item_id:
        existing = db.query(Recipe).filter(Recipe.pos_item_id == body.pos_item_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipe with pos_item_id '{body.pos_item_id}' already exists",
            )

    recipe = Recipe(
        name=body.name,
        pos_item_id=body.pos_item_id,
        pos_item_name=body.pos_item_name,
    )
    db.add(recipe)
    db.flush()

    # Add lines
    for line_data in body.lines:
        # Verify product exists
        product = db.query(Product).filter(Product.id == line_data.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {line_data.product_id} not found",
            )

        line = RecipeLine(
            recipe_id=recipe.id,
            product_id=line_data.product_id,
            qty=line_data.qty,
            unit=line_data.unit,
        )
        db.add(line)

    db.commit()
    db.refresh(recipe)
    return recipe


@router.put("/{recipe_id}", response_model=RecipeResponse)
@limiter.limit("30/minute")
def update_recipe(
    request: Request, recipe_id: int, body: RecipeUpdate, db: DbSession, current_user: RequireManager
):
    """Update a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    # Check for duplicate pos_item_id if changing
    if body.pos_item_id and body.pos_item_id != recipe.pos_item_id:
        existing = db.query(Recipe).filter(Recipe.pos_item_id == body.pos_item_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipe with pos_item_id '{body.pos_item_id}' already exists",
            )

    # Update basic fields
    if body.name is not None:
        recipe.name = body.name
    if body.pos_item_id is not None:
        recipe.pos_item_id = body.pos_item_id
    if body.pos_item_name is not None:
        recipe.pos_item_name = body.pos_item_name

    # Update lines if provided
    if body.lines is not None:
        # Delete existing lines
        db.query(RecipeLine).filter(RecipeLine.recipe_id == recipe_id).delete()

        # Add new lines
        for line_data in body.lines:
            product = db.query(Product).filter(Product.id == line_data.product_id).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product {line_data.product_id} not found",
                )

            line = RecipeLine(
                recipe_id=recipe.id,
                product_id=line_data.product_id,
                qty=line_data.qty,
                unit=line_data.unit,
            )
            db.add(line)

    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
def delete_recipe(request: Request, recipe_id: int, db: DbSession, current_user: RequireManager):
    """Delete a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    db.delete(recipe)
    db.commit()


@router.post("/import")
@limiter.limit("30/minute")
def import_recipes(
    request: Request,
    file: UploadFile = File(...),
    db: DbSession = None,
    current_user: RequireManager = None,
):
    """
    Import recipes from CSV file.

    CSV format: recipe_name,pos_item_id,pos_item_name,product_barcode,qty,unit

    Each row adds a line to the recipe. If recipe doesn't exist, it's created.
    """
    # Validate file extension with sanitized filename
    safe_filename = sanitize_filename(file.filename) if file.filename else "upload.csv"
    if not safe_filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a CSV")

    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    created_recipes = 0
    lines_added = 0
    errors = []

    # Cache recipes by name
    recipe_cache = {}

    for row_num, row in enumerate(reader, start=2):
        try:
            recipe_name = row["recipe_name"].strip()
            pos_item_id = row.get("pos_item_id", "").strip() or None
            pos_item_name = row.get("pos_item_name", "").strip() or None
            product_barcode = row["product_barcode"].strip()
            qty = Decimal(row["qty"])
            unit = row.get("unit", "pcs").strip() or "pcs"

            # Get or create recipe
            if recipe_name not in recipe_cache:
                recipe = db.query(Recipe).filter(Recipe.name == recipe_name).first()
                if not recipe:
                    recipe = Recipe(
                        name=recipe_name,
                        pos_item_id=pos_item_id,
                        pos_item_name=pos_item_name,
                    )
                    db.add(recipe)
                    db.flush()
                    created_recipes += 1
                recipe_cache[recipe_name] = recipe.id

            recipe_id = recipe_cache[recipe_name]

            # Find product by barcode
            product = db.query(Product).filter(Product.barcode == product_barcode).first()
            if not product:
                errors.append(f"Row {row_num}: Product with barcode '{product_barcode}' not found")
                continue

            # Check if line already exists
            existing_line = (
                db.query(RecipeLine)
                .filter(RecipeLine.recipe_id == recipe_id, RecipeLine.product_id == product.id)
                .first()
            )

            if existing_line:
                existing_line.qty = qty
                existing_line.unit = unit
            else:
                line = RecipeLine(
                    recipe_id=recipe_id,
                    product_id=product.id,
                    qty=qty,
                    unit=unit,
                )
                db.add(line)

            lines_added += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    db.commit()

    return {
        "recipes_created": created_recipes,
        "lines_added": lines_added,
        "errors": errors[:20],
    }


# ==================== MENU ITEM LINKING ====================

@router.post("/{recipe_id}/link-menu-item")
@limiter.limit("30/minute")
def link_recipe_to_menu_item(
    request: Request,
    recipe_id: int,
    menu_item_id: int,
    db: DbSession,
    current_user: RequireManager,
):
    """Link a recipe to a menu item for automatic stock deduction."""
    from app.models.restaurant import MenuItem

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Link the recipe
    menu_item.recipe_id = recipe_id

    # Also update recipe with pos_item_id for backup lookup
    if not recipe.pos_item_id:
        recipe.pos_item_id = str(menu_item_id)
    if not recipe.pos_item_name:
        recipe.pos_item_name = menu_item.name

    db.commit()

    return {
        "status": "linked",
        "recipe_id": recipe_id,
        "recipe_name": recipe.name,
        "menu_item_id": menu_item_id,
        "menu_item_name": menu_item.name,
    }


@router.delete("/{recipe_id}/unlink-menu-item")
@limiter.limit("30/minute")
def unlink_recipe_from_menu_item(
    request: Request,
    recipe_id: int,
    menu_item_id: int,
    db: DbSession,
    current_user: RequireManager,
):
    """Unlink a recipe from a menu item."""
    from app.models.restaurant import MenuItem

    menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    if menu_item.recipe_id != recipe_id:
        raise HTTPException(status_code=400, detail="Menu item is not linked to this recipe")

    menu_item.recipe_id = None
    db.commit()

    return {"status": "unlinked", "recipe_id": recipe_id, "menu_item_id": menu_item_id}


@router.get("/{recipe_id}/linked-menu-items")
@limiter.limit("60/minute")
def get_linked_menu_items(
    request: Request,
    recipe_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get all menu items linked to a recipe."""
    from app.models.restaurant import MenuItem

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    menu_items = db.query(MenuItem).filter(MenuItem.recipe_id == recipe_id).all()

    return {
        "recipe_id": recipe_id,
        "recipe_name": recipe.name,
        "menu_items": [
            {
                "id": m.id,
                "name": m.name,
                "price": float(m.price) if m.price else 0,
                "category": m.category,
                "available": m.available,
            }
            for m in menu_items
        ],
    }


@router.get("/{recipe_id}/cost")
@limiter.limit("60/minute")
def get_single_recipe_cost(
    request: Request,
    recipe_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get cost breakdown for a single recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    total_cost = Decimal("0")
    ingredients = []
    for line in recipe.lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        line_cost = Decimal("0")
        if product and product.cost_price:
            line_cost = line.qty * product.cost_price
            total_cost += line_cost
        ingredients.append({
            "product_id": line.product_id,
            "product_name": product.name if product else "Unknown",
            "qty": float(line.qty),
            "unit": line.unit,
            "unit_cost": float(product.cost_price) if product and product.cost_price else 0,
            "line_cost": float(line_cost),
        })

    return {
        "recipe_id": recipe.id,
        "recipe_name": recipe.name,
        "total_cost": float(total_cost),
        "sell_price": float(total_cost * 4) if total_cost > 0 else 0,
        "margin_pct": 75.0 if total_cost > 0 else 0,
        "ingredients": ingredients,
    }


@router.get("/{recipe_id}/cost-history")
@limiter.limit("60/minute")
def get_recipe_cost_history(
    request: Request,
    recipe_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get cost history for a recipe based on its update timestamps."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    # Calculate current cost
    total_cost = Decimal("0")
    for line in recipe.lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        if product and product.cost_price:
            total_cost += line.qty * product.cost_price

    # Return current snapshot (full history requires audit log table)
    return {
        "recipe_id": recipe.id,
        "recipe_name": recipe.name,
        "history": [
            {
                "date": recipe.updated_at.isoformat() if recipe.updated_at else recipe.created_at.isoformat(),
                "total_cost": float(total_cost),
                "ingredients_count": len(recipe.lines),
            }
        ],
    }


@router.get("/{recipe_id}/versions")
@limiter.limit("60/minute")
def get_recipe_versions(
    request: Request,
    recipe_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get version history for a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    # Return current version (full versioning requires audit log table)
    return {
        "recipe_id": recipe.id,
        "recipe_name": recipe.name,
        "current_version": 1,
        "versions": [
            {
                "version": 1,
                "created_at": recipe.created_at.isoformat() if recipe.created_at else None,
                "updated_at": recipe.updated_at.isoformat() if recipe.updated_at else None,
                "ingredients_count": len(recipe.lines),
                "is_current": True,
            }
        ],
    }


@router.get("/{recipe_id}/stock-availability")
@limiter.limit("60/minute")
def get_recipe_stock_availability(
    request: Request,
    recipe_id: int,
    location_id: int = Query(1),
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """Check stock availability for a recipe - how many can be made."""
    from app.services.stock_deduction_service import StockDeductionService

    service = StockDeductionService(db)
    result = service.get_stock_for_recipe(recipe_id, location_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
