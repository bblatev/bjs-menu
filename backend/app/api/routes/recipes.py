"""Recipe (BOM) routes."""

from __future__ import annotations

import csv
import io

from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.core.rbac import CurrentUser, RequireManager
from app.db.session import DbSession
from app.models.product import Product
from app.models.recipe import Recipe, RecipeLine
from app.schemas.recipe import RecipeCreate, RecipeResponse, RecipeUpdate

router = APIRouter()


@router.get("/", response_model=List[RecipeResponse])
def list_recipes(
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


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: int, db: DbSession, current_user: CurrentUser):
    """Get a specific recipe with lines."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


@router.post("/", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(request: RecipeCreate, db: DbSession, current_user: RequireManager):
    """Create a new recipe."""
    # Check for duplicate pos_item_id
    if request.pos_item_id:
        existing = db.query(Recipe).filter(Recipe.pos_item_id == request.pos_item_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipe with pos_item_id '{request.pos_item_id}' already exists",
            )

    recipe = Recipe(
        name=request.name,
        pos_item_id=request.pos_item_id,
        pos_item_name=request.pos_item_name,
    )
    db.add(recipe)
    db.flush()

    # Add lines
    for line_data in request.lines:
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
def update_recipe(
    recipe_id: int, request: RecipeUpdate, db: DbSession, current_user: RequireManager
):
    """Update a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    # Check for duplicate pos_item_id if changing
    if request.pos_item_id and request.pos_item_id != recipe.pos_item_id:
        existing = db.query(Recipe).filter(Recipe.pos_item_id == request.pos_item_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipe with pos_item_id '{request.pos_item_id}' already exists",
            )

    # Update basic fields
    if request.name is not None:
        recipe.name = request.name
    if request.pos_item_id is not None:
        recipe.pos_item_id = request.pos_item_id
    if request.pos_item_name is not None:
        recipe.pos_item_name = request.pos_item_name

    # Update lines if provided
    if request.lines is not None:
        # Delete existing lines
        db.query(RecipeLine).filter(RecipeLine.recipe_id == recipe_id).delete()

        # Add new lines
        for line_data in request.lines:
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
def delete_recipe(recipe_id: int, db: DbSession, current_user: RequireManager):
    """Delete a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    db.delete(recipe)
    db.commit()


@router.post("/import")
def import_recipes(
    file: UploadFile = File(...),
    db: DbSession = None,
    current_user: RequireManager = None,
):
    """
    Import recipes from CSV file.

    CSV format: recipe_name,pos_item_id,pos_item_name,product_barcode,qty,unit

    Each row adds a line to the recipe. If recipe doesn't exist, it's created.
    """
    if not file.filename.endswith(".csv"):
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
