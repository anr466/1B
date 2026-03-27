"""
✅ Phase 2.3: Pydantic Schemas للـ Request Validation
=====================================================

جميع الـ Request/Response models للـ API endpoints

الميزات:
- Validation تلقائي
- رسائل خطأ واضحة بالعربي
- Type hints
- Documentation تلقائي في Swagger
"""

from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================================
# Enums
# ============================================================


class TradingStatus(str, Enum):
    """حالة الصفقة"""

    ALL = "all"
    OPEN = "open"
    CLOSED = "closed"


class TradingMode(str, Enum):
    """وضع التداول - الأدمن يمكنه Demo, المستخدمون Real فقط"""

    AUTO = "auto"
    DEMO = "demo"
    REAL = "real"


class RiskLevel(str, Enum):
    """مستوى المخاطرة"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AGGRESSIVE = "aggressive"


class UserType(str, Enum):
    """نوع المستخدم"""

    USER = "user"
    ADMIN = "admin"


# ============================================================
# Authentication Schemas
# ============================================================


class LoginRequest(BaseModel):
    """طلب تسجيل الدخول"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="اسم المستخدم أو البريد الإلكتروني",
    )
    password: str = Field(..., min_length=8, description="كلمة المرور")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "user@example.com",
                "password": "secure_password123",
            }
        }


class RegisterRequest(BaseModel):
    """طلب التسجيل"""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr = Field(..., description="البريد الإلكتروني")
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=200)

    @validator("username")
    def username_alphanumeric(cls, v):
        if not v.replace("_", "").replace(".", "").replace("@", "").isalnum():
            raise ValueError("اسم المستخدم يجب أن يحتوي على حروف وأرقام فقط")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "username": "newuser",
                "email": "user@example.com",
                "password": "secure_password123",
                "full_name": "John Doe",
            }
        }


class ChangePasswordRequest(BaseModel):
    """طلب تغيير كلمة المرور"""

    user_id: int = Field(..., gt=0)
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator("new_password")
    def passwords_different(cls, v, values):
        if "current_password" in values and v == values["current_password"]:
            raise ValueError(
                "كلمة المرور الجديدة يجب أن تكون مختلفة عن القديمة"
            )
        return v


# ============================================================
# User Settings Schemas
# ============================================================


class UserSettingsUpdate(BaseModel):
    """تحديث إعدادات المستخدم"""

    trading_enabled: Optional[bool] = Field(
        None, description="تفعيل/تعطيل التداول"
    )
    max_trade_amount: Optional[float] = Field(
        None,
        ge=5.0,
        le=10000.0,
        description="حد أقصى لمبلغ الصفقة (5-10000 USDT)",
    )
    risk_level: Optional[RiskLevel] = Field(None, description="مستوى المخاطرة")
    stop_loss_percentage: Optional[float] = Field(
        None, ge=0.5, le=50.0, description="نسبة وقف الخسارة (0.5-50%)"
    )
    take_profit_percentage: Optional[float] = Field(
        None, ge=1.0, le=100.0, description="نسبة جني الربح (1-100%)"
    )
    max_open_trades: Optional[int] = Field(
        None, ge=1, le=50, description="عدد الصفقات المفتوحة المسموح (1-50)"
    )
    trading_mode: Optional[TradingMode] = Field(
        None, description="وضع التداول"
    )
    max_daily_loss_pct: Optional[float] = Field(
        None, ge=1.0, le=50.0, description="حد الخسارة اليومية (1-50%)"
    )

    @validator("take_profit_percentage")
    def take_profit_greater_than_stop_loss(cls, v, values):
        if (
            "stop_loss_percentage" in values
            and values["stop_loss_percentage"] is not None
        ):
            if v <= values["stop_loss_percentage"]:
                raise ValueError(
                    "نسبة جني الربح يجب أن تكون أكبر من نسبة وقف الخسارة"
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "trading_enabled": True,
                "max_trade_amount": 100.0,
                "risk_level": "medium",
                "stop_loss_percentage": 3.0,
                "take_profit_percentage": 6.0,
                "max_open_trades": 5,
                "trading_mode": "medium",
                "max_daily_loss_pct": 10.0,
            }
        }


# ============================================================
# Binance Keys Schemas
# ============================================================


class BinanceKeysCreate(BaseModel):
    """إضافة مفاتيح Binance"""

    user_id: int = Field(..., gt=0)
    api_key: str = Field(
        ..., min_length=20, max_length=200, description="Binance API Key"
    )
    api_secret: str = Field(
        ..., min_length=20, max_length=200, description="Binance API Secret"
    )

    @validator("api_key", "api_secret")
    def validate_key_format(cls, v):
        if not v or v.isspace():
            raise ValueError("المفتاح لا يمكن أن يكون فارغاً")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "api_key": "your_binance_api_key_here",
                "api_secret": "your_binance_api_secret_here",
            }
        }


# ============================================================
# Trades Schemas
# ============================================================


