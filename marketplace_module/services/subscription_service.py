"""
Community subscription service for managing paid module access
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from ..models import db

logger = logging.getLogger(__name__)

class SubscriptionService:
    """Service for managing community subscriptions and payment verification"""
    
    def __init__(self):
        self.grace_period_days = 7  # 7 days grace period after expiration
    
    def get_subscription_status(self, entity_id: str) -> Dict[str, Any]:
        """
        Get current subscription status for an entity
        
        Args:
            entity_id: The entity ID to check
            
        Returns:
            Dict with subscription status information
        """
        try:
            subscription = db(
                db.community_subscriptions.entity_id == entity_id
            ).select().first()
            
            if not subscription:
                # No subscription found, default to free
                return {
                    "has_subscription": False,
                    "subscription_type": "free",
                    "subscription_status": "none",
                    "can_install_paid": False,
                    "expires_at": None,
                    "grace_period_end": None,
                    "days_remaining": 0
                }
            
            now = datetime.utcnow()
            subscription_end = subscription.subscription_end
            grace_period_end = subscription.grace_period_end
            
            # Calculate days remaining
            days_remaining = 0
            if subscription_end and subscription_end > now:
                days_remaining = (subscription_end - now).days
            elif grace_period_end and grace_period_end > now:
                days_remaining = (grace_period_end - now).days
            
            # Determine if can install paid modules
            can_install_paid = False
            if subscription.subscription_status == "active":
                if subscription_end > now:
                    can_install_paid = True
                elif grace_period_end and grace_period_end > now:
                    can_install_paid = True
            
            return {
                "has_subscription": True,
                "subscription_type": subscription.subscription_type,
                "subscription_status": subscription.subscription_status,
                "can_install_paid": can_install_paid,
                "expires_at": subscription_end.isoformat() if subscription_end else None,
                "grace_period_end": grace_period_end.isoformat() if grace_period_end else None,
                "days_remaining": days_remaining,
                "auto_renew": subscription.auto_renew,
                "payment_method": subscription.payment_method,
                "amount_paid": subscription.amount_paid,
                "currency": subscription.currency
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription status for {entity_id}: {str(e)}")
            return {
                "has_subscription": False,
                "subscription_type": "free",
                "subscription_status": "error",
                "can_install_paid": False,
                "expires_at": None,
                "grace_period_end": None,
                "days_remaining": 0
            }
    
    def can_install_paid_module(self, entity_id: str, module_price: float) -> Dict[str, Any]:
        """
        Check if entity can install a paid module
        
        Args:
            entity_id: Entity ID to check
            module_price: Price of the module
            
        Returns:
            Dict with permission status and reason
        """
        try:
            # Free modules can always be installed
            if module_price <= 0:
                return {
                    "can_install": True,
                    "reason": "free_module"
                }
            
            # Check subscription status
            subscription_status = self.get_subscription_status(entity_id)
            
            if not subscription_status["can_install_paid"]:
                return {
                    "can_install": False,
                    "reason": "subscription_required",
                    "subscription_status": subscription_status["subscription_status"],
                    "message": "A premium subscription is required to install paid modules",
                    "expires_at": subscription_status["expires_at"],
                    "grace_period_end": subscription_status["grace_period_end"]
                }
            
            # Check if subscription is about to expire (within 3 days)
            if subscription_status["days_remaining"] <= 3:
                return {
                    "can_install": True,
                    "reason": "subscription_expiring",
                    "warning": f"Your subscription expires in {subscription_status['days_remaining']} days",
                    "expires_at": subscription_status["expires_at"]
                }
            
            return {
                "can_install": True,
                "reason": "subscription_active"
            }
            
        except Exception as e:
            logger.error(f"Error checking paid module permission for {entity_id}: {str(e)}")
            return {
                "can_install": False,
                "reason": "error",
                "message": "Error checking subscription status"
            }
    
    def create_subscription(self, entity_id: str, subscription_type: str, 
                          duration_days: int, payment_method: str = None,
                          payment_id: str = None, amount_paid: float = 0.0,
                          currency: str = "USD") -> Dict[str, Any]:
        """
        Create a new subscription for an entity
        
        Args:
            entity_id: Entity to create subscription for
            subscription_type: Type of subscription (free, premium, enterprise)
            duration_days: Duration in days
            payment_method: Payment method used
            payment_id: External payment ID
            amount_paid: Amount paid
            currency: Currency code
            
        Returns:
            Dict with success status and subscription info
        """
        try:
            now = datetime.utcnow()
            subscription_end = now + timedelta(days=duration_days)
            grace_period_end = subscription_end + timedelta(days=self.grace_period_days)
            
            # Check if subscription already exists
            existing = db(
                db.community_subscriptions.entity_id == entity_id
            ).select().first()
            
            if existing:
                # Update existing subscription
                db.community_subscriptions[existing.id] = dict(
                    subscription_type=subscription_type,
                    subscription_status="active",
                    subscription_start=now,
                    subscription_end=subscription_end,
                    auto_renew=True,
                    payment_method=payment_method,
                    payment_id=payment_id,
                    last_payment_date=now,
                    next_payment_date=subscription_end,
                    amount_paid=amount_paid,
                    currency=currency,
                    grace_period_end=grace_period_end,
                    updated_at=now
                )
            else:
                # Create new subscription
                db.community_subscriptions.insert(
                    entity_id=entity_id,
                    subscription_type=subscription_type,
                    subscription_status="active",
                    subscription_start=now,
                    subscription_end=subscription_end,
                    auto_renew=True,
                    payment_method=payment_method,
                    payment_id=payment_id,
                    last_payment_date=now,
                    next_payment_date=subscription_end,
                    amount_paid=amount_paid,
                    currency=currency,
                    grace_period_end=grace_period_end
                )
            
            db.commit()
            
            return {
                "success": True,
                "message": "Subscription created successfully",
                "subscription_end": subscription_end.isoformat(),
                "grace_period_end": grace_period_end.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating subscription for {entity_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Error creating subscription: {str(e)}"
            }
    
    def renew_subscription(self, entity_id: str, duration_days: int,
                          payment_method: str = None, payment_id: str = None,
                          amount_paid: float = 0.0, currency: str = "USD") -> Dict[str, Any]:
        """
        Renew an existing subscription
        
        Args:
            entity_id: Entity to renew subscription for
            duration_days: Additional duration in days
            payment_method: Payment method used
            payment_id: External payment ID
            amount_paid: Amount paid
            currency: Currency code
            
        Returns:
            Dict with success status and subscription info
        """
        try:
            subscription = db(
                db.community_subscriptions.entity_id == entity_id
            ).select().first()
            
            if not subscription:
                return {
                    "success": False,
                    "error": "No subscription found"
                }
            
            now = datetime.utcnow()
            
            # Calculate new end date from current end date or now, whichever is later
            current_end = subscription.subscription_end
            start_date = max(current_end, now) if current_end else now
            new_end = start_date + timedelta(days=duration_days)
            grace_period_end = new_end + timedelta(days=self.grace_period_days)
            
            # Update subscription
            db.community_subscriptions[subscription.id] = dict(
                subscription_status="active",
                subscription_end=new_end,
                payment_method=payment_method or subscription.payment_method,
                payment_id=payment_id or subscription.payment_id,
                last_payment_date=now,
                next_payment_date=new_end,
                amount_paid=amount_paid,
                currency=currency,
                grace_period_end=grace_period_end,
                updated_at=now
            )
            
            db.commit()
            
            return {
                "success": True,
                "message": "Subscription renewed successfully",
                "subscription_end": new_end.isoformat(),
                "grace_period_end": grace_period_end.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error renewing subscription for {entity_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Error renewing subscription: {str(e)}"
            }
    
    def cancel_subscription(self, entity_id: str, reason: str = None) -> Dict[str, Any]:
        """
        Cancel a subscription
        
        Args:
            entity_id: Entity to cancel subscription for
            reason: Reason for cancellation
            
        Returns:
            Dict with success status
        """
        try:
            subscription = db(
                db.community_subscriptions.entity_id == entity_id
            ).select().first()
            
            if not subscription:
                return {
                    "success": False,
                    "error": "No subscription found"
                }
            
            # Update subscription status
            db.community_subscriptions[subscription.id] = dict(
                subscription_status="cancelled",
                auto_renew=False,
                cancellation_reason=reason,
                updated_at=datetime.utcnow()
            )
            
            db.commit()
            
            return {
                "success": True,
                "message": "Subscription cancelled successfully"
            }
            
        except Exception as e:
            logger.error(f"Error cancelling subscription for {entity_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Error cancelling subscription: {str(e)}"
            }
    
    def record_payment(self, entity_id: str, payment_id: str, payment_method: str,
                      amount: float, currency: str, payment_status: str = "completed",
                      description: str = None, metadata: Dict = None) -> Dict[str, Any]:
        """
        Record a payment for a community
        
        Args:
            entity_id: Entity the payment is for
            payment_id: External payment ID
            payment_method: Payment method used
            amount: Payment amount
            currency: Currency code
            payment_status: Status of payment
            description: Payment description
            metadata: Additional metadata
            
        Returns:
            Dict with success status
        """
        try:
            db.community_payments.insert(
                entity_id=entity_id,
                payment_id=payment_id,
                payment_method=payment_method,
                amount=amount,
                currency=currency,
                payment_status=payment_status,
                payment_date=datetime.utcnow(),
                description=description,
                metadata=metadata or {}
            )
            
            db.commit()
            
            return {
                "success": True,
                "message": "Payment recorded successfully"
            }
            
        except Exception as e:
            logger.error(f"Error recording payment for {entity_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Error recording payment: {str(e)}"
            }
    
    def get_payment_history(self, entity_id: str, limit: int = 50) -> List[Dict]:
        """
        Get payment history for an entity
        
        Args:
            entity_id: Entity to get history for
            limit: Maximum number of payments to return
            
        Returns:
            List of payment records
        """
        try:
            payments = db(
                db.community_payments.entity_id == entity_id
            ).select(
                orderby=~db.community_payments.payment_date,
                limitby=(0, limit)
            )
            
            return [dict(payment) for payment in payments]
            
        except Exception as e:
            logger.error(f"Error getting payment history for {entity_id}: {str(e)}")
            return []
    
    def check_expired_subscriptions(self) -> List[str]:
        """
        Check for expired subscriptions and update their status
        
        Returns:
            List of entity IDs with expired subscriptions
        """
        try:
            now = datetime.utcnow()
            expired_entities = []
            
            # Find subscriptions that have expired (past grace period)
            expired_subscriptions = db(
                (db.community_subscriptions.subscription_status == "active") &
                (db.community_subscriptions.grace_period_end < now)
            ).select()
            
            for subscription in expired_subscriptions:
                # Update status to expired
                db.community_subscriptions[subscription.id] = dict(
                    subscription_status="expired",
                    updated_at=now
                )
                
                expired_entities.append(subscription.entity_id)
                logger.info(f"Subscription expired for entity: {subscription.entity_id}")
            
            # Find subscriptions expiring soon (within grace period)
            expiring_subscriptions = db(
                (db.community_subscriptions.subscription_status == "active") &
                (db.community_subscriptions.subscription_end < now) &
                (db.community_subscriptions.grace_period_end >= now)
            ).select()
            
            for subscription in expiring_subscriptions:
                logger.warning(f"Subscription in grace period for entity: {subscription.entity_id}")
            
            db.commit()
            
            return expired_entities
            
        except Exception as e:
            logger.error(f"Error checking expired subscriptions: {str(e)}")
            return []

# Create singleton instance
subscription_service = SubscriptionService()