"""
AI & Automation Service - Section Y
AI model management, predictions, and automated actions
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid


class AIAutomationService:
    """Service for AI models, predictions, and automated actions."""
    
    # ==================== AI MODEL MANAGEMENT ====================
    
    @staticmethod
    def register_model(
        db: Session,
        venue_id: int,
        model_name: str,
        model_type: str,  # "demand_forecast", "price_optimization", "inventory", "staffing", "fraud_detection"
        model_version: str,
        configuration: Dict[str, Any],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Register a new AI model."""
        from app.models.advanced_features_v9 import AIModel
        
        # Check if model already exists
        existing = db.query(AIModel).filter(
            AIModel.venue_id == venue_id,
            AIModel.model_name == model_name,
            AIModel.model_version == model_version
        ).first()
        
        if existing:
            raise ValueError(f"Model {model_name} v{model_version} already exists")
        
        model = AIModel(
            venue_id=venue_id,
            model_name=model_name,
            model_type=model_type,
            model_version=model_version,
            model_parameters=configuration,
            is_active=False,
            is_production=False,
            accuracy_score=None,
            last_trained=None,
            last_prediction=None,
            predictions_count=0
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        
        return {
            "id": model.id,
            "model_name": model.model_name,
            "model_type": model.model_type,
            "model_version": model.model_version,
            "status": "active" if model.is_active else "inactive",
            "message": "Model registered successfully"
        }
    
    @staticmethod
    def activate_model(
        db: Session,
        model_id: int
    ) -> Dict[str, Any]:
        """Activate an AI model."""
        from app.models.advanced_features_v9 import AIModel
        
        model = db.query(AIModel).filter(AIModel.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        # Deactivate other models of same type at same venue
        db.query(AIModel).filter(
            AIModel.venue_id == model.venue_id,
            AIModel.model_type == model.model_type,
            AIModel.id != model_id
        ).update({"is_active": False, "is_production": False})

        model.is_active = True
        model.is_production = True
        db.commit()
        
        return {
            "id": model.id,
            "model_name": model.model_name,
            "status": "active",
            "message": f"Model activated. Other {model.model_type} models deactivated."
        }
    
    @staticmethod
    def get_active_models(
        db: Session,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Get all active AI models for a venue."""
        from app.models.advanced_features_v9 import AIModel
        
        models = db.query(AIModel).filter(
            AIModel.venue_id == venue_id,
            AIModel.is_active == True
        ).all()

        return [{
            "id": m.id,
            "model_name": m.model_name,
            "model_type": m.model_type,
            "model_version": m.model_version,
            "accuracy_score": float(m.accuracy_score) if m.accuracy_score else None,
            "prediction_count": m.predictions_count or 0,
            "last_used": m.last_prediction.isoformat() if m.last_prediction else None
        } for m in models]
    
    @staticmethod
    def update_model_accuracy(
        db: Session,
        model_id: int,
        accuracy_score: Decimal
    ) -> Dict[str, Any]:
        """Update model accuracy score after evaluation."""
        from app.models.advanced_features_v9 import AIModel
        
        model = db.query(AIModel).filter(AIModel.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        model.accuracy_score = accuracy_score
        model.last_trained = datetime.utcnow()
        db.commit()
        
        return {
            "id": model.id,
            "model_name": model.model_name,
            "accuracy_score": float(accuracy_score),
            "last_trained": model.last_trained.isoformat()
        }
    
    # ==================== PREDICTIONS ====================
    
    @staticmethod
    def log_prediction(
        db: Session,
        model_id: int,
        prediction_type: str,
        input_data: Dict[str, Any],
        predicted_value: Any,
        confidence_score: Decimal,
        target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Log an AI prediction."""
        from app.models.advanced_features_v9 import AIModel, AIPrediction
        
        model = db.query(AIModel).filter(AIModel.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        prediction = AIPrediction(
            model_id=model_id,
            venue_id=model.venue_id,
            prediction_type=prediction_type,
            input_data=input_data,
            predicted_value=predicted_value,
            confidence_score=confidence_score,
            target_date=target_date,
            actual_value=None,
            accuracy=None
        )
        db.add(prediction)
        
        # Update model usage stats
        model.last_prediction = datetime.utcnow()
        model.predictions_count = (model.predictions_count or 0) + 1

        db.commit()
        db.refresh(prediction)

        return {
            "id": prediction.id,
            "model_id": model_id,
            "prediction_type": prediction_type,
            "predicted_value": predicted_value,
            "confidence_score": float(confidence_score),
            "target_date": str(target_date) if target_date else None,
            "created_at": prediction.predicted_at.isoformat() if prediction.predicted_at else datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def record_actual_value(
        db: Session,
        prediction_id: int,
        actual_value: Any
    ) -> Dict[str, Any]:
        """Record actual value for a prediction to measure accuracy."""
        from app.models.advanced_features_v9 import AIPrediction
        
        prediction = db.query(AIPrediction).filter(
            AIPrediction.id == prediction_id
        ).first()
        
        if not prediction:
            raise ValueError(f"Prediction {prediction_id} not found")
        
        prediction.actual_value = actual_value
        
        # Calculate accuracy based on prediction type
        predicted = prediction.predicted_value
        if isinstance(predicted, (int, float)) and isinstance(actual_value, (int, float)):
            if actual_value != 0:
                error_pct = abs(predicted - actual_value) / actual_value * 100
                prediction.accuracy = Decimal(str(max(0, 100 - error_pct)))
            else:
                prediction.accuracy = Decimal("100") if predicted == 0 else Decimal("0")
        
        db.commit()
        db.refresh(prediction)
        
        return {
            "id": prediction.id,
            "predicted_value": prediction.predicted_value,
            "actual_value": actual_value,
            "accuracy": float(prediction.accuracy) if prediction.accuracy else None
        }
    
    @staticmethod
    def get_prediction_accuracy_report(
        db: Session,
        venue_id: int,
        model_id: Optional[int] = None,
        prediction_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get prediction accuracy report."""
        from app.models.advanced_features_v9 import AIPrediction
        
        query = db.query(AIPrediction).filter(
            AIPrediction.venue_id == venue_id,
            AIPrediction.actual_value.isnot(None)
        )
        
        if model_id:
            query = query.filter(AIPrediction.model_id == model_id)
        if prediction_type:
            query = query.filter(AIPrediction.prediction_type == prediction_type)
        if start_date:
            query = query.filter(AIPrediction.predicted_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(AIPrediction.predicted_at <= datetime.combine(end_date, datetime.max.time()))
        
        predictions = query.all()
        
        if not predictions:
            return {
                "venue_id": venue_id,
                "message": "No predictions with actual values found",
                "total_predictions": 0
            }
        
        accuracies = [float(p.accuracy) for p in predictions if p.accuracy is not None]
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
        
        by_type = {}
        for p in predictions:
            if p.prediction_type not in by_type:
                by_type[p.prediction_type] = {"count": 0, "total_accuracy": 0}
            by_type[p.prediction_type]["count"] += 1
            if p.accuracy:
                by_type[p.prediction_type]["total_accuracy"] += float(p.accuracy)
        
        for ptype in by_type:
            by_type[ptype]["avg_accuracy"] = (
                by_type[ptype]["total_accuracy"] / by_type[ptype]["count"]
                if by_type[ptype]["count"] > 0 else 0
            )
        
        return {
            "venue_id": venue_id,
            "total_predictions": len(predictions),
            "predictions_with_accuracy": len(accuracies),
            "average_accuracy": round(avg_accuracy, 2),
            "by_type": by_type,
            "accuracy_trend": "stable"  # Would calculate from historical data
        }
    
    # ==================== AUTOMATED ACTIONS ====================
    
    @staticmethod
    def create_automation_rule(
        db: Session,
        venue_id: int,
        rule_name: str,
        trigger_type: str,  # "threshold", "schedule", "event", "prediction"
        trigger_config: Dict[str, Any],
        action_type: str,  # "alert", "reorder", "price_change", "staff_notification", "menu_update"
        action_config: Dict[str, Any],
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Create an automation rule."""
        from app.models.advanced_features_v9 import AutomatedAction
        
        rule = AutomatedAction(
            venue_id=venue_id,
            rule_name=rule_name,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            action_type=action_type,
            action_config=action_config,
            enabled=enabled,
            last_triggered=None,
            trigger_count=0
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        return {
            "id": rule.id,
            "rule_name": rule_name,
            "trigger_type": trigger_type,
            "action_type": action_type,
            "enabled": enabled,
            "message": "Automation rule created"
        }
    
    @staticmethod
    def check_and_execute_automations(
        db: Session,
        venue_id: int,
        trigger_type: str,
        trigger_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check and execute matching automation rules."""
        from app.models.advanced_features_v9 import AutomatedAction
        
        rules = db.query(AutomatedAction).filter(
            AutomatedAction.venue_id == venue_id,
            AutomatedAction.enabled == True,
            AutomatedAction.trigger_type == trigger_type
        ).all()
        
        executed = []
        
        for rule in rules:
            if AIAutomationService._check_trigger(rule.trigger_config, trigger_data):
                # Execute action
                result = AIAutomationService._execute_action(
                    db, rule.action_type, rule.action_config, trigger_data
                )
                
                # Update rule stats
                rule.last_triggered = datetime.utcnow()
                rule.trigger_count += 1
                
                executed.append({
                    "rule_id": rule.id,
                    "rule_name": rule.rule_name,
                    "action_type": rule.action_type,
                    "result": result
                })
        
        db.commit()
        return executed
    
    @staticmethod
    def _check_trigger(trigger_config: Dict[str, Any], trigger_data: Dict[str, Any]) -> bool:
        """Check if trigger conditions are met."""
        condition = trigger_config.get("condition", "eq")
        field = trigger_config.get("field")
        threshold = trigger_config.get("threshold")
        
        if not field or field not in trigger_data:
            return False
        
        value = trigger_data[field]
        
        if condition == "eq":
            return value == threshold
        elif condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "contains":
            return threshold in value if isinstance(value, (str, list)) else False
        
        return False
    
    @staticmethod
    def _execute_action(
        db: Session,
        action_type: str,
        action_config: Dict[str, Any],
        trigger_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an automated action."""
        if action_type == "alert":
            return {
                "type": "alert",
                "message": action_config.get("message", "Automated alert triggered"),
                "severity": action_config.get("severity", "info"),
                "recipients": action_config.get("recipients", [])
            }
        elif action_type == "reorder":
            return {
                "type": "reorder",
                "item_id": action_config.get("item_id"),
                "quantity": action_config.get("quantity"),
                "status": "pending_approval"
            }
        elif action_type == "price_change":
            return {
                "type": "price_change",
                "item_id": action_config.get("item_id"),
                "new_price": action_config.get("new_price"),
                "status": "pending_approval"
            }
        elif action_type == "staff_notification":
            return {
                "type": "notification",
                "message": action_config.get("message"),
                "staff_roles": action_config.get("roles", []),
                "sent": True
            }
        else:
            return {"type": action_type, "status": "executed"}
    
    @staticmethod
    def get_automation_rules(
        db: Session,
        venue_id: int,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all automation rules for a venue."""
        from app.models.advanced_features_v9 import AutomatedAction

        query = db.query(AutomatedAction).filter(
            AutomatedAction.venue_id == venue_id
        )

        if enabled_only:
            # Filter for non-cancelled actions (active rules)
            query = query.filter(AutomatedAction.status != 'cancelled')

        rules = query.all()

        return [{
            "id": r.id,
            "rule_name": r.action_name,
            "trigger_type": r.trigger_type,
            "action_type": r.action_type,
            "enabled": r.status not in ('cancelled', 'failed'),
            "status": r.status,
            "executed_at": r.executed_at.isoformat() if r.executed_at else None
        } for r in rules]
    
    @staticmethod
    def toggle_automation_rule(
        db: Session,
        rule_id: int,
        enabled: bool
    ) -> Dict[str, Any]:
        """Enable or disable an automation rule."""
        from app.models.advanced_features_v9 import AutomatedAction
        
        rule = db.query(AutomatedAction).filter(
            AutomatedAction.id == rule_id
        ).first()
        
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")
        
        # Use status field to enable/disable
        rule.status = 'pending' if enabled else 'cancelled'
        db.commit()

        return {
            "id": rule.id,
            "rule_name": rule.action_name,
            "enabled": enabled
        }
    
    # ==================== AI-POWERED RECOMMENDATIONS ====================
    
    @staticmethod
    def get_menu_optimization_suggestions(
        db: Session,
        venue_id: int
    ) -> Dict[str, Any]:
        """Get AI-powered menu optimization suggestions based on real sales data."""
        from app.models import MenuItem, Order, OrderItem
        import statistics

        # Get sales data for the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Query menu items with their sales data
        items = db.query(MenuItem).filter(
            MenuItem.venue_id == venue_id,
            MenuItem.is_active == True
        ).all()

        suggestions = []
        item_stats = []

        for item in items:
            # Get sales for this item
            sales_data = db.query(
                func.sum(OrderItem.quantity).label('total_qty'),
                func.sum(OrderItem.price * OrderItem.quantity).label('total_revenue'),
                func.count(OrderItem.id).label('order_count')
            ).join(Order).filter(
                OrderItem.menu_item_id == item.id,
                Order.created_at >= thirty_days_ago,
                Order.status != 'cancelled'
            ).first()

            total_qty = sales_data.total_qty or 0
            total_revenue = float(sales_data.total_revenue or 0)
            order_count = sales_data.order_count or 0

            # Calculate metrics
            margin = 0
            if item.cost and item.price and item.price > 0:
                margin = ((item.price - item.cost) / item.price) * 100

            item_stats.append({
                'id': item.id,
                'name': item.name,
                'price': float(item.price) if item.price else 0,
                'cost': float(item.cost) if item.cost else 0,
                'sales': total_qty,
                'revenue': total_revenue,
                'orders': order_count,
                'margin': margin
            })

        if not item_stats:
            return {
                "venue_id": venue_id,
                "suggestions": [],
                "message": "No menu items found for analysis",
                "generated_at": datetime.utcnow().isoformat()
            }

        # Calculate percentiles for comparison
        sales_values = [s['sales'] for s in item_stats]
        margin_values = [s['margin'] for s in item_stats if s['margin'] > 0]

        avg_sales = statistics.mean(sales_values) if sales_values else 0
        avg_margin = statistics.mean(margin_values) if margin_values else 0

        for stat in item_stats:
            # High demand, high margin - suggest price increase
            if stat['sales'] > avg_sales * 1.5 and stat['margin'] > avg_margin:
                suggested_increase = min(0.15, (stat['sales'] / avg_sales - 1) * 0.1)
                suggestions.append({
                    "type": "price_increase",
                    "item_id": stat['id'],
                    "item_name": stat['name'],
                    "current_price": stat['price'],
                    "suggested_price": round(stat['price'] * (1 + suggested_increase), 2),
                    "reason": f"High demand ({int(stat['sales'])} units) with good margin ({stat['margin']:.1f}%)",
                    "confidence": min(0.95, 0.7 + (stat['sales'] / avg_sales - 1) * 0.1)
                })

            # Low sales, high margin - suggest promotion
            elif stat['sales'] < avg_sales * 0.5 and stat['margin'] > avg_margin * 1.2:
                suggestions.append({
                    "type": "promotion",
                    "item_id": stat['id'],
                    "item_name": stat['name'],
                    "current_price": stat['price'],
                    "reason": f"Low sales ({int(stat['sales'])} units) but high margin ({stat['margin']:.1f}%) - would benefit from visibility",
                    "confidence": 0.72
                })

            # Low sales, low margin - suggest removal
            elif stat['sales'] < avg_sales * 0.3 and stat['margin'] < avg_margin * 0.5 and stat['margin'] > 0:
                suggestions.append({
                    "type": "remove",
                    "item_id": stat['id'],
                    "item_name": stat['name'],
                    "current_price": stat['price'],
                    "reason": f"Low sales ({int(stat['sales'])} units) and low margin ({stat['margin']:.1f}%)",
                    "confidence": 0.68
                })

            # Very low margin - suggest price increase or cost review
            elif stat['margin'] > 0 and stat['margin'] < 20:
                suggestions.append({
                    "type": "review_cost",
                    "item_id": stat['id'],
                    "item_name": stat['name'],
                    "current_price": stat['price'],
                    "current_cost": stat['cost'],
                    "margin": round(stat['margin'], 1),
                    "reason": f"Very low margin ({stat['margin']:.1f}%) - review pricing or ingredient costs",
                    "confidence": 0.80
                })

        # Sort by confidence
        suggestions.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        return {
            "venue_id": venue_id,
            "analysis_period_days": 30,
            "items_analyzed": len(item_stats),
            "suggestions": suggestions[:20],  # Top 20 suggestions
            "summary": {
                "avg_sales_per_item": round(avg_sales, 1),
                "avg_margin": round(avg_margin, 1),
                "total_suggestions": len(suggestions)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_staffing_recommendations(
        db: Session,
        venue_id: int,
        target_date: date
    ) -> Dict[str, Any]:
        """Get AI-powered staffing recommendations based on historical data."""
        from app.models import Order
        import statistics

        day_of_week = target_date.strftime("%A")
        target_dow = target_date.weekday()

        # Get historical sales data for same day of week (last 8 weeks)
        historical_data = []
        for weeks_back in range(1, 9):
            check_date = target_date - timedelta(weeks=weeks_back)
            start_dt = datetime.combine(check_date, datetime.min.time())
            end_dt = datetime.combine(check_date, datetime.max.time())

            day_orders = db.query(Order).filter(
                Order.venue_id == venue_id,
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status != 'cancelled'
            ).all()

            if day_orders:
                total_revenue = sum(float(o.total or 0) for o in day_orders)
                order_count = len(day_orders)

                # Analyze orders by hour
                hourly_orders = {}
                for order in day_orders:
                    hour = order.created_at.hour
                    hourly_orders[hour] = hourly_orders.get(hour, 0) + 1

                historical_data.append({
                    'date': check_date,
                    'revenue': total_revenue,
                    'orders': order_count,
                    'hourly': hourly_orders
                })

        if not historical_data:
            # No historical data - use defaults with low confidence
            return {
                "venue_id": venue_id,
                "target_date": str(target_date),
                "day_of_week": day_of_week,
                "predicted_demand": "unknown",
                "recommendations": {
                    "front_of_house": 3,
                    "kitchen": 2,
                    "bar": 1,
                    "support": 1
                },
                "peak_hours": ["12:00-14:00", "19:00-21:00"],
                "confidence": 0.30,
                "note": "Limited historical data - using defaults",
                "generated_at": datetime.utcnow().isoformat()
            }

        # Calculate averages and predictions
        avg_orders = statistics.mean([d['orders'] for d in historical_data])
        avg_revenue = statistics.mean([d['revenue'] for d in historical_data])

        # Aggregate hourly patterns
        hourly_totals = {}
        for data in historical_data:
            for hour, count in data['hourly'].items():
                hourly_totals[hour] = hourly_totals.get(hour, 0) + count

        # Find peak hours
        peak_hours = []
        if hourly_totals:
            avg_hourly = sum(hourly_totals.values()) / len(hourly_totals)
            for hour in sorted(hourly_totals.keys()):
                if hourly_totals[hour] > avg_hourly * 1.3:
                    end_hour = hour + 1
                    peak_hours.append(f"{hour:02d}:00-{end_hour:02d}:00")

        # Determine demand level
        if day_of_week in ["Friday", "Saturday"]:
            demand_multiplier = 1.2
        elif day_of_week == "Sunday":
            demand_multiplier = 1.1
        else:
            demand_multiplier = 1.0

        predicted_orders = avg_orders * demand_multiplier

        if predicted_orders > avg_orders * 1.5:
            demand_level = "very_high"
        elif predicted_orders > avg_orders * 1.2:
            demand_level = "high"
        elif predicted_orders > avg_orders * 0.8:
            demand_level = "normal"
        else:
            demand_level = "low"

        # Calculate staffing needs based on predicted orders
        # Assuming ~15 orders per FOH staff per shift, ~20 orders per kitchen staff
        foh_needed = max(2, int(predicted_orders / 15) + 1)
        kitchen_needed = max(2, int(predicted_orders / 20) + 1)
        bar_needed = max(1, int(predicted_orders / 30))
        support_needed = max(1, int(predicted_orders / 40))

        # Adjust for peak periods
        if len(peak_hours) >= 3:
            foh_needed += 1
            kitchen_needed += 1

        # Calculate confidence based on data quality
        data_points = len(historical_data)
        confidence = min(0.95, 0.5 + (data_points * 0.05))

        # Check variance - high variance = lower confidence
        if len(historical_data) > 1:
            order_variance = statistics.stdev([d['orders'] for d in historical_data])
            if order_variance > avg_orders * 0.3:
                confidence *= 0.8

        return {
            "venue_id": venue_id,
            "target_date": str(target_date),
            "day_of_week": day_of_week,
            "predicted_demand": demand_level,
            "predicted_orders": int(predicted_orders),
            "predicted_revenue": round(avg_revenue * demand_multiplier, 2),
            "recommendations": {
                "front_of_house": foh_needed,
                "kitchen": kitchen_needed,
                "bar": bar_needed,
                "support": support_needed,
                "total": foh_needed + kitchen_needed + bar_needed + support_needed
            },
            "peak_hours": peak_hours or ["12:00-14:00", "19:00-21:00"],
            "analysis": {
                "historical_weeks_analyzed": len(historical_data),
                "avg_orders_same_day": round(avg_orders, 1),
                "avg_revenue_same_day": round(avg_revenue, 2)
            },
            "confidence": round(confidence, 2),
            "generated_at": datetime.utcnow().isoformat()
        }


# Class aliases for backwards compatibility with endpoint imports
AIModelService = AIAutomationService
PredictionService = AIAutomationService
AutomationRuleService = AIAutomationService
MenuOptimizationService = AIAutomationService
StaffingRecommendationService = AIAutomationService

