"""
Gamification Service
Implements comprehensive gamification system:
- Point-based reward system
- Achievement badges (Ski Season, Après-Ski Champion, etc.)
- Leaderboards (daily, weekly, seasonal)
- Special ski-themed challenges
- Social sharing of achievements
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.models import (
    Customer, Order, OrderItem, MenuItem, GameProfile,
    UserAchievement, Challenge, UserChallenge, PointTransaction,
    PointTransactionType, ChallengeStatus
)

logger = logging.getLogger(__name__)


# Achievement definitions
ACHIEVEMENTS = {
    # Ski-themed achievements
    'first_order': {
        'name': '🎿 First Run',
        'description': 'Place your first order',
        'points': 50,
        'icon': '🎿'
    },
    'apres_ski_regular': {
        'name': '🍺 Après-Ski Regular',
        'description': 'Order during après-ski hours (4-7 PM) 5 times',
        'points': 200,
        'icon': '🍺',
        'requirement': 5
    },
    'ski_season_champion': {
        'name': '❄️ Ski Season Champion',
        'description': 'Order 20 times during winter season',
        'points': 500,
        'icon': '❄️',
        'requirement': 20
    },
    'hot_chocolate_lover': {
        'name': '☕ Hot Chocolate Lover',
        'description': 'Order hot chocolate 10 times',
        'points': 300,
        'icon': '☕',
        'requirement': 10
    },
    'powder_day_special': {
        'name': '🌨️ Powder Day Special',
        'description': 'Order on a snowy day',
        'points': 100,
        'icon': '🌨️'
    },
    
    # Spending achievements
    'big_spender': {
        'name': '💰 Big Spender',
        'description': 'Spend €100 in a single order',
        'points': 250,
        'icon': '💰'
    },
    'loyal_customer': {
        'name': '👑 Loyal Customer',
        'description': 'Place 50 orders',
        'points': 1000,
        'icon': '👑',
        'requirement': 50
    },
    'early_bird': {
        'name': '🌅 Early Bird',
        'description': 'Order before 9 AM',
        'points': 100,
        'icon': '🌅'
    },
    'night_owl': {
        'name': '🦉 Night Owl',
        'description': 'Order after 10 PM',
        'points': 100,
        'icon': '🦉'
    },
    
    # Social achievements
    'social_butterfly': {
        'name': '🦋 Social Butterfly',
        'description': 'Share 5 achievements on social media',
        'points': 200,
        'icon': '🦋',
        'requirement': 5
    },
    'table_host': {
        'name': '🎉 Table Host',
        'description': 'Have 4+ people order at your table',
        'points': 150,
        'icon': '🎉'
    },
    
    # Variety achievements
    'menu_explorer': {
        'name': '🗺️ Menu Explorer',
        'description': 'Try 20 different menu items',
        'points': 400,
        'icon': '🗺️',
        'requirement': 20
    },
    'category_master': {
        'name': '🏆 Category Master',
        'description': 'Order from all menu categories',
        'points': 300,
        'icon': '🏆'
    },
    
    # Streak achievements
    'weekly_regular': {
        'name': '📅 Weekly Regular',
        'description': 'Order every day for a week',
        'points': 500,
        'icon': '📅',
        'requirement': 7
    },
    'monthly_vip': {
        'name': '⭐ Monthly VIP',
        'description': 'Order at least once every week for a month',
        'points': 800,
        'icon': '⭐',
        'requirement': 4
    }
}


# Challenge definitions
CHALLENGES = {
    'weekend_warrior': {
        'name': '🎿 Weekend Warrior',
        'description': 'Place 3 orders this weekend',
        'points': 300,
        'duration_days': 2,  # Weekend
        'requirement': 3
    },
    'apres_ski_week': {
        'name': '🍻 Après-Ski Week',
        'description': 'Order during après-ski hours 5 times this week',
        'points': 400,
        'duration_days': 7,
        'requirement': 5
    },
    'new_dish_challenge': {
        'name': '🆕 New Dish Challenge',
        'description': 'Try 5 items you\'ve never ordered before',
        'points': 250,
        'duration_days': 14,
        'requirement': 5
    },
    'double_points_day': {
        'name': '✨ Double Points Day',
        'description': 'Earn double points on all orders today',
        'points_multiplier': 2.0,
        'duration_days': 1
    }
}


class GamificationService:
    """Comprehensive gamification engine"""
    
    def __init__(self, db: Session):
        self.db = db
        self.points_per_euro = 10  # Earn 10 points per €1 spent
        
    # ==================== POINTS SYSTEM ====================
    
    def calculate_order_points(
        self,
        order_total: Decimal,
        customer_id: int,
        order_time: datetime
    ) -> int:
        """Calculate points earned from an order"""
        base_points = int(float(order_total) * self.points_per_euro)
        
        # Check for active challenges with multipliers
        multiplier = self._get_active_points_multiplier(customer_id, order_time)
        
        # Bonus points for après-ski orders
        if 16 <= order_time.hour < 19:
            base_points = int(base_points * 1.5)  # 50% bonus
        
        final_points = int(base_points * multiplier)
        
        return final_points
    
    def _get_active_points_multiplier(
        self,
        customer_id: int,
        current_time: datetime
    ) -> float:
        """Get active points multiplier from challenges"""
        # This would query active challenges from database
        # For now, return base multiplier
        return 1.0
    
    def award_points(
        self,
        customer_id: int,
        points: int,
        reason: str,
        order_id: Optional[int] = None,
        achievement_id: Optional[str] = None,
        challenge_id: Optional[int] = None
    ) -> Dict:
        """Award points to a customer"""
        try:
            # Get or create game profile
            profile = self.db.query(GameProfile).filter(
                GameProfile.customer_id == customer_id
            ).first()

            if not profile:
                profile = GameProfile(
                    customer_id=customer_id,
                    total_points=0,
                    current_level=1
                )
                self.db.add(profile)
                self.db.flush()

            # Update points
            old_balance = profile.total_points
            profile.total_points += points
            profile.points_earned_all_time += points

            # Determine transaction type
            if achievement_id:
                trans_type = PointTransactionType.EARNED_ACHIEVEMENT.value
            elif challenge_id:
                trans_type = PointTransactionType.EARNED_CHALLENGE.value
            elif order_id:
                trans_type = PointTransactionType.EARNED_ORDER.value
            else:
                trans_type = PointTransactionType.EARNED_BONUS.value

            # Create transaction record
            transaction = PointTransaction(
                game_profile_id=profile.id,
                transaction_type=trans_type,
                points=points,
                balance_after=profile.total_points,
                order_id=order_id,
                achievement_id=achievement_id,
                challenge_id=challenge_id,
                reason=reason
            )
            self.db.add(transaction)

            # Update level if needed
            new_level = self.get_customer_level(profile.total_points)
            if new_level['level'] > profile.current_level:
                profile.current_level = new_level['level']
                logger.info(f"Customer {customer_id} leveled up to {new_level['name']}!")

            self.db.commit()
            self.db.refresh(profile)

            logger.info(
                f"Awarded {points} points to customer {customer_id} "
                f"for: {reason}. New balance: {profile.total_points}"
            )

            return {
                'customer_id': customer_id,
                'points_awarded': points,
                'reason': reason,
                'order_id': order_id,
                'old_balance': old_balance,
                'new_balance': profile.total_points,
                'current_level': profile.current_level,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error awarding points: {e}")
            self.db.rollback()
            return {
                'error': str(e),
                'customer_id': customer_id,
                'points_awarded': 0
            }
    
    def get_customer_points(self, customer_id: int) -> int:
        """Get total points for a customer"""
        profile = self.db.query(GameProfile).filter(
            GameProfile.customer_id == customer_id
        ).first()

        if profile:
            return profile.total_points

        # If no profile exists, return 0
        return 0
    
    def get_customer_level(self, total_points: int) -> Dict:
        """Calculate customer level based on points"""
        levels = [
            {'level': 1, 'name': '🥉 Beginner', 'min_points': 0, 'max_points': 499},
            {'level': 2, 'name': '🥈 Regular', 'min_points': 500, 'max_points': 1499},
            {'level': 3, 'name': '🥇 Frequent', 'min_points': 1500, 'max_points': 3999},
            {'level': 4, 'name': '💎 VIP', 'min_points': 4000, 'max_points': 9999},
            {'level': 5, 'name': '👑 Legend', 'min_points': 10000, 'max_points': float('inf')}
        ]
        
        for level_info in levels:
            if level_info['min_points'] <= total_points <= level_info['max_points']:
                # Calculate progress to next level
                next_level_points = level_info['max_points'] + 1
                points_to_next = next_level_points - total_points
                progress_percent = (
                    (total_points - level_info['min_points']) / 
                    (level_info['max_points'] - level_info['min_points']) * 100
                ) if level_info['max_points'] != float('inf') else 100
                
                return {
                    **level_info,
                    'current_points': total_points,
                    'points_to_next_level': points_to_next if points_to_next > 0 else 0,
                    'progress_percent': min(100, progress_percent)
                }
        
        return levels[0]  # Default to first level
    
    # ==================== ACHIEVEMENTS ====================
    
    def check_and_award_achievements(
        self,
        customer_id: int,
        order_id: Optional[int] = None
    ) -> List[Dict]:
        """Check and award any newly unlocked achievements"""
        newly_unlocked = []

        # Get or create game profile
        profile = self.db.query(GameProfile).filter(
            GameProfile.customer_id == customer_id
        ).first()

        if not profile:
            profile = GameProfile(
                customer_id=customer_id,
                total_points=0,
                current_level=1
            )
            self.db.add(profile)
            self.db.flush()

        # Get customer's current achievements from database
        unlocked_achievement_ids = set(
            ua.achievement_id for ua in
            self.db.query(UserAchievement).filter(
                UserAchievement.game_profile_id == profile.id
            ).all()
        )

        # Check each achievement
        for achievement_id, achievement in ACHIEVEMENTS.items():
            if achievement_id not in unlocked_achievement_ids:
                if self._check_achievement_criteria(customer_id, achievement_id, achievement):
                    # Award achievement
                    unlocked = self._award_achievement(
                        profile.id, customer_id, achievement_id, achievement
                    )
                    if unlocked:
                        newly_unlocked.append(unlocked)
                        profile.total_achievements += 1

        if newly_unlocked:
            self.db.commit()

        return newly_unlocked
    
    def _check_achievement_criteria(
        self,
        customer_id: int,
        achievement_id: str,
        achievement: Dict
    ) -> bool:
        """Check if customer meets criteria for achievement"""
        
        # First order
        if achievement_id == 'first_order':
            order_count = self.db.query(func.count(Order.id)).filter(
                Order.customer_id == customer_id
            ).scalar()
            return order_count >= 1
        
        # Après-ski regular
        elif achievement_id == 'apres_ski_regular':
            apres_orders = self.db.query(func.count(Order.id)).filter(
                Order.customer_id == customer_id,
                func.extract('hour', Order.created_at).between(16, 18)
            ).scalar()
            return apres_orders >= achievement.get('requirement', 5)
        
        # Ski season champion
        elif achievement_id == 'ski_season_champion':
            winter_orders = self.db.query(func.count(Order.id)).filter(
                Order.customer_id == customer_id,
                or_(
                    func.extract('month', Order.created_at) == 12,
                    func.extract('month', Order.created_at).in_([1, 2, 3])
                )
            ).scalar()
            return winter_orders >= achievement.get('requirement', 20)
        
        # Hot chocolate lover
        elif achievement_id == 'hot_chocolate_lover':
            hot_choc_orders = self.db.query(func.count(OrderItem.id)).join(
                Order
            ).join(MenuItem).filter(
                Order.customer_id == customer_id,
                or_(
                    MenuItem.name.contains('hot chocolate'),
                    MenuItem.name.contains('Hot Chocolate')
                )
            ).scalar()
            return hot_choc_orders >= achievement.get('requirement', 10)
        
        # Big spender
        elif achievement_id == 'big_spender':
            has_big_order = self.db.query(Order).filter(
                Order.customer_id == customer_id,
                Order.total >= 100
            ).first() is not None
            return has_big_order
        
        # Loyal customer
        elif achievement_id == 'loyal_customer':
            total_orders = self.db.query(func.count(Order.id)).filter(
                Order.customer_id == customer_id
            ).scalar()
            return total_orders >= achievement.get('requirement', 50)
        
        # Early bird
        elif achievement_id == 'early_bird':
            early_orders = self.db.query(Order).filter(
                Order.customer_id == customer_id,
                func.extract('hour', Order.created_at) < 9
            ).first() is not None
            return early_orders
        
        # Night owl
        elif achievement_id == 'night_owl':
            late_orders = self.db.query(Order).filter(
                Order.customer_id == customer_id,
                func.extract('hour', Order.created_at) >= 22
            ).first() is not None
            return late_orders
        
        # Menu explorer
        elif achievement_id == 'menu_explorer':
            unique_items = self.db.query(
                func.count(func.distinct(OrderItem.menu_item_id))
            ).join(Order).filter(
                Order.customer_id == customer_id
            ).scalar()
            return unique_items >= achievement.get('requirement', 20)
        
        # Category master
        elif achievement_id == 'category_master':
            # Check if ordered from all categories
            total_categories = self.db.query(
                func.count(func.distinct(MenuItem.category_id))
            ).join(OrderItem).join(Order).filter(
                Order.customer_id == customer_id
            ).scalar()
            
            venue_categories = self.db.query(
                func.count(func.distinct(MenuItem.category_id))
            ).scalar()
            
            return total_categories >= venue_categories
        
        return False
    
    def _award_achievement(
        self,
        profile_id: int,
        customer_id: int,
        achievement_id: str,
        achievement: Dict
    ) -> Optional[Dict]:
        """Award achievement to customer"""
        try:
            points = achievement.get('points', 0)

            # Create UserAchievement record
            user_achievement = UserAchievement(
                game_profile_id=profile_id,
                achievement_id=achievement_id,
                points_awarded=points,
                unlocked_at=datetime.utcnow()
            )
            self.db.add(user_achievement)

            # Award points
            self.award_points(
                customer_id,
                points,
                f"Achievement unlocked: {achievement['name']}",
                achievement_id=achievement_id
            )

            logger.info(
                f"Achievement unlocked for customer {customer_id}: "
                f"{achievement_id} (+{points} points)"
            )

            return {
                'achievement_id': achievement_id,
                'name': achievement['name'],
                'description': achievement['description'],
                'points': points,
                'icon': achievement.get('icon', '🏆'),
                'unlocked_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error awarding achievement: {e}")
            self.db.rollback()
            return None
    
    def get_customer_achievements(
        self,
        customer_id: int
    ) -> Dict[str, List[Dict]]:
        """Get all achievements for a customer (unlocked and locked)"""
        # Get game profile
        profile = self.db.query(GameProfile).filter(
            GameProfile.customer_id == customer_id
        ).first()

        unlocked_ids = set()
        unlocked_data = {}

        if profile:
            # Query UserAchievement table
            user_achievements = self.db.query(UserAchievement).filter(
                UserAchievement.game_profile_id == profile.id
            ).all()

            for ua in user_achievements:
                unlocked_ids.add(ua.achievement_id)
                unlocked_data[ua.achievement_id] = {
                    'unlocked_at': ua.unlocked_at.isoformat() if ua.unlocked_at else None,
                    'points_awarded': ua.points_awarded,
                    'shared_on_social': ua.shared_on_social
                }

        unlocked = []
        locked = []

        for achievement_id, achievement in ACHIEVEMENTS.items():
            achievement_data = {
                'id': achievement_id,
                **achievement
            }

            if achievement_id in unlocked_ids:
                # Add unlock details
                achievement_data.update(unlocked_data[achievement_id])
                unlocked.append(achievement_data)
            else:
                locked.append(achievement_data)

        return {
            'unlocked': unlocked,
            'locked': locked,
            'total_unlocked': len(unlocked),
            'total_points_from_achievements': sum(a.get('points_awarded', 0) for a in unlocked)
        }
    
    # ==================== LEADERBOARDS ====================
    
    def get_leaderboard(
        self,
        venue_id: int,
        period: str = 'weekly',  # 'daily', 'weekly', 'monthly', 'seasonal', 'all_time'
        limit: int = 50
    ) -> List[Dict]:
        """Get leaderboard for specified period"""

        # Determine date range
        now = datetime.now()
        if period == 'daily':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'weekly':
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'monthly':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'seasonal':
            # Winter season: Dec-Mar
            if now.month in [12, 1, 2, 3]:
                start_date = datetime(now.year if now.month != 12 else now.year - 1, 12, 1)
            else:
                start_date = datetime(now.year, 1, 1)
        else:  # all_time
            start_date = datetime(2020, 1, 1)

        # Get top customers by actual points from GameProfile
        # Join with orders to get order counts and spending in the period
        leaderboard = self.db.query(
            Customer.id,
            Customer.name,
            GameProfile.total_points,
            GameProfile.current_level,
            func.count(Order.id).label('order_count'),
            func.coalesce(func.sum(Order.total), 0).label('total_spent')
        ).join(
            GameProfile, Customer.id == GameProfile.customer_id
        ).outerjoin(
            Order,
            and_(
                Order.customer_id == Customer.id,
                Order.created_at >= start_date,
                Order.venue_id == venue_id
            )
        ).filter(
            Customer.venue_id == venue_id,
            GameProfile.total_points > 0
        ).group_by(
            Customer.id, GameProfile.id
        ).order_by(
            desc(GameProfile.total_points)
        ).limit(limit).all()

        results = []
        for rank, entry in enumerate(leaderboard, 1):
            level = self.get_customer_level(entry.total_points)

            results.append({
                'rank': rank,
                'customer_id': entry.id,
                'customer_name': entry.name or 'Anonymous',
                'points': entry.total_points,
                'order_count': entry.order_count or 0,
                'total_spent': float(entry.total_spent or 0),
                'level': level['name'],
                'level_number': level['level']
            })

        return results
    
    def get_customer_rank(
        self,
        customer_id: int,
        venue_id: int,
        period: str = 'weekly'
    ) -> Dict:
        """Get customer's rank on leaderboard"""
        leaderboard = self.get_leaderboard(venue_id, period, limit=1000)
        
        for entry in leaderboard:
            if entry['customer_id'] == customer_id:
                return entry
        
        # Customer not on leaderboard
        return {
            'rank': None,
            'customer_id': customer_id,
            'points': self.get_customer_points(customer_id),
            'message': 'Not yet ranked - keep ordering!'
        }
    
    # ==================== CHALLENGES ====================
    
    def get_active_challenges(
        self,
        customer_id: int,
        venue_id: int
    ) -> List[Dict]:
        """Get active challenges for customer"""
        # Get game profile
        profile = self.db.query(GameProfile).filter(
            GameProfile.customer_id == customer_id
        ).first()

        if not profile:
            return []

        # Query active UserChallenge records
        user_challenges = self.db.query(UserChallenge).join(
            Challenge
        ).filter(
            UserChallenge.game_profile_id == profile.id,
            UserChallenge.status.in_([ChallengeStatus.ACTIVE.value]),
            or_(
                UserChallenge.expires_at.is_(None),
                UserChallenge.expires_at > datetime.utcnow()
            )
        ).all()

        active = []
        for uc in user_challenges:
            challenge = uc.challenge
            progress_percent = (uc.current_progress / uc.target_progress * 100) if uc.target_progress > 0 else 0

            active.append({
                'id': uc.id,
                'challenge_id': challenge.challenge_id,
                'name': challenge.name,
                'description': challenge.description,
                'points': challenge.points_reward,
                'progress': uc.current_progress,
                'requirement': uc.target_progress,
                'progress_percent': round(progress_percent, 1),
                'expires_at': uc.expires_at.isoformat() if uc.expires_at else None,
                'started_at': uc.started_at.isoformat() if uc.started_at else None,
                'completed': uc.status == ChallengeStatus.COMPLETED.value
            })

        return active
    
    def _get_challenge_progress(
        self,
        customer_id: int,
        challenge_id: str,
        challenge: Dict
    ) -> Dict:
        """Get customer's progress on a challenge"""
        # Simplified - in production would track from start of challenge
        now = datetime.now()
        
        if challenge_id == 'weekend_warrior':
            # Count orders this weekend
            weekend_start = now - timedelta(days=now.weekday() + 1)
            weekend_orders = self.db.query(func.count(Order.id)).filter(
                Order.customer_id == customer_id,
                Order.created_at >= weekend_start
            ).scalar() or 0
            
            return {
                'current': weekend_orders,
                'required': challenge.get('requirement', 3)
            }
        
        elif challenge_id == 'apres_ski_week':
            # Count après-ski orders this week
            week_start = now - timedelta(days=now.weekday())
            apres_orders = self.db.query(func.count(Order.id)).filter(
                Order.customer_id == customer_id,
                Order.created_at >= week_start,
                func.extract('hour', Order.created_at).between(16, 18)
            ).scalar() or 0
            
            return {
                'current': apres_orders,
                'required': challenge.get('requirement', 5)
            }
        
        # Default
        return {'current': 0, 'required': challenge.get('requirement', 1)}
    
    # ==================== CUSTOMER PROFILE ====================
    
    def get_customer_gamification_profile(
        self,
        customer_id: int,
        venue_id: int
    ) -> Dict:
        """Get complete gamification profile for customer"""
        
        total_points = self.get_customer_points(customer_id)
        level = self.get_customer_level(total_points)
        achievements = self.get_customer_achievements(customer_id)
        rank = self.get_customer_rank(customer_id, venue_id, 'weekly')
        active_challenges = self.get_active_challenges(customer_id, venue_id)
        
        return {
            'customer_id': customer_id,
            'points': {
                'total': total_points,
                'level': level
            },
            'achievements': achievements,
            'leaderboard': {
                'weekly_rank': rank.get('rank'),
                'weekly_points': rank.get('points', 0)
            },
            'active_challenges': active_challenges,
            'statistics': self._get_customer_statistics(customer_id)
        }
    
    def _get_customer_statistics(self, customer_id: int) -> Dict:
        """Get customer statistics"""
        total_orders = self.db.query(func.count(Order.id)).filter(
            Order.customer_id == customer_id
        ).scalar() or 0
        
        total_spent = self.db.query(func.sum(Order.total)).filter(
            Order.customer_id == customer_id
        ).scalar() or 0
        
        favorite_items = self.db.query(
            MenuItem.name,
            func.count(OrderItem.id).label('count')
        ).join(OrderItem).join(Order).filter(
            Order.customer_id == customer_id
        ).group_by(MenuItem.id).order_by(desc('count')).limit(3).all()
        
        return {
            'total_orders': total_orders,
            'total_spent': float(total_spent),
            'avg_order_value': float(total_spent) / total_orders if total_orders > 0 else 0,
            'favorite_items': [
                {'name': item.name, 'order_count': item.count}
                for item in favorite_items
            ]
        }
