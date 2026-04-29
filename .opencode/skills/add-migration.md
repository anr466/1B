# Skill: add-migration
# إضافة ملف ترحيل قاعدة بيانات جديد

## Rules
- NEVER modify existing migration files in `database/migrations/`
- Create a new file: `database/migrations/{NNN}_{description}.sql`
- Increment the number from the last migration
- Use PostgreSQL syntax (psycopg2 — no ORM)
- Test with direct DB connection

## Verification
```bash
python -c "from backend.infrastructure.db_access import get_db_manager; db = get_db_manager(); conn = db.get_connection(); print(conn.cursor().execute('SELECT current_database()').fetchone())"
```
