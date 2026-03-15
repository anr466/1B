"""
مدير Binance API - للتعامل مع حسابات المستخدمين الحقيقية
يوفر واجهة آمنة للتفاعل مع Binance API
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import asyncio
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "database"))
from database_manager import DatabaseManager
import hashlib
import hmac
import base64

# استيراد خدمة التشفير الموحدة
try:
    from config.security.encryption_service import decrypt_binance_keys, decrypt_text
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

class BinanceManager:
    """مدير Binance API للمستخدمين"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(__name__)
        self._clients = {}  # تخزين مؤقت للعملاء
        
    def _decrypt_api_keys(self, encrypted_key: str, encrypted_secret: str) -> tuple:
        """فك تشفير مفاتيح API باستخدام خدمة التشفير الموحدة"""
        try:
            if ENCRYPTION_AVAILABLE:
                api_key = decrypt_text(encrypted_key)
                api_secret = decrypt_text(encrypted_secret)
                return api_key, api_secret
            else:
                # Fallback: المفاتيح غير مشفرة
                return encrypted_key, encrypted_secret
        except Exception as e:
            self.logger.error(f"خطأ في فك تشفير المفاتيح: {e}")
            # محاولة إرجاع المفاتيح كما هي (ربما غير مشفرة)
            return encrypted_key, encrypted_secret
    
    def save_user_api_keys(self, user_id: int, api_key: str, api_secret: str, 
                          is_testnet: bool = True) -> bool:
        """حفظ مفاتيح API للمستخدم"""
        try:
            # تشفير المفتاح السري
            encrypted_secret = self._encrypt_api_secret(api_secret, user_id)
            
            with self.db_manager.get_write_connection() as conn:
                # حذف المفاتيح القديمة إن وجدت
                conn.execute("DELETE FROM user_binance_keys WHERE user_id = ?", (user_id,))
                
                # إدراج المفاتيح الجديدة
                conn.execute("""
                    INSERT INTO user_binance_keys 
                    (user_id, api_key, api_secret, is_testnet, is_active)
                    VALUES (?, ?, ?, ?, FALSE)
                """, (user_id, api_key, encrypted_secret, is_testnet))
                
            self.logger.info(f"تم حفظ مفاتيح API للمستخدم {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"خطأ في حفظ مفاتيح API: {e}")
            return False
    
    def verify_user_api_keys(self, user_id: int) -> Dict[str, Any]:
        """التحقق من صحة مفاتيح API للمستخدم"""
        try:
            # جلب مفاتيح المستخدم
            api_data = self.get_user_api_keys(user_id)
            if not api_data:
                return {"success": False, "message": "لا توجد مفاتيح API"}
            
            # إنشاء عميل Binance
            client = self._get_binance_client(user_id)
            if not client:
                return {"success": False, "message": "فشل في إنشاء عميل Binance"}
            
            # اختبار الاتصال
            account_info = client.get_account()
            
            # استخراج الصلاحيات
            permissions = []
            if account_info.get('canTrade'):
                permissions.append('spot')
            if account_info.get('canWithdraw'):
                permissions.append('withdraw')
            if account_info.get('canDeposit'):
                permissions.append('deposit')
            
            # تحديث بيانات التحقق
            with self.db_manager.get_write_connection() as conn:
                conn.execute("""
                    UPDATE user_binance_keys SET is_active = TRUE, 
                        permissions = ?, 
                        last_verified = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (json.dumps(permissions), user_id))
            
            # مزامنة الرصيد
            self.sync_user_balance(user_id)
            
            return {
                "success": True, 
                "message": "تم التحقق بنجاح",
                "permissions": permissions,
                "account_type": account_info.get('accountType', 'SPOT')
            }
            
        except BinanceAPIException as e:
            self.logger.error(f"خطأ Binance API: {e}")
            return {"success": False, "message": f"خطأ في API: {e.message}"}
        except Exception as e:
            self.logger.error(f"خطأ في التحقق من API: {e}")
            return {"success": False, "message": f"خطأ غير متوقع: {str(e)}"}
    
    def get_user_api_keys(self, user_id: int) -> Optional[Dict[str, Any]]:
        """جلب مفاتيح API للمستخدم"""
        try:
            with self.db_manager.get_connection() as conn:
                row = conn.execute("""
                    SELECT api_key, api_secret, is_testnet, is_active, permissions, last_verified
                    FROM user_binance_keys 
                    WHERE user_id = ?
                """, (user_id,)).fetchone()
                
                if row:
                    return {
                        'api_key': row[0],
                        'api_secret': row[1],
                        'is_testnet': bool(row[2]),
                        'is_active': bool(row[3]),
                        'permissions': json.loads(row[4]) if row[4] else [],
                        'last_verified': row[5]
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب مفاتيح API: {e}")
            return None
    
    def _get_binance_client(self, user_id: int) -> Optional[Client]:
        """إنشاء عميل Binance للمستخدم"""
        try:
            # التحقق من التخزين المؤقت
            if user_id in self._clients:
                return self._clients[user_id]
            
            # جلب مفاتيح المستخدم
            api_data = self.get_user_api_keys(user_id)
            if not api_data or not api_data['is_active']:
                return None
            
            # فك تشفير المفاتيح باستخدام خدمة التشفير الموحدة
            api_key, api_secret = self._decrypt_api_keys(
                api_data['api_key'], 
                api_data['api_secret']
            )
            
            # إنشاء العميل
            client = Client(
                api_key=api_key,
                api_secret=api_secret,
                testnet=api_data['is_testnet']
            )
            
            # حفظ في التخزين المؤقت
            self._clients[user_id] = client
            
            return client
            
        except Exception as e:
            self.logger.error(f"خطأ في إنشاء عميل Binance: {e}")
            return None
    
    def sync_user_balance(self, user_id: int) -> bool:
        """مزامنة رصيد المستخدم من Binance"""
        try:
            client = self._get_binance_client(user_id)
            if not client:
                return False
            
            # جلب معلومات الحساب
            account_info = client.get_account()
            
            with self.db_manager.get_write_connection() as conn:
                # حذف الأرصدة القديمة
                conn.execute("DELETE FROM user_binance_balance WHERE user_id = ?", (user_id,))
                
                # إدراج الأرصدة الجديدة
                for balance in account_info['balances']:
                    asset = balance['asset']
                    free = Decimal(balance['free'])
                    locked = Decimal(balance['locked'])
                    total = free + locked
                    
                    # حفظ فقط الأصول التي لها رصيد
                    if total > 0:
                        conn.execute("""
                            INSERT INTO user_binance_balance 
                            (user_id, asset, free_balance, locked_balance, total_balance)
                            VALUES (?, ?, ?, ?, ?)
                        """, (user_id, asset, float(free), float(locked), float(total)))
                
                # تحديث المحفظة المحلية بالرصيد الحقيقي
                usdt_balance = next(
                    (b for b in account_info['balances'] if b['asset'] == 'USDT'), 
                    {'free': '0', 'locked': '0'}
                )
                
                total_usdt = Decimal(usdt_balance['free']) + Decimal(usdt_balance['locked'])
                
                # تحديث أو إنشاء سجل المحفظة
                conn.execute("""
                    INSERT INTO portfolio (user_id, total_balance, available_balance, is_demo, updated_at)
                    VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, is_demo) DO UPDATE SET 
                    total_balance = excluded.total_balance, 
                    available_balance = excluded.available_balance,
                    updated_at = CURRENT_TIMESTAMP
                """, (user_id, float(total_usdt), float(total_usdt)))
            
            self.logger.info(f"تم مزامنة رصيد المستخدم {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"خطأ في مزامنة الرصيد: {e}")
            return False
    
    def execute_buy_order(self, user_id: int, symbol: str, quantity: float, 
                         order_type: str = 'MARKET', price: float = None) -> Dict[str, Any]:
        """تنفيذ أمر شراء (حقيقي أو وهمي) مع سحب البيانات الفعلية"""
        try:
            # التحقق من وضع التداول للأدمن
            if user_id == 1:  # الأدمن
                # فحص وجود مفاتيح Binance المفعلة
                if not self.is_user_api_active(user_id):
                    # تداول وهمي - لا توجد مفاتيح Binance
                    current_price = price if price else self._get_current_price(symbol)
                    return self._execute_demo_buy_order(user_id, symbol, quantity, current_price)
                # إذا كانت المفاتيح موجودة، يتم التداول الحقيقي (يكمل الكود أدناه)
            
            client = self._get_binance_client(user_id)
            if not client:
                return {"success": False, "message": "عميل Binance غير متاح"}
            
            # 🚀 الخطوة 1: تنفيذ الأمر
            self.logger.info(f"🔄 إرسال أمر شراء {symbol}: {quantity}")
            
            if order_type == 'MARKET':
                order = client.order_market_buy(
                    symbol=symbol,
                    quantity=quantity
                )
            else:
                return {"success": False, "message": "نوع الأمر غير مدعوم حالياً"}
            
            order_id = order.get('orderId')
            if not order_id:
                return {"success": False, "message": "لم يتم إرجاع order_id من Binance"}
            self.logger.info(f"✅ تم إرسال الأمر برقم: {order_id}")
            
            # 🔍 الخطوة 2: سحب بيانات الأمر الفعلية من Binance
            actual_order_data = self._fetch_real_order_data(client, symbol, order_id)
            
            if not actual_order_data:
                return {
                    "success": False,
                    "message": "فشل تأكيد تنفيذ الأمر من Binance بعد الانتظار"
                }

            # استخدام البيانات الحقيقية حصراً (لا fallback)
            final_order_data = actual_order_data
            self.logger.info(f"📊 تم سحب البيانات الحقيقية للأمر {order_id}")

            if not final_order_data.get('orderId'):
                return {
                    "success": False,
                    "message": "لا يوجد order_id في بيانات الأمر المؤكدة"
                }
            
            # 🗄️ الخطوة 3: حفظ البيانات الحقيقية في قاعدة البيانات
            self._save_real_binance_order(user_id, final_order_data)
            
            # 💰 الخطوة 4: مزامنة الرصيد الحقيقي
            self.sync_user_balance(user_id)
            
            return {
                "success": True,
                "order_id": final_order_data['orderId'],
                "symbol": final_order_data['symbol'],
                "side": final_order_data['side'],
                "quantity": final_order_data['executedQty'],
                "price": self._calculate_average_price(final_order_data),
                "status": final_order_data['status'],
                "commission": self._calculate_total_commission(final_order_data),
                "data_source": "binance_api"  # مصدر البيانات
            }
            
        except BinanceOrderException as e:
            self.logger.error(f"❌ خطأ في تنفيذ الأمر: {e}")
            return {"success": False, "message": f"خطأ في الأمر: {e.message}"}
        except Exception as e:
            self.logger.error(f"❌ خطأ غير متوقع في التنفيذ: {e}")
            return {"success": False, "message": f"خطأ غير متوقع: {str(e)}"}
    
    def execute_sell_order(self, user_id: int, symbol: str, quantity: float,
                          order_type: str = 'MARKET') -> Dict[str, Any]:
        """تنفيذ أمر بيع (حقيقي أو وهمي) مع سحب البيانات الفعلية"""
        try:
            # التحقق من وضع التداول للأدمن
            if user_id == 1:  # الأدمن
                # فحص وجود مفاتيح Binance المفعلة
                if not self.is_user_api_active(user_id):
                    # تداول وهمي - لا توجد مفاتيح Binance
                    return self._execute_demo_sell_order(user_id, symbol, quantity)
                # إذا كانت المفاتيح موجودة، يتم التداول الحقيقي (يكمل الكود أدناه)
            
            client = self._get_binance_client(user_id)
            if not client:
                return {"success": False, "message": "عميل Binance غير متاح"}
            
            # 🚀 الخطوة 1: تنفيذ أمر البيع
            self.logger.info(f"🔄 إرسال أمر بيع {symbol}: {quantity}")
            
            if order_type == 'MARKET':
                order = client.order_market_sell(
                    symbol=symbol,
                    quantity=quantity
                )
            else:
                return {"success": False, "message": "نوع الأمر غير مدعوم حالياً"}
            
            order_id = order.get('orderId')
            if not order_id:
                return {"success": False, "message": "لم يتم إرجاع order_id من Binance"}
            self.logger.info(f"✅ تم إرسال أمر البيع برقم: {order_id}")
            
            # 🔍 الخطوة 2: سحب بيانات الأمر الفعلية
            actual_order_data = self._fetch_real_order_data(client, symbol, order_id)
            
            if not actual_order_data:
                return {
                    "success": False,
                    "message": "فشل تأكيد تنفيذ أمر البيع من Binance بعد الانتظار"
                }

            final_order_data = actual_order_data
            self.logger.info(f"📊 تم سحب بيانات البيع الحقيقية للأمر {order_id}")

            if not final_order_data.get('orderId'):
                return {
                    "success": False,
                    "message": "لا يوجد order_id في بيانات أمر البيع المؤكدة"
                }
            
            # 🗄️ الخطوة 3: حفظ بيانات البيع الحقيقية
            self._save_real_binance_order(user_id, final_order_data)
            
            # 💰 الخطوة 4: مزامنة الرصيد
            self.sync_user_balance(user_id)
            
            return {
                "success": True,
                "order_id": final_order_data['orderId'],
                "symbol": final_order_data['symbol'],
                "side": final_order_data['side'],
                "quantity": final_order_data['executedQty'],
                "price": self._calculate_average_price(final_order_data),
                "status": final_order_data['status'],
                "commission": self._calculate_total_commission(final_order_data),
                "data_source": "binance_api"
            }
            
        except BinanceOrderException as e:
            self.logger.error(f"❌ خطأ في تنفيذ أمر البيع: {e}")
            return {"success": False, "message": f"خطأ في الأمر: {e.message}"}
        except Exception as e:
            self.logger.error(f"❌ خطأ غير متوقع في بيع: {e}")
            return {"success": False, "message": f"خطأ غير متوقع: {str(e)}"}
    
    def _fetch_real_order_data(self, client, symbol: str, order_id: str) -> Dict[str, Any]:
        """سحب بيانات الأمر الحقيقية من Binance مع انتظار قصير للتأكيد"""
        try:
            import time

            max_attempts = 5
            for attempt in range(1, max_attempts + 1):
                time.sleep(1)

                order_data = client.get_order(symbol=symbol, orderId=order_id)
                if not isinstance(order_data, dict):
                    continue

                fetched_order_id = order_data.get('orderId')
                executed_qty = float(order_data.get('executedQty', 0) or 0)
                status = str(order_data.get('status', '')).upper()

                if fetched_order_id and executed_qty > 0 and status in ['FILLED', 'PARTIALLY_FILLED']:
                    self.logger.info(
                        f"🔍 تم تأكيد الأمر {order_id} من Binance "
                        f"(status={status}, executedQty={executed_qty})"
                    )
                    return order_data

                self.logger.debug(
                    f"⏳ انتظار تأكيد الأمر {order_id} "
                    f"(attempt={attempt}/{max_attempts}, status={status}, executedQty={executed_qty})"
                )

            self.logger.error(f"❌ تعذر تأكيد تنفيذ الأمر {order_id} بعد {max_attempts} محاولات")
            return None
            
        except Exception as e:
            self.logger.error(f"⚠️ خطأ في سحب بيانات الأمر {order_id}: {e}")
            return None
    
    def _calculate_average_price(self, order: Dict[str, Any]) -> float:
        """حساب السعر المتوسط الحقيقي"""
        try:
            if order.get('fills'):
                total_qty = sum(float(fill['qty']) for fill in order['fills'])
                if total_qty > 0:
                    weighted_price = sum(float(fill['price']) * float(fill['qty']) for fill in order['fills'])
                    return weighted_price / total_qty
            return float(order.get('price', 0))
        except Exception:
            return 0.0
    
    def _calculate_total_commission(self, order: Dict[str, Any]) -> float:
        """حساب إجمالي العمولة الحقيقية"""
        try:
            total_commission = 0.0
            if order.get('fills'):
                for fill in order['fills']:
                    commission = float(fill.get('commission', 0))
                    total_commission += commission
            return total_commission
        except Exception:
            return 0.0
    
    def _save_real_binance_order(self, user_id: int, order: Dict[str, Any]) -> None:
        """حفظ أمر Binance الحقيقي في قاعدة البيانات"""
        try:
            with self.db_manager.get_write_connection() as conn:
                # حساب البيانات الحقيقية
                avg_price = self._calculate_average_price(order)
                total_commission = self._calculate_total_commission(order)
                
                conn.execute("""
                    INSERT INTO user_binance_orders 
                    (user_id, binance_order_id, symbol, side, type, quantity, 
                     price, status, executed_qty, executed_price, commission)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    order['orderId'],
                    order['symbol'],
                    order['side'],
                    order['type'],
                    float(order['origQty']),
                    float(order.get('price', 0)),
                    order['status'],
                    float(order['executedQty']),
                    avg_price,  # السعر المتوسط الحقيقي
                    total_commission  # العمولة الحقيقية
                ))
                
                self.logger.info(f"🗄️ تم حفظ أمر حقيقي {order['symbol']} - {order['side']} برقم {order['orderId']}")
                self.logger.info(f"💰 السعر المتوسط: {avg_price:.8f} | العمولة: {total_commission:.8f}")
                
        except Exception as e:
            self.logger.error(f"❌ خطأ في حفظ الأمر الحقيقي: {e}")
    
    def _save_binance_order(self, user_id: int, order: Dict[str, Any], is_demo: bool = False) -> None:
        """حفظ أمر Binance في قاعدة البيانات (للوهمي فقط)"""
        try:
            with self.db_manager.get_write_connection() as conn:
                # حساب السعر المتوسط
                avg_price = 0.0
                if order.get('fills'):
                    total_qty = sum(float(fill['qty']) for fill in order['fills'])
                    if total_qty > 0:
                        weighted_price = sum(float(fill['price']) * float(fill['qty']) for fill in order['fills'])
                        avg_price = weighted_price / total_qty
                else:
                    avg_price = float(order.get('price', 0))
                
                conn.execute("""
                    INSERT INTO user_binance_orders 
                    (user_id, binance_order_id, symbol, side, type, quantity, 
                     price, status, executed_qty, executed_price, commission)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    order['orderId'],
                    order['symbol'],
                    order['side'],
                    order['type'],
                    float(order['origQty']),
                    float(order.get('price', 0)),
                    order['status'],
                    float(order['executedQty']),
                    avg_price,
                    0.0  # عمولة وهمية للحساب الوهمي
                ))
                
                # تسجيل نوع الأمر (حقيقي أو وهمي)
                order_type = "وهمي" if is_demo else "حقيقي"
                self.logger.info(f"تم حفظ أمر {order_type} {order['symbol']} - {order['side']} برقم {order['orderId']}")
                
        except Exception as e:
            self.logger.error(f"خطأ في حفظ الأمر: {e}")
    
    def get_user_real_balance(self, user_id: int) -> Dict[str, Any]:
        """جلب الرصيد الحقيقي للمستخدم"""
        try:
            with self.db_manager.get_connection() as conn:
                balances = conn.execute("""
                    SELECT asset, free_balance, locked_balance, total_balance, updated_at
                    FROM user_binance_balance 
                    WHERE user_id = ?
                    ORDER BY total_balance DESC
                """, (user_id,)).fetchall()
                
                balance_list = []
                total_usdt = 0
                
                for balance in balances:
                    balance_data = {
                        'asset': balance[0],
                        'free': balance[1],
                        'locked': balance[2],
                        'total': balance[3],
                        'last_sync': balance[4]
                    }
                    balance_list.append(balance_data)
                    
                    if balance[0] == 'USDT':
                        total_usdt = balance[3]
                
                return {
                    "success": True,
                    "balances": balance_list,
                    "total_usdt": total_usdt
                }
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب الرصيد: {e}")
            return {"success": False, "message": str(e)}
    
    def _execute_demo_buy_order(self, user_id: int, symbol: str, quantity: float, price: float) -> Dict[str, Any]:
        """تنفيذ أمر شراء وهمي"""
        try:
            from datetime import datetime
            import uuid
            
            # إنشاء رقم أمر وهمي
            demo_order_id = f"DEMO_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            
            # محاكاة استجابة Binance
            demo_order = {
                'symbol': symbol,
                'orderId': demo_order_id,
                'orderListId': -1,
                'clientOrderId': f"demo_{uuid.uuid4().hex[:16]}",
                'transactTime': int(datetime.now().timestamp() * 1000),
                'price': str(price) if price else '0.00000000',
                'origQty': str(quantity),
                'executedQty': str(quantity),
                'cummulativeQuoteQty': str(quantity * price) if price else '0.00000000',
                'status': 'FILLED',
                'timeInForce': 'GTC',
                'type': 'MARKET',
                'side': 'BUY',
                'fills': [{
                    'price': str(price) if price else '0.00000000',
                    'qty': str(quantity),
                    'commission': '0.00000000',
                    'commissionAsset': 'BNB'
                }]
            }
            
            # حفظ الأمر الوهمي في قاعدة البيانات
            self._save_binance_order(user_id, demo_order, is_demo=True)
            
            self.logger.info(f"تم تنفيذ أمر شراء وهمي {symbol}: {quantity} بسعر {price}")
            
            return {
                "success": True,
                "order": demo_order,
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "total_amount": quantity * price if price else 0,
                "order_type": "virtual",
                "message": "تم تنفيذ أمر شراء وهمي بنجاح"
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تنفيذ أمر شراء وهمي: {e}")
            return {"success": False, "message": str(e)}
    
    def _execute_demo_sell_order(self, user_id: int, symbol: str, quantity: float) -> Dict[str, Any]:
        """تنفيذ أمر بيع وهمي"""
        try:
            from datetime import datetime
            import uuid
            
            # جلب السعر الحالي
            current_price = self._get_current_price(symbol)
            if not current_price:
                return {"success": False, "message": f"لا يمكن جلب سعر {symbol}"}
            
            # إنشاء رقم أمر وهمي
            demo_order_id = f"DEMO_SELL_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            
            # محاكاة استجابة Binance للبيع
            demo_order = {
                'symbol': symbol,
                'orderId': demo_order_id,
                'orderListId': -1,
                'clientOrderId': f"demo_sell_{uuid.uuid4().hex[:16]}",
                'transactTime': int(datetime.now().timestamp() * 1000),
                'price': str(current_price),
                'origQty': str(quantity),
                'executedQty': str(quantity),
                'cummulativeQuoteQty': str(quantity * current_price),
                'status': 'FILLED',
                'timeInForce': 'GTC',
                'type': 'MARKET',
                'side': 'SELL',
                'fills': [{
                    'price': str(current_price),
                    'qty': str(quantity),
                    'commission': '0.00000000',
                    'commissionAsset': 'USDT',
                    'tradeId': int(datetime.now().timestamp())
                }]
            }
            
            # حفظ أمر البيع الوهمي
            self._save_binance_order(user_id, demo_order, is_demo=True)
            
            self.logger.info(f"تم تنفيذ أمر بيع وهمي {symbol}: {quantity} بسعر {current_price}")
            
            return {
                "success": True,
                "order_id": demo_order_id,
                "symbol": symbol,
                "quantity": quantity,
                "price": current_price,
                "total_amount": quantity * current_price,
                "order_type": "virtual",
                "message": "تم تنفيذ أمر بيع وهمي بنجاح"
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تنفيذ أمر بيع وهمي: {e}")
            return {"success": False, "message": str(e)}
    
    def _get_current_price(self, symbol: str) -> float:
        """جلب السعر الحالي للرمز من Binance"""
        try:
            # استخدام عميل عام لجلب السعر
            from binance.client import Client
            client = Client()
            ticker = client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            self.logger.error(f"خطأ في جلب سعر {symbol}: {e}")
            # إرجاع سعر افتراضي للاختبار
            if symbol == 'BTCUSDT':
                return 95000.0
            elif symbol == 'ETHUSDT':
                return 3400.0
            else:
                return 1.0
    
    def is_user_api_active(self, user_id: int) -> bool:
        """التحقق من تفعيل API للمستخدم"""
        api_data = self.get_user_api_keys(user_id)
        return api_data and api_data['is_active']

# إنشاء مثيل مشترك
binance_manager = BinanceManager()
