# FCM Integration Guide for Next.js

This guide explains how to integrate Firebase Cloud Messaging (FCM) in your Next.js admin panel to receive push notifications for chat messages.

## Prerequisites

1. Firebase project configured
2. Next.js app with authentication
3. Service Worker support

## Installation

```bash
npm install firebase
```

## Implementation

### 1. Firebase Configuration

Create `lib/firebase.ts`:

```typescript
import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

const app = initializeApp(firebaseConfig);

export { app };
```

### 2. Create FCM Service

Create `lib/fcm.ts`:

```typescript
import { getMessaging, getToken, onMessage, isSupported } from 'firebase/messaging';
import { app } from './firebase';

const VAPID_KEY = process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY;
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function registerFCMToken(jwtToken: string): Promise<boolean> {
  try {
    // Check if messaging is supported (not supported in SSR)
    const supported = await isSupported();
    if (!supported) {
      console.log('⚠️ FCM not supported in this browser');
      return false;
    }

    const messaging = getMessaging(app);

    // Request notification permission
    const permission = await Notification.requestPermission();
    
    if (permission !== 'granted') {
      console.log('⚠️ Notification permission denied');
      return false;
    }

    // Get FCM token
    const token = await getToken(messaging, {
      vapidKey: VAPID_KEY,
    });

    if (!token) {
      console.log('❌ No FCM token received');
      return false;
    }

    console.log('📱 FCM Token:', token);

    // Send to backend
    const response = await fetch(`${API_BASE_URL}/user/fcm-token`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ fcm_token: token }),
    });

    if (response.ok) {
      console.log('✅ FCM token registered successfully');
      return true;
    } else {
      console.error('❌ Failed to register FCM token:', response.status);
      return false;
    }
  } catch (error) {
    console.error('❌ FCM registration failed:', error);
    return false;
  }
}

export async function deleteFCMToken(jwtToken: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/user/fcm-token`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
      },
    });

    if (response.ok) {
      console.log('✅ FCM token deleted successfully');
      return true;
    } else {
      console.error('❌ Failed to delete FCM token:', response.status);
      return false;
    }
  } catch (error) {
    console.error('❌ Failed to delete FCM token:', error);
    return false;
  }
}

