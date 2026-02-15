#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified User Lookup Service - خدمة موحدة للبحث عن المستخدمين
Consolidates all user lookup functions from multiple endpoints
"""

from typing import Optional, Dict
import logging
import sys
from pathlib import Path

# ✅ FIX: إضافة استيراد DatabaseManager
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

def get_user_by_email(email: str) -> Optional[Dict]:
    """
    البحث عن مستخدم بالإيميل
    
    Args:
        email: البريد الإلكتروني
        
    Returns:
        dict مع بيانات المستخدم أو None
    """
    try:
        # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, username, email, password_hash, email_verified, 
                          user_type, phone_number 
                   FROM users 
                   WHERE LOWER(email) = LOWER(?)""",
                (email,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'password_hash': row[3],
                    'email_verified': row[4],
                    'user_type': row[5],
                    'phone_number': row[6]
                }
            return None
    except Exception as e:
        logger.error(f"❌ خطأ في البحث عن المستخدم بالإيميل: {e}")
        return None


def get_user_by_username(username: str) -> Optional[Dict]:
    """
    البحث عن مستخدم باسم المستخدم
    
    Args:
        username: اسم المستخدم
        
    Returns:
        dict مع بيانات المستخدم أو None
    """
    try:
        # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, username, email, password_hash, email_verified, 
                          user_type, phone_number 
                   FROM users 
                   WHERE username = ?""",
                (username,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'password_hash': row[3],
                    'email_verified': row[4],
                    'user_type': row[5],
                    'phone_number': row[6]
                }
            return None
    except Exception as e:
        logger.error(f"❌ خطأ في البحث عن المستخدم باسم المستخدم: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """
    البحث عن مستخدم بالـ ID
    
    Args:
        user_id: معرف المستخدم
        
    Returns:
        dict مع بيانات المستخدم أو None
    """
    try:
        # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, username, email, password_hash, email_verified, 
                          user_type, phone_number 
               FROM users 
               WHERE id = ?""",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'password_hash': row[3],
                    'email_verified': row[4],
                    'user_type': row[5],
                    'phone_number': row[6]
                }
            return None
    except Exception as e:
        logger.error(f"❌ خطأ في البحث عن المستخدم بالـ ID: {e}")
        return None


def get_user_by_identifier(identifier: str) -> Optional[Dict]:
    """
    البحث عن مستخدم بالإيميل أو اسم المستخدم
    يجرب البحث بالإيميل أولاً ثم اسم المستخدم
    
    Args:
        identifier: الإيميل أو اسم المستخدم
        
    Returns:
        dict مع بيانات المستخدم أو None
    """
    # محاولة البحث بالإيميل أولاً
    user = get_user_by_email(identifier)
    if user:
        return user
    
    # إذا لم يُعثر عليه، محاولة البحث باسم المستخدم
    user = get_user_by_username(identifier)
    return user
