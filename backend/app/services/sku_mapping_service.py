"""SKU Mapping Service: Match products using various strategies."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import logging
import re

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models.product import Product

logger = logging.getLogger(__name__)


class MatchMethod(str, Enum):
    """Method used to match a product."""
    BARCODE = "barcode"          # Exact barcode match
    SKU = "sku"                  # Exact SKU match
    AI_RECOGNITION = "ai"        # AI model recognition
    FUZZY_NAME = "fuzzy"         # Fuzzy name matching
    MANUAL_MAP = "manual"        # Manual mapping table
    NOT_FOUND = "not_found"      # No match found


@dataclass
class MatchResult:
    """Result of a product matching attempt."""
    product_id: Optional[int]
    product_name: Optional[str]
    method: MatchMethod
    confidence: float  # 0.0 to 1.0
    alternatives: List[Dict] = None  # Other possible matches

    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []


class SKUMappingService:
    """Service for matching products using multiple strategies."""

    def __init__(self, db: Session):
        self.db = db
        # Configurable thresholds
        self.fuzzy_threshold = 0.4  # Minimum similarity for fuzzy match (lowered to allow partial matches)
        self.ai_confidence_threshold = 0.65  # Minimum AI confidence

    def match_by_barcode(self, barcode: str) -> Optional[MatchResult]:
        """
        Try to match product by exact barcode.
        Returns MatchResult if found, None otherwise.
        """
        if not barcode:
            return None

        # Clean barcode (remove spaces, dashes)
        clean_barcode = re.sub(r'[\s\-]', '', barcode.strip())

        product = self.db.query(Product).filter(
            Product.barcode == clean_barcode
        ).first()

        if product:
            return MatchResult(
                product_id=product.id,
                product_name=product.name,
                method=MatchMethod.BARCODE,
                confidence=1.0,
            )

        # Try with leading zeros removed/added
        if clean_barcode.startswith('0'):
            alt_barcode = clean_barcode.lstrip('0')
            product = self.db.query(Product).filter(
                Product.barcode == alt_barcode
            ).first()
            if product:
                return MatchResult(
                    product_id=product.id,
                    product_name=product.name,
                    method=MatchMethod.BARCODE,
                    confidence=0.95,
                )

        return None

    def match_by_sku(self, sku: str) -> Optional[MatchResult]:
        """
        Try to match product by exact SKU.
        """
        if not sku:
            return None

        clean_sku = sku.strip().upper()

        product = self.db.query(Product).filter(
            func.upper(Product.sku) == clean_sku
        ).first()

        if product:
            return MatchResult(
                product_id=product.id,
                product_name=product.name,
                method=MatchMethod.SKU,
                confidence=1.0,
            )

        return None

    def match_by_ai_recognition(
        self,
        product_id: int,
        confidence: float,
    ) -> Optional[MatchResult]:
        """
        Create match result from AI recognition.
        """
        if confidence < self.ai_confidence_threshold:
            return None

        product = self.db.query(Product).filter(
            Product.id == product_id
        ).first()

        if product:
            return MatchResult(
                product_id=product.id,
                product_name=product.name,
                method=MatchMethod.AI_RECOGNITION,
                confidence=confidence,
            )

        return None

    def match_by_fuzzy_name(
        self,
        name: str,
        limit: int = 5,
    ) -> Optional[MatchResult]:
        """
        Try to match product by fuzzy name matching.
        Returns best match if above threshold.
        """
        if not name or len(name) < 2:
            return None

        # Normalize search term
        search_term = self._normalize_name(name)
        search_words = set(search_term.split())

        # Get candidate products
        products = self.db.query(Product).filter(
            Product.active == True
        ).all()

        matches = []
        for product in products:
            product_name = self._normalize_name(product.name)
            product_words = set(product_name.split())

            # Calculate similarity
            similarity = self._calculate_similarity(
                search_term, search_words,
                product_name, product_words
            )

            if similarity >= self.fuzzy_threshold:
                matches.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "similarity": similarity,
                })

        if not matches:
            return None

        # Sort by similarity
        matches.sort(key=lambda x: x["similarity"], reverse=True)

        best_match = matches[0]
        alternatives = matches[1:limit] if len(matches) > 1 else []

        return MatchResult(
            product_id=best_match["product_id"],
            product_name=best_match["product_name"],
            method=MatchMethod.FUZZY_NAME,
            confidence=best_match["similarity"],
            alternatives=alternatives,
        )

    def _normalize_name(self, name: str) -> str:
        """Normalize product name for comparison."""
        if not name:
            return ""

        # Lowercase
        name = name.lower()

        # Remove common words/suffixes
        remove_words = ['bottle', 'btl', 'ml', 'cl', 'ltr', 'l', 'pk', 'pack', 'cs', 'case']
        for word in remove_words:
            name = re.sub(rf'\b{word}\b', '', name)

        # Remove numbers (volumes, etc)
        name = re.sub(r'\d+', '', name)

        # Remove special characters
        name = re.sub(r'[^\w\s]', '', name)

        # Collapse whitespace
        name = ' '.join(name.split())

        return name.strip()

    def _calculate_similarity(
        self,
        search_term: str,
        search_words: set,
        product_name: str,
        product_words: set,
    ) -> float:
        """
        Calculate similarity between search term and product name.
        Uses combination of word overlap and substring matching.
        """
        if not search_term or not product_name:
            return 0.0

        # Word overlap (Jaccard similarity)
        if search_words and product_words:
            intersection = len(search_words & product_words)
            union = len(search_words | product_words)
            word_similarity = intersection / union if union > 0 else 0
        else:
            word_similarity = 0

        # Substring containment
        substring_score = 0
        if search_term in product_name:
            substring_score = len(search_term) / len(product_name)
        elif product_name in search_term:
            substring_score = len(product_name) / len(search_term)

        # Levenshtein-like ratio (simplified)
        max_len = max(len(search_term), len(product_name))
        min_len = min(len(search_term), len(product_name))
        length_ratio = min_len / max_len if max_len > 0 else 0

        # Common prefix bonus
        common_prefix = 0
        for i, (c1, c2) in enumerate(zip(search_term, product_name)):
            if c1 == c2:
                common_prefix += 1
            else:
                break
        prefix_score = common_prefix / max_len if max_len > 0 else 0

        # Weighted combination
        similarity = (
            word_similarity * 0.4 +
            substring_score * 0.3 +
            length_ratio * 0.1 +
            prefix_score * 0.2
        )

        return min(similarity, 1.0)

    def search_products(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search products by name, barcode, or SKU.
        Returns list of matching products with relevance scores.
        """
        if not query or len(query) < 2:
            return []

        results = []

        # Exact barcode match
        barcode_match = self.match_by_barcode(query)
        if barcode_match and barcode_match.product_id:
            results.append({
                "product_id": barcode_match.product_id,
                "product_name": barcode_match.product_name,
                "match_type": "barcode",
                "confidence": barcode_match.confidence,
            })

        # Exact SKU match
        sku_match = self.match_by_sku(query)
        if sku_match and sku_match.product_id:
            # Avoid duplicates
            if not any(r["product_id"] == sku_match.product_id for r in results):
                results.append({
                    "product_id": sku_match.product_id,
                    "product_name": sku_match.product_name,
                    "match_type": "sku",
                    "confidence": sku_match.confidence,
                })

        # Database LIKE search
        like_pattern = f"%{query}%"
        db_matches = self.db.query(Product).filter(
            Product.active == True,
            or_(
                Product.name.ilike(like_pattern),
                Product.barcode.ilike(like_pattern),
                Product.sku.ilike(like_pattern),
            )
        ).limit(limit * 2).all()

        for product in db_matches:
            if not any(r["product_id"] == product.id for r in results):
                # Calculate relevance
                name_match = query.lower() in product.name.lower() if product.name else False
                confidence = 0.9 if name_match else 0.7

                results.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "match_type": "search",
                    "confidence": confidence,
                })

        # Fuzzy match for remaining slots
        if len(results) < limit:
            fuzzy_match = self.match_by_fuzzy_name(query, limit=limit - len(results))
            if fuzzy_match:
                if not any(r["product_id"] == fuzzy_match.product_id for r in results):
                    results.append({
                        "product_id": fuzzy_match.product_id,
                        "product_name": fuzzy_match.product_name,
                        "match_type": "fuzzy",
                        "confidence": fuzzy_match.confidence,
                    })

                for alt in fuzzy_match.alternatives:
                    if not any(r["product_id"] == alt["product_id"] for r in results):
                        results.append({
                            "product_id": alt["product_id"],
                            "product_name": alt["product_name"],
                            "match_type": "fuzzy",
                            "confidence": alt["similarity"],
                        })

        # Sort by confidence and limit
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:limit]

    def match_product(
        self,
        barcode: Optional[str] = None,
        sku: Optional[str] = None,
        name: Optional[str] = None,
        ai_product_id: Optional[int] = None,
        ai_confidence: Optional[float] = None,
    ) -> MatchResult:
        """
        Try to match a product using all available strategies in priority order.
        Returns the best match found.
        """
        # 1. Try barcode (highest priority, exact match)
        if barcode:
            result = self.match_by_barcode(barcode)
            if result:
                return result

        # 2. Try SKU
        if sku:
            result = self.match_by_sku(sku)
            if result:
                return result

        # 3. Try AI recognition
        if ai_product_id and ai_confidence:
            result = self.match_by_ai_recognition(ai_product_id, ai_confidence)
            if result:
                return result

        # 4. Try fuzzy name match
        if name:
            result = self.match_by_fuzzy_name(name)
            if result:
                return result

        # No match found
        return MatchResult(
            product_id=None,
            product_name=None,
            method=MatchMethod.NOT_FOUND,
            confidence=0.0,
        )


def match_product_from_scan(
    db: Session,
    barcode: Optional[str] = None,
    ai_product_id: Optional[int] = None,
    ai_confidence: Optional[float] = None,
    manual_name: Optional[str] = None,
) -> MatchResult:
    """
    Convenience function to match a product from various scan inputs.
    """
    service = SKUMappingService(db)
    return service.match_product(
        barcode=barcode,
        ai_product_id=ai_product_id,
        ai_confidence=ai_confidence,
        name=manual_name,
    )
