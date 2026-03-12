-- Migration: Add role field to users table
-- Date: 2026-03-12
-- Description: Add role field with enum values for user permissions

USE comiccraft_ai;

-- Add role column to users table
ALTER TABLE users 
ADD COLUMN role ENUM('user', 'admin') DEFAULT 'user' 
AFTER is_active;

-- Add index for role field (for faster queries)
ALTER TABLE users ADD INDEX idx_role (role);

-- Update first user to be admin (if exists)
UPDATE users SET role = 'admin' WHERE id = 1 LIMIT 1;

-- Show updated structure
DESCRIBE users;
