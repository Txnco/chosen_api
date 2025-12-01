import firebase_admin
from firebase_admin import credentials, messaging
from typing import List, Optional
import logging
from pathlib import Path

logger = logging.getLogger("chosen_api")

class FCMService:
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize Firebase Admin SDK (call once on app startup)"""
        if cls._initialized:
            return
        
        try:
            # Use the existing Firebase Admin SDK credentials file
            cred_path = Path(__file__).parent.parent / "firebaseCreds.json"
            
            if not cred_path.exists():
                logger.error(f"Firebase credentials file not found at {cred_path}")
                return
            
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred)
            cls._initialized = True
            logger.info("✅ Firebase Admin SDK initialized successfully", extra={'color': True})
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase Admin SDK: {e}", extra={'color': True})
    
    @staticmethod
    def send_message_notification(
        fcm_token: str,
        sender_name: str,
        message_body: str,
        thread_id: int,
        sender_id: int
    ) -> bool:
        """
        Send FCM notification for new chat message
        
        Args:
            fcm_token: Device FCM registration token
            sender_name: Name of the person who sent the message
            message_body: Message content (will be truncated if too long)
            thread_id: Chat thread ID for deep linking
            sender_id: ID of the message sender
            
        Returns:
            bool: True if notification sent successfully
        """
        if not FCMService._initialized:
            logger.warning("FCM not initialized, skipping notification")
            return False
        
        try:
            # Truncate message if too long
            preview = message_body[:100] + "..." if len(message_body) > 100 else message_body
            
            # Build notification payload
            message = messaging.Message(
                notification=messaging.Notification(
                    title=sender_name,
                    body=preview,
                ),
                data={
                    "type": "chat_message",
                    "thread_id": str(thread_id),
                    "sender_id": str(sender_id),
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                },
                token=fcm_token,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        icon="notification_icon",
                        color="#000000",
                        sound="default",
                        channel_id="chat_messages",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                            category="CHAT_MESSAGE",
                        ),
                    ),
                ),
            )
            
            # Send the message
            response = messaging.send(message)
            logger.info(f"✅ FCM notification sent successfully: {response}", extra={'color': True})
            return True
            
        except messaging.UnregisteredError:
            logger.warning(f"⚠️ FCM token is invalid or unregistered: {fcm_token[:20]}...")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send FCM notification: {e}", extra={'color': True})
            return False
    
    @staticmethod
    def send_bulk_notifications(
        fcm_tokens: List[str],
        sender_name: str,
        message_body: str,
        thread_id: int,
        sender_id: int
    ) -> dict:
        """
        Send FCM notifications to multiple devices
        
        Returns:
            dict: {"success_count": int, "failure_count": int}
        """
        if not FCMService._initialized:
            logger.warning("FCM not initialized, skipping bulk notifications")
            return {"success_count": 0, "failure_count": len(fcm_tokens)}
        
        success_count = 0
        failure_count = 0
        
        for token in fcm_tokens:
            if FCMService.send_message_notification(token, sender_name, message_body, thread_id, sender_id):
                success_count += 1
            else:
                failure_count += 1
        
        logger.info(f"📊 Bulk FCM: {success_count} sent, {failure_count} failed", extra={'color': True})
        return {"success_count": success_count, "failure_count": failure_count}
