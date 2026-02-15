"""
🔐 Encryption Utilities - تشفير وفك تشفير البيانات الحساسة
"""

import os
from cryptography.fernet import Fernet
from config.logging_config import get_logger

# تحميل متغيرات البيئة من .env تلقائياً
try:
    from dotenv import load_dotenv
    # البحث عن .env في المسار الصحيح
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv غير مثبت - سيستخدم متغيرات البيئة مباشرة

logger = get_logger(__name__)


class EncryptionManager:
    """مدير التشفير - يتعامل مع تشفير وفك تشفير البيانات الحساسة"""
    
    def __init__(self):
        """تهيئة مدير التشفير مع مفتاح التشفير الرئيسي من ENV"""
        self.encryption_key = os.environ.get('ENCRYPTION_KEY')
        
        if not self.encryption_key:
            # محاولة قراءة من .env مباشرة
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('ENCRYPTION_KEY='):
                            self.encryption_key = line.split('=', 1)[1].strip()
                            break
        
        if not self.encryption_key:
            # للتطوير فقط - استخدام مفتاح افتراضي (بدون تحذيرات مزعجة)
            self.encryption_key = Fernet.generate_key().decode()
            logger.debug(f"استخدام مفتاح تشفير مؤقت للتطوير")
        
        try:
            if isinstance(self.encryption_key, str):
                self.encryption_key = self.encryption_key.encode()
            
            self.cipher = Fernet(self.encryption_key)
            logger.debug("مدير التشفير تم تهيئته بنجاح")
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة مدير التشفير: {e}")
            raise
    
    def encrypt(self, plaintext: str) -> str:
        """
        تشفير نص عادي
        
        Args:
            plaintext: النص المراد تشفيره
            
        Returns:
            النص المشفر (base64 encoded)
        """
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode()
            
            ciphertext = self.cipher.encrypt(plaintext)
            return ciphertext.decode()
        except Exception as e:
            logger.error(f"❌ خطأ في تشفير البيانات: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        فك تشفير نص مشفر
        
        Args:
            ciphertext: النص المشفر
            
        Returns:
            النص الأصلي
        """
        try:
            # التحقق من أن البيانات ليست فارغة
            if not ciphertext:
                logger.debug("محاولة فك تشفير بيانات فارغة")
                return ""
            
            # التحقق من أن البيانات تبدو مشفرة (تبدأ بـ gAAAAA... عادة)
            if isinstance(ciphertext, str) and len(ciphertext) < 20:
                logger.debug(f"البيانات قصيرة جداً لتكون مشفرة: {len(ciphertext)} حرف")
                return ciphertext
            
            if isinstance(ciphertext, str):
                ciphertext = ciphertext.encode()
            
            plaintext = self.cipher.decrypt(ciphertext)
            return plaintext.decode()
        except Exception as e:
            # تقليل مستوى الـ log لتجنب الإزعاج
            logger.debug(f"فشل فك التشفير (قد تكون البيانات غير مشفرة): {type(e).__name__}")
            # إرجاع البيانات كما هي إذا فشل فك التشفير
            if isinstance(ciphertext, bytes):
                return ciphertext.decode()
            return str(ciphertext)
    
    def is_encrypted(self, text: str) -> bool:
        """
        التحقق من ما إذا كان النص مشفراً
        
        Args:
            text: النص للتحقق منه
            
        Returns:
            True إذا كان النص مشفراً، False خلاف ذلك
        """
        try:
            if isinstance(text, str):
                text = text.encode()
            self.cipher.decrypt(text)
            return True
        except Exception:
            return False


# إنشاء instance واحد من مدير التشفير
encryption_manager = EncryptionManager()


def encrypt_key(plaintext: str) -> str:
    """دالة مساعدة لتشفير المفتاح"""
    return encryption_manager.encrypt(plaintext)


def decrypt_key(ciphertext: str) -> str:
    """دالة مساعدة لفك تشفير المفتاح"""
    return encryption_manager.decrypt(ciphertext)
