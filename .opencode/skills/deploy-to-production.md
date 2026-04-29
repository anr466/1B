# Skill: deploy-to-production
# نشر الإنتاج عبر Docker على VPS

## VPS
```bash
ssh root@72.60.190.188
```

## Docker Architecture
4 services in `docker-compose.yml`:
| Service | CMD | Port |
|---------|-----|------|
| `api` | `start_server.py` (Flask) | 3002 |
| `scanner` | `bin/scanner_worker.py` | — |
| `executor` | `bin/executor_worker.py` | — |
| `postgres` | postgres:16-alpine | 5432 |
| `nginx` | nginx:1.27-alpine | 80 → api:3002 |

## نشر سريع
```bash
# 1. انسخ الملفات
scp Dockerfile docker-compose.yml docker/nginx/default.conf root@72.60.190.188:/app/
scp -r backend/ bin/ database/ config/ scripts/ start_server.py requirements-prod.txt root@72.60.190.188:/app/

# 2. أنشئ .env على الخادم
ssh root@72.60.190.188 "cd /app && cp .env.example .env && nano .env"

# 3. شغّل
ssh root@72.60.190.188 "cd /app && docker compose up -d --build"
```

## تحديث deps بعد إضافة مكتبات
```bash
pip freeze > requirements-frozen.txt
```

## مراقبة
```bash
ssh root@72.60.190.188 "cd /app && docker compose ps"
ssh root@72.60.190.188 "cd /app && docker compose logs api --tail 50"
ssh root@72.60.190.188 "curl http://localhost:3002/admin/system/health"
```

## إعادة تشغيل
```bash
ssh root@72.60.190.188 "cd /app && docker compose restart api"
```
