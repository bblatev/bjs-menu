"""Firebase Cloud Messaging (FCM) push notification service."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FirebasePushService:
    """Send push notifications via Firebase Cloud Messaging (FCM v1 API)."""

    def __init__(self):
        self._initialized = False
        self._app = None

    def initialize(self, credentials_path: Optional[str] = None):
        """Initialize Firebase Admin SDK."""
        try:
            import firebase_admin
            from firebase_admin import credentials as fb_credentials

            if credentials_path:
                cred = fb_credentials.Certificate(credentials_path)
                self._app = firebase_admin.initialize_app(cred)
            else:
                self._app = firebase_admin.initialize_app()
            self._initialized = True
            logger.info("Firebase Admin SDK initialized")
        except ImportError:
            logger.info("firebase-admin not installed, push notifications disabled")
        except Exception as e:
            logger.warning(f"Firebase initialization failed: {e}. Push notifications disabled.")

    async def send_to_device(
        self, token: str, title: str, body: str, data: Optional[Dict[str, str]] = None
    ) -> bool:
        """Send notification to a single device."""
        if not self._initialized:
            logger.debug("Firebase not initialized, skipping push notification")
            return False
        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                token=token,
            )
            response = messaging.send(message)
            logger.info(f"Push notification sent: {response}")
            return True
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return False

    async def send_to_topic(
        self, topic: str, title: str, body: str, data: Optional[Dict[str, str]] = None
    ) -> bool:
        """Send notification to a topic (e.g., 'kitchen', 'managers')."""
        if not self._initialized:
            return False
        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                topic=topic,
            )
            response = messaging.send(message)
            logger.info(f"Topic notification sent to '{topic}': {response}")
            return True
        except Exception as e:
            logger.error(f"Topic notification failed: {e}")
            return False

    async def send_multicast(
        self, tokens: List[str], title: str, body: str, data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send notification to multiple devices."""
        if not self._initialized:
            return {"success_count": 0, "failure_count": len(tokens)}
        try:
            from firebase_admin import messaging

            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                tokens=tokens,
            )
            response = messaging.send_each_for_multicast(message)
            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
            }
        except Exception as e:
            logger.error(f"Multicast notification failed: {e}")
            return {"success_count": 0, "failure_count": len(tokens)}


firebase_push = FirebasePushService()