export async function setupFCMListener(
  onMessageReceived: (payload: any) => void
): Promise<void> {
  try {
    const supported = await isSupported();
    if (!supported) return;

    const messaging = getMessaging(app);

    onMessage(messaging, (payload) => {
      console.log('📱 Message received:', payload);
      
      // Call callback with message data
      onMessageReceived(payload);
      
      // Show browser notification
      if (payload.notification) {
        new Notification(payload.notification.title || 'New Message', {
          body: payload.notification.body,
          icon: '/logo.png',
          badge: '/badge.png',
          tag: 'chat-message',
          data: payload.data,
        });
      }
    });

    console.log('✅ FCM listener setup complete');
  } catch (error) {
    console.error('❌ Failed to setup FCM listener:', error);
  }
}
```

### 3. Create Service Worker

Create `public/firebase-messaging-sw.js`:

```javascript
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_AUTH_DOMAIN",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID",
});

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage((payload) => {
  console.log('📱 Background message received:', payload);

  const notificationTitle = payload.notification?.title || 'New Message';
  const notificationOptions = {
    body: payload.notification?.body || '',
    icon: '/logo.png',
    badge: '/badge.png',
    tag: 'chat-message',
    data: payload.data,
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  console.log('📱 Notification clicked:', event.notification.data);
  
  event.notification.close();
  
  // Navigate to chat thread
  const threadId = event.notification.data?.thread_id;
  const url = threadId ? `/chat/${threadId}` : '/chat';
  
  event.waitUntil(
    clients.openWindow(url)
  );
});
```

### 4. Update _app.tsx

```typescript
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { registerFCMToken, setupFCMListener, deleteFCMToken } from '../lib/fcm';
import { useAuth } from '../hooks/useAuth'; // Your auth hook

function MyApp({ Component, pageProps }) {
  const router = useRouter();
  const { user, jwtToken, logout } = useAuth();

  useEffect(() => {
    if (typeof window !== 'undefined' && user && jwtToken) {
      initializeFCM();
    }
  }, [user, jwtToken]);

  const initializeFCM = async () => {
    // Register FCM token
    const registered = await registerFCMToken(jwtToken);
    
    if (registered) {
      // Setup message listener
      setupFCMListener((payload) => {
        console.log('New message received:', payload);
        
        // Handle incoming message (e.g., show toast, update UI)
        const threadId = payload.data?.thread_id;
        
        // Optional: Show toast notification
        showNotificationToast(payload.notification?.title, payload.notification?.body);
        
        // Optional: Refresh chat data if on chat page
        if (router.pathname.includes('/chat')) {
          // Refresh chat messages
        }
      });
    }
  };

  const handleLogout = async () => {
    if (jwtToken) {
      await deleteFCMToken(jwtToken);
    }
    await logout();
  };

  const showNotificationToast = (title: string, body: string) => {
    // Use your preferred toast library (react-hot-toast, react-toastify, etc.)
    // Example with react-hot-toast:
    // toast.success(`${title}: ${body}`);
  };

  return <Component {...pageProps} />;
}

export default MyApp;
```

### 5. Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_auth_domain
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_storage_bucket
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id
NEXT_PUBLIC_FIREBASE_VAPID_KEY=your_vapid_key
NEXT_PUBLIC_API_BASE_URL=https://api.chosen-international.com
```

### 6. Generate VAPID Key

1. Go to Firebase Console
2. Project Settings → Cloud Messaging
3. Under "Web configuration" → "Web Push certificates"
4. Click "Generate key pair"
5. Copy the key to `NEXT_PUBLIC_FIREBASE_VAPID_KEY`

### 7. Register Service Worker

Update `next.config.js`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow service worker
  async headers() {
    return [
      {
        source: '/firebase-messaging-sw.js',
        headers: [
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

### 8. Create Notification Component (Optional)

Create `components/NotificationToast.tsx`:

```typescript
import { useEffect } from 'react';
import { toast } from 'react-hot-toast';

export function NotificationHandler() {
  useEffect(() => {
    // Request notification permission on mount
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
          console.log('✅ Notification permission granted');
        }
      });
    }
  }, []);

  return null;
}
```

## Testing

### Test FCM Registration

1. **Login to admin panel**
2. **Open browser console** - Look for "✅ FCM token registered successfully"
3. **Check Network tab** - Verify POST request to `/user/fcm-token` succeeded

### Test Notifications

1. **Open admin panel in one browser/tab**
2. **Send a chat message from mobile app or another account**
3. **Verify notification appears** in browser
4. **Click notification** - Should navigate to chat thread

### Test Service Worker

1. Open Chrome DevTools → Application → Service Workers
2. Verify `firebase-messaging-sw.js` is registered and activated
3. Click "Update" to refresh service worker

## Browser Compatibility

- ✅ Chrome/Edge (Desktop & Mobile)
- ✅ Firefox (Desktop & Mobile)
- ✅ Safari (iOS 16.4+, macOS)
- ❌ Safari (older versions - no service worker support)

## Production Checklist

- [ ] Register VAPID key in Firebase Console
- [ ] Configure service worker with production Firebase config
- [ ] Set up HTTPS (required for service workers)
- [ ] Test notifications in production environment
- [ ] Handle notification permissions gracefully
- [ ] Add error boundaries for FCM initialization failures
- [ ] Implement notification preferences in UI
- [ ] Test on multiple browsers
- [ ] Add analytics for notification engagement

## Troubleshooting

### Service worker not registering

1. Ensure HTTPS is enabled (required for service workers)
2. Check `next.config.js` headers configuration
3. Clear browser cache and reload
4. Check console for service worker errors

### No notifications in browser

1. Check notification permission: `Notification.permission`
2. Verify FCM token is registered with backend
3. Ensure service worker is active
4. Check browser console for errors

### Notifications not appearing when app is open

This is expected behavior. Use `onMessage` handler to show in-app notifications (toast, etc.)

### VAPID key error

1. Generate new VAPID key in Firebase Console
2. Update environment variable
3. Rebuild and redeploy application

## Resources

- [Firebase Cloud Messaging Documentation](https://firebase.google.com/docs/cloud-messaging/js/client)
- [Next.js Service Workers](https://nextjs.org/docs/pages/building-your-application/configuring/progressive-web-apps)
- [Web Push Notifications](https://web.dev/push-notifications-overview/)
