"""Ratings API routes - item and service ratings."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel

from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser

router = APIRouter()


# ==================== SCHEMAS ====================

class RatingStats(BaseModel):
    total_ratings: int
    average_rating: float
    rating_distribution: dict

class ItemRatingCreate(BaseModel):
    order_item_id: int
    rating: int
    comment: Optional[str] = None

class ItemRatingResponse(BaseModel):
    id: int
    order_item_id: int
    item_id: Optional[int] = None
    rating: int
    comment: Optional[str] = None
    created_at: Optional[str] = None

class ServiceRatingCreate(BaseModel):
    table_token: Optional[str] = None
    table_id: Optional[int] = None
    rating: int
    comment: Optional[str] = None

class ServiceRatingResponse(BaseModel):
    id: int
    rating: int
    comment: Optional[str] = None
    created_at: Optional[str] = None

class RatingUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None

class ItemRatingList(BaseModel):
    ratings: List[ItemRatingResponse]
    total: int
    average: float

class ServiceRatingList(BaseModel):
    ratings: List[ServiceRatingResponse]
    total: int
    average: float


# ==================== In-memory store (placeholder) ====================
_item_ratings: list = []
_service_ratings: list = []
_next_item_id = 1
_next_service_id = 1


# ==================== ITEM RATINGS ====================

@router.post("/items", response_model=ItemRatingResponse, status_code=201)
def rate_item(request: ItemRatingCreate, db: DbSession):
    """Rate a menu item (public endpoint)."""
    global _next_item_id
    if not 1 <= request.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    rating = {"id": _next_item_id, "order_item_id": request.order_item_id, "item_id": None, "rating": request.rating, "comment": request.comment, "created_at": datetime.utcnow().isoformat()}
    _item_ratings.append(rating)
    _next_item_id += 1
    return ItemRatingResponse(**rating)


@router.get("/items", response_model=ItemRatingList)
def get_item_ratings(db: DbSession, menu_item_id: Optional[int] = None, min_rating: Optional[int] = Query(None, ge=1, le=5), max_rating: Optional[int] = Query(None, ge=1, le=5), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    """Get all item ratings with optional filters."""
    filtered = list(_item_ratings)
    if menu_item_id:
        filtered = [r for r in filtered if r.get("item_id") == menu_item_id]
    if min_rating:
        filtered = [r for r in filtered if r["rating"] >= min_rating]
    if max_rating:
        filtered = [r for r in filtered if r["rating"] <= max_rating]
    total = len(filtered)
    avg = sum(r["rating"] for r in filtered) / total if total > 0 else 0
    page = filtered[skip: skip + limit]
    return ItemRatingList(ratings=[ItemRatingResponse(**r) for r in page], total=total, average=round(avg, 2))


@router.get("/items/{rating_id}", response_model=ItemRatingResponse)
def get_item_rating(rating_id: int, db: DbSession):
    """Get a specific item rating by ID."""
    for r in _item_ratings:
        if r["id"] == rating_id:
            return ItemRatingResponse(**r)
    raise HTTPException(status_code=404, detail="Rating not found")


@router.get("/items/menu/{menu_item_id}/stats", response_model=RatingStats)
def get_menu_item_rating_stats(menu_item_id: int, db: DbSession):
    """Get rating statistics for a specific menu item."""
    ratings = [r for r in _item_ratings if r.get("item_id") == menu_item_id]
    if not ratings:
        return RatingStats(total_ratings=0, average_rating=0.0, rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        if 1 <= r["rating"] <= 5:
            distribution[r["rating"]] += 1
    avg = sum(r["rating"] for r in ratings) / len(ratings)
    return RatingStats(total_ratings=len(ratings), average_rating=round(avg, 2), rating_distribution=distribution)


@router.put("/items/{rating_id}", response_model=ItemRatingResponse)
def update_item_rating(rating_id: int, update_data: RatingUpdate, db: DbSession):
    """Update an item rating."""
    for r in _item_ratings:
        if r["id"] == rating_id:
            if update_data.rating is not None:
                if not 1 <= update_data.rating <= 5:
                    raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
                r["rating"] = update_data.rating
            if update_data.comment is not None:
                r["comment"] = update_data.comment
            return ItemRatingResponse(**r)
    raise HTTPException(status_code=404, detail="Rating not found")


@router.delete("/items/{rating_id}", status_code=204)
def delete_item_rating(rating_id: int, db: DbSession):
    """Delete an item rating."""
    global _item_ratings
    original_len = len(_item_ratings)
    _item_ratings = [r for r in _item_ratings if r["id"] != rating_id]
    if len(_item_ratings) == original_len:
        raise HTTPException(status_code=404, detail="Rating not found")
    return None


# ==================== SERVICE RATINGS ====================

@router.post("/service", response_model=ServiceRatingResponse, status_code=201)
def rate_service(request: ServiceRatingCreate, db: DbSession):
    """Rate service (public endpoint)."""
    global _next_service_id
    if not 1 <= request.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    rating = {"id": _next_service_id, "rating": request.rating, "comment": request.comment, "created_at": datetime.utcnow().isoformat()}
    _service_ratings.append(rating)
    _next_service_id += 1
    return ServiceRatingResponse(**rating)


@router.get("/service", response_model=ServiceRatingList)
def get_service_ratings(db: DbSession, table_id: Optional[int] = None, min_rating: Optional[int] = Query(None, ge=1, le=5), max_rating: Optional[int] = Query(None, ge=1, le=5), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    """Get all service ratings with optional filters."""
    filtered = list(_service_ratings)
    if min_rating:
        filtered = [r for r in filtered if r["rating"] >= min_rating]
    if max_rating:
        filtered = [r for r in filtered if r["rating"] <= max_rating]
    total = len(filtered)
    avg = sum(r["rating"] for r in filtered) / total if total > 0 else 0
    page = filtered[skip: skip + limit]
    return ServiceRatingList(ratings=[ServiceRatingResponse(**r) for r in page], total=total, average=round(avg, 2))


@router.get("/service/{rating_id}", response_model=ServiceRatingResponse)
def get_service_rating(rating_id: int, db: DbSession):
    """Get a specific service rating by ID."""
    for r in _service_ratings:
        if r["id"] == rating_id:
            return ServiceRatingResponse(**r)
    raise HTTPException(status_code=404, detail="Rating not found")


@router.get("/service/stats", response_model=RatingStats)
def get_service_rating_stats(db: DbSession, table_id: Optional[int] = None):
    """Get overall service rating statistics."""
    ratings = list(_service_ratings)
    if not ratings:
        return RatingStats(total_ratings=0, average_rating=0.0, rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        if 1 <= r["rating"] <= 5:
            distribution[r["rating"]] += 1
    avg = sum(r["rating"] for r in ratings) / len(ratings)
    return RatingStats(total_ratings=len(ratings), average_rating=round(avg, 2), rating_distribution=distribution)


@router.put("/service/{rating_id}", response_model=ServiceRatingResponse)
def update_service_rating(rating_id: int, update_data: RatingUpdate, db: DbSession):
    """Update a service rating."""
    for r in _service_ratings:
        if r["id"] == rating_id:
            if update_data.rating is not None:
                if not 1 <= update_data.rating <= 5:
                    raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
                r["rating"] = update_data.rating
            if update_data.comment is not None:
                r["comment"] = update_data.comment
            return ServiceRatingResponse(**r)
    raise HTTPException(status_code=404, detail="Rating not found")


@router.delete("/service/{rating_id}", status_code=204)
def delete_service_rating(rating_id: int, db: DbSession):
    """Delete a service rating."""
    global _service_ratings
    original_len = len(_service_ratings)
    _service_ratings = [r for r in _service_ratings if r["id"] != rating_id]
    if len(_service_ratings) == original_len:
        raise HTTPException(status_code=404, detail="Rating not found")
    return None
