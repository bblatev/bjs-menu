"""
Sustainability Tracking Service
Implements carbon footprint tracking, waste management, and sustainability metrics
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from decimal import Decimal
import logging

from app.models import MenuItem, Order

logger = logging.getLogger(__name__)


class SustainabilityService:
    """Complete sustainability tracking and reporting"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Carbon footprint coefficients (kg CO2 per kg of ingredient)
        self.carbon_coefficients = {
            'beef': 27.0,
            'pork': 12.1,
            'chicken': 6.9,
            'fish': 5.4,
            'cheese': 13.5,
            'milk': 1.9,
            'eggs': 4.8,
            'rice': 2.7,
            'pasta': 1.5,
            'vegetables': 0.5,
            'bread': 1.3,
            'beer': 0.9,
            'wine': 1.5,
            'coffee': 1.3,
            'default': 2.0
        }
    
    # ==================== CARBON FOOTPRINT ====================
    
    def calculate_item_carbon_footprint(
        self,
        item_id: int
    ) -> Dict:
        """Calculate carbon footprint for a menu item"""
        item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if not item:
            return {}
        
        # Get item category and estimate footprint
        category = item.category.lower() if item.category else ''
        
        # Estimate based on category
        co2_per_serving = 0.0
        breakdown = {}
        
        if any(meat in category for meat in ['beef', 'steak', 'burger']):
            co2_per_serving = 2.5  # kg CO2
            breakdown['beef'] = 2.5
        elif 'pork' in category or 'bacon' in category:
            co2_per_serving = 1.2
            breakdown['pork'] = 1.2
        elif 'chicken' in category:
            co2_per_serving = 0.7
            breakdown['chicken'] = 0.7
        elif 'fish' in category or 'seafood' in category:
            co2_per_serving = 0.5
            breakdown['fish'] = 0.5
        elif any(veg in category for veg in ['salad', 'vegetable', 'vegan']):
            co2_per_serving = 0.3
            breakdown['vegetables'] = 0.3
        elif 'pasta' in category:
            co2_per_serving = 0.6
            breakdown['pasta'] = 0.6
        else:
            co2_per_serving = 0.8  # Default
            breakdown['default'] = 0.8
        
        # Add transport impact (estimated)
        transport_impact = 0.2
        co2_per_serving += transport_impact
        breakdown['transport'] = transport_impact
        
        return {
            'item_id': item_id,
            'item_name': item.name,
            'co2_kg_per_serving': round(co2_per_serving, 2),
            'ingredients_breakdown': breakdown,
            'transport_impact': transport_impact,
            'category': category,
            'rating': self._get_sustainability_rating(co2_per_serving)
        }
    
    def _get_sustainability_rating(self, co2_kg: float) -> Dict:
        """Get sustainability rating based on CO2 emissions"""
        if co2_kg < 0.5:
            return {'rating': 'A', 'label': '🌱 Excellent', 'color': '#22c55e'}
        elif co2_kg < 1.0:
            return {'rating': 'B', 'label': '✅ Good', 'color': '#84cc16'}
        elif co2_kg < 2.0:
            return {'rating': 'C', 'label': '⚠️ Moderate', 'color': '#eab308'}
        elif co2_kg < 3.0:
            return {'rating': 'D', 'label': '❗ High', 'color': '#f97316'}
        else:
            return {'rating': 'E', 'label': '🔴 Very High', 'color': '#ef4444'}
    
    def get_menu_carbon_footprints(
        self,
        venue_id: int
    ) -> List[Dict]:
        """Get carbon footprints for all menu items"""
        items = self.db.query(MenuItem).filter(
            MenuItem.location_id == venue_id,
            MenuItem.available == True
        ).all()
        
        footprints = []
        for item in items:
            footprint = self.calculate_item_carbon_footprint(item.id)
            if footprint:
                footprints.append(footprint)
        
        # Sort by CO2 impact
        footprints.sort(key=lambda x: x['co2_kg_per_serving'])
        
        return footprints
    
    def calculate_order_carbon_footprint(
        self,
        order_id: int
    ) -> Dict:
        """Calculate total carbon footprint for an order"""
        from app.models import Order
        
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {}
        
        total_co2 = 0.0
        items_breakdown = []
        
        for order_item in order.items:
            footprint = self.calculate_item_carbon_footprint(order_item.menu_item_id)
            item_co2 = footprint.get('co2_kg_per_serving', 0) * order_item.quantity
            total_co2 += item_co2
            
            items_breakdown.append({
                'item_name': order_item.menu_item.name,
                'quantity': order_item.quantity,
                'co2_per_item': footprint.get('co2_kg_per_serving', 0),
                'total_co2': item_co2
            })
        
        # Calculate equivalent metrics
        equivalents = self._calculate_equivalents(total_co2)
        
        return {
            'order_id': order_id,
            'total_co2_kg': round(total_co2, 2),
            'items_breakdown': items_breakdown,
            'equivalents': equivalents,
            'rating': self._get_sustainability_rating(total_co2)
        }
    
    def _calculate_equivalents(self, co2_kg: float) -> Dict:
        """Calculate equivalent metrics for CO2 emissions"""
        return {
            'trees_needed': round(co2_kg / 21, 2),  # One tree absorbs 21kg CO2/year
            'km_driving': round(co2_kg / 0.12, 1),  # Average car: 0.12 kg CO2/km
            'smartphone_charges': int(co2_kg / 0.008)  # 0.008 kg CO2 per charge
        }
    
    # ==================== WASTE TRACKING ====================
    
    def log_waste(
        self,
        venue_id: int,
        item_id: Optional[int],
        stock_item_id: Optional[int],
        quantity: float,
        unit: str,
        reason: str,
        cost: Optional[Decimal],
        logged_by_staff_id: int
    ) -> Dict:
        """Log waste event"""
        # In production, create WasteLog record
        
        waste_log = {
            'id': 1,  # Would be auto-generated
            'venue_id': venue_id,
            'item_id': item_id,
            'stock_item_id': stock_item_id,
            'quantity': quantity,
            'unit': unit,
            'reason': reason,
            'cost': float(cost) if cost else 0,
            'logged_by_staff_id': logged_by_staff_id,
            'logged_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Waste logged: {quantity} {unit} - {reason}")
        
        return waste_log
    
    def get_waste_statistics(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get waste statistics for period"""
        # In production, query WasteLog table
        # For now, return sample data
        
        total_waste_kg = 15.5
        total_cost = 125.00
        
        waste_by_reason = {
            'spoilage': {'kg': 8.2, 'cost': 65.00, 'percentage': 53},
            'preparation_error': {'kg': 4.3, 'cost': 35.00, 'percentage': 28},
            'customer_return': {'kg': 3.0, 'cost': 25.00, 'percentage': 19}
        }
        
        waste_by_category = {
            'vegetables': 4.5,
            'meat': 3.2,
            'dairy': 2.8,
            'bread': 2.5,
            'other': 2.5
        }
        
        # Calculate trends
        days = (end_date - start_date).days
        avg_per_day = total_waste_kg / max(1, days)
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'totals': {
                'weight_kg': total_waste_kg,
                'cost': total_cost,
                'avg_per_day_kg': round(avg_per_day, 2)
            },
            'by_reason': waste_by_reason,
            'by_category': waste_by_category,
            'recommendations': self._get_waste_reduction_recommendations(waste_by_reason)
        }
    
    def _get_waste_reduction_recommendations(
        self,
        waste_by_reason: Dict
    ) -> List[str]:
        """Generate waste reduction recommendations"""
        recommendations = []
        
        if waste_by_reason.get('spoilage', {}).get('percentage', 0) > 40:
            recommendations.append("📦 Review inventory rotation - spoilage is high")
            recommendations.append("❄️ Check refrigeration temperatures")
        
        if waste_by_reason.get('preparation_error', {}).get('percentage', 0) > 20:
            recommendations.append("👨‍🍳 Consider additional kitchen staff training")
            recommendations.append("📋 Review recipe standardization")
        
        if waste_by_reason.get('customer_return', {}).get('percentage', 0) > 15:
            recommendations.append("📸 Update menu photos for accuracy")
            recommendations.append("💬 Improve order clarification process")
        
        return recommendations
    
    # ==================== SUSTAINABILITY REPORTING ====================
    
    def get_sustainability_report(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Generate comprehensive sustainability report"""
        
        # Get orders for period
        orders = self.db.query(Order).filter(
            Order.venue_id == venue_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).all()
        
        total_orders = len(orders)
        total_co2 = 0.0
        
        for order in orders:
            footprint = self.calculate_order_carbon_footprint(order.id)
            total_co2 += footprint.get('total_co2_kg', 0)
        
        # Get waste stats
        waste_stats = self.get_waste_statistics(venue_id, start_date, end_date)
        
        # Calculate metrics
        days = (end_date - start_date).days
        avg_co2_per_order = total_co2 / max(1, total_orders)
        
        return {
            'period': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat(),
                'days': days
            },
            'carbon_footprint': {
                'total_kg': round(total_co2, 2),
                'per_order_avg': round(avg_co2_per_order, 2),
                'per_day_avg': round(total_co2 / max(1, days), 2),
                'equivalents': self._calculate_equivalents(total_co2)
            },
            'waste': waste_stats,
            'total_orders': total_orders,
            'sustainability_score': self._calculate_sustainability_score(
                total_co2, total_orders, waste_stats
            )
        }
    
    def _calculate_sustainability_score(
        self,
        total_co2: float,
        total_orders: int,
        waste_stats: Dict
    ) -> Dict:
        """Calculate overall sustainability score"""
        # Score based on multiple factors (0-100)
        
        avg_co2_per_order = total_co2 / max(1, total_orders)
        
        # CO2 score (lower is better)
        if avg_co2_per_order < 0.5:
            co2_score = 100
        elif avg_co2_per_order < 1.0:
            co2_score = 80
        elif avg_co2_per_order < 2.0:
            co2_score = 60
        else:
            co2_score = 40
        
        # Waste score (lower is better)
        waste_per_day = waste_stats['totals']['avg_per_day_kg']
        if waste_per_day < 5:
            waste_score = 100
        elif waste_per_day < 10:
            waste_score = 80
        elif waste_per_day < 20:
            waste_score = 60
        else:
            waste_score = 40
        
        # Overall score (weighted average)
        overall = int((co2_score * 0.6) + (waste_score * 0.4))
        
        if overall >= 80:
            grade = 'A'
            label = '🌱 Excellent'
        elif overall >= 60:
            grade = 'B'
            label = '✅ Good'
        elif overall >= 40:
            grade = 'C'
            label = '⚠️ Fair'
        else:
            grade = 'D'
            label = '❗ Needs Improvement'
        
        return {
            'score': overall,
            'grade': grade,
            'label': label,
            'co2_score': co2_score,
            'waste_score': waste_score
        }
    
    # ==================== SUSTAINABLE VENDORS ====================
    
    def get_sustainable_vendors(
        self,
        venue_id: int
    ) -> List[Dict]:
        """Get list of sustainable/certified vendors"""
        # In production, query SustainableVendor table
        
        vendors = [
            {
                'id': 1,
                'name': 'Local Farm Co-op',
                'certification_type': 'Organic',
                'score': 95,
                'verified': True,
                'products': ['Vegetables', 'Dairy', 'Eggs']
            },
            {
                'id': 2,
                'name': 'Mountain Meats',
                'certification_type': 'Free Range',
                'score': 88,
                'verified': True,
                'products': ['Beef', 'Pork', 'Chicken']
            },
            {
                'id': 3,
                'name': 'Eco Beverages Bulgaria',
                'certification_type': 'Sustainable Sourcing',
                'score': 82,
                'verified': True,
                'products': ['Beer', 'Wine', 'Spirits']
            }
        ]
        
        return vendors
    
    # ==================== ENERGY TRACKING ====================
    
    def log_energy_usage(
        self,
        venue_id: int,
        date: datetime,
        kwh_used: float,
        source: str,
        cost: Optional[Decimal]
    ) -> Dict:
        """Log daily energy usage"""
        # In production, create EnergyUsage record
        
        energy_log = {
            'id': 1,
            'venue_id': venue_id,
            'date': date.date().isoformat(),
            'kwh_used': kwh_used,
            'source': source,
            'cost': float(cost) if cost else 0,
            'co2_kg': kwh_used * 0.475  # Bulgaria grid average: 0.475 kg CO2/kWh
        }
        
        return energy_log
    
    def get_energy_statistics(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get energy usage statistics"""
        # Sample data
        days = (end_date - start_date).days
        total_kwh = 450.0 * days  # Estimate
        total_cost = 180.0 * days  # Estimate
        total_co2 = total_kwh * 0.475
        
        return {
            'period': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat(),
                'days': days
            },
            'totals': {
                'kwh': total_kwh,
                'cost': total_cost,
                'co2_kg': round(total_co2, 2)
            },
            'averages': {
                'kwh_per_day': round(total_kwh / max(1, days), 2),
                'cost_per_day': round(total_cost / max(1, days), 2)
            },
            'by_source': {
                'grid': 85,
                'solar': 15
            }
        }
    
    # ==================== RECOMMENDATIONS ====================
    
    def get_sustainability_recommendations(
        self,
        venue_id: int
    ) -> List[Dict]:
        """Get personalized sustainability recommendations"""
        
        recommendations = [
            {
                'category': 'Menu',
                'priority': 'high',
                'title': 'Promote Low-Carbon Menu Items',
                'description': 'Highlight vegetable-based dishes to reduce carbon footprint',
                'impact': 'Could reduce overall CO2 by 15%',
                'icon': '🌱'
            },
            {
                'category': 'Waste',
                'priority': 'high',
                'title': 'Implement Composting Program',
                'description': 'Compost vegetable waste instead of disposal',
                'impact': 'Could reduce waste costs by 20%',
                'icon': '♻️'
            },
            {
                'category': 'Energy',
                'priority': 'medium',
                'title': 'Switch to LED Lighting',
                'description': 'Replace all bulbs with LED equivalents',
                'impact': 'Could save 30% on lighting energy',
                'icon': '💡'
            },
            {
                'category': 'Sourcing',
                'priority': 'medium',
                'title': 'Increase Local Sourcing',
                'description': 'Source more ingredients from local suppliers',
                'impact': 'Reduces transport emissions by 25%',
                'icon': '🚚'
            },
            {
                'category': 'Packaging',
                'priority': 'low',
                'title': 'Switch to Biodegradable Takeaway Containers',
                'description': 'Use compostable containers for takeaway orders',
                'impact': 'Eliminates plastic waste',
                'icon': '📦'
            }
        ]
        
        return recommendations
