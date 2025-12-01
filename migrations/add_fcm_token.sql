-- Add FCM token column to users table
ALTER TABLE users ADD COLUMN fcm_token VARCHAR(500) NULL AFTER notification_preferences;

-- Add index for faster lookups
CREATE INDEX idx_users_fcm_token ON users(fcm_token);
