# FCM Quick Start Guide

Get Firebase Cloud Messaging working in 5 minutes!

## 🚀 Quick Setup (Backend)

### Step 1: Apply Database Migration (Required!)

```cmd
mysql -u your_username -p your_database < migrations\add_fcm_token.sql
```

Or connect to your database and run:
```sql
ALTER TABLE users ADD COLUMN fcm_token VARCHAR(500) NULL AFTER notification_preferences;
CREATE INDEX idx_users_fcm_token ON users(fcm_token);
```

### Step 2: Verify Firebase Credentials

Check that this file exists:
```
chosen-554d3-firebase-adminsdk-fbsvc-30df192b31.json
```

If missing, download from Firebase Console → Project Settings → Service Accounts

### Step 3: Install Package (Already Done!)

```bash
pip install firebase-admin
```

### Step 4: Start API

```bash
uvicorn main:app --reload
```

Look for this in the output:
```
✅ Firebase Admin SDK initialized successfully
```

**That's it! Backend is ready.** 🎉

---

## 📱 Quick Test

### Test 1: Register FCM Token

```bash
curl -X POST http://localhost:8000/user/fcm-token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"fcm_token\": \"test_token_12345\"}"
```

**Expected:** `"message": "FCM token updated successfully"`

### Test 2: Verify in Database

```sql
SELECT id, first_name, fcm_token FROM users WHERE id = YOUR_USER_ID;
```

**Expected:** Your token appears in the `fcm_token` column

### Test 3: Send Test Message

```bash
curl -X POST http://localhost:8000/chat/message \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"thread_id\": 1, \"body\": \"Test notification\", \"image_url\": null}"
```

**Check logs for:**
```
📱 FCM notification sent to user X
✅ FCM notification sent successfully
```

---

## 🎯 Integration with Clients

### Flutter App

1. **Add to `pubspec.yaml`:**
   ```yaml
   dependencies:
     firebase_messaging: ^14.7.9
     http: ^1.1.0
   ```

2. **Initialize on login:**
   ```dart
   import 'package:firebase_messaging/firebase_messaging.dart';
   
   final fcm = FirebaseMessaging.instance;
   String? token = await fcm.getToken();
   
   // Send to backend
   await http.post(
     Uri.parse('YOUR_API/user/fcm-token'),
     headers: {'Authorization': 'Bearer $jwtToken', 'Content-Type': 'application/json'},
     body: jsonEncode({'fcm_token': token}),
   );
   ```

3. **See full guide:** `FCM_FLUTTER_INTEGRATION.md`

### Next.js Admin

1. **Install Firebase:**
   ```bash
   npm install firebase
   ```

2. **Register token on login:**
   ```typescript
   import { getMessaging, getToken } from 'firebase/messaging';
   
   const messaging = getMessaging();
   const token = await getToken(messaging, { vapidKey: 'YOUR_VAPID_KEY' });
   
   // Send to backend
   await fetch('YOUR_API/user/fcm-token', {
     method: 'POST',
     headers: {
       'Authorization': `Bearer ${jwtToken}`,
       'Content-Type': 'application/json',
     },
     body: JSON.stringify({ fcm_token: token }),
   });
   ```

3. **See full guide:** `FCM_NEXTJS_INTEGRATION.md`

---

## 🔧 Troubleshooting

### Problem: "Firebase Admin SDK failed to initialize"

**Solution:**
- Check file exists: `dir "chosen-554d3-firebase-adminsdk-fbsvc-30df192b31.json"`
- Verify it's valid JSON
- Check file permissions

### Problem: "No such column: fcm_token"

**Solution:**
- Run database migration: `migrations\add_fcm_token.sql`
- Restart API

### Problem: "No FCM token for user"

**Solution:**
- This is normal! User hasn't registered token yet
- User needs to login on Flutter/Next.js app
- Token will be registered automatically

### Problem: Notifications not received

**Solution:**
1. Verify real FCM token (not "test_token_12345")
2. Check device has notification permissions
3. Test with Firebase Console test message
4. Verify token is in database

---

## 📚 Documentation

- **Complete Guide:** `FCM_IMPLEMENTATION_GUIDE.md`
- **Flutter Integration:** `FCM_FLUTTER_INTEGRATION.md`
- **Next.js Integration:** `FCM_NEXTJS_INTEGRATION.md`
- **Testing Guide:** `FCM_TESTING_GUIDE.md`
- **Summary:** `FCM_IMPLEMENTATION_SUMMARY.md`

---

## ✅ Checklist

- [ ] Database migration applied
- [ ] Firebase credentials file exists
- [ ] API starts with "Firebase Admin SDK initialized"
- [ ] Can register FCM token via API
- [ ] Token appears in database
- [ ] Flutter app integrated (optional)
- [ ] Next.js app integrated (optional)

---

## 🎉 You're Done!

Backend is ready to send push notifications. Now integrate with your Flutter and Next.js apps to start receiving notifications!

**Questions?** Check the detailed documentation files listed above.
