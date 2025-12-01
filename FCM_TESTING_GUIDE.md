# FCM Testing Guide

Quick guide to test the Firebase Cloud Messaging implementation.

## Prerequisites

- Backend API running
- Firebase credentials file present
- Database migration applied
- Firebase Admin SDK installed

## Step 1: Verify Installation

```bash
# Check if firebase-admin is installed
pip show firebase-admin

# Should show: Name: firebase-admin, Version: X.X.X
```

## Step 2: Apply Database Migration

```bash
# Connect to your MySQL database
mysql -u your_username -p your_database

# Run the migration
source migrations/add_fcm_token.sql;

# Verify the column was added
DESCRIBE users;

# Should show: fcm_token | varchar(500) | YES | | NULL |
```

## Step 3: Start the API

```bash
uvicorn main:app --reload
```

**Expected output:**
```
🚀 CHOSEN API Starting up...
✅ Firebase Admin SDK initialized successfully
📁 Logs directory: ...
✅ CHOSEN API Started successfully!
```

**If you see an error:**
```
❌ Failed to initialize Firebase Admin SDK: ...
```
- Check if `chosen-554d3-firebase-adminsdk-fbsvc-30df192b31.json` exists
- Verify file permissions
- Check JSON format is valid

## Step 4: Test FCM Token Registration

### Using curl (Windows CMD):

```cmd
curl -X POST http://localhost:8000/user/fcm-token ^
  -H "Authorization: Bearer YOUR_JWT_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"fcm_token\": \"test_token_12345\"}"
```

### Using PowerShell:

```powershell
$headers = @{
    "Authorization" = "Bearer YOUR_JWT_TOKEN"
    "Content-Type" = "application/json"
}
$body = @{
    fcm_token = "test_token_12345"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/user/fcm-token" -Headers $headers -Body $body
```

**Expected response:**
```json
{
  "message": "FCM token updated successfully",
  "user_id": 1
}
```

**Check logs:**
```
✅ FCM token updated for user 1
```

## Step 5: Verify Token in Database

```sql
SELECT id, first_name, last_name, fcm_token 
FROM users 
WHERE id = 1;
```

Should show your test token: `test_token_12345`

## Step 6: Test Message Sending with FCM

### 6.1 Register Real FCM Token

Use a real FCM token from your Flutter app or browser:

```bash
# Flutter: Get token from FCMService.initialize()
# Browser: Get token from registerFCMToken()
```

### 6.2 Send Test Message

```cmd
curl -X POST http://localhost:8000/chat/message ^
  -H "Authorization: Bearer SENDER_JWT_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"thread_id\": 1, \"body\": \"Hello! This is a test message.\", \"image_url\": null}"
```

**Check backend logs:**
```
📱 FCM notification sent to user 2
✅ FCM notification sent successfully: projects/chosen-554d3/messages/0:...
```

**On recipient device:**
- Should receive push notification
- Title: "Sender Name"
- Body: "Hello! This is a test message."

## Step 7: Test Token Deletion

```cmd
curl -X DELETE http://localhost:8000/user/fcm-token ^
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected response:**
```json
{
  "message": "FCM token deleted successfully",
  "user_id": 1
}
```

**Verify in database:**
```sql
SELECT fcm_token FROM users WHERE id = 1;
-- Should be NULL
```

## Common Test Scenarios

### Scenario 1: User Without FCM Token

1. Delete FCM token for user
2. Send message to that user
3. **Expected:** Message saved successfully, no notification sent
4. **Log:** `⚠️ No FCM token for user X, skipping notification`

### Scenario 2: Invalid FCM Token

1. Register fake token: `"invalid_token_abc123"`
2. Send message to that user
3. **Expected:** Message saved, notification attempt fails gracefully
4. **Log:** `⚠️ FCM token is invalid or unregistered: invalid_token_abc...`

### Scenario 3: Multiple Devices

1. Register FCM token from mobile app
2. Register FCM token from web browser (overwrites)
3. Send message
4. **Expected:** Only latest device receives notification

### Scenario 4: Long Message

1. Send message with 200+ characters
2. **Expected:** Notification truncates to 100 chars + "..."
3. **Full message** available when user opens app

## Testing with Firebase Console

### Send Test Notification Directly

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select `chosen-554d3` project
3. Cloud Messaging → Send test message
4. Enter FCM token from your database
5. Set title and body
6. Send

**This bypasses your API and tests:**
- FCM token validity
- Device connectivity
- Notification permissions

## Monitoring

### Check Logs

```bash
# Real-time logs
tail -f logs/api.log

