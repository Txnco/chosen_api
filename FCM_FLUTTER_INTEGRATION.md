# FCM Integration Guide for Flutter

This guide explains how to integrate Firebase Cloud Messaging (FCM) in your Flutter app to receive push notifications when chat messages arrive.

## Prerequisites

1. Firebase project already configured
2. `firebase_messaging` package
3. `http` package for API calls

## Installation

Add to your `pubspec.yaml`:

```yaml
dependencies:
  firebase_messaging: ^14.7.9
  http: ^1.1.0
```

## Implementation

### 1. Create FCM Service

Create `lib/services/fcm_service.dart`:

```dart
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class FCMService {
  static final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  static const String baseUrl = 'YOUR_API_BASE_URL';  // e.g., https://api.chosen-international.com

  /// Initialize FCM and register token with backend
  static Future<void> initialize(String jwtToken) async {
    // Request notification permissions
    NotificationSettings settings = await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      print('✅ User granted notification permission');
      
      // Get FCM token
      String? token = await _fcm.getToken();
      
      if (token != null) {
        print('📱 FCM Token: $token');
        
        // Send token to backend
        await registerToken(token, jwtToken);
        
        // Listen for token refresh
        _fcm.onTokenRefresh.listen((newToken) {
          print('🔄 FCM Token refreshed');
          registerToken(newToken, jwtToken);
        });
      }
    } else if (settings.authorizationStatus == AuthorizationStatus.denied) {
      print('⚠️ User denied notification permission');
    }
  }

  /// Register FCM token with backend
  static Future<void> registerToken(String fcmToken, String jwtToken) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/user/fcm-token'),
        headers: {
          'Authorization': 'Bearer $jwtToken',
          'Content-Type': 'application/json',
        },
        body: json.encode({'fcm_token': fcmToken}),
      );

      if (response.statusCode == 200) {
        print('✅ FCM token registered successfully');
      } else {
        print('❌ Failed to register FCM token: ${response.statusCode}');
        print('Response: ${response.body}');
      }
    } catch (e) {
      print('❌ Error registering FCM token: $e');
    }
  }

  /// Delete FCM token (call on logout)
  static Future<void> deleteToken(String jwtToken) async {
    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/user/fcm-token'),
        headers: {
          'Authorization': 'Bearer $jwtToken',
        },
      );

      if (response.statusCode == 200) {
        print('✅ FCM token deleted from backend');
      }
      
      // Delete local FCM token
      await _fcm.deleteToken();
      print('✅ Local FCM token deleted');
    } catch (e) {
      print('❌ Failed to delete FCM token: $e');
    }
  }

  /// Setup foreground message handler
  static void setupForegroundMessageHandler() {
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      print('📱 Foreground message received');
      print('Title: ${message.notification?.title}');
      print('Body: ${message.notification?.body}');
      print('Data: ${message.data}');
      
      // Show local notification or update UI
      // You can use flutter_local_notifications package here
    });
  }

  /// Setup background message tap handler
  static void setupBackgroundMessageHandler(Function(int) onNavigateToChat) {
    // When user taps notification while app is in background
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      print('📱 Notification tapped (app in background)');
      
      final threadId = int.tryParse(message.data['thread_id'] ?? '');
      if (threadId != null) {
        onNavigateToChat(threadId);
      }
    });
  }

  /// Check for initial message (app opened from terminated state)
  static Future<void> checkInitialMessage(Function(int) onNavigateToChat) async {
    RemoteMessage? initialMessage = await _fcm.getInitialMessage();
    
    if (initialMessage != null) {
      print('📱 App opened from notification (terminated state)');
      
      final threadId = int.tryParse(initialMessage.data['thread_id'] ?? '');
      if (threadId != null) {
        onNavigateToChat(threadId);
      }
    }
  }
}

/// Background message handler (must be top-level function)
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  print('📱 Background message received: ${message.messageId}');
  print('Data: ${message.data}');
}
```

