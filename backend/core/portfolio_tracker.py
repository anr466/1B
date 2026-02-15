"""
خدمة تتبع نمو المحفظة
تحديث يومي لسجل النمو من البيانات الفعلية
"""

from datetime import datetime, timedelta
import logging
from database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class PortfolioTracker:
    def __init__(self):
        self.db = DatabaseManager()
    
    # ============ للمستخدمين العاديين ============
    
    def record_daily_portfolio_snapshot(self, user_id: str):
        """تسجيل لقطة يومية من المحفظة الحالية"""
        try:
            # جلب بيانات المحفظة الحالية (من portfolio للمستخدم العادي is_demo=0)
            with self.db.get_connection() as conn:
                portfolio = conn.execute(
                    "SELECT total_balance FROM portfolio WHERE user_id = ? AND is_demo = 0 LIMIT 1",
                    (user_id,)
                ).fetchone()
                
                if not portfolio:
                    logger.warning(f"لا توجد محفظة للمستخدم: {user_id}")
                    return False
                
                total_balance = portfolio[0]
                today = datetime.now().date()
                
                # فحص وجود لقطة اليوم
                today_snapshot = conn.execute(
                    "SELECT total_balance FROM portfolio_growth_history WHERE user_id = ? AND date = ? LIMIT 1",
                    (user_id, today)
                ).fetchone()
                
                if today_snapshot:
                    logger.info(f"لقطة اليوم موجودة بالفعل للمستخدم: {user_id}")
                    return True
                
                # حساب PnL اليومي
                yesterday = today - timedelta(days=1)
                yesterday_snapshot = conn.execute(
                    "SELECT total_balance FROM portfolio_growth_history WHERE user_id = ? AND date = ? LIMIT 1",
                    (user_id, yesterday)
                ).fetchone()
                
                yesterday_balance = yesterday_snapshot[0] if yesterday_snapshot else total_balance
                daily_pnl = total_balance - yesterday_balance
                daily_pnl_percentage = (daily_pnl / yesterday_balance * 100) if yesterday_balance > 0 else 0
                
                # جلب عدد الصفقات المفتوحة
                active_trades = conn.execute(
                    "SELECT COUNT(*) FROM active_positions WHERE user_id = ? AND is_active = 1",
                    (user_id,)
                ).fetchone()
                active_trades_count = active_trades[0] if active_trades else 0
                
                # حفظ اللقطة
                conn.execute(
                    """
                    INSERT INTO portfolio_growth_history 
                    (user_id, date, total_balance, daily_pnl, daily_pnl_percentage, active_trades_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, today, total_balance, daily_pnl, daily_pnl_percentage, active_trades_count)
                )
                conn.commit()
                
                logger.info(f"✅ تم تسجيل لقطة المحفظة للمستخدم: {user_id} - الرصيد: {total_balance}")
                return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل لقطة المحفظة: {e}")
            return False
    
    # ============ للأدمن (تداول وهمي) ============
    
    def update_admin_demo_balance(self, admin_id: str, total_pnl: float = 0):
        """
        🔧 دالة مركزية موحدة لتحديث الرصيد الوهمي للأدمن
        
        الرصيد الوهمي = الرصيد الأولي + إجمالي الأرباح/الخسائر من الصفقات الوهمية
        
        المنطق:
        1. جلب الرصيد الأولي من جدول portfolio (is_demo=1)
        2. حساب الرصيد الجديد = الرصيد الأولي + total_pnl
        3. تحديث الرصيد الحالي في جدول portfolio
        4. تسجيل لقطة يومية في جدول admin_demo_portfolio_history
        
        Args:
            admin_id: معرف الأدمن
            total_pnl: إجمالي الأرباح/الخسائر من الصفقات الوهمية
        
        Returns:
            dict: {success: bool, new_balance: float, message: str}
        """
        try:
            # ✅ FIX: استخدام get_write_connection لتجنب database lock
            with self.db.get_write_connection() as conn:
                # 1️⃣ جلب الرصيد الأولي والحالي
                portfolio = conn.execute(
                    "SELECT initial_balance, total_balance FROM portfolio WHERE user_id = ? AND is_demo = 1 LIMIT 1",
                    (admin_id,)
                ).fetchone()
                
                if not portfolio:
                    logger.warning(f"⚠️ لا توجد محفظة وهمية للأدمن: {admin_id}")
                    return {
                        'success': False,
                        'message': 'لا توجد محفظة وهمية',
                        'new_balance': 0
                    }
                
                initial_balance = float(portfolio[0])
                old_balance = float(portfolio[1])
                
                # 2️⃣ حساب الرصيد الجديد
                new_balance = initial_balance + total_pnl
                
                # 3️⃣ تحديث الرصيد الحالي في جدول portfolio
                conn.execute(
                    """
                    UPDATE portfolio 
                    SET total_balance = ?,
                        available_balance = ?,
                        total_profit_loss = ?,
                        total_profit_loss_percentage = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND is_demo = 1
                    """,
                    (
                        new_balance,
                        new_balance,  # الرصيد المتاح = الرصيد الكلي (لا توجد صفقات مقفلة)
                        total_pnl,
                        (total_pnl / initial_balance * 100) if initial_balance > 0 else 0,
                        admin_id
                    )
                )
                
                # 4️⃣ تسجيل لقطة يومية في جدول admin_demo_portfolio_history
                today = datetime.now().date()
                daily_pnl = new_balance - old_balance
                daily_pnl_percentage = (daily_pnl / old_balance * 100) if old_balance > 0 else 0
                
                # فحص وجود لقطة اليوم
                today_snapshot = conn.execute(
                    "SELECT id FROM admin_demo_portfolio_history WHERE admin_id = ? AND date = ? LIMIT 1",
                    (admin_id, today)
                ).fetchone()
                
                if today_snapshot:
                    # تحديث اللقطة الموجودة
                    conn.execute(
                        """
                        UPDATE admin_demo_portfolio_history
                        SET total_balance = ?, daily_pnl = ?, daily_pnl_percentage = ?
                        WHERE admin_id = ? AND date = ?
                        """,
                        (new_balance, daily_pnl, daily_pnl_percentage, admin_id, today)
                    )
                else:
                    # إنشاء لقطة جديدة
                    conn.execute(
                        """
                        INSERT INTO admin_demo_portfolio_history 
                        (admin_id, date, total_balance, daily_pnl, daily_pnl_percentage, active_trades_count)
                        VALUES (?, ?, ?, ?, ?, 0)
                        """,
                        (admin_id, today, new_balance, daily_pnl, daily_pnl_percentage)
                    )
                
                conn.commit()
                
                logger.info(f"✅ تم تحديث الرصيد الوهمي للأدمن {admin_id}: {old_balance} → {new_balance} (PnL: {total_pnl:+.2f})")
                
                return {
                    'success': True,
                    'new_balance': new_balance,
                    'old_balance': old_balance,
                    'daily_pnl': daily_pnl,
                    'message': f'تم تحديث الرصيد الوهمي بنجاح: {new_balance:.2f}'
                }
        
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الرصيد الوهمي: {e}")
            return {
                'success': False,
                'message': f'خطأ في التحديث: {str(e)}',
                'new_balance': 0
            }
    
    def record_admin_demo_snapshot(self, admin_id: str, demo_balance: float):
        """تسجيل لقطة يومية من المحفظة الوهمية للأدمن"""
        try:
            # ✅ FIX: استخدام get_write_connection لتجنب database lock
            with self.db.get_write_connection() as conn:
                today = datetime.now().date()
                
                # فحص وجود لقطة اليوم
                today_snapshot = conn.execute(
                    "SELECT total_balance FROM admin_demo_portfolio_history WHERE admin_id = ? AND date = ? LIMIT 1",
                    (admin_id, today)
                ).fetchone()
                
                if today_snapshot:
                    logger.info(f"لقطة اليوم موجودة بالفعل للأدمن: {admin_id}")
                    return True
                
                # حساب PnL اليومي
                yesterday = today - timedelta(days=1)
                yesterday_snapshot = conn.execute(
                    "SELECT total_balance FROM admin_demo_portfolio_history WHERE admin_id = ? AND date = ? LIMIT 1",
                    (admin_id, yesterday)
                ).fetchone()
                
                yesterday_balance = yesterday_snapshot[0] if yesterday_snapshot else demo_balance
                daily_pnl = demo_balance - yesterday_balance
                daily_pnl_percentage = (daily_pnl / yesterday_balance * 100) if yesterday_balance > 0 else 0
                
                # ✅ FIX: الصفقات المفتوحة تُسجل في active_positions، وليس user_trades
                active_demo_trades = conn.execute(
                    "SELECT COUNT(*) FROM active_positions WHERE user_id = ? AND is_active = 1 AND is_demo = 1",
                    (admin_id,)
                ).fetchone()
                active_trades_count = active_demo_trades[0] if active_demo_trades else 0
                
                # حفظ اللقطة
                conn.execute(
                    """
                    INSERT INTO admin_demo_portfolio_history 
                    (admin_id, date, total_balance, daily_pnl, daily_pnl_percentage, active_trades_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (admin_id, today, demo_balance, daily_pnl, daily_pnl_percentage, active_trades_count)
                )
                conn.commit()
                
                logger.info(f"✅ تم تسجيل لقطة المحفظة الوهمية للأدمن: {admin_id} - الرصيد: {demo_balance}")
                return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل لقطة المحفظة الوهمية: {e}")
            return False
    
    # ============ جلب البيانات للرسوم البيانية ============
    
    def get_portfolio_growth_data(self, user_id: str, days: int = 90, mode: str = None) -> dict:
        """جلب بيانات نمو المحفظة (آخر 90 يوم)
        
        Args:
            user_id: معرف المستخدم
            days: عدد الأيام
            mode: وضع التداول (demo/real) - للأدمن فقط
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).date()
            
            # ✅ تحديد الجدول والعمود حسب الوضع
            if mode == 'demo':
                # جلب من جدول المحفظة الوهمية للأدمن
                table_name = 'admin_demo_portfolio_history'
                id_column = 'admin_id'
            else:
                table_name = 'portfolio_growth_history'
                id_column = 'user_id'
            
            with self.db.get_connection() as conn:
                data = conn.execute(
                    f"""
                    SELECT date, total_balance, daily_pnl, daily_pnl_percentage
                    FROM {table_name}
                    WHERE {id_column} = ? AND date >= ?
                    ORDER BY date ASC
                    """,
                    (user_id, start_date)
                ).fetchall()
            
            if not data:
                logger.warning(f"لا توجد بيانات نمو للمستخدم: {user_id}")
                return {
                    'dates': [],
                    'balances': [],
                    'daily_pnl': [],
                    'daily_pnl_percentage': [],
                    'total_growth': 0,
                    'total_growth_percentage': 0,
                    'first_balance': 0,
                    'last_balance': 0
                }
            
            dates = [str(row[0]) for row in data]
            balances = [float(row[1]) for row in data]
            daily_pnl = [float(row[2]) for row in data]
            daily_pnl_percentage = [float(row[3]) for row in data]
            
            # حساب النمو الكلي
            first_balance = balances[0]
            last_balance = balances[-1]
            total_growth = last_balance - first_balance
            total_growth_percentage = (total_growth / first_balance * 100) if first_balance > 0 else 0
            
            return {
                'dates': dates,
                'balances': balances,
                'daily_pnl': daily_pnl,
                'daily_pnl_percentage': daily_pnl_percentage,
                'total_growth': round(total_growth, 2),
                'total_growth_percentage': round(total_growth_percentage, 2),
                'first_balance': round(first_balance, 2),
                'last_balance': round(last_balance, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب بيانات النمو: {e}")
            return {}
    
    def get_admin_demo_growth_data(self, admin_id: str, days: int = 90) -> dict:
        """جلب بيانات نمو المحفظة الوهمية للأدمن"""
        try:
            start_date = (datetime.now() - timedelta(days=days)).date()
            
            with self.db.get_connection() as conn:
                data = conn.execute(
                    """
                    SELECT date, total_balance, daily_pnl, daily_pnl_percentage
                    FROM admin_demo_portfolio_history
                    WHERE admin_id = ? AND date >= ?
                    ORDER BY date ASC
                    """,
                    (admin_id, start_date)
                ).fetchall()
            
            if not data:
                logger.warning(f"لا توجد بيانات نمو وهمية للأدمن: {admin_id}")
                return {
                    'dates': [],
                    'balances': [],
                    'daily_pnl': [],
                    'daily_pnl_percentage': [],
                    'total_growth': 0,
                    'total_growth_percentage': 0,
                    'first_balance': 0,
                    'last_balance': 0
                }
            
            dates = [str(row[0]) for row in data]
            balances = [float(row[1]) for row in data]
            daily_pnl = [float(row[2]) for row in data]
            daily_pnl_percentage = [float(row[3]) for row in data]
            
            first_balance = balances[0]
            last_balance = balances[-1]
            total_growth = last_balance - first_balance
            total_growth_percentage = (total_growth / first_balance * 100) if first_balance > 0 else 0
            
            return {
                'dates': dates,
                'balances': balances,
                'daily_pnl': daily_pnl,
                'daily_pnl_percentage': daily_pnl_percentage,
                'total_growth': round(total_growth, 2),
                'total_growth_percentage': round(total_growth_percentage, 2),
                'first_balance': round(first_balance, 2),
                'last_balance': round(last_balance, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب بيانات النمو الوهمية: {e}")
            return {}