# Error logs only
tail -f logs/errors.log

# Search for FCM-related logs
findstr "FCM" logs/api.log
```

### Key Log Patterns

**Successful notification:**
```
📱 FCM notification sent to user 123
✅ FCM notification sent successfully
```

**No token (expected):**
```
⚠️ No FCM token for user 123, skipping notification
```

**Invalid token:**
```
⚠️ FCM token is invalid or unregistered
```

**FCM not initialized:**
```
FCM not initialized, skipping notification
```

## Performance Testing

### Test Notification Latency

```python
import time
import requests

def test_notification_speed():
    start = time.time()
    
    response = requests.post(
        'http://localhost:8000/chat/message',
        headers={'Authorization': 'Bearer YOUR_TOKEN'},
        json={'thread_id': 1, 'body': 'Speed test', 'image_url': None}
    )
    
    end = time.time()
    print(f"Message sent in {end - start:.3f} seconds")

test_notification_speed()
```

**Expected:** < 0.5 seconds (including notification sending)

### Test Concurrent Messages

```python
import concurrent.futures
import requests

def send_message(thread_id, user_num):
    requests.post(
        'http://localhost:8000/chat/message',
        headers={'Authorization': f'Bearer TOKEN_{user_num}'},
        json={'thread_id': thread_id, 'body': f'Test {user_num}', 'image_url': None}
    )

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(send_message, 1, i) for i in range(10)]
    concurrent.futures.wait(futures)

print("✅ All messages sent")
```

## Troubleshooting

### Problem: FCM not initializing

**Check:**
1. File exists: `dir "chosen-554d3-firebase-adminsdk-fbsvc-30df192b31.json"`
2. Valid JSON: Open in text editor, check format
3. Check logs: `type logs\errors.log`

### Problem: Notifications not received

**Debug steps:**
1. Verify FCM token in database: `SELECT fcm_token FROM users WHERE id = X;`
2. Check Firebase Console → Cloud Messaging → Reports
3. Test token with Firebase Console test message
4. Verify notification permissions on device
5. Check device is online and connected

### Problem: Token registration fails

**Check:**
1. JWT token is valid and not expired
2. User exists in database
3. Request format is correct (JSON)
4. Check API logs for errors

## Quick Verification Checklist

- [ ] `firebase-admin` package installed
- [ ] Database migration applied (`fcm_token` column exists)
- [ ] Firebase credentials file present
- [ ] API starts successfully with "✅ Firebase Admin SDK initialized"
- [ ] Can register FCM token via API
- [ ] Token stored in database correctly
- [ ] Can send chat message successfully
- [ ] Notification log appears in console
- [ ] Can delete FCM token via API
- [ ] Token removed from database

## Next Steps

After successful testing:

1. **Deploy to production**
   - Update Firebase credentials for production
   - Set up production database
   - Configure HTTPS

2. **Integrate with Flutter**
   - Follow `FCM_FLUTTER_INTEGRATION.md`
   - Test on real devices (iOS and Android)
   - Test deep linking to chat

3. **Integrate with Next.js**
   - Follow `FCM_NEXTJS_INTEGRATION.md`
   - Set up service worker
   - Test web push notifications

4. **Monitor in production**
   - Set up alerts for FCM failures
   - Monitor notification delivery rates
   - Track user engagement

## Support

If issues persist:
1. Check `FCM_IMPLEMENTATION_GUIDE.md` for detailed documentation
2. Review Firebase Admin SDK logs
3. Test with Firebase Console
4. Verify Firebase project status and quotas
