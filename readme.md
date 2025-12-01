# CHOSEN API

FastAPI backend for CHOSEN fitness application with Firebase Cloud Messaging integration.

## Quick Start

### Installation

```bash
# Install all dependencies
pip install -r requirements.txt
```

### Database Setup

```bash
# Apply FCM migration
mysql -u your_username -p your_database < migrations/add_fcm_token.sql
```

### Run the Application

```bash
uvicorn main:app --reload
```

### Verify Startup

Look for these messages:
```
🚀 CHOSEN API Starting up...
✅ Firebase Admin SDK initialized successfully
✅ CHOSEN API Started successfully!
```

## Features

✅ User authentication & authorization (JWT)
✅ Chat messaging system
✅ Push notifications via Firebase Cloud Messaging (FCM)
✅ Progress tracking (weight, water, photos)
✅ Event management
✅ Questionnaire system
✅ Motivational quotes

## 📱 Firebase Cloud Messaging (FCM)

Push notifications are automatically sent when chat messages are received.

### Quick Setup

1. **Apply database migration:** `migrations/add_fcm_token.sql`
2. **Verify Firebase credentials:** `chosen-554d3-firebase-adminsdk-fbsvc-30df192b31.json`
3. **Start API:** Backend is ready!

### Documentation

- 🚀 **[Quick Start Guide](FCM_QUICK_START.md)** - Get started in 5 minutes
- 📖 **[Implementation Guide](FCM_IMPLEMENTATION_GUIDE.md)** - Complete technical documentation
- 📱 **[Flutter Integration](FCM_FLUTTER_INTEGRATION.md)** - Mobile app setup
- 🌐 **[Next.js Integration](FCM_NEXTJS_INTEGRATION.md)** - Web admin setup
- 🧪 **[Testing Guide](FCM_TESTING_GUIDE.md)** - Testing procedures
- 📋 **[Implementation Summary](FCM_IMPLEMENTATION_SUMMARY.md)** - What was built

### API Endpoints

```http
# Register FCM token
POST /user/fcm-token
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
{"fcm_token": "device_token"}

# Delete FCM token (logout)
DELETE /user/fcm-token
Authorization: Bearer <JWT_TOKEN>
```

## API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

## Project Structure

```
chosen_api/
├── auth/                   # JWT authentication
├── functions/              # Utility functions
│   ├── fcm.py             # Firebase Cloud Messaging service
│   ├── send_mail.py       # Email service
│   └── upload.py          # File upload handling
├── migrations/            # Database migrations
│   └── add_fcm_token.sql # FCM token column
├── models/                # SQLAlchemy models
├── routers/               # API route handlers
├── schema/                # Pydantic schemas
├── logs/                  # Application logs
├── uploads/               # User-uploaded files
├── config.py              # Configuration
├── database.py            # Database connection
├── main.py                # FastAPI application
└── requirements.txt       # Python dependencies
```

## Environment Variables

Create a `.env` file:

```env
DATABASE_URL=mysql+mysqlconnector://user:pass@localhost/chosen_db
JWT_SECRET_KEY=your_secret_key_here
UPLOAD_URL=./uploads
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# View logs
tail -f logs/api.log
tail -f logs/errors.log
```

## Testing

See **[FCM_TESTING_GUIDE.md](FCM_TESTING_GUIDE.md)** for comprehensive testing procedures.

Quick test:
```bash
# Test API health
curl http://localhost:8000/health

# Test FCM token registration
curl -X POST http://localhost:8000/user/fcm-token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fcm_token": "test_token"}'
```

## Deployment

1. Update Firebase credentials for production
2. Configure production database
3. Set up HTTPS (required for service workers)
4. Configure CORS for production domains
5. Set up reverse proxy (nginx recommended)
6. Enable firewall rules for ports 8000/443

## Support

- Check documentation files for detailed guides
- Review logs: `logs/api.log` and `logs/errors.log`
- Test with Firebase Console
- Verify Firebase project status

## License

Proprietary - CHOSEN International


uvicorn main:app --reload  