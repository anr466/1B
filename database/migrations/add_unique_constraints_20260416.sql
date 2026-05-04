-- Critical Data Integrity Migration
-- Applied: 2026-04-16
-- Purpose: Add UNIQUE constraints to prevent duplicate users and key collisions
-- Status: PENDING

-- 1. Prevent duplicate email registrations
-- First: Check for existing duplicates
DO $$
DECLARE
    dup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO dup_count
    FROM (
        SELECT email FROM users WHERE email IS NOT NULL
        GROUP BY email HAVING COUNT(*) > 1
    ) dups;

    IF dup_count > 0 THEN
        RAISE NOTICE 'Found % duplicate email(s) — marking older ones with _dup suffix', dup_count;
        -- Keep the oldest (lowest id), mark others
        UPDATE users SET email = email || '_dup_' || id
        WHERE id NOT IN (
            SELECT MIN(id) FROM users WHERE email IS NOT NULL GROUP BY email
        )
        AND email IN (
            SELECT email FROM users WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1
        );
    END IF;
END $$;

-- Now add the constraint
ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);

-- 2. Prevent duplicate username registrations
DO $$
DECLARE
    dup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO dup_count
    FROM (
        SELECT username FROM users WHERE username IS NOT NULL
        GROUP BY username HAVING COUNT(*) > 1
    ) dups;

    IF dup_count > 0 THEN
        RAISE NOTICE 'Found % duplicate username(s) — marking older ones with _dup suffix', dup_count;
        UPDATE users SET username = username || '_dup_' || id
        WHERE id NOT IN (
            SELECT MIN(id) FROM users WHERE username IS NOT NULL GROUP BY username
        )
        AND username IN (
            SELECT username FROM users WHERE username IS NOT NULL GROUP BY username HAVING COUNT(*) > 1
        );
    END IF;
END $$;

ALTER TABLE users ADD CONSTRAINT uq_users_username UNIQUE (username);

-- 3. Prevent duplicate user_binance_keys (one active set per user)
ALTER TABLE user_binance_keys ADD CONSTRAINT uq_binance_keys_user UNIQUE (user_id);

-- 4. Prevent duplicate pending_verifications per action
ALTER TABLE pending_verifications ADD CONSTRAINT uq_pending_verifications_user_action UNIQUE (user_id, action);

-- 5. Prevent duplicate fcm_tokens per device
ALTER TABLE fcm_tokens ADD CONSTRAINT uq_fcm_tokens_user_device UNIQUE (user_id, device_id);

-- 6. Prevent duplicate user_sessions per token
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token);
