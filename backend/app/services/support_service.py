"""
Support Service - Production Ready
Full database integration with SLA tracking
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from app.models.v31_models import (
    SupportTicket, SupportTicketMessage, KnowledgeBaseArticle
)


class SupportService:
    """Production-ready Support Service with SLA Tracking"""
    
    # SLA definitions in hours
    SLA_CONFIG = {
        "critical": {"first_response": 0.25, "resolution": 4},    # 15 min / 4 hours
        "high": {"first_response": 1, "resolution": 8},           # 1 hour / 8 hours
        "medium": {"first_response": 4, "resolution": 24},        # 4 hours / 24 hours
        "low": {"first_response": 8, "resolution": 72}            # 8 hours / 72 hours
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== TICKET MANAGEMENT ==========
    
    def create_ticket(
        self,
        venue_id: int,
        user_id: int,
        subject: str,
        description: str,
        category: str,
        priority: str = "medium",
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a support ticket"""
        ticket_code = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate SLA deadlines
        sla = self.SLA_CONFIG.get(priority, self.SLA_CONFIG["medium"])
        now = datetime.now(timezone.utc)
        
        ticket = SupportTicket(
            ticket_code=ticket_code,
            venue_id=venue_id,
            user_id=user_id,
            subject=subject,
            description=description,
            category=category,
            priority=priority,
            status="open",
            first_response_due=now + timedelta(hours=sla["first_response"]),
            resolution_due=now + timedelta(hours=sla["resolution"])
        )
        
        self.db.add(ticket)
        self.db.flush()
        
        # Add initial message
        message = SupportTicketMessage(
            ticket_id=ticket.id,
            sender_type="customer",
            sender_id=user_id,
            content=description,
            attachments=attachments
        )
        self.db.add(message)
        self.db.commit()
        
        # Search for relevant KB articles
        suggested_articles = self._search_kb(f"{subject} {description}")[:3]
        
        return {
            "success": True,
            "ticket_id": ticket.id,
            "ticket_code": ticket_code,
            "priority": priority,
            "status": "open",
            "sla_first_response": ticket.first_response_due.isoformat(),
            "sla_resolution": ticket.resolution_due.isoformat(),
            "suggested_articles": suggested_articles,
            "message": f"Ticket {ticket_code} created. We'll respond within {sla['first_response']} hours."
        }
    
    def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """Get ticket details with messages"""
        ticket = self.db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id
        ).first()
        
        if not ticket:
            return {"success": False, "error": "Ticket not found"}
        
        messages = self.db.query(SupportTicketMessage).filter(
            SupportTicketMessage.ticket_id == ticket_id
        ).order_by(SupportTicketMessage.created_at).all()
        
        return {
            "success": True,
            "ticket": {
                "id": ticket.id,
                "ticket_code": ticket.ticket_code,
                "subject": ticket.subject,
                "description": ticket.description,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "first_response_due": ticket.first_response_due.isoformat() if ticket.first_response_due else None,
                "resolution_due": ticket.resolution_due.isoformat() if ticket.resolution_due else None,
                "first_response_at": ticket.first_response_at.isoformat() if ticket.first_response_at else None,
                "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                "satisfaction_rating": ticket.satisfaction_rating,
                "messages": [
                    {
                        "id": m.id,
                        "sender_type": m.sender_type,
                        "content": m.content,
                        "created_at": m.created_at.isoformat() if m.created_at else None
                    }
                    for m in messages
                ]
            }
        }
    
    def list_tickets(
        self,
        venue_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """List tickets with filters"""
        query = self.db.query(SupportTicket)
        
        if venue_id:
            query = query.filter(SupportTicket.venue_id == venue_id)
        
        if status:
            query = query.filter(SupportTicket.status == status)
        
        if priority:
            query = query.filter(SupportTicket.priority == priority)
        
        # Order by priority and creation date
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tickets = query.order_by(SupportTicket.created_at.desc()).limit(limit).all()
        
        # Sort by priority in Python (SQLAlchemy CASE is complex)
        tickets = sorted(tickets, key=lambda t: (priority_order.get(t.priority, 4), t.created_at or datetime.min))
        
        result = []
        for t in tickets:
            result.append({
                "id": t.id,
                "ticket_code": t.ticket_code,
                "subject": t.subject,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None
            })
        
        # Get status counts
        status_counts = {}
        for s in ["open", "in_progress", "waiting_customer", "resolved", "closed"]:
            count_query = self.db.query(func.count(SupportTicket.id)).filter(
                SupportTicket.status == s
            )
            if venue_id:
                count_query = count_query.filter(SupportTicket.venue_id == venue_id)
            status_counts[s] = count_query.scalar() or 0
        
        return {
            "success": True,
            "tickets": result,
            "total": len(result),
            "by_status": status_counts
        }
    
    def add_message(
        self,
        ticket_id: int,
        sender_type: str,
        sender_id: int,
        content: str,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Add message to ticket"""
        ticket = self.db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id
        ).first()
        
        if not ticket:
            return {"success": False, "error": "Ticket not found"}
        
        message = SupportTicketMessage(
            ticket_id=ticket_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            attachments=attachments
        )
        self.db.add(message)
        
        # Track first response
        if sender_type == "support" and not ticket.first_response_at:
            ticket.first_response_at = datetime.now(timezone.utc)
            ticket.status = "in_progress"
        
        # Update status based on sender
        if sender_type == "support":
            ticket.status = "waiting_customer"
        elif sender_type == "customer" and ticket.status == "waiting_customer":
            ticket.status = "in_progress"
        
        self.db.commit()
        
        return {
            "success": True,
            "message_id": message.id,
            "ticket_status": ticket.status
        }
    
    def update_ticket_status(
        self,
        ticket_id: int,
        status: str,
        resolution_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update ticket status"""
        ticket = self.db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id
        ).first()
        
        if not ticket:
            return {"success": False, "error": "Ticket not found"}
        
        old_status = ticket.status
        ticket.status = status
        
        if status == "resolved":
            ticket.resolved_at = datetime.now(timezone.utc)
            ticket.resolution_notes = resolution_notes
        
        self.db.commit()
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "old_status": old_status,
            "new_status": status
        }
    
    def escalate_ticket(
        self,
        ticket_id: int,
        reason: str,
        new_priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """Escalate a ticket"""
        ticket = self.db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id
        ).first()
        
        if not ticket:
            return {"success": False, "error": "Ticket not found"}
        
        old_priority = ticket.priority
        
        if new_priority:
            ticket.priority = new_priority
        else:
            # Auto-escalate to next level
            escalation_map = {"low": "medium", "medium": "high", "high": "critical"}
            ticket.priority = escalation_map.get(old_priority, "critical")
        
        # Recalculate SLA
        sla = self.SLA_CONFIG.get(ticket.priority, self.SLA_CONFIG["medium"])
        now = datetime.now(timezone.utc)
        ticket.resolution_due = now + timedelta(hours=sla["resolution"])
        
        self.db.commit()
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "old_priority": old_priority,
            "new_priority": ticket.priority,
            "message": f"Ticket escalated to {ticket.priority}"
        }
    
    def submit_satisfaction(
        self,
        ticket_id: int,
        rating: int,
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit satisfaction rating"""
        if rating < 1 or rating > 5:
            return {"success": False, "error": "Rating must be 1-5"}
        
        ticket = self.db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id
        ).first()
        
        if not ticket:
            return {"success": False, "error": "Ticket not found"}
        
        ticket.satisfaction_rating = rating
        ticket.satisfaction_feedback = feedback
        self.db.commit()
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "rating": rating,
            "message": "Thank you for your feedback!"
        }
    
    # ========== KNOWLEDGE BASE ==========
    
    def search_knowledge_base(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search knowledge base"""
        results = self._search_kb(query, category, limit)
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results)
        }
    
    def _search_kb(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Internal KB search"""
        query_filter = self.db.query(KnowledgeBaseArticle).filter(
            KnowledgeBaseArticle.status == "published"
        )
        
        if category:
            query_filter = query_filter.filter(KnowledgeBaseArticle.category == category)
        
        # Simple search - in production would use full-text search
        search_terms = query.lower().split()
        articles = query_filter.all()
        
        results = []
        for article in articles:
            score = 0
            title_lower = article.title.lower()
            content_lower = (article.content or "").lower()
            
            for term in search_terms:
                if term in title_lower:
                    score += 10
                if term in content_lower:
                    score += 5
                if article.tags:
                    for tag in article.tags:
                        if term in tag.lower():
                            score += 3
            
            if score > 0:
                results.append({
                    "id": article.id,
                    "article_code": article.article_code,
                    "title": article.title,
                    "category": article.category,
                    "excerpt": (article.content or "")[:200],
                    "relevance_score": score,
                    "views": article.views
                })
        
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]
    
    def get_article(self, article_id: int) -> Dict[str, Any]:
        """Get KB article and increment views"""
        article = self.db.query(KnowledgeBaseArticle).filter(
            KnowledgeBaseArticle.id == article_id
        ).first()
        
        if not article:
            return {"success": False, "error": "Article not found"}
        
        article.views = (article.views or 0) + 1
        self.db.commit()
        
        return {
            "success": True,
            "article": {
                "id": article.id,
                "article_code": article.article_code,
                "title": article.title,
                "content": article.content,
                "category": article.category,
                "tags": article.tags,
                "views": article.views
            }
        }
    
    def create_article(
        self,
        title: str,
        content: str,
        category: str,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create KB article"""
        article_code = f"KB-{uuid.uuid4().hex[:6].upper()}"
        
        article = KnowledgeBaseArticle(
            article_code=article_code,
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            status="published"
        )
        
        self.db.add(article)
        self.db.commit()
        
        return {
            "success": True,
            "article_id": article.id,
            "article_code": article_code,
            "message": "Article created"
        }
    
    # ========== METRICS ==========
    
    def get_support_metrics(
        self,
        venue_id: Optional[int] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get support performance metrics"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        
        query = self.db.query(SupportTicket).filter(
            SupportTicket.created_at >= cutoff
        )
        
        if venue_id:
            query = query.filter(SupportTicket.venue_id == venue_id)
        
        tickets = query.all()
        
        if not tickets:
            return {"success": True, "metrics": {"no_data": True}}
        
        resolved = [t for t in tickets if t.status in ["resolved", "closed"]]
        rated = [t for t in resolved if t.satisfaction_rating]
        
        avg_satisfaction = sum(t.satisfaction_rating for t in rated) / len(rated) if rated else None
        
        # Calculate SLA compliance
        first_response_met = 0
        resolution_met = 0
        
        for t in tickets:
            if t.first_response_at and t.first_response_due:
                if t.first_response_at <= t.first_response_due:
                    first_response_met += 1
            if t.resolved_at and t.resolution_due:
                if t.resolved_at <= t.resolution_due:
                    resolution_met += 1
        
        return {
            "success": True,
            "period_days": period_days,
            "metrics": {
                "total_tickets": len(tickets),
                "resolved": len(resolved),
                "open": len([t for t in tickets if t.status == "open"]),
                "in_progress": len([t for t in tickets if t.status == "in_progress"]),
                "resolution_rate": round(len(resolved) / len(tickets) * 100, 1) if tickets else 0,
                "avg_satisfaction": round(avg_satisfaction, 2) if avg_satisfaction else None,
                "sla_compliance": {
                    "first_response": round(first_response_met / len(tickets) * 100, 1) if tickets else 0,
                    "resolution": round(resolution_met / len(resolved) * 100, 1) if resolved else 0
                },
                "by_priority": {
                    p: len([t for t in tickets if t.priority == p])
                    for p in ["critical", "high", "medium", "low"]
                },
                "by_category": {
                    cat: len([t for t in tickets if t.category == cat])
                    for cat in set(t.category for t in tickets if t.category)
                }
            }
        }
    
    def get_support_hours(self) -> Dict[str, Any]:
        """Get support availability"""
        return {
            "success": True,
            "support_hours": {
                "phone": {
                    "available": True,
                    "hours": "24/7",
                    "languages": ["English", "Bulgarian"],
                    "number": "+359 888 SUPPORT"
                },
                "chat": {
                    "available": True,
                    "hours": "24/7",
                    "current_wait": "< 2 minutes"
                },
                "email": {
                    "available": True,
                    "address": "support@bjsbar.com",
                    "response_time": "< 4 hours"
                },
                "emergency": {
                    "phone": "+359 888 URGENT",
                    "for": "System down, payment issues"
                }
            }
        }
