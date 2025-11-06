-- Manual migration script to add notification_preferences column to users table
-- Run this SQL script manually on your MySQL database

-- Add notification_preferences JSON column to users table
ALTER TABLE users
ADD COLUMN notification_preferences JSON NULL
COMMENT 'Stores user notification preferences and schedules';

-- Optional: Update existing users with default preferences
-- Uncomment the following lines if you want to initialize all existing users with default preferences

-- UPDATE users
-- SET notification_preferences = JSON_OBJECT(
--     'daily_planning', JSON_OBJECT('enabled', true, 'time', '20:00'),
--     'day_rating', JSON_OBJECT('enabled', true, 'time', '20:00'),
--     'progress_photo', JSON_OBJECT('enabled', true, 'day', 'monday', 'time', '09:00'),
--     'weigh_in', JSON_OBJECT('enabled', true, 'day', 'monday', 'time', '08:00'),
--     'water_intake', JSON_OBJECT('enabled', false, 'interval_hours', 2),
--     'birthday', JSON_OBJECT('enabled', true, 'time', '09:00')
-- )
-- WHERE notification_preferences IS NULL;

-- Verify the column was added
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'users'
  AND COLUMN_NAME = 'notification_preferences';

-- Test query to view notification preferences for all users
-- SELECT id, email, first_name, last_name, notification_preferences
-- FROM users
-- LIMIT 10;
