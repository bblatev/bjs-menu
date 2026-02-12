"""
Currency Service
Handles EUR/BGN conversion and dual currency operations for euro adoption
"""

from typing import Dict, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import MenuItem


# Fixed EUR to BGN rate (official Bulgarian National Bank rate)
EUR_TO_BGN_RATE = Decimal('1.95583')
BGN_TO_EUR_RATE = Decimal('1') / EUR_TO_BGN_RATE


class CurrencyService:
    """Service for handling dual currency operations during euro transition"""
    
    def __init__(self, db: Session):
        self.db = db
        self.eur_rate = EUR_TO_BGN_RATE
        self.bgn_rate = BGN_TO_EUR_RATE
    
    def convert_eur_to_bgn(self, eur_amount: Decimal) -> Decimal:
        """
        Convert EUR to BGN using fixed rate

        Args:
            eur_amount: Amount in EUR

        Returns:
            Amount in BGN, rounded to 2 decimal places
        """
        # Ensure we have a Decimal
        if not isinstance(eur_amount, Decimal):
            eur_amount = Decimal(str(eur_amount))
        bgn_amount = eur_amount * self.eur_rate
        return bgn_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def convert_bgn_to_eur(self, bgn_amount: Decimal) -> Decimal:
        """
        Convert BGN to EUR using fixed rate

        Args:
            bgn_amount: Amount in BGN

        Returns:
            Amount in EUR, rounded to 2 decimal places
        """
        # Ensure we have a Decimal
        if not isinstance(bgn_amount, Decimal):
            bgn_amount = Decimal(str(bgn_amount))
        eur_amount = bgn_amount * self.bgn_rate
        return eur_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def get_dual_price(self, amount: Decimal, currency: str = 'BGN') -> Dict:
        """
        Get price in both currencies
        
        Args:
            amount: Price amount
            currency: Original currency ('EUR' or 'BGN')
            
        Returns:
            Dict with EUR and BGN values plus formatted strings
        """
        if currency == 'EUR':
            eur = amount
            bgn = self.convert_eur_to_bgn(amount)
        else:  # BGN
            bgn = amount
            eur = self.convert_bgn_to_eur(amount)
        
        return {
            'eur': float(eur),
            'bgn': float(bgn),
            'eur_formatted': f"€{eur:.2f}",
            'bgn_formatted': f"{bgn:.2f} лв",
            'conversion_rate': float(self.eur_rate)
        }
    
    def format_dual_price(self, amount: Decimal, currency: str = 'BGN') -> str:
        """
        Format price for display in both currencies
        
        Args:
            amount: Price amount
            currency: Original currency
            
        Returns:
            Formatted string like "€5.00 / 9.78 лв"
        """
        prices = self.get_dual_price(amount, currency)
        return f"{prices['eur_formatted']} / {prices['bgn_formatted']}"
    
    def is_dual_pricing_active(self, venue_id: int) -> bool:
        """
        Check if dual pricing should be shown
        
        Dual pricing mandatory from August 8, 2025 to December 31, 2026
        """
        now = datetime.now()
        
        # Dual pricing mandatory from August 8, 2025
        dual_pricing_start = datetime(2025, 8, 8)
        
        # Until December 31, 2026 (12 months after EUR adoption)
        dual_pricing_end = datetime(2026, 12, 31, 23, 59, 59)
        
        return dual_pricing_start <= now <= dual_pricing_end
    
    def get_primary_currency(self, venue_id: int) -> str:
        """
        Get primary currency based on date
        
        Returns 'BGN' before January 1, 2026, 'EUR' after
        """
        now = datetime.now()
        euro_adoption = datetime(2026, 1, 1)
        
        if now >= euro_adoption:
            return 'EUR'
        else:
            return 'BGN'
    
    def accept_both_currencies(self, venue_id: int) -> bool:
        """
        Check if venue accepts both currencies
        
        Both currencies accepted during dual circulation period:
        January 1, 2026 - January 31, 2026
        """
        now = datetime.now()
        
        # Dual circulation period: Jan 1 - Jan 31, 2026
        dual_start = datetime(2026, 1, 1)
        dual_end = datetime(2026, 1, 31, 23, 59, 59)
        
        return dual_start <= now <= dual_end
    
    def calculate_order_totals_dual(
        self, 
        items: list, 
        payment_currency: str = 'BGN',
        vat_rate: Decimal = Decimal('0.09')
    ) -> Dict:
        """
        Calculate order totals in both currencies
        
        Args:
            items: List of order items with price and quantity
            payment_currency: Currency customer is paying in
            vat_rate: VAT rate (default 9% for restaurants)
            
        Returns:
            Dict with subtotal, tax, and total in both currencies
        """
        subtotal = Decimal('0')
        
        for item in items:
            price = Decimal(str(item.get('price', 0)))
            quantity = item.get('quantity', 1)
            subtotal += price * quantity
        
        # Calculate VAT
        tax = subtotal * vat_rate
        total = subtotal + tax
        
        # Get both currencies
        if payment_currency == 'EUR':
            totals = {
                'subtotal_eur': float(subtotal),
                'tax_eur': float(tax),
                'total_eur': float(total),
                'subtotal_bgn': float(self.convert_eur_to_bgn(subtotal)),
                'tax_bgn': float(self.convert_eur_to_bgn(tax)),
                'total_bgn': float(self.convert_eur_to_bgn(total)),
                'currency': 'EUR',
                'vat_rate': float(vat_rate)
            }
        else:  # BGN
            totals = {
                'subtotal_bgn': float(subtotal),
                'tax_bgn': float(tax),
                'total_bgn': float(total),
                'subtotal_eur': float(self.convert_bgn_to_eur(subtotal)),
                'tax_eur': float(self.convert_bgn_to_eur(tax)),
                'total_eur': float(self.convert_bgn_to_eur(total)),
                'currency': 'BGN',
                'vat_rate': float(vat_rate)
            }
        
        return totals
    
    def get_menu_item_dual_price(self, item_id: int) -> Optional[Dict]:
        """
        Get menu item price in both currencies
        
        Args:
            item_id: Menu item ID
            
        Returns:
            Dict with prices in both currencies, or None if item not found
        """
        item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if not item:
            return None
        
        # Use stored EUR price if available, else convert
        if hasattr(item, 'price_eur') and item.price_eur:
            eur_price = item.price_eur
            bgn_price = item.price
        else:
            bgn_price = item.price
            eur_price = self.convert_bgn_to_eur(bgn_price)
        
        return {
            'item_id': item.id,
            'name': item.name,
            'price_eur': float(eur_price),
            'price_bgn': float(bgn_price),
            'formatted': self.format_dual_price(eur_price, 'EUR'),
            'original_currency': getattr(item, 'original_currency', 'BGN')
        }
    
    def get_currency_status(self, venue_id: int) -> Dict:
        """
        Get complete currency status for venue
        
        Returns:
            Dict with all currency-related information
        """
        return {
            'dual_pricing_active': self.is_dual_pricing_active(venue_id),
            'primary_currency': self.get_primary_currency(venue_id),
            'accepts_both_currencies': self.accept_both_currencies(venue_id),
            'conversion_rate': float(self.eur_rate),
            'euro_adoption_date': '2026-01-01',
            'dual_pricing_start': '2025-08-08',
            'dual_pricing_end': '2026-12-31',
            'dual_circulation_start': '2026-01-01',
            'dual_circulation_end': '2026-01-31'
        }