class TradesQueryParams(BaseModel):
    """معاملات استعلام الصفقات"""

    page: Optional[int] = Field(1, ge=1, description="رقم الصفحة")
    limit: Optional[int] = Field(
        50, ge=1, le=200, description="عدد النتائج (حد أقصى 200)"
    )
    status: Optional[TradingStatus] = Field(
        TradingStatus.ALL, description="حالة الصفقة"
    )
    date_from: Optional[str] = Field(
        None, description="من تاريخ (ISO format: 2025-01-01)"
    )
    date_to: Optional[str] = Field(
        None, description="إلى تاريخ (ISO format: 2025-12-31)"
    )

    @validator("date_from", "date_to")
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise ValueError(
                    "صيغة التاريخ غير صحيحة - استخدم ISO format (YYYY-MM-DD)"
                )
        return v

    @validator("date_to")
    def date_to_after_date_from(cls, v, values):
        if (
            v is not None
            and "date_from" in values
            and values["date_from"] is not None
        ):
            if v < values["date_from"]:
                raise ValueError("تاريخ النهاية يجب أن يكون بعد تاريخ البداية")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "limit": 50,
                "status": "closed",
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            }
        }


# ============================================================
# Profile Schemas
# ============================================================


class ProfileUpdate(BaseModel):
    """تحديث الملف الشخصي"""

    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)

    @validator("phone")
    def validate_phone(cls, v):
        if v is not None:
            # Remove spaces and special characters
            cleaned = "".join(filter(str.isdigit, v))
            if len(cleaned) < 10 or len(cleaned) > 15:
                raise ValueError("رقم الهاتف يجب أن يكون بين 10-15 رقم")
        return v


# ============================================================
# Notification Settings Schemas
# ============================================================


class NotificationSettingsUpdate(BaseModel):
    """تحديث إعدادات الإشعارات"""

    trade_opened: Optional[bool] = Field(
        None, description="إشعار عند فتح صفقة"
    )
    trade_closed: Optional[bool] = Field(
        None, description="إشعار عند إغلاق صفقة"
    )
    profit_alert: Optional[bool] = Field(
        None, description="إشعار عند تحقيق ربح"
    )
    loss_alert: Optional[bool] = Field(None, description="إشعار عند خسارة")
    low_balance: Optional[bool] = Field(
        None, description="إشعار عند انخفاض الرصيد"
    )
    system_alerts: Optional[bool] = Field(None, description="إشعارات النظام")
    daily_summary: Optional[bool] = Field(None, description="ملخص يومي")
    weekly_summary: Optional[bool] = Field(None, description="ملخص أسبوعي")

    class Config:
        json_schema_extra = {
            "example": {
                "trade_opened": True,
                "trade_closed": True,
                "profit_alert": True,
                "loss_alert": True,
                "low_balance": True,
                "system_alerts": False,
                "daily_summary": True,
                "weekly_summary": False,
            }
        }


# ============================================================
# Admin Schemas
# ============================================================


class ActivityLogsQueryParams(BaseModel):
    """معاملات استعلام سجل النشاطات (Admin)"""

    page: Optional[int] = Field(1, ge=1)
    limit: Optional[int] = Field(50, ge=1, le=200)
    user_id: Optional[int] = Field(None, ge=1)
    action: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, pattern="^(success|failed)$")
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    @validator("date_from", "date_to")
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise ValueError("صيغة التاريخ غير صحيحة")
        return v


class UserManagementUpdate(BaseModel):
    """تحديث بيانات مستخدم (Admin)"""

    is_active: Optional[bool] = None
    user_type: Optional[UserType] = None
    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None


# ============================================================
# Response Schemas (للتوثيق فقط)
# ============================================================


class StandardResponse(BaseModel):
    """استجابة قياسية"""

    success: bool
    timestamp: str
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel):
    """استجابة مع Pagination"""

    success: bool
    data: Dict[str, Any]
    timestamp: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "items": [],
                    "pagination": {
                        "total": 100,
                        "page": 1,
                        "limit": 50,
                        "pages": 2,
                        "has_next": True,
                        "has_prev": False,
                    },
                },
                "timestamp": "2025-10-30T06:00:00",
            }
        }


class ErrorResponse(BaseModel):
    """استجابة خطأ"""

    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "بيانات غير صحيحة",
                "error_code": "INVALID_INPUT",
                "timestamp": "2025-10-30T06:00:00",
            }
        }


# ============================================================
# Validation Helper Functions
# ============================================================


def validate_user_id(user_id: int) -> int:
    """التحقق من صحة user_id"""
    if user_id <= 0:
        raise ValueError("معرف المستخدم يجب أن يكون أكبر من صفر")
    return user_id


def validate_pagination_params(page: int, limit: int) -> tuple:
    """التحقق من صحة معاملات Pagination"""
    if page < 1:
        page = 1
    if limit < 1:
        limit = 50
    if limit > 200:
        limit = 200
    return page, limit


def validate_date_range(
    date_from: Optional[str], date_to: Optional[str]
) -> tuple:
    """التحقق من صحة نطاق التاريخ"""
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from)
        except ValueError:
            raise ValueError("صيغة تاريخ البداية غير صحيحة")

    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to)
        except ValueError:
            raise ValueError("صيغة تاريخ النهاية غير صحيحة")

    if date_from and date_to:
        if date_to_obj < date_from_obj:
            raise ValueError("تاريخ النهاية يجب أن يكون بعد تاريخ البداية")

    return date_from, date_to
