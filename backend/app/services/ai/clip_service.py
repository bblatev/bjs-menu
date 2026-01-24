"""CLIP-based zero-shot product recognition service.

Uses OpenAI's CLIP model for recognizing products without training.
Falls back to custom-trained features when CLIP confidence is low.
"""

import logging
from typing import List, Dict, Tuple, Optional
from io import BytesIO

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Lazy loading of CLIP model
_clip_model = None
_clip_processor = None
_clip_available = None


def is_clip_available() -> bool:
    """Check if CLIP is available."""
    global _clip_available
    if _clip_available is None:
        try:
            from transformers import CLIPProcessor, CLIPModel
            _clip_available = True
        except ImportError:
            _clip_available = False
            logger.warning("CLIP not available - transformers package not installed")
    return _clip_available


def _load_clip_model():
    """Lazy load CLIP model."""
    global _clip_model, _clip_processor

    if _clip_model is None:
        try:
            from transformers import CLIPProcessor, CLIPModel

            logger.info("Loading CLIP model (first time may take a moment)...")

            # Use the smaller but effective CLIP model
            model_name = "openai/clip-vit-base-patch32"

            _clip_processor = CLIPProcessor.from_pretrained(model_name)
            _clip_model = CLIPModel.from_pretrained(model_name)

            logger.info("CLIP model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise

    return _clip_model, _clip_processor


# Default product descriptions for common bar items
# These are used for zero-shot recognition
DEFAULT_PRODUCT_DESCRIPTIONS = {
    # Vodkas
    "Absolut Vodka": ["Absolut Vodka bottle", "blue label vodka bottle", "Swedish vodka Absolut"],
    "Grey Goose Vodka": ["Grey Goose vodka bottle", "French vodka grey goose"],
    "Smirnoff Vodka": ["Smirnoff vodka bottle", "red label vodka"],
    "Belvedere Vodka": ["Belvedere vodka bottle", "Polish vodka"],
    "Ketel One Vodka": ["Ketel One vodka bottle", "Dutch vodka"],

    # Whiskeys
    "Jack Daniels": ["Jack Daniels whiskey bottle", "Tennessee whiskey black label", "JD whiskey"],
    "Jameson Irish Whiskey": ["Jameson whiskey bottle", "Irish whiskey green label"],
    "Johnnie Walker": ["Johnnie Walker whiskey", "walking man whiskey label"],
    "Jim Beam": ["Jim Beam bourbon bottle", "Kentucky bourbon"],
    "Makers Mark": ["Makers Mark bourbon", "red wax seal bourbon"],

    # Rums
    "Bacardi White Rum": ["Bacardi rum bottle", "white rum Bacardi bat logo"],
    "Captain Morgan": ["Captain Morgan rum", "spiced rum pirate logo"],
    "Havana Club": ["Havana Club rum bottle", "Cuban rum"],
    "Malibu": ["Malibu coconut rum", "white bottle coconut rum"],

    # Gins
    "Bombay Sapphire Gin": ["Bombay Sapphire gin bottle", "blue bottle gin", "sapphire blue gin"],
    "Tanqueray Gin": ["Tanqueray gin bottle", "green bottle gin"],
    "Hendricks Gin": ["Hendricks gin bottle", "dark bottle cucumber gin"],
    "Gordons Gin": ["Gordons gin bottle", "green label gin"],
    "Beefeater Gin": ["Beefeater gin bottle", "London dry gin red label"],

    # Tequilas
    "Jose Cuervo Tequila": ["Jose Cuervo tequila", "gold tequila bottle"],
    "Patron Tequila": ["Patron tequila bottle", "premium tequila bee logo"],
    "Don Julio Tequila": ["Don Julio tequila", "Mexican tequila"],

    # Liqueurs
    "Baileys Irish Cream": ["Baileys Irish cream bottle", "cream liqueur"],
    "Kahlua": ["Kahlua coffee liqueur", "brown bottle coffee liqueur"],
    "Triple Sec": ["Triple Sec orange liqueur", "clear orange liqueur bottle"],
    "Cointreau": ["Cointreau orange liqueur", "square bottle orange liqueur"],
    "Amaretto": ["Amaretto almond liqueur", "Italian almond liqueur"],

    # Bitters
    "Angostura Bitters": ["Angostura bitters bottle", "small brown bottle bitters"],

    # Mixers & Soft Drinks
    "Coca-Cola": ["Coca-Cola bottle", "Coke red label", "cola bottle"],
    "Pepsi": ["Pepsi bottle", "blue cola bottle"],
    "Sprite": ["Sprite bottle", "lemon lime soda green bottle"],
    "Fanta": ["Fanta orange soda", "orange soda bottle"],
    "7-Up": ["7-Up bottle", "lemon lime soda"],
    "Schweppes Tonic Water": ["Schweppes tonic water", "yellow label tonic"],
    "Schweppes Soda Water": ["Schweppes soda water", "soda water bottle"],
    "Red Bull": ["Red Bull energy drink", "blue silver can energy drink"],
    "Monster Energy": ["Monster energy drink", "green M logo energy drink"],

    # Juices
    "Orange Juice": ["orange juice bottle", "OJ carton"],
    "Cranberry Juice": ["cranberry juice bottle", "red juice bottle"],
    "Pineapple Juice": ["pineapple juice bottle", "yellow juice bottle"],
    "Tomato Juice": ["tomato juice bottle", "red tomato juice"],
    "Grapefruit Juice": ["grapefruit juice bottle", "pink juice"],

    # Beers
    "Heineken": ["Heineken beer bottle", "green bottle beer star logo"],
    "Corona": ["Corona beer bottle", "Mexican beer clear bottle"],
    "Budweiser": ["Budweiser beer", "Bud beer red label"],
    "Stella Artois": ["Stella Artois beer", "Belgian beer"],
    "Guinness": ["Guinness stout", "black beer Irish stout"],

    # Wines
    "Red Wine": ["red wine bottle", "wine bottle dark glass"],
    "White Wine": ["white wine bottle", "wine bottle light colored"],
    "Rose Wine": ["rose wine bottle", "pink wine bottle"],
    "Prosecco": ["Prosecco bottle", "Italian sparkling wine"],
    "Champagne": ["Champagne bottle", "sparkling wine French"],

    # Other
    "Fresh Mint": ["fresh mint leaves", "mint herb bunch"],
    "Lime": ["lime citrus fruit", "green lime"],
    "Lemon": ["lemon citrus fruit", "yellow lemon"],
    "Green Olives": ["green olives jar", "olives in jar"],
    "Maraschino Cherries": ["maraschino cherries jar", "red cherries in jar"],
}


def recognize_with_clip(
    image_data: bytes,
    product_labels: Optional[List[str]] = None,
    product_descriptions: Optional[Dict[str, List[str]]] = None,
    top_k: int = 5,
    confidence_threshold: float = 0.15
) -> List[Dict]:
    """
    Recognize products using CLIP zero-shot classification.

    Args:
        image_data: Raw image bytes
        product_labels: List of product names to match against
        product_descriptions: Dict mapping product names to description lists
        top_k: Number of top results to return
        confidence_threshold: Minimum confidence to consider a match

    Returns:
        List of dicts with product_name, confidence, is_match
    """
    if not is_clip_available():
        return []

    try:
        model, processor = _load_clip_model()

        # Load image
        image = Image.open(BytesIO(image_data)).convert("RGB")

        # Use provided descriptions or defaults
        if product_descriptions is None:
            product_descriptions = DEFAULT_PRODUCT_DESCRIPTIONS

        if product_labels is None:
            product_labels = list(product_descriptions.keys())

        # Build text prompts - use primary description for each product
        text_prompts = []
        label_map = []  # Maps index back to product name

        for label in product_labels:
            if label in product_descriptions:
                # Use all descriptions for better matching
                for desc in product_descriptions[label][:2]:  # Use top 2 descriptions
                    text_prompts.append(f"a photo of {desc}")
                    label_map.append(label)
            else:
                # Use label directly
                text_prompts.append(f"a photo of {label} bottle")
                label_map.append(label)

        # Process image and text
        inputs = processor(
            text=text_prompts,
            images=image,
            return_tensors="pt",
            padding=True
        )

        # Get predictions
        import torch
        with torch.no_grad():
            outputs = model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]

        # Aggregate scores by product (take max across descriptions)
        product_scores = {}
        for idx, prob in enumerate(probs):
            label = label_map[idx]
            if label not in product_scores or prob > product_scores[label]:
                product_scores[label] = float(prob)

        # Sort by score
        sorted_products = sorted(
            product_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        # Format results
        results = []
        for product_name, confidence in sorted_products:
            results.append({
                "product_name": product_name,
                "confidence": round(confidence, 4),
                "is_match": confidence >= confidence_threshold,
                "source": "clip"
            })

        return results

    except Exception as e:
        logger.error(f"CLIP recognition failed: {e}")
        return []


def get_clip_embedding(image_data: bytes) -> Optional[np.ndarray]:
    """
    Get CLIP image embedding for an image.

    Can be used to compare images or for hybrid recognition.
    """
    if not is_clip_available():
        return None

    try:
        model, processor = _load_clip_model()

        image = Image.open(BytesIO(image_data)).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")

        import torch
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
            # Normalize
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy()[0]

    except Exception as e:
        logger.error(f"Failed to get CLIP embedding: {e}")
        return None


def match_product_to_database(
    clip_result: str,
    db_products: List[Dict],
    fuzzy_threshold: float = 0.6
) -> Optional[Dict]:
    """
    Match a CLIP result to a database product.

    Uses fuzzy string matching to handle variations in naming.
    """
    from difflib import SequenceMatcher

    clip_lower = clip_result.lower()

    best_match = None
    best_score = 0

    for product in db_products:
        product_name = product.get("name", "").lower()

        # Direct substring match
        if clip_lower in product_name or product_name in clip_lower:
            return product

        # Fuzzy match
        score = SequenceMatcher(None, clip_lower, product_name).ratio()

        # Check individual words
        clip_words = set(clip_lower.split())
        product_words = set(product_name.split())
        word_overlap = len(clip_words & product_words) / max(len(clip_words), 1)

        combined_score = (score + word_overlap) / 2

        if combined_score > best_score and combined_score >= fuzzy_threshold:
            best_score = combined_score
            best_match = product

    return best_match
