# Firebase Cloud Messaging (FCM) Implementation

Complete implementation of Firebase Cloud Messaging for push notifications in the CHOSEN API chat system.

## Overview

This implementation enables real-time push notifications for chat messages across:
- **Backend API**: FastAPI (Python) with Firebase Admin SDK
- **Flutter App**: Mobile push notifications
- **Next.js Admin**: Web push notifications

## Features

✅ Real-time push notifications for chat messages
✅ Automatic FCM token registration and refresh
✅ Token cleanup on logout
✅ Support for iOS (APNS) and Android (FCM)
✅ Web push notifications for admin panel
✅ Message preview in notifications
✅ Deep linking to chat threads
✅ Notification customization (sound, icon, badge)

## Architecture

```
┌─────────────────┐
│  Flutter App    │──────┐
└─────────────────┘      │
                         │ FCM Token
┌─────────────────┐      │ Registration
│  Next.js Admin  │──────┼──────────> ┌──────────────┐
└─────────────────┘      │            │  Backend API │
                         │            └──────────────┘
                                             │
                                             │ Send Notification
                                             ▼
                                      ┌──────────────┐
                                      │   Firebase   │
                                      │     FCM      │
                                      └──────────────┘
                                             │
                         ┌───────────────────┼───────────────────┐
                         │                   │                   │
                         ▼                   ▼                   ▼
                  ┌───────────┐       ┌───────────┐      ┌───────────┐
                  │  iOS App  │       │Android App│      │  Browser  │
                  └───────────┘       └───────────┘      └───────────┘
```

## Backend Implementation

### Files Created/Modified

1. **`functions/fcm.py`** - FCM service module
   - `FCMService.initialize()` - Initialize Firebase Admin SDK
   - `FCMService.send_message_notification()` - Send notification to single device
   - `FCMService.send_bulk_notifications()` - Send to multiple devices

2. **`models/user.py`** - Added FCM token storage
   - New column: `fcm_token VARCHAR(500)`

3. **`routers/user.py`** - FCM token management endpoints
   - `POST /user/fcm-token` - Register/update FCM token
   - `DELETE /user/fcm-token` - Remove FCM token (logout)

4. **`routers/chat.py`** - Send notifications on new messages
   - Automatically sends FCM notification when message is created
   - Logs notification status

5. **`main.py`** - Initialize FCM on startup
   - Calls `FCMService.initialize()` on app startup

6. **`requirements.txt`** - Added dependency
   - `firebase-admin` package

7. **`migrations/add_fcm_token.sql`** - Database migration
   - Adds `fcm_token` column to users table
   - Creates index for performance

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Database Migration

```bash
# Using MySQL client
mysql -u your_username -p your_database < migrations/add_fcm_token.sql

# Or using Python
python -c "
from database import engine
with open('migrations/add_fcm_token.sql', 'r') as f:
    for statement in f.read().split(';'):
        if statement.strip():
            engine.execute(statement)
"
```

### 3. Verify Firebase Credentials

Ensure `chosen-554d3-firebase-adminsdk-fbsvc-30df192b31.json` exists in the project root.

### 4. Start the API

```bash
uvicorn main:app --reload
```

Check startup logs for:
```
✅ Firebase Admin SDK initialized successfully
```

## API Endpoints

### Register FCM Token

```http
POST /user/fcm-token
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "fcm_token": "device_fcm_token_here"
}
```

**Response:**
```json
{
  "message": "FCM token updated successfully",
  "user_id": 123
}
```

### Delete FCM Token (Logout)

```http
DELETE /user/fcm-token
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "message": "FCM token deleted successfully",
  "user_id": 123
}
```

## Notification Payload

When a chat message is sent, the backend automatically sends this FCM notification:

```json
{
  "notification": {
    "title": "John Doe",
    "body": "Hey, how are you doing?"
  },
  "data": {
    "type": "chat_message",
    "thread_id": "42",
    "sender_id": "123",
    "click_action": "FLUTTER_NOTIFICATION_CLICK"
  },
  "token": "recipient_fcm_token"
}
```

### Android-Specific Configuration

```json
{
  "android": {
    "priority": "high",
    "notification": {
      "icon": "notification_icon",
      "color": "#000000",
      "sound": "default",
      "channel_id": "chat_messages"
    }
  }
}
```

### iOS-Specific Configuration (APNS)

```json
{
  "apns": {
    "payload": {
      "aps": {
        "sound": "default",
        "badge": 1,
        "category": "CHAT_MESSAGE"
      }
    }
  }
}
```

## Client Integration Guides

### Flutter Integration

See **[FCM_FLUTTER_INTEGRATION.md](FCM_FLUTTER_INTEGRATION.md)** for complete Flutter setup including:
- FCM service implementation
- Foreground/background message handling
- Deep linking to chat threads
- iOS and Android configuration

### Next.js Integration

See **[FCM_NEXTJS_INTEGRATION.md](FCM_NEXTJS_INTEGRATION.md)** for web push setup including:
- Service worker configuration
- Browser notification handling
- VAPID key setup
- Environment configuration

## Testing

### Test Backend FCM Initialization

```bash
# Start the API and check logs
uvicorn main:app --reload

# Expected output:
# 🚀 CHOSEN API Starting up...
# ✅ Firebase Admin SDK initialized successfully
# ✅ CHOSEN API Started successfully!
```

### Test FCM Token Registration

```bash
# Register a test token
curl -X POST http://localhost:8000/user/fcm-token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fcm_token": "test_token_123456"}'

# Expected response:
# {
#   "message": "FCM token updated successfully",
#   "user_id": 1
# }
```

### Test Notification Sending

