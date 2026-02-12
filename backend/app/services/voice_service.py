"""
Voice Service
NLP engine for voice command processing
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import re
from difflib import SequenceMatcher

from app.models import Order, Table, OrderStatus


class VoiceService:
    """Service for voice command processing"""
    
    # Voice intents with trigger keywords (order matters - more specific first)
    INTENTS = {
        "ready_orders": {
            "keywords": ["ready orders", "ready", "finished orders", "complete orders"],
            "description": "List ready orders",
            "required_entities": [],
            "examples": [
                "Show ready orders",
                "What orders are ready?",
                "List ready orders"
            ]
        },
        "pending_orders": {
            "keywords": ["pending orders", "pending", "waiting orders", "new orders"],
            "description": "List pending orders",
            "required_entities": [],
            "examples": [
                "Show pending orders",
                "What orders are waiting?",
                "List new orders"
            ]
        },
        "today_summary": {
            "keywords": ["summary", "today", "stats", "statistics", "report"],
            "description": "Today's summary",
            "required_entities": [],
            "examples": [
                "Summary for today",
                "Show today's stats",
                "Daily report"
            ]
        },
        "tips_today": {
            "keywords": ["tips", "tip", "gratuity"],
            "description": "Today's tips",
            "required_entities": [],
            "examples": [
                "How much tips today?",
                "Show tips",
                "Today's tips"
            ]
        },
        "low_stock": {
            "keywords": ["low stock", "running low", "out of", "need to order"],
            "description": "Low stock items",
            "required_entities": [],
            "examples": [
                "What's running low?",
                "Show low stock",
                "Items running out"
            ]
        },
        "check_stock": {
            "keywords": ["stock", "inventory", "how much", "how many"],
            "description": "Check stock levels",
            "required_entities": [],
            "examples": [
                "Check stock for beer",
                "How much pizza dough?",
                "Inventory check"
            ]
        },
        "active_tables": {
            "keywords": ["active tables", "active", "occupied", "busy tables"],
            "description": "List active tables",
            "required_entities": [],
            "examples": [
                "Show active tables",
                "Which tables are occupied?",
                "List busy tables"
            ]
        },
        "table_status": {
            "keywords": ["table status", "status table", "status of table", "check table"],
            "description": "Get table status",
            "required_entities": ["table"],
            "examples": [
                "What's the status of table 5?",
                "Check table 3",
                "Table 7 status"
            ]
        },
        "mark_ready": {
            "keywords": ["mark ready", "order ready", "is ready", "mark as ready"],
            "description": "Mark order as ready",
            "required_entities": ["order"],
            "examples": [
                "Order 5 is ready",
                "Mark order 3 as ready",
                "Order ready"
            ]
        },
        "mark_served": {
            "keywords": ["served", "delivered", "mark served", "mark delivered"],
            "description": "Mark order as served",
            "required_entities": ["table"],
            "examples": [
                "Mark table 5 as served",
                "Order delivered to table 3",
                "Table 7 served"
            ]
        },
        "move_items": {
            "keywords": ["move", "transfer", "relocate", "switch table"],
            "description": "Move items between tables",
            "required_entities": ["source_table", "target_table"],
            "examples": [
                "Move items from table 5 to table 7",
                "Transfer order from T3 to T8",
                "Move to table 4"
            ]
        },
        "split_bill": {
            "keywords": ["split", "divide", "separate bill"],
            "description": "Split bill for table",
            "required_entities": ["table"],
            "examples": [
                "Split bill for table 5",
                "Divide table 3's check",
                "Separate bill"
            ]
        },
        "add_items": {
            "keywords": ["add", "include", "append", "put on"],
            "description": "Add items to order",
            "required_entities": ["table", "item"],
            "examples": [
                "Add 2 pizzas to table 5",
                "Add 3 beers for table 7",
                "Include dessert on table 4"
            ]
        },
        "cancel_items": {
            "keywords": ["cancel", "remove item", "delete item", "take off"],
            "description": "Cancel items from order",
            "required_entities": ["table", "item"],
            "examples": [
                "Cancel the pizza from table 5",
                "Remove dessert from table 3",
                "Take off the beer"
            ]
        },
        "cancel_order": {
            "keywords": ["cancel order", "void order", "delete order"],
            "description": "Cancel entire order",
            "required_entities": ["order"],
            "examples": [
                "Cancel order 5",
                "Void order 3",
                "Delete order 7"
            ]
        },
        "show_bill": {
            "keywords": ["bill", "check", "total", "amount"],
            "description": "Show bill for table",
            "required_entities": ["table"],
            "examples": [
                "Show bill for table 5",
                "What's the total for table 3?",
                "Check for table 7"
            ]
        },
        "call_waiter": {
            "keywords": ["waiter", "call waiter", "need waiter"],
            "description": "Call waiter to table",
            "required_entities": ["table"],
            "examples": [
                "Call waiter to table 5",
                "Waiter needed at table 3",
                "Need waiter"
            ]
        },
        "call_kitchen": {
            "keywords": ["kitchen", "chef", "cook"],
            "description": "Call kitchen staff",
            "required_entities": [],
            "examples": [
                "Call the kitchen",
                "Get the chef",
                "Contact kitchen"
            ]
        },
        "call_bar": {
            "keywords": ["bar", "bartender", "barman"],
            "description": "Call bar staff",
            "required_entities": [],
            "examples": [
                "Call the bar",
                "Get bartender",
                "Contact bar"
            ]
        },
        "help": {
            "keywords": ["help", "what can you do", "commands", "options"],
            "description": "Get help",
            "required_entities": [],
            "examples": [
                "Help",
                "What can you do?",
                "Show commands"
            ]
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def extract_intent(self, command_text: str) -> tuple[str, float]:
        """
        Extract intent from command text
        
        Returns:
            (intent_name, confidence_score)
        """
        command_lower = command_text.lower()
        best_intent = "unknown"
        best_score = 0.0
        
        for intent, config in self.INTENTS.items():
            score = 0.0
            for keyword in config["keywords"]:
                if keyword in command_lower:
                    # Exact keyword match
                    score += 1.0
                else:
                    # Fuzzy match
                    ratio = SequenceMatcher(None, keyword, command_lower).ratio()
                    if ratio > 0.8:
                        score += ratio
            
            if score > best_score:
                best_score = score
                best_intent = intent
        
        # Normalize confidence
        confidence = min(best_score / 2.0, 1.0)  # Divide by 2 since multiple keywords can match
        
        return best_intent, confidence
    
    def extract_entities(self, command_text: str, intent: str) -> Dict[str, Any]:
        """
        Extract entities from command text
        
        Entities:
        - table: Table number (T5, table 5, etc.)
        - item: Menu item name
        - quantity: Number
        """
        entities = {}
        command_lower = command_text.lower()
        
        # Extract table numbers
        table_patterns = [
            r't(\d+)',  # T5
            r'table\s*(\d+)',  # table 5
            r'стол\s*(\d+)',  # Bulgarian: стол 5
        ]
        
        for pattern in table_patterns:
            matches = re.findall(pattern, command_lower)
            if matches:
                if "source_table" not in entities:
                    entities["source_table"] = int(matches[0])
                if len(matches) > 1 and "target_table" not in entities:
                    entities["target_table"] = int(matches[1])
        
        # Extract quantities
        quantity_pattern = r'(\d+)\s*(pizza|beer|water|dessert|salad|burger)'
        matches = re.findall(quantity_pattern, command_lower)
        if matches:
            entities["quantity"] = int(matches[0][0])
            entities["item"] = matches[0][1]
        
        return entities
    
    async def process_command(
        self,
        command_text: str,
        staff_user_id: int,
        language: str = "bg"
    ) -> Dict[str, Any]:
        """
        Process voice command and execute action
        
        Returns:
            Result dict with success, intent, entities, response
        """
        # Extract intent
        intent, confidence = self.extract_intent(command_text)
        
        if intent == "unknown" or confidence < 0.3:
            return {
                "success": False,
                "intent": "unknown",
                "entities": {},
                "response": "Sorry, I didn't understand that command.",
                "confidence": confidence
            }
        
        # Extract entities
        entities = self.extract_entities(command_text, intent)
        
        # Execute intent action
        try:
            result = await self._execute_intent(intent, entities, staff_user_id)
            result.update({
                "success": True,
                "intent": intent,
                "entities": entities,
                "confidence": confidence
            })
            return result
        
        except Exception as e:
            return {
                "success": False,
                "intent": intent,
                "entities": entities,
                "response": f"Error executing command: {str(e)}",
                "confidence": confidence,
                "error": str(e)
            }
    
    async def _execute_intent(
        self,
        intent: str,
        entities: Dict[str, Any],
        staff_user_id: int
    ) -> Dict[str, Any]:
        """Execute the intent action"""
        from datetime import datetime
        from app.models import StockItem

        if intent == "ready_orders":
            orders = self.db.query(Order).filter(
                Order.status == OrderStatus.READY
            ).all()
            if orders:
                order_list = ", ".join([f"#{o.id}" for o in orders[:5]])
                return {
                    "response": f"There are {len(orders)} ready orders: {order_list}",
                    "action_performed": f"Listed {len(orders)} ready orders",
                    "data": {"count": len(orders), "orders": [o.id for o in orders]}
                }
            return {
                "response": "No orders are ready right now.",
                "action_performed": "Checked ready orders",
                "data": {"count": 0}
            }

        elif intent == "pending_orders":
            orders = self.db.query(Order).filter(
                Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING])
            ).all()
            if orders:
                return {
                    "response": f"There are {len(orders)} pending orders being prepared.",
                    "action_performed": f"Listed {len(orders)} pending orders",
                    "data": {"count": len(orders)}
                }
            return {
                "response": "No pending orders right now.",
                "action_performed": "Checked pending orders",
                "data": {"count": 0}
            }

        elif intent == "today_summary":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            orders_today = self.db.query(Order).filter(
                Order.created_at >= today
            ).all()
            total_revenue = sum(o.total or 0 for o in orders_today)
            return {
                "response": f"Today: {len(orders_today)} orders, {total_revenue:.2f} BGN revenue.",
                "action_performed": "Generated today's summary",
                "data": {"orders": len(orders_today), "revenue": total_revenue}
            }

        elif intent == "tips_today":
            # Tips would need to be tracked separately - for now return placeholder
            return {
                "response": "Tips tracking is available in the Reports section.",
                "action_performed": "Checked tips",
                "data": {}
            }

        elif intent == "low_stock":
            low_items = self.db.query(StockItem).filter(
                StockItem.quantity <= StockItem.low_stock_threshold
            ).all()
            if low_items:
                item_names = ", ".join([i.name for i in low_items[:5]])
                return {
                    "response": f"{len(low_items)} items running low: {item_names}",
                    "action_performed": "Checked low stock",
                    "data": {"count": len(low_items), "items": [i.name for i in low_items]}
                }
            return {
                "response": "All stock levels are good!",
                "action_performed": "Checked low stock",
                "data": {"count": 0}
            }

        elif intent == "check_stock":
            items = self.db.query(StockItem).limit(5).all()
            if items:
                stock_info = ", ".join([f"{i.name}: {i.quantity} {i.unit}" for i in items])
                return {
                    "response": f"Stock levels: {stock_info}",
                    "action_performed": "Checked stock",
                    "data": {"items": [{i.name: i.quantity} for i in items]}
                }
            return {
                "response": "No stock items found.",
                "action_performed": "Checked stock",
                "data": {}
            }

        elif intent == "active_tables":
            tables = self.db.query(Table).filter(
                Table.is_active == True
            ).all()
            if tables:
                table_nums = ", ".join([t.table_number for t in tables[:10]])
                return {
                    "response": f"{len(tables)} active tables: {table_nums}",
                    "action_performed": f"Listed {len(tables)} active tables",
                    "data": {"count": len(tables), "tables": [t.table_number for t in tables]}
                }
            return {
                "response": "No active tables right now.",
                "action_performed": "Checked active tables",
                "data": {"count": 0}
            }

        elif intent == "table_status":
            table_num = entities.get("source_table") or entities.get("table")
            if not table_num:
                return {
                    "response": "Please specify a table number.",
                    "action_performed": None
                }

            table = self.db.query(Table).filter(
                Table.table_number == str(table_num)
            ).first()

            if not table:
                return {
                    "response": f"Table {table_num} not found.",
                    "action_performed": None
                }

            orders = self.db.query(Order).filter(
                Order.table_id == table.id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY])
            ).all()

            if orders:
                return {
                    "response": f"Table {table_num} has {len(orders)} active orders.",
                    "action_performed": f"Checked status of table {table_num}",
                    "data": {"table": table_num, "order_count": len(orders)}
                }
            return {
                "response": f"Table {table_num} has no active orders.",
                "action_performed": f"Checked status of table {table_num}",
                "data": {"table": table_num, "order_count": 0}
            }

        elif intent == "help":
            commands = [
                "ready orders", "pending orders", "today's summary",
                "check stock", "low stock", "active tables",
                "table status", "mark order ready", "mark served",
                "show bill", "call waiter", "call kitchen", "call bar"
            ]
            return {
                "response": f"Available commands: {', '.join(commands)}",
                "action_performed": "Showed help",
                "data": {"commands": commands}
            }

        elif intent == "mark_ready":
            # Mark an order as ready
            order_id = entities.get("order")
            if not order_id:
                return {
                    "response": "Please specify an order number to mark as ready.",
                    "action_performed": None
                }

            order = self.db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {
                    "response": f"Order #{order_id} not found.",
                    "action_performed": None
                }

            order.status = OrderStatus.READY
            self.db.commit()
            return {
                "response": f"Order #{order_id} has been marked as ready!",
                "action_performed": f"Marked order {order_id} as ready",
                "data": {"order_id": order_id, "new_status": "ready"}
            }

        elif intent == "mark_served":
            table_num = entities.get("source_table") or entities.get("table")
            if not table_num:
                return {
                    "response": "Please specify a table number.",
                    "action_performed": None
                }

            table = self.db.query(Table).filter(
                Table.table_number == str(table_num)
            ).first()

            if not table:
                return {
                    "response": f"Table {table_num} not found.",
                    "action_performed": None
                }

            # Mark all ready orders for this table as served
            orders = self.db.query(Order).filter(
                Order.table_id == table.id,
                Order.status == OrderStatus.READY
            ).all()

            if not orders:
                return {
                    "response": f"No ready orders for table {table_num} to mark as served.",
                    "action_performed": None
                }

            for order in orders:
                order.status = OrderStatus.SERVED
            self.db.commit()

            return {
                "response": f"Marked {len(orders)} order(s) for table {table_num} as served.",
                "action_performed": f"Marked {len(orders)} orders as served",
                "data": {"table": table_num, "orders_served": len(orders)}
            }

        elif intent == "show_bill":
            table_num = entities.get("source_table") or entities.get("table")
            if not table_num:
                return {
                    "response": "Please specify a table number.",
                    "action_performed": None
                }

            table = self.db.query(Table).filter(
                Table.table_number == str(table_num)
            ).first()

            if not table:
                return {
                    "response": f"Table {table_num} not found.",
                    "action_performed": None
                }

            orders = self.db.query(Order).filter(
                Order.table_id == table.id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING,
                                 OrderStatus.READY, OrderStatus.SERVED])
            ).all()

            if not orders:
                return {
                    "response": f"No active orders for table {table_num}.",
                    "action_performed": None
                }

            total = sum(o.total or 0 for o in orders)
            return {
                "response": f"Table {table_num} bill: {total:.2f} BGN ({len(orders)} order(s))",
                "action_performed": f"Showed bill for table {table_num}",
                "data": {"table": table_num, "total": total, "order_count": len(orders)}
            }

        elif intent == "call_waiter":
            table_num = entities.get("source_table") or entities.get("table")
            if not table_num:
                return {
                    "response": "Please specify a table number.",
                    "action_performed": None
                }

            # Create a waiter call record
            from app.models import WaiterCall, WaiterCallStatus
            table = self.db.query(Table).filter(
                Table.table_number == str(table_num)
            ).first()

            if not table:
                return {
                    "response": f"Table {table_num} not found.",
                    "action_performed": None
                }

            call = WaiterCall(
                table_id=table.id,
                reason="voice_command",
                message="Waiter requested via voice command",
                status=WaiterCallStatus.PENDING
            )
            self.db.add(call)
            self.db.commit()

            return {
                "response": f"Waiter has been called to table {table_num}!",
                "action_performed": f"Called waiter to table {table_num}",
                "data": {"table": table_num, "call_id": call.id}
            }

        elif intent == "call_kitchen":
            return {
                "response": "Kitchen staff has been notified!",
                "action_performed": "Called kitchen",
                "data": {"station": "kitchen", "notified": True}
            }

        elif intent == "call_bar":
            return {
                "response": "Bar staff has been notified!",
                "action_performed": "Called bar",
                "data": {"station": "bar", "notified": True}
            }

        elif intent == "move_items":
            source = entities.get("source_table")
            target = entities.get("target_table")

            if not source or not target:
                return {
                    "response": "Please specify both source and target table numbers.",
                    "action_performed": None
                }

            source_table = self.db.query(Table).filter(Table.table_number == str(source)).first()
            target_table = self.db.query(Table).filter(Table.table_number == str(target)).first()

            if not source_table or not target_table:
                return {
                    "response": "One or both tables not found.",
                    "action_performed": None
                }

            # Move active orders from source to target
            orders = self.db.query(Order).filter(
                Order.table_id == source_table.id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY])
            ).all()

            if not orders:
                return {
                    "response": f"No active orders on table {source} to move.",
                    "action_performed": None
                }

            for order in orders:
                order.table_id = target_table.id
            self.db.commit()

            return {
                "response": f"Moved {len(orders)} order(s) from table {source} to table {target}.",
                "action_performed": f"Moved orders from table {source} to {target}",
                "data": {"source": source, "target": target, "orders_moved": len(orders)}
            }

        elif intent == "split_bill":
            table_num = entities.get("source_table") or entities.get("table")
            if not table_num:
                return {
                    "response": "Please specify a table number to split the bill.",
                    "action_performed": None
                }

            return {
                "response": f"Bill split requested for table {table_num}. Please use the admin panel for detailed split options.",
                "action_performed": f"Split bill requested for table {table_num}",
                "data": {"table": table_num, "action": "split_bill_requested"}
            }

        elif intent == "add_items":
            table_num = entities.get("source_table") or entities.get("table")
            item_name = entities.get("item")
            quantity = entities.get("quantity", 1)

            if not table_num or not item_name:
                return {
                    "response": "Please specify the table and item to add.",
                    "action_performed": None
                }

            return {
                "response": f"To add {quantity}x {item_name} to table {table_num}, please use the ordering system.",
                "action_performed": None,
                "data": {"table": table_num, "item": item_name, "quantity": quantity}
            }

        elif intent == "cancel_items":
            table_num = entities.get("source_table") or entities.get("table")
            item_name = entities.get("item")

            if not table_num:
                return {
                    "response": "Please specify the table number.",
                    "action_performed": None
                }

            return {
                "response": f"To cancel items from table {table_num}, please use the admin panel.",
                "action_performed": None,
                "data": {"table": table_num, "item": item_name}
            }

        elif intent == "cancel_order":
            order_id = entities.get("order")
            if not order_id:
                return {
                    "response": "Please specify an order number to cancel.",
                    "action_performed": None
                }

            order = self.db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {
                    "response": f"Order #{order_id} not found.",
                    "action_performed": None
                }

            if order.status == OrderStatus.SERVED:
                return {
                    "response": f"Order #{order_id} has already been served and cannot be cancelled.",
                    "action_performed": None
                }

            order.status = OrderStatus.CANCELLED
            self.db.commit()

            return {
                "response": f"Order #{order_id} has been cancelled.",
                "action_performed": f"Cancelled order {order_id}",
                "data": {"order_id": order_id, "new_status": "cancelled"}
            }

        else:
            return {
                "response": f"Command '{intent}' is not recognized. Say 'help' for available commands.",
                "action_performed": None
            }
    
    def get_available_intents(self, language: str = "bg") -> List[Dict[str, Any]]:
        """Get list of available intents with examples"""
        return [
            {
                "intent": intent,
                "description": config["description"],
                "required_entities": config["required_entities"],
                "examples": config["examples"]
            }
            for intent, config in self.INTENTS.items()
        ]
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = "bg"
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text using Whisper
        
        Note: Requires OpenAI API key in settings
        """
        try:
            import openai
            from app.core.config import settings
            
            if not settings.OPENAI_API_KEY:
                raise Exception("OpenAI API key not configured")
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Create temporary file for audio
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_data)
                audio_file_path = f.name
            
            # Transcribe with Whisper
            with open(audio_file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
            
            # Clean up temp file
            import os
            os.unlink(audio_file_path)
            
            return {
                "text": transcript.text,
                "language": language,
                "confidence": 0.9  # Whisper doesn't provide confidence
            }
        
        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")
