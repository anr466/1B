"""
🔐 خدمة المصادقة الموحدة - مرجع واحد فقط لجميع عمليات المصادقة
يستخدمها جميع الـ endpoints (Flask و FastAPI)
"""

import hashlib
import time
import jwt
import os
from typing import Dict, Optional, Tuple

# استيراد قاعدة البيانات
from backend.infrastructure.db_access import get_db_manager

# استيراد bcrypt للأمان الأفضل
try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

# استيراد JWT - إجباري من البيئة
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError(
        "❌ JWT_SECRET_KEY environment variable is required for production"
    )
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY = 3600  # ساعة واحدة
REFRESH_TOKEN_EXPIRY = 604800  # 7 أيام


class AuthService:
    """خدمة المصادقة الموحدة"""

    def __init__(self):
        self.db = get_db_manager()

    # ==================== دوال مساعدة للتجزئة ====================

    def _hash_password(self, password: str) -> str:
        """
        تجزئة كلمة المرور باستخدام bcrypt (أو SHA256 كبديل)
        ✅ bcrypt: آمن جداً (slow hash)
        ⚠️ SHA256: للتوافق مع كلمات المرور القديمة
        """
        if BCRYPT_AVAILABLE:
            # استخدام bcrypt للأمان الأفضل
            salt = bcrypt.gensalt(rounds=12)
            return bcrypt.hashpw(password.encode(), salt).decode()
        else:
            # fallback إلى SHA256 إذا لم يكن bcrypt متوفراً
            return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        التحقق من كلمة المرور مع دعم كلا النوعين
        ✅ يدعم bcrypt و SHA256
        ✅ backward compatible مع كلمات المرور القديمة
        """
        if BCRYPT_AVAILABLE and password_hash.startswith("$2b$"):
            # bcrypt hash
            try:
                return bcrypt.checkpw(password.encode(), password_hash.encode())
            except Exception:
                return False
        else:
            # SHA256 hash (قديم)
            sha256_hash = hashlib.sha256(password.encode()).hexdigest()
            return sha256_hash == password_hash

    def _should_upgrade_password_hash(self, password_hash: str) -> bool:
        """
        فحص إذا كانت كلمة المرور تحتاج تحديث من SHA256 إلى bcrypt
        """
        if not BCRYPT_AVAILABLE:
            return False
        # إذا كانت SHA256 (64 حرف hex)، تحتاج تحديث
        return len(password_hash) == 64 and not password_hash.startswith("$2b$")

    # ==================== تسجيل الدخول ====================

    def login(
        self, username: str, password: str, device_id: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        تسجيل دخول المستخدم

        Returns:
            (success, data)
            data = {
                'access_token': str,
                'refresh_token': str,
                'user': {...}
            }
        """
        try:
            # التحقق من البيانات
            if not username or not password:
                return False, {"error": "اسم المستخدم وكلمة المرور مطلوبان"}

            # البحث عن المستخدم
            user = self._get_user_by_username(username)
            if not user:
                return False, {"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}

            # التحقق من كلمة المرور (يدعم bcrypt و SHA256)
            if not self._verify_password(password, user["password_hash"]):
                return False, {"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}

            # ✅ تحديث كلمة المرور من SHA256 إلى bcrypt (تدريجي)
            if self._should_upgrade_password_hash(user["password_hash"]):
                try:
                    new_hash = self._hash_password(password)
                    self._update_password_hash(user["id"], new_hash)
                except Exception:
                    # لا نوقف تسجيل الدخول إذا فشل التحديث
                    pass

            # توليد tokens
            tokens = self._generate_tokens(
                user["id"], user["username"], user["user_type"]
            )

            # تحديث آخر تسجيل دخول
            self._update_last_login(user["id"], device_id)

            return True, {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "user_type": user["user_type"],
                },
            }

        except Exception as e:
            return False, {"error": f"خطأ في تسجيل الدخول: {str(e)}"}

    # ==================== التسجيل ====================

    def register(
        self,
        username: str,
        password: str,
        email: str,
        phone_number: Optional[str] = None,
    ) -> Tuple[bool, Dict]:
        """
        تسجيل مستخدم جديد

        Returns:
            (success, data)
        """
        try:
            # التحقق من البيانات
            if not username or not password or not email:
                return False, {"error": "جميع الحقول مطلوبة"}

            # التحقق من عدم وجود المستخدم
            if self._get_user_by_username(username) or self._get_user_by_email(email):
                return False, {"error": "المستخدم موجود مسبقاً"}

            # تشفير كلمة المرور باستخدام bcrypt (آمن)
            password_hash = self._hash_password(password)

            # إنشاء المستخدم
            user_id = self._create_user(username, password_hash, email, phone_number)
            if not user_id:
                return False, {"error": "فشل في إنشاء المستخدم"}

            # توليد tokens
            tokens = self._generate_tokens(user_id, username, "user")

            return True, {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "user_type": "user",
                },
            }

        except Exception as e:
            return False, {"error": f"خطأ في التسجيل: {str(e)}"}

    # ==================== تحديث Token ====================

    def refresh_token(self, refresh_token: str) -> Tuple[bool, Dict]:
        """
        تحديث Access Token باستخدام Refresh Token

        Returns:
            (success, data)
        """
        try:
            # التحقق من الـ token
            payload = self._verify_token(refresh_token, token_type="refresh")
            if not payload:
                return False, {"error": "Refresh token غير صالح"}

            # إنشاء access token جديد
            user_id = payload["user_id"]
            username = payload["username"]
            user_type = payload.get("user_type", "user")

            tokens = self._generate_tokens(user_id, username, user_type)

            return True, {
                "access_token": tokens["access_token"],
                "expires_in": ACCESS_TOKEN_EXPIRY,
            }

        except Exception as e:
            return False, {"error": f"خطأ في تحديث الـ token: {str(e)}"}

    # ==================== التحقق من Token ====================

    def verify_token(self, token: str) -> Tuple[bool, Dict]:
        """
        التحقق من صحة Access Token

        Returns:
            (success, payload)
        """
        try:
            payload = self._verify_token(token, token_type="access")
            if not payload:
                return False, {"error": "Token غير صالح"}

            return True, payload

        except Exception as e:
            return False, {"error": f"خطأ في التحقق: {str(e)}"}

    # ==================== تسجيل الخروج ====================

    def logout(self, user_id: int) -> Tuple[bool, Dict]:
        """تسجيل خروج المستخدم"""
        try:
            # في نظام JWT stateless، لا نحتاج لفعل شيء
            # يمكن إضافة token blacklist في المستقبل
            return True, {"message": "تم تسجيل الخروج بنجاح"}

        except Exception as e:
            return False, {"error": f"خطأ في تسجيل الخروج: {str(e)}"}

    # ==================== حذف الحساب ====================

    def delete_account(self, user_id: int, password: str) -> Tuple[bool, Dict]:
        """حذف حساب المستخدم نهائياً"""
        try:
            # الحصول على المستخدم
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT password_hash, username FROM users WHERE id = %s",
                    (user_id,),
                )
                user = cursor.fetchone()

                if not user:
                    return False, {"error": "المستخدم غير موجود"}

                # التحقق من كلمة المرور
                if not self._verify_password(password, user["password_hash"]):
                    return False, {"error": "كلمة المرور غير صحيحة"}

                # منع حذف حساب الأدمن الرئيسي
                if user["username"] == "admin_user":
                    return False, {"error": "لا يمكن حذف حساب الأدمن الرئيسي"}

                # حذف المستخدم (CASCADE سيحذف جميع البيانات)
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

            return True, {"message": "تم حذف حسابك نهائياً"}

        except Exception as e:
            return False, {"error": f"خطأ في حذف الحساب: {str(e)}"}

    # ==================== دوال مساعدة خاصة ====================

    def _get_user_by_username(self, username: str) -> Optional[Dict]:
        """الحصول على المستخدم من خلال اسم المستخدم"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, username, email, password_hash, user_type FROM users WHERE username = %s",
                    (username,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "username": row[1],
                        "email": row[2],
                        "password_hash": row[3],
                        "user_type": row[4],
                    }
                return None
        except Exception:
            return None

    def _get_user_by_email(self, email: str) -> Optional[Dict]:
        """الحصول على المستخدم من خلال البريد الإلكتروني"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, username, email, password_hash, user_type FROM users WHERE email = %s",
                    (email.lower(),),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "username": row[1],
                        "email": row[2],
                        "password_hash": row[3],
                        "user_type": row[4],
                    }
                return None
        except Exception:
            return None

    def _create_user(
        self,
        username: str,
        password_hash: str,
        email: str,
        phone_number: Optional[str] = None,
    ) -> Optional[int]:
        """إنشاء مستخدم جديد"""
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, phone_number, user_type, created_at)
                    VALUES (%s, %s, %s, %s, 'user', CURRENT_TIMESTAMP)
                    RETURNING id
                """,
                    (username, email.lower(), password_hash, phone_number),
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def _update_password_hash(self, user_id: int, new_hash: str) -> bool:
        """تحديث كلمة المرور المشفرة (للترقية من SHA256 إلى bcrypt)"""
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (new_hash, user_id),
                )
                return True
        except Exception:
            return False

    def _update_last_login(self, user_id: int, device_id: Optional[str] = None):
        """تحديث آخر تسجيل دخول"""
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (user_id,),
                )
        except Exception:
            pass

    def _generate_tokens(
        self, user_id: int, username: str, user_type: str
    ) -> Dict[str, str]:
        """توليد Access و Refresh tokens"""
        now = time.time()

        # Access Token
        access_payload = {
            "user_id": user_id,
            "username": username,
            "user_type": user_type,
            "type": "access",
            "iat": now,
            "exp": now + ACCESS_TOKEN_EXPIRY,
        }
        access_token = jwt.encode(
            access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
        )

        # Refresh Token
        refresh_payload = {
            "user_id": user_id,
            "username": username,
            "user_type": user_type,
            "type": "refresh",
            "iat": now,
            "exp": now + REFRESH_TOKEN_EXPIRY,
        }
        refresh_token = jwt.encode(
            refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
        )

        return {"access_token": access_token, "refresh_token": refresh_token}

    def _verify_token(self, token: str, token_type: str = "access") -> Optional[Dict]:
        """التحقق من صحة الـ token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            # التحقق من نوع الـ token
            if payload.get("type") != token_type:
                return None

            return payload
        except Exception:
            return None


# إنشاء instance عام
auth_service = AuthService()