1. Register FCM token for User A (mobile/web)
2. Login as User B
3. Send a chat message to User A
4. Check logs:
   ```
   📱 FCM notification sent to user 1
   ✅ FCM notification sent successfully: projects/...
   ```
5. User A should receive push notification

### Test Token Deletion

```bash
# Delete FCM token
curl -X DELETE http://localhost:8000/user/fcm-token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Expected response:
# {
#   "message": "FCM token deleted successfully",
#   "user_id": 1
# }
```

## Monitoring & Logging

The implementation includes comprehensive logging:

### Successful Notification
```
📱 FCM notification sent to user 123
✅ FCM notification sent successfully: projects/chosen-554d3/messages/0:1234567890
```

### No FCM Token (Expected)
```
⚠️ No FCM token for user 123, skipping notification
```

### Invalid Token
```
⚠️ FCM token is invalid or unregistered: abc123...
```

### FCM Initialization Error
```
❌ Failed to initialize Firebase Admin SDK: [error details]
```

## Error Handling

### Invalid FCM Token

When a token becomes invalid (app uninstalled, token expired):
- Backend logs warning: `⚠️ FCM token is invalid or unregistered`
- Returns `False` from `send_message_notification()`
- Does NOT crash or throw exception
- Consider: Automatically delete invalid tokens from database

### FCM Not Initialized

If Firebase fails to initialize:
- Logs error with details
- All notification attempts return `False`
- Chat messages still work normally
- Consider: Add health check endpoint

### Network Errors

Firebase Admin SDK handles retries automatically for transient network errors.

## Performance Considerations

### Database Indexing

The migration adds an index on `fcm_token` for efficient lookups:
```sql
CREATE INDEX idx_users_fcm_token ON users(fcm_token);
```

### Async Notification Sending (Future Enhancement)

Current implementation sends notifications synchronously. For high-volume applications, consider:

```python
import asyncio

async def send_notification_async(fcm_token, sender_name, message_body, thread_id, sender_id):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        FCMService.send_message_notification,
        fcm_token, sender_name, message_body, thread_id, sender_id
    )
```

## Security

### Token Storage

- FCM tokens are stored in database (encrypted at rest recommended)
- Tokens are user-specific and cannot be used by other users
- Tokens are deleted on logout

### Authorization

- All FCM token endpoints require JWT authentication
- Users can only modify their own FCM token
- No admin bypass for token management

## Firebase Console Configuration

### Enable Cloud Messaging API

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (`chosen-554d3`)
3. Settings → Cloud Messaging
4. Verify Cloud Messaging API is enabled

### View Message Statistics

Firebase Console → Cloud Messaging → Reports shows:
- Messages sent
- Delivery rate
- Open rate
- Error logs

## Troubleshooting

### FCM Not Initializing

**Symptom:** `❌ Failed to initialize Firebase Admin SDK`

**Solutions:**
1. Verify `chosen-554d3-firebase-adminsdk-fbsvc-30df192b31.json` exists
2. Check file permissions (readable by API)
3. Verify JSON format is valid
4. Check Firebase project is active

### Notifications Not Received

**Symptom:** Message sent but no notification appears

**Solutions:**
1. Verify FCM token is registered: `SELECT fcm_token FROM users WHERE id = X;`
2. Check recipient has granted notification permissions
3. Review backend logs for errors
4. Test with FCM console: Send test notification to token
5. Verify Firebase Cloud Messaging API is enabled

### Invalid Token Errors

**Symptom:** `⚠️ FCM token is invalid or unregistered`

**Solutions:**
1. User may have uninstalled app → Token is invalid
2. Token may have expired → User needs to re-login
3. Implement automatic token cleanup:
   ```python
   if not success:
       user.fcm_token = None
       db.commit()
   ```

## Future Enhancements

### 1. Message Priority Levels

```python
def send_urgent_notification(fcm_token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        android=messaging.AndroidConfig(priority='high'),
        apns=messaging.APNSConfig(
            headers={'apns-priority': '10'}
        ),
        token=fcm_token
    )
    return messaging.send(message)
```

### 2. Topic-Based Notifications

```python
# Subscribe users to topics
messaging.subscribe_to_topic(['token1', 'token2'], 'trainers')

# Send to all subscribers
messaging.send_to_topic('trainers', message)
```

### 3. Rich Notifications

```python
# With image
message = messaging.Message(
    notification=messaging.Notification(
        title=title,
        body=body,
        image='https://example.com/image.jpg'
    ),
    token=fcm_token
)
```

### 4. Scheduled Notifications

Integrate with APScheduler or Celery for scheduled reminders.

### 5. Notification Preferences

Add user preferences table:
```sql
CREATE TABLE notification_preferences (
    user_id INT PRIMARY KEY,
    chat_messages BOOLEAN DEFAULT TRUE,
    reminders BOOLEAN DEFAULT TRUE,
    marketing BOOLEAN DEFAULT FALSE
);
```

### 6. Analytics Integration

Track notification engagement:
```python
from firebase_admin import analytics

def log_notification_sent(user_id, notification_type):
    analytics.log_event('notification_sent', {
        'user_id': user_id,
        'type': notification_type
    })
```

## Resources

- [Firebase Admin SDK Documentation](https://firebase.google.com/docs/admin/setup)
- [FCM Server Implementation](https://firebase.google.com/docs/cloud-messaging/server)
- [Firebase Console](https://console.firebase.google.com/)
- [Flutter Firebase Messaging](https://firebase.flutter.dev/docs/messaging/overview/)
- [Web Push Notifications](https://firebase.google.com/docs/cloud-messaging/js/client)

## Support

For issues or questions:
1. Check logs: `logs/api.log` and `logs/errors.log`
2. Review this documentation
3. Test with Firebase Console test notifications
4. Check Firebase project status

## License

This implementation uses Firebase Admin SDK under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).
