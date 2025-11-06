# Notification Preferences API Documentation

## Overview

This document describes the backend API endpoints for managing user notification preferences in the CHOSEN app. The notification preferences system allows users to configure when and how they receive local notifications on their Flutter mobile app.

## Database Changes

### Users Table - New Column

A new `notification_preferences` JSON column has been added to the `users` table:

```sql
ALTER TABLE users
ADD COLUMN notification_preferences JSON NULL
COMMENT 'Stores user notification preferences and schedules';
```

### Schema Structure

The `notification_preferences` JSON field stores a nested object with the following structure:

```json
{
  "daily_planning": {
    "enabled": true,
    "time": "20:00"
  },
  "day_rating": {
    "enabled": true,
    "time": "20:00"
  },
  "progress_photo": {
    "enabled": true,
    "day": "monday",
    "time": "09:00"
  },
  "weigh_in": {
    "enabled": true,
    "day": "monday",
    "time": "08:00"
  },
  "water_intake": {
    "enabled": false,
    "interval_hours": 2
  },
  "birthday": {
    "enabled": true,
    "time": "09:00"
  }
}
```

### Default Preferences

When a new user is registered, their notification preferences are automatically initialized with the following defaults:

| Notification Type | Enabled | Time/Schedule |
|------------------|---------|---------------|
| Daily Planning   | ✅ Yes  | 20:00 (8:00 PM) |
| Day Rating       | ✅ Yes  | 20:00 (8:00 PM) |
| Progress Photo   | ✅ Yes  | Monday at 09:00 (9:00 AM) |
| Weigh In         | ✅ Yes  | Monday at 08:00 (8:00 AM) |
| Water Intake     | ❌ No   | Every 2 hours |
| Birthday         | ✅ Yes  | 09:00 (9:00 AM) |

## API Endpoints

### Base Path

All notification endpoints are prefixed with:

```
/notifications
```

### Authentication

All endpoints require JWT authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

---

## 1. Get Notification Preferences

Retrieve the current user's notification preferences.

### Endpoint

```
GET /notifications/preferences
```

### Headers

| Header | Value | Required |
|--------|-------|----------|
| Authorization | Bearer {token} | ✅ Yes |

### Response

**Status Code:** `200 OK`

```json
{
  "user_id": 123,
  "notifications": {
    "daily_planning": {
      "enabled": true,
      "time": "20:00"
    },
    "day_rating": {
      "enabled": true,
      "time": "20:00"
    },
    "progress_photo": {
      "enabled": true,
      "day": "monday",
      "time": "09:00"
    },
    "weigh_in": {
      "enabled": true,
      "day": "monday",
      "time": "08:00"
    },
    "water_intake": {
      "enabled": false,
      "interval_hours": 2
    },
    "birthday": {
      "enabled": true,
      "time": "09:00"
    }
  }
}
```

### Error Responses

**Status Code:** `401 Unauthorized`
```json
{
  "detail": "Not authenticated"
}
```

**Status Code:** `404 Not Found`
```json
{
  "detail": "User not found"
}
```

### Notes

- If the user has no preferences stored (e.g., legacy users), the API returns default preferences automatically.
- The `user_id` in the response matches the authenticated user's ID from the JWT token.

---

## 2. Update Notification Preferences

Update one or more notification preferences for the current user.

### Endpoint

```
PUT /notifications/preferences
```

### Headers

| Header | Value | Required |
|--------|-------|----------|
| Authorization | Bearer {token} | ✅ Yes |
| Content-Type | application/json | ✅ Yes |

### Request Body

You can update one or multiple notification types. Only include the fields you want to change.

**Example 1: Update a single notification**

```json
{
  "water_intake": {
    "enabled": true,
    "interval_hours": 3
  }
}
```

**Example 2: Update multiple notifications**

```json
{
  "daily_planning": {
    "enabled": false,
    "time": "21:00"
  },
  "day_rating": {
    "enabled": true,
    "time": "22:00"
  },
  "water_intake": {
    "enabled": true,
    "interval_hours": 4
  }
}
```

**Example 3: Partial update (only change enabled state)**

```json
{
  "daily_planning": {
    "enabled": false
  }
}
```

### Field Validation

| Field | Type | Validation | Required |
|-------|------|------------|----------|
| enabled | boolean | true or false | ✅ Yes |
| time | string | HH:mm format (00:00 to 23:59) | ⚠️ For time-based notifications |
| day | string | monday, tuesday, wednesday, thursday, friday, saturday, sunday | ⚠️ For weekly notifications |
| interval_hours | integer | 1 to 24 | ⚠️ For water_intake only |

### Response

**Status Code:** `200 OK`

