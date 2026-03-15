"""
إعدادات النظام الموحدة
تحميل متغيرات البيئة وتوفير واجهة موحدة للوصول إليها
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class UnifiedSettings:
    """إعدادات النظام الموحدة"""
    
    def __init__(self):
        self.BASE_DIR = Path(__file__).parent.parent
        
        # Database
        self.DATABASE_ENGINE = os.getenv('DATABASE_ENGINE', 'postgresql').strip().lower()
        self.DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
        self.DATABASE_TIMEOUT = int(os.getenv('DATABASE_TIMEOUT', '30'))
        
        # Security
        self.JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', '')
        self.JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
        self.JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
        self.ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '')
        
        # Server
        self.SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
        self.SERVER_PORT = int(os.getenv('SERVER_PORT', '3002'))
        self.SERVER_WORKERS = int(os.getenv('SERVER_WORKERS', '4'))
        
        # Environment
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # CORS
        self.CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
        self.CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'True').lower() == 'true'
        
        # Logging
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'logs/server.log')
        self.LOG_ERROR_FILE = os.getenv('LOG_ERROR_FILE', 'logs/errors.log')
        
        # Rate Limiting
        self.RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
        self.RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
        self.RATE_LIMIT_PERIOD = int(os.getenv('RATE_LIMIT_PERIOD', '3600'))
        
        # Binance
        self.BINANCE_API_BASE_URL = os.getenv('BINANCE_API_BASE_URL', 'https://api.binance.com')
        
        # Email
        self.SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
        self.SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
        self.SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
        self.SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL', '')
        self.SMTP_ENABLED = os.getenv('SMTP_ENABLED', 'True').lower() == 'true'

settings = UnifiedSettings()

def get_database_engine():
    """الحصول على نوع قاعدة البيانات الحالية"""
    engine = (settings.DATABASE_ENGINE or 'postgresql').strip().lower()
    return engine if engine in {'postgres', 'postgresql'} else 'postgresql'

def get_database_url():
    """الحصول على رابط قاعدة البيانات إن كان مضبوطًا"""
    return (settings.DATABASE_URL or '').strip()

def get_database_path():
    """Legacy — لم يعد مستخدمًا مع PostgreSQL. يبقى لتوافق الاستيرادات القديمة."""
    return ''
