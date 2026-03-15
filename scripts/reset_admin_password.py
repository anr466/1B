import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.utils.password_utils import hash_password
from database.database_manager import DatabaseManager

NEW_PASSWORD = 'admin123'
ADMIN_USERNAME = 'admin'
ADMIN_EMAIL = 'admin@tradingbot.com'


def main() -> None:
    db = DatabaseManager()
    password_hash = hash_password(NEW_PASSWORD)
    with db.get_write_connection() as conn:
        existing = conn.execute(
            """
            SELECT id, username, email
            FROM users
            WHERE username = ?
               OR email = ?
               OR user_type = 'admin'
            ORDER BY CASE WHEN username = ? THEN 0 ELSE 1 END, id ASC
            LIMIT 1
            """,
            (ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_USERNAME),
        ).fetchone()

        if existing:
            admin_id = existing['id'] if hasattr(existing, '__getitem__') else existing[0]
            conn.execute(
                """
                UPDATE users
                SET username = ?,
                    password_hash = ?,
                    user_type = 'admin',
                    is_active = 1,
                    email_verified = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (ADMIN_USERNAME, password_hash, admin_id),
            )
            row = conn.execute(
                "SELECT id, username, email, user_type, is_active FROM users WHERE id = ?",
                (admin_id,),
            ).fetchone()
        else:
            conn.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, user_type, is_active, email_verified, created_at, updated_at
                ) VALUES (?, ?, ?, 'admin', 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (ADMIN_USERNAME, ADMIN_EMAIL, password_hash),
            )
            row = conn.execute(
                """
                SELECT id, username, email, user_type, is_active
                FROM users
                WHERE username = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (ADMIN_USERNAME,),
            ).fetchone()
    print(row)


if __name__ == '__main__':
    main()