```json
{
  "user_id": 123,
  "notifications": {
    "daily_planning": {
      "enabled": false,
      "time": "21:00"
    },
    "day_rating": {
      "enabled": true,
      "time": "22:00"
    },
    "progress_photo": {
      "enabled": true,
      "day": "monday",
      "time": "09:00"
    },
    "weigh_in": {
      "enabled": true,
      "day": "monday",
      "time": "08:00"
    },
    "water_intake": {
      "enabled": true,
      "interval_hours": 4
    },
    "birthday": {
      "enabled": true,
      "time": "09:00"
    }
  }
}
```

### Error Responses

**Status Code:** `400 Bad Request` (Invalid time format)

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "daily_planning", "time"],
      "msg": "Time must be in HH:mm format (24-hour)",
      "input": "25:00"
    }
  ]
}
```

**Status Code:** `400 Bad Request` (Invalid day)

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "weigh_in", "day"],
      "msg": "Day must be one of: monday, tuesday, wednesday, thursday, friday, saturday, sunday",
      "input": "funday"
    }
  ]
}
```

**Status Code:** `401 Unauthorized`

```json
{
  "detail": "Not authenticated"
}
```

**Status Code:** `404 Not Found`

```json
{
  "detail": "User not found"
}
```

**Status Code:** `500 Internal Server Error`

```json
{
  "detail": "Failed to update notification preferences: <error_message>"
}
```

---

## 3. Reset Notification Preferences

Reset all notification preferences to their default values.

### Endpoint

```
POST /notifications/reset
```

### Headers

| Header | Value | Required |
|--------|-------|----------|
| Authorization | Bearer {token} | ✅ Yes |

### Request Body

None (empty body)

### Response

**Status Code:** `200 OK`

```json
{
  "user_id": 123,
  "notifications": {
    "daily_planning": {
      "enabled": true,
      "time": "20:00"
    },
    "day_rating": {
      "enabled": true,
      "time": "20:00"
    },
    "progress_photo": {
      "enabled": true,
      "day": "monday",
      "time": "09:00"
    },
    "weigh_in": {
      "enabled": true,
      "day": "monday",
      "time": "08:00"
    },
    "water_intake": {
      "enabled": false,
      "interval_hours": 2
    },
    "birthday": {
      "enabled": true,
      "time": "09:00"
    }
  },
  "message": "Notification preferences reset to defaults"
}
```

### Error Responses

**Status Code:** `401 Unauthorized`

```json
{
  "detail": "Not authenticated"
}
```

**Status Code:** `404 Not Found`

```json
{
  "detail": "User not found"
}
```

**Status Code:** `500 Internal Server Error`

```json
{
  "detail": "Failed to reset notification preferences: <error_message>"
}
```

---

## Usage Examples

### cURL Examples

#### 1. Get Preferences

```bash
curl -X GET "http://localhost:8000/notifications/preferences" \
  -H "Authorization: Bearer eyJhbGc..."
```

#### 2. Update Preferences

```bash
curl -X PUT "http://localhost:8000/notifications/preferences" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "water_intake": {
      "enabled": true,
      "interval_hours": 3
    },
    "daily_planning": {
      "enabled": false
    }
  }'
```

#### 3. Reset Preferences

```bash
curl -X POST "http://localhost:8000/notifications/reset" \
  -H "Authorization: Bearer eyJhbGc..."
```