### 2. Update main.dart

```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'services/fcm_service.dart';
import 'firebase_options.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  
  // Register background message handler
  FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
  
  runApp(MyApp());
}

class MyApp extends StatefulWidget {
  @override
  _MyAppState createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  @override
  void initState() {
    super.initState();
    _initializeFCM();
  }

  Future<void> _initializeFCM() async {
    // Get JWT token from your auth service
    String? jwtToken = await getStoredJWTToken();
    
    if (jwtToken != null) {
      // Initialize FCM
      await FCMService.initialize(jwtToken);
      
      // Setup message handlers
      FCMService.setupForegroundMessageHandler();
      FCMService.setupBackgroundMessageHandler(_navigateToChat);
      
      // Check if app was opened from notification
      await FCMService.checkInitialMessage(_navigateToChat);
    }
  }

  void _navigateToChat(int threadId) {
    // Navigate to chat screen
    // Example: Navigator.pushNamed(context, '/chat/$threadId');
    print('Navigate to chat thread: $threadId');
  }

  Future<String?> getStoredJWTToken() async {
    // Retrieve JWT token from secure storage
    // Example: return await SecureStorage.read('jwt_token');
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CHOSEN',
      home: HomeScreen(),
    );
  }
}
```

### 3. Handle Logout

When user logs out, delete the FCM token:

```dart
Future<void> logout() async {
  String? jwtToken = await getStoredJWTToken();
  
  if (jwtToken != null) {
    // Delete FCM token from backend
    await FCMService.deleteToken(jwtToken);
  }
  
  // Clear local storage and navigate to login
  // ...
}
```

### 4. Android Configuration

Update `android/app/src/main/AndroidManifest.xml`:

```xml
<manifest>
    <application>
        <!-- ... -->
        
        <!-- FCM notification channel -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_channel_id"
            android:value="chat_messages" />
        
        <!-- Default notification icon -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_icon"
            android:resource="@drawable/notification_icon" />
        
        <!-- Default notification color -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_color"
            android:resource="@color/notification_color" />
    </application>
</manifest>
```

Create notification icon at `android/app/src/main/res/drawable/notification_icon.xml`:

```xml
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M12,2C6.48,2 2,6.48 2,12s4.48,10 10,10 10,-4.48 10,-10S17.52,2 12,2zM13,17h-2v-2h2v2zM13,13h-2L11,7h2v6z"/>
</vector>
```

### 5. iOS Configuration

Update `ios/Runner/AppDelegate.swift`:

```swift
import UIKit
import Flutter
import Firebase

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    FirebaseApp.configure()
    
    if #available(iOS 10.0, *) {
      UNUserNotificationCenter.current().delegate = self as UNUserNotificationCenterDelegate
    }
    
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
```

## Testing

1. **Login to the app** - FCM token is automatically registered
2. **Send a message from another user** - You should receive a push notification
3. **Tap the notification** - App should open to the chat thread
4. **Check logs** for FCM token registration confirmation

## Troubleshooting

### No notifications received

1. Check if FCM token is registered: Look for "✅ FCM token registered successfully" in logs
2. Verify Firebase project configuration
3. Check notification permissions are granted
4. Ensure app is not in foreground (foreground notifications need local notification display)

### Token not registering

1. Check API base URL is correct
2. Verify JWT token is valid
3. Check network connectivity
3. Look for error messages in console

### Notifications not opening chat

1. Verify `thread_id` is included in notification data
2. Check navigation logic in `_navigateToChat` function
3. Ensure routing is properly set up

## Production Considerations

1. **Handle token refresh** - Token can change, ensure it's updated on backend
2. **Notification channels (Android)** - Create custom channels for different notification types
3. **Badge count (iOS)** - Update badge count when notifications are received
4. **Sound and vibration** - Customize notification sounds
5. **Notification priority** - Set appropriate priority for chat messages
