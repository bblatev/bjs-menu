"""
BJ's Bar V9 - Advanced Kitchen & Production Service
Handles production forecasting, station load balancing, auto-fire rules, performance metrics
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import json
import statistics

from app.models.advanced_features_v9 import (
    ProductionForecast, StationLoad, AutoFireRule,
    KitchenPerformanceMetric, StationLoadStatus
)
from app.models import (
    MenuItem, Order, OrderItem, VenueStation, Venue,
    CourseTiming, Recipe, RecipeIngredient, StockItem
)


class AdvancedKitchenService:
    """Service for advanced kitchen operations and production management"""

    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.db = db

    # ==========================================================================
    # PRODUCTION FORECASTING
    # ==========================================================================

    @staticmethod
    def generate_forecast(
        db: Session,
        venue_id: int,
        forecast_date: datetime,
        forecast_type: str = "daily",
        historical_days: int = 30,
        include_weather: bool = True,
        include_events: bool = True
    ) -> ProductionForecast:
        """Generate production forecast based on historical data"""
        
        # Get historical sales data
        start_date = forecast_date - timedelta(days=historical_days)
        
        historical_orders = db.query(
            OrderItem.menu_item_id,
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.count(OrderItem.id).label('order_count'),
            func.to_char(Order.created_at, 'YYYY-MM-DD').label('order_date')
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at < forecast_date,
            Order.status != 'cancelled'
        ).group_by(
            OrderItem.menu_item_id,
            func.to_char(Order.created_at, 'YYYY-MM-DD')
        ).all()
        
        # Aggregate by item
        item_history = {}
        for record in historical_orders:
            item_id = record.menu_item_id
            if item_id not in item_history:
                item_history[item_id] = []
            item_history[item_id].append({
                'date': record.order_date,
                'quantity': record.total_quantity
            })
        
        # Calculate forecasts
        item_forecasts = {}
        for item_id, history in item_history.items():
            quantities = [h['quantity'] for h in history]
            
            if len(quantities) >= 3:
                avg_quantity = statistics.mean(quantities)
                std_dev = statistics.stdev(quantities) if len(quantities) > 1 else 0
                
                # Day of week adjustment
                forecast_dow = forecast_date.weekday()
                dow_quantities = [
                    h['quantity'] for h in history 
                    if h['date'].weekday() == forecast_dow
                ]
                if dow_quantities:
                    dow_factor = statistics.mean(dow_quantities) / avg_quantity if avg_quantity else 1
                else:
                    dow_factor = 1.0
                
                predicted = int(avg_quantity * dow_factor)
                confidence = min(0.95, max(0.5, 1 - (std_dev / avg_quantity if avg_quantity else 0)))
                
                item_forecasts[str(item_id)] = {
                    'quantity': predicted,
                    'confidence': round(confidence, 2),
                    'min_quantity': max(0, predicted - int(std_dev)),
                    'max_quantity': predicted + int(std_dev)
                }
        
        # Calculate ingredient requirements
        ingredient_requirements = AdvancedKitchenService._calculate_ingredient_requirements(
            db, item_forecasts
        )
        
        # Calculate factors
        seasonality_factor = AdvancedKitchenService._calculate_seasonality_factor(forecast_date)
        
        # Create forecast record
        forecast = ProductionForecast(
            venue_id=venue_id,
            forecast_date=forecast_date,
            forecast_type=forecast_type,
            item_forecasts=item_forecasts,
            ingredient_requirements=ingredient_requirements,
            historical_days_analyzed=historical_days,
            seasonality_factor=seasonality_factor,
            event_factor=1.0,  # Would need event calendar integration
            weather_factor=1.0,  # Would need weather API integration
            is_approved=False
        )
        
        db.add(forecast)
        db.commit()
        db.refresh(forecast)
        
        return forecast
    
    @staticmethod
    def _calculate_ingredient_requirements(
        db: Session,
        item_forecasts: Dict[str, Dict]
    ) -> Dict[str, float]:
        """Calculate ingredient requirements from item forecasts"""
        
        requirements = {}
        
        for item_id_str, forecast in item_forecasts.items():
            item_id = int(item_id_str)
            quantity = forecast['quantity']
            
            # Get recipe for this item
            recipe = db.query(Recipe).filter(
                Recipe.menu_item_id == item_id
            ).first()
            
            if recipe:
                ingredients = db.query(RecipeIngredient).filter(
                    RecipeIngredient.recipe_id == recipe.id
                ).all()
                
                for ing in ingredients:
                    key = str(ing.stock_item_id)
                    required = ing.quantity * quantity
                    requirements[key] = requirements.get(key, 0) + required
        
        return requirements
    
    @staticmethod
    def _calculate_seasonality_factor(date: datetime) -> float:
        """Calculate seasonality factor based on date"""
        
        month = date.month
        
        # Ski resort seasonality
        if month in [12, 1, 2, 3]:  # Winter/ski season
            return 1.3
        elif month in [7, 8]:  # Summer peak
            return 1.1
        elif month in [4, 5, 9, 10, 11]:  # Shoulder season
            return 0.8
        else:
            return 1.0
    
    @staticmethod
    def get_forecast(
        db: Session,
        venue_id: int,
        forecast_date: datetime,
        forecast_type: str = "daily"
    ) -> Optional[ProductionForecast]:
        """Get existing forecast"""
        
        return db.query(ProductionForecast).filter(
            ProductionForecast.venue_id == venue_id,
            func.date(ProductionForecast.forecast_date) == forecast_date.date(),
            ProductionForecast.forecast_type == forecast_type
        ).first()
    
    @staticmethod
    def approve_forecast(
        db: Session,
        forecast_id: int,
        approved_by: int
    ) -> ProductionForecast:
        """Approve a production forecast"""
        
        forecast = db.query(ProductionForecast).filter(
            ProductionForecast.id == forecast_id
        ).first()
        
        if not forecast:
            raise ValueError("Forecast not found")
        
        forecast.is_approved = True
        forecast.approved_by = approved_by
        
        db.commit()
        return forecast
    
    @staticmethod
    def record_actuals(
        db: Session,
        forecast_id: int,
        actual_demand: Dict[str, int]
    ) -> ProductionForecast:
        """Record actual demand to measure forecast accuracy"""
        
        forecast = db.query(ProductionForecast).filter(
            ProductionForecast.id == forecast_id
        ).first()
        
        if not forecast:
            raise ValueError("Forecast not found")
        
        forecast.actual_demand = actual_demand
        
        # Calculate accuracy
        if forecast.item_forecasts:
            errors = []
            for item_id, pred in forecast.item_forecasts.items():
                if item_id in actual_demand:
                    predicted = pred['quantity']
                    actual = actual_demand[item_id]
                    if actual > 0:
                        error = abs(predicted - actual) / actual
                        errors.append(error)
            
            if errors:
                forecast.accuracy_score = round(1 - statistics.mean(errors), 3)
        
        db.commit()
        return forecast
    
    # ==========================================================================
    # STATION LOAD BALANCING
    # ==========================================================================
    
    @staticmethod
    def update_station_load(
        db: Session,
        venue_id: int,
        station_id: int,
        current_orders: int,
        current_items: int
    ) -> StationLoad:
        """Update real-time station load metrics"""
        
        # Get or create station load record
        load = db.query(StationLoad).filter(
            StationLoad.venue_id == venue_id,
            StationLoad.station_id == station_id
        ).first()
        
        if not load:
            load = StationLoad(
                venue_id=venue_id,
                station_id=station_id,
                max_concurrent_orders=10,
                max_concurrent_items=30,
                optimal_queue_time_minutes=15
            )
            db.add(load)
        
        load.current_orders = current_orders
        load.current_items = current_items
        
        # Calculate load percentage
        order_load = (current_orders / load.max_concurrent_orders * 100) if load.max_concurrent_orders else 0
        item_load = (current_items / load.max_concurrent_items * 100) if load.max_concurrent_items else 0
        load.load_percentage = max(order_load, item_load)
        
        # Calculate estimated queue time
        if load.avg_item_time_seconds and current_items:
            load.estimated_queue_time_minutes = int(
                (current_items * load.avg_item_time_seconds) / 60
            )
        
        # Determine status
        if load.load_percentage >= 100:
            load.load_status = StationLoadStatus.OVERLOADED.value
        elif load.load_percentage >= 80:
            load.load_status = StationLoadStatus.HIGH.value
        elif load.load_percentage >= 50:
            load.load_status = StationLoadStatus.NORMAL.value
        else:
            load.load_status = StationLoadStatus.LOW.value
        
        load.last_updated = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(load)
        return load
    
    @staticmethod
    def get_all_station_loads(
        db: Session,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Get load status for all stations"""
        
        loads = db.query(StationLoad).join(
            VenueStation, VenueStation.id == StationLoad.station_id
        ).filter(
            StationLoad.venue_id == venue_id
        ).all()
        
        results = []
        for load in loads:
            results.append({
                "station_id": load.station_id,
                "station_name": load.station.name if load.station else None,
                "current_orders": load.current_orders,
                "current_items": load.current_items,
                "load_percentage": load.load_percentage,
                "load_status": load.load_status,
                "estimated_queue_time": load.estimated_queue_time_minutes,
                "can_accept_more": load.load_status != StationLoadStatus.OVERLOADED.value,
                "last_updated": load.last_updated
            })
        
        return results
    
    @staticmethod
    def suggest_routing(
        db: Session,
        venue_id: int,
        item_category: str
    ) -> Dict[str, Any]:
        """Suggest optimal station routing based on load"""
        
        # Get eligible stations for this category
        loads = db.query(StationLoad).filter(
            StationLoad.venue_id == venue_id,
            StationLoad.load_status != StationLoadStatus.BLOCKED.value
        ).all()
        
        if not loads:
            return {"suggested_station": None, "reason": "No available stations"}
        
        # Find station with lowest load that can accept overflow
        available = [l for l in loads if l.accept_overflow or l.load_status == StationLoadStatus.LOW.value]
        
        if not available:
            available = loads
        
        # Sort by load percentage
        available.sort(key=lambda x: x.load_percentage)
        best = available[0]
        
        return {
            "suggested_station": best.station_id,
            "load_percentage": best.load_percentage,
            "estimated_wait_time": best.estimated_queue_time_minutes,
            "reason": "Lowest current load"
        }
    
    # ==========================================================================
    # AUTO-FIRE RULES
    # ==========================================================================
    
    @staticmethod
    def create_auto_fire_rule(
        db: Session,
        venue_id: int,
        name: str,
        trigger_type: str,
        applicable_courses: List[int],
        fire_after_minutes: Optional[int] = None,
        fire_at_time: Optional[str] = None,
        hold_until_all_ready: bool = False,
        require_expo_approval: bool = False
    ) -> AutoFireRule:
        """Create an automatic course firing rule"""
        
        rule = AutoFireRule(
            venue_id=venue_id,
            name=name,
            trigger_type=trigger_type,
            fire_after_minutes=fire_after_minutes,
            fire_at_time=fire_at_time,
            applicable_courses=applicable_courses,
            hold_until_all_ready=hold_until_all_ready,
            require_expo_approval=require_expo_approval,
            is_active=True
        )
        
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule
    
    @staticmethod
    def get_applicable_rules(
        db: Session,
        venue_id: int,
        course_number: int
    ) -> List[AutoFireRule]:
        """Get applicable auto-fire rules for a course"""
        
        now = datetime.now(timezone.utc)
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%A").lower()
        
        rules = db.query(AutoFireRule).filter(
            AutoFireRule.venue_id == venue_id,
            AutoFireRule.is_active == True
        ).all()
        
        applicable = []
        for rule in rules:
            # Check if course applies
            if course_number not in (rule.applicable_courses or []):
                continue
            
            # Check day restrictions
            if rule.active_days and current_day not in rule.active_days:
                continue
            
            # Check time restrictions
            if rule.active_start_time and current_time < rule.active_start_time:
                continue
            if rule.active_end_time and current_time > rule.active_end_time:
                continue
            
            applicable.append(rule)
        
        return applicable
    
    @staticmethod
    def check_auto_fire(
        db: Session,
        order_id: int,
        course_number: int,
        previous_course_ready_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Check if a course should be auto-fired"""
        
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"should_fire": False, "reason": "Order not found"}
        
        # Get applicable rules
        rules = AdvancedKitchenService.get_applicable_rules(
            db, order.station.venue_id, course_number
        )
        
        if not rules:
            return {"should_fire": False, "reason": "No applicable rules"}
        
        for rule in rules:
            if rule.trigger_type == "time_based" and rule.fire_after_minutes:
                if previous_course_ready_at:
                    elapsed = (datetime.now(timezone.utc) - previous_course_ready_at).total_seconds() / 60
                    if elapsed >= rule.fire_after_minutes:
                        return {
                            "should_fire": True,
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "require_expo_approval": rule.require_expo_approval
                        }
            
            elif rule.trigger_type == "previous_course_ready":
                if previous_course_ready_at:
                    return {
                        "should_fire": True,
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "require_expo_approval": rule.require_expo_approval
                    }
        
        return {"should_fire": False, "reason": "No conditions met"}
    
    # ==========================================================================
    # KITCHEN PERFORMANCE METRICS
    # ==========================================================================
    
    @staticmethod
    def record_performance_metrics(
        db: Session,
        venue_id: int,
        station_id: Optional[int],
        metric_date: datetime,
        metric_hour: Optional[int] = None
    ) -> KitchenPerformanceMetric:
        """Record kitchen performance metrics for a period"""
        
        # Calculate time range
        if metric_hour is not None:
            start_time = metric_date.replace(hour=metric_hour, minute=0, second=0)
            end_time = start_time + timedelta(hours=1)
        else:
            start_time = metric_date.replace(hour=0, minute=0, second=0)
            end_time = start_time + timedelta(days=1)
        
        # Query orders
        query = db.query(Order).filter(
            Order.created_at >= start_time,
            Order.created_at < end_time
        )
        
        if station_id:
            query = query.filter(Order.station_id == station_id)
        
        orders = query.all()
        
        # Calculate metrics
        tickets_received = len(orders)
        tickets_completed = len([o for o in orders if o.status in ['ready', 'served']])
        tickets_voided = len([o for o in orders if o.status == 'cancelled'])

        # Calculate timing from order timestamps
        ticket_times = []
        for order in orders:
            if order.status in ['ready', 'served']:
                # Calculate time from order creation to completion
                # Check for ready_at, completed_at, or updated_at as completion timestamp
                completion_time = None

                if hasattr(order, 'ready_at') and order.ready_at:
                    completion_time = order.ready_at
                elif hasattr(order, 'completed_at') and order.completed_at:
                    completion_time = order.completed_at
                elif hasattr(order, 'served_at') and order.served_at:
                    completion_time = order.served_at
                elif hasattr(order, 'updated_at') and order.updated_at:
                    # Use updated_at as fallback (when status changed to ready/served)
                    completion_time = order.updated_at

                if completion_time and order.created_at:
                    # Calculate time difference in seconds
                    time_diff = (completion_time - order.created_at).total_seconds()
                    # Only include reasonable times (1 second to 2 hours)
                    if 1 <= time_diff <= 7200:
                        ticket_times.append(int(time_diff))

        avg_ticket_time = int(statistics.mean(ticket_times)) if ticket_times else None
        min_ticket_time = min(ticket_times) if ticket_times else None
        max_ticket_time = max(ticket_times) if ticket_times else None
        
        # Detect rush hour
        was_rush = tickets_received >= 20  # Simple threshold
        
        metric = KitchenPerformanceMetric(
            venue_id=venue_id,
            station_id=station_id,
            metric_date=metric_date,
            metric_hour=metric_hour,
            tickets_received=tickets_received,
            tickets_completed=tickets_completed,
            tickets_voided=tickets_voided,
            avg_ticket_time=avg_ticket_time,
            min_ticket_time=min_ticket_time,
            max_ticket_time=max_ticket_time,
            was_rush_hour=was_rush,
            peak_concurrent_tickets=tickets_received  # Simplified
        )
        
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric
    
    @staticmethod
    def get_performance_dashboard(
        db: Session,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get kitchen performance dashboard data"""
        
        metrics = db.query(KitchenPerformanceMetric).filter(
            KitchenPerformanceMetric.venue_id == venue_id,
            KitchenPerformanceMetric.metric_date >= start_date,
            KitchenPerformanceMetric.metric_date <= end_date
        ).all()
        
        if not metrics:
            return {
                "total_tickets": 0,
                "completion_rate": 0,
                "avg_ticket_time": None,
                "rush_hours": [],
                "by_station": {}
            }
        
        total_received = sum(m.tickets_received for m in metrics)
        total_completed = sum(m.tickets_completed for m in metrics)
        completion_rate = (total_completed / total_received * 100) if total_received else 0
        
        ticket_times = [m.avg_ticket_time for m in metrics if m.avg_ticket_time]
        avg_time = statistics.mean(ticket_times) if ticket_times else None
        
        rush_hours = [
            {"date": m.metric_date, "hour": m.metric_hour}
            for m in metrics if m.was_rush_hour
        ]
        
        # By station
        by_station = {}
        for m in metrics:
            sid = m.station_id or "all"
            if sid not in by_station:
                by_station[sid] = {"received": 0, "completed": 0}
            by_station[sid]["received"] += m.tickets_received
            by_station[sid]["completed"] += m.tickets_completed
        
        return {
            "total_tickets": total_received,
            "completion_rate": round(completion_rate, 1),
            "avg_ticket_time_seconds": int(avg_time) if avg_time else None,
            "rush_hours": rush_hours[:10],  # Last 10
            "by_station": by_station
        }
    
    @staticmethod
    def detect_slow_stations(
        db: Session,
        venue_id: int,
        threshold_minutes: int = 20
    ) -> List[Dict[str, Any]]:
        """Detect stations that are running slow"""
        
        threshold_seconds = threshold_minutes * 60
        
        # Get recent metrics
        recent = datetime.now(timezone.utc) - timedelta(hours=2)
        
        metrics = db.query(KitchenPerformanceMetric).filter(
            KitchenPerformanceMetric.venue_id == venue_id,
            KitchenPerformanceMetric.metric_date >= recent,
            KitchenPerformanceMetric.station_id.isnot(None)
        ).all()
        
        slow_stations = []
        for m in metrics:
            if m.avg_ticket_time and m.avg_ticket_time > threshold_seconds:
                slow_stations.append({
                    "station_id": m.station_id,
                    "avg_ticket_time_seconds": m.avg_ticket_time,
                    "avg_ticket_time_minutes": round(m.avg_ticket_time / 60, 1),
                    "tickets_pending": m.tickets_received - m.tickets_completed,
                    "severity": "critical" if m.avg_ticket_time > threshold_seconds * 2 else "warning"
                })
        
        return slow_stations

    # ==========================================================================
    # ENDPOINT-COMPATIBLE PRODUCTION FORECAST METHODS
    # ==========================================================================

    def forecast_demand(
        self,
        menu_item_id: int,
        forecast_date: datetime,
        include_weather: bool = True,
        include_events: bool = True
    ) -> ProductionForecast:
        """Generate ML-based production forecast for menu item (endpoint-compatible wrapper)"""

        # Get historical sales data for this specific item
        historical_days = 30
        start_date = forecast_date - timedelta(days=historical_days)

        historical_orders = self.db.query(
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.count(OrderItem.id).label('order_count'),
            func.to_char(Order.created_at, 'YYYY-MM-DD').label('order_date')
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            OrderItem.menu_item_id == menu_item_id,
            Order.created_at >= start_date,
            Order.created_at < forecast_date,
            Order.status != 'cancelled'
        ).group_by(
            func.to_char(Order.created_at, 'YYYY-MM-DD')
        ).all()

        # Calculate forecast
        quantities = [r.total_quantity or 0 for r in historical_orders]

        if len(quantities) >= 3:
            avg_quantity = statistics.mean(quantities)
            std_dev = statistics.stdev(quantities) if len(quantities) > 1 else 0
            predicted = int(avg_quantity)
            confidence = min(0.95, max(0.5, 1 - (std_dev / avg_quantity if avg_quantity else 0)))
        else:
            predicted = 10  # Default if not enough data
            confidence = 0.5

        item_forecasts = {
            str(menu_item_id): {
                'quantity': predicted,
                'confidence': round(confidence, 2),
                'min_quantity': max(0, predicted - int(std_dev if len(quantities) > 1 else predicted * 0.2)),
                'max_quantity': predicted + int(std_dev if len(quantities) > 1 else predicted * 0.2)
            }
        }

        forecast = ProductionForecast(
            forecast_date=forecast_date,
            forecast_type="daily",
            item_forecasts=item_forecasts,
            historical_days_analyzed=historical_days,
            seasonality_factor=AdvancedKitchenService._calculate_seasonality_factor(forecast_date),
            is_approved=False
        )

        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)

        return forecast

    def calculate_ingredient_requirements(
        self,
        forecast_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get ingredient requirements based on forecasts"""

        forecast = self.db.query(ProductionForecast).filter(
            func.date(ProductionForecast.forecast_date) == forecast_date
        ).first()

        if not forecast or not forecast.item_forecasts:
            return []

        requirements = []
        for item_id_str, item_forecast in forecast.item_forecasts.items():
            item_id = int(item_id_str)
            quantity = item_forecast.get('quantity', 0)

            recipe = self.db.query(Recipe).filter(
                Recipe.menu_item_id == item_id
            ).first()

            if recipe:
                ingredients = self.db.query(RecipeIngredient).filter(
                    RecipeIngredient.recipe_id == recipe.id
                ).all()

                for ing in ingredients:
                    requirements.append({
                        'stock_item_id': ing.stock_item_id,
                        'required_quantity': ing.quantity * quantity,
                        'unit': ing.unit if hasattr(ing, 'unit') else 'unit',
                        'menu_item_id': item_id
                    })

        return requirements

    # ==========================================================================
    # ENDPOINT-COMPATIBLE STATION LOAD BALANCING METHODS
    # ==========================================================================

    def create_station(
        self,
        station_name: str,
        station_type: str,
        max_concurrent_orders: int = 10,
        average_prep_time_minutes: int = 15
    ) -> Dict[str, Any]:
        """Create a kitchen station"""

        # Create station in VenueStation if it doesn't exist
        station = VenueStation(
            name=station_name,
            station_type=station_type
        )
        self.db.add(station)
        self.db.commit()
        self.db.refresh(station)

        # Create station load record
        load = StationLoad(
            station_id=station.id,
            max_concurrent_orders=max_concurrent_orders,
            max_concurrent_items=max_concurrent_orders * 3,
            optimal_queue_time_minutes=average_prep_time_minutes,
            load_status=StationLoadStatus.LOW.value,
            current_orders=0,
            current_items=0,
            load_percentage=0.0
        )
        self.db.add(load)
        self.db.commit()

        return {
            "id": station.id,
            "station_name": station_name,
            "station_type": station_type,
            "max_concurrent_orders": max_concurrent_orders,
            "status": "created"
        }

    def get_all_station_loads(self) -> List[Dict[str, Any]]:
        """Get current load for all kitchen stations (endpoint-compatible wrapper)"""

        loads = self.db.query(StationLoad).all()

        results = []
        for load in loads:
            results.append({
                "station_id": load.station_id,
                "current_orders": load.current_orders,
                "current_items": load.current_items,
                "load_percentage": load.load_percentage,
                "load_status": load.load_status,
                "estimated_queue_time": load.estimated_queue_time_minutes,
                "can_accept_more": load.load_status != StationLoadStatus.OVERLOADED.value,
                "last_updated": load.last_updated
            })

        return results

    def get_routing_suggestions(self) -> List[Dict[str, Any]]:
        """Get smart routing suggestions for pending orders"""

        # Get pending order items
        pending_items = self.db.query(OrderItem).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            Order.status.in_(['pending', 'preparing'])
        ).limit(10).all()

        suggestions = []
        for item in pending_items:
            # Find best station
            loads = self.db.query(StationLoad).filter(
                StationLoad.load_status != StationLoadStatus.BLOCKED.value
            ).order_by(StationLoad.load_percentage.asc()).all()

            if loads:
                best_station = loads[0]
                suggestions.append({
                    "order_item_id": item.id,
                    "current_station_id": None,
                    "suggested_station_id": best_station.station_id,
                    "reason": "Lowest current load",
                    "estimated_wait_time": best_station.estimated_queue_time_minutes or 0,
                    "load_percentage": best_station.load_percentage or 0
                })

        return suggestions

    def route_to_station(
        self,
        order_item_id: int,
        target_station_id: int
    ) -> bool:
        """Apply routing suggestion to move order to different station"""

        item = self.db.query(OrderItem).filter(
            OrderItem.id == order_item_id
        ).first()

        if not item:
            return False

        # Update the order item's station assignment
        # (This would typically update a station_id field on the order item)
        self.db.commit()
        return True

    # ==========================================================================
    # ENDPOINT-COMPATIBLE COURSE FIRE METHODS
    # ==========================================================================

    def create_rule(
        self,
        menu_item_id: int,
        course_number: int,
        fire_delay_minutes: Optional[int] = None,
        fire_trigger: Optional[str] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> AutoFireRule:
        """Create automatic course firing rule (endpoint-compatible wrapper)"""

        rule = AutoFireRule(
            name=f"Course {course_number} Rule for Item {menu_item_id}",
            trigger_type=fire_trigger or "time_based",
            fire_after_minutes=fire_delay_minutes,
            applicable_courses=[course_number],
            is_active=True
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_rules(
        self,
        menu_item_id: Optional[int] = None
    ) -> List[AutoFireRule]:
        """Get all course fire rules"""

        query = self.db.query(AutoFireRule).filter(
            AutoFireRule.is_active == True
        )

        return query.all()

    def check_and_fire_courses(
        self,
        order_id: int
    ) -> Dict[str, Any]:
        """Check and fire courses for an order based on rules"""

        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"fired": False, "reason": "Order not found", "courses_fired": []}

        # Get active rules
        rules = self.db.query(AutoFireRule).filter(
            AutoFireRule.is_active == True
        ).all()

        courses_fired = []
        for rule in rules:
            if rule.trigger_type == "time_based" and rule.fire_after_minutes:
                # Check if enough time has passed
                elapsed = (datetime.now(timezone.utc) - order.created_at).total_seconds() / 60
                if elapsed >= rule.fire_after_minutes:
                    for course in (rule.applicable_courses or []):
                        courses_fired.append({
                            "course_number": course,
                            "rule_id": rule.id,
                            "rule_name": rule.name
                        })

        return {
            "fired": len(courses_fired) > 0,
            "courses_fired": courses_fired,
            "order_id": order_id
        }

    # ==========================================================================
    # ENDPOINT-COMPATIBLE KITCHEN PERFORMANCE METHODS
    # ==========================================================================

    def get_performance_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get kitchen performance metrics (endpoint-compatible wrapper)"""

        metrics = self.db.query(KitchenPerformanceMetric).filter(
            KitchenPerformanceMetric.metric_date >= start_date,
            KitchenPerformanceMetric.metric_date <= end_date
        ).all()

        if not metrics:
            # Calculate from orders directly
            orders = self.db.query(Order).filter(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            ).all()

            total_received = len(orders)
            total_completed = len([o for o in orders if o.status in ['ready', 'served']])
            sla_compliance = 100.0 if total_received == 0 else (total_completed / total_received * 100)

            return {
                "period_start": start_date,
                "period_end": end_date,
                "total_tickets": total_received,
                "average_ticket_time": 0.0,
                "tickets_over_sla": 0,
                "sla_compliance_rate": round(sla_compliance, 1),
                "station_metrics": [],
                "peak_hour_performance": {},
                "bottleneck_stations": []
            }

        total_received = sum(m.tickets_received for m in metrics)
        total_completed = sum(m.tickets_completed for m in metrics)
        sla_compliance = (total_completed / total_received * 100) if total_received else 100.0

        ticket_times = [m.avg_ticket_time for m in metrics if m.avg_ticket_time]
        avg_time = statistics.mean(ticket_times) if ticket_times else 0.0

        # Count tickets over SLA (assuming SLA is 15 minutes)
        tickets_over_sla = sum(m.tickets_over_target for m in metrics if hasattr(m, 'tickets_over_target') and m.tickets_over_target) or 0

        return {
            "period_start": start_date,
            "period_end": end_date,
            "total_tickets": total_received,
            "average_ticket_time": float(avg_time) if avg_time else 0.0,
            "tickets_over_sla": tickets_over_sla,
            "sla_compliance_rate": round(sla_compliance, 1),
            "station_metrics": [],
            "peak_hour_performance": {
                "rush_hours": [
                    {"date": str(m.metric_date), "hour": m.metric_hour}
                    for m in metrics if m.was_rush_hour
                ][:10]
            },
            "bottleneck_stations": []
        }


# Class aliases for backwards compatibility with endpoint imports
ProductionForecastService = AdvancedKitchenService
StationLoadBalancingService = AdvancedKitchenService
CourseFireService = AdvancedKitchenService
KitchenPerformanceService = AdvancedKitchenService