### Flutter/Dart Integration Example

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class NotificationPreferencesService {
  final String baseUrl = 'http://your-api-domain.com';
  final String token;

  NotificationPreferencesService(this.token);

  // Get notification preferences
  Future<Map<String, dynamic>> getPreferences() async {
    final response = await http.get(
      Uri.parse('$baseUrl/notifications/preferences'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load preferences');
    }
  }

  // Update notification preferences
  Future<Map<String, dynamic>> updatePreferences(
    Map<String, dynamic> updates
  ) async {
    final response = await http.put(
      Uri.parse('$baseUrl/notifications/preferences'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: json.encode(updates),
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to update preferences');
    }
  }

  // Reset notification preferences
  Future<Map<String, dynamic>> resetPreferences() async {
    final response = await http.post(
      Uri.parse('$baseUrl/notifications/reset'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to reset preferences');
    }
  }
}

// Usage example
void example() async {
  final service = NotificationPreferencesService('your_jwt_token');

  // Get current preferences
  final prefs = await service.getPreferences();
  print('Current preferences: $prefs');

  // Update water intake notification
  await service.updatePreferences({
    'water_intake': {
      'enabled': true,
      'interval_hours': 3,
    }
  });

  // Reset to defaults
  await service.resetPreferences();
}
```

---

## Backend Implementation Details

### Files Modified/Created

1. **models/user.py** - Added `notification_preferences` JSON column
2. **schema/notification.py** - Created Pydantic schemas for validation
3. **routers/notification.py** - Created notification preferences endpoints
4. **routers/auth.py** - Updated to initialize preferences on user registration
5. **main.py** - Integrated notification router

### Data Flow

1. **User Registration:**
   - User registers via `/auth/register`
   - `notification_preferences` is initialized with default values
   - User object is saved to database

2. **Get Preferences:**
   - Flutter app calls `GET /notifications/preferences`
   - Backend retrieves user from database
   - If preferences are `NULL`, return defaults
   - Otherwise, return stored preferences

3. **Update Preferences:**
   - Flutter app calls `PUT /notifications/preferences` with updates
   - Backend validates the request (time format, day values, etc.)
   - Only provided fields are updated (partial update support)
   - Updated preferences are saved to database
   - Response includes all preferences (merged result)

4. **Reset Preferences:**
   - Flutter app calls `POST /notifications/reset`
   - Backend replaces all preferences with default values
   - Response confirms reset and returns default preferences

### Security & Validation

✅ **Authentication Required** - All endpoints require valid JWT token
✅ **User Isolation** - Users can only access/modify their own preferences
✅ **Input Validation** - Time format (HH:mm), day names, interval hours validated
✅ **SQL Injection Safe** - Using SQLAlchemy ORM with parameterized queries
✅ **JSON Schema Validation** - Pydantic models validate all input data

### Testing

A comprehensive test script is provided at `test_notifications_api.py`. Run it to verify all endpoints:

```bash
# Set environment variables
export API_BASE_URL=http://localhost:8000
export JWT_TOKEN=your_jwt_token

# Or use login credentials
export TEST_EMAIL=test@example.com
export TEST_PASSWORD=password123

# Run tests
python test_notifications_api.py
```

---

## Migration Instructions

### Step 1: Run SQL Migration

Execute the SQL migration script to add the `notification_preferences` column:

```bash
mysql -u your_user -p your_database < migrations/add_notification_preferences.sql
```

Or run manually in your MySQL client:

```sql
ALTER TABLE users
ADD COLUMN notification_preferences JSON NULL
COMMENT 'Stores user notification preferences and schedules';
```

### Step 2: (Optional) Initialize Existing Users

If you have existing users who don't have notification preferences set, you can:

**Option A:** Let them use defaults automatically (handled by API)

**Option B:** Bulk update all existing users:

```sql
UPDATE users
SET notification_preferences = JSON_OBJECT(
    'daily_planning', JSON_OBJECT('enabled', true, 'time', '20:00'),
    'day_rating', JSON_OBJECT('enabled', true, 'time', '20:00'),
    'progress_photo', JSON_OBJECT('enabled', true, 'day', 'monday', 'time', '09:00'),
    'weigh_in', JSON_OBJECT('enabled', true, 'day', 'monday', 'time', '08:00'),
    'water_intake', JSON_OBJECT('enabled', false, 'interval_hours', 2),
    'birthday', JSON_OBJECT('enabled', true, 'time', '09:00')
)
WHERE notification_preferences IS NULL;
```

### Step 3: Restart API Server

Restart your FastAPI server to load the new notification endpoints:

```bash
# If using uvicorn directly
uvicorn main:app --reload

# If using systemd
sudo systemctl restart chosen-api
```

### Step 4: Verify API

Test the health endpoint and notification endpoints:

```bash
# Health check
curl http://localhost:8000/health

# API docs (check for /notifications endpoints)
open http://localhost:8000/docs
```

### Step 5: Update Flutter App

Update your Flutter app to use the new API endpoints. The app should:

1. Fetch preferences on startup/login
2. Sync local changes to backend when user modifies settings
3. Handle offline mode gracefully (use cached preferences)

---

## Troubleshooting

### Error: "notification_preferences column does not exist"

**Solution:** Run the SQL migration to add the column:

```sql
ALTER TABLE users ADD COLUMN notification_preferences JSON NULL;
```

### Error: "Invalid time format"

**Solution:** Ensure time values are in 24-hour HH:mm format:
- ✅ Valid: `"09:00"`, `"14:30"`, `"23:59"`
- ❌ Invalid: `"9:00"`, `"2:30 PM"`, `"25:00"`

### Error: "Invalid day"

**Solution:** Use lowercase weekday names:
- ✅ Valid: `"monday"`, `"tuesday"`, `"wednesday"`
- ❌ Invalid: `"Monday"`, `"Mon"`, `"mon"`

### Preferences not syncing to Flutter app

**Checklist:**
1. Verify API is accessible from mobile device/emulator
2. Check JWT token is valid and not expired
3. Verify user is authenticated before calling endpoints
4. Check network connectivity
5. Review API response in Flutter debug console

---

## API Reference Quick Links

- **Swagger/OpenAPI Docs:** `http://your-api-domain.com/docs`
- **ReDoc:** `http://your-api-domain.com/redoc`
- **Health Check:** `http://your-api-domain.com/health`

---

## Support

For issues or questions:
1. Check this documentation
2. Review test script at `test_notifications_api.py`
3. Check FastAPI logs for detailed error messages
4. Verify database schema matches expected structure

---

**Last Updated:** 2025-11-06
**API Version:** 1.0.0
**Compatible with:** Flutter notification system v1.0+
