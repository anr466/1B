#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 قوائم العملات المحسّنة - بناءً على اختبار 40 عملة / 42 يوم
==============================================================
تاريخ التحديث: 2026-01-30
"""

# ========== القائمة البيضاء - عملات مُثبتة الربحية ==========
# معايير الاختيار: PnL > 0 AND Win Rate > 50%
WHITELIST_COINS = [
    # 🏆 الأفضل أداءً
    'ICPUSDT',    # +8.86% | WR: 60% | 20 صفقة
    'GMTUSDT',    # +7.28% | WR: 60% | 20 صفقة
    'FILUSDT',    # +6.72% | WR: 62% | 21 صفقة
    'IMXUSDT',    # +5.92% | WR: 64% | 22 صفقة
    'ALGOUSDT',   # +5.08% | WR: 61% | 18 صفقة
    'ATOMUSDT',   # +4.73% | WR: 56% | 16 صفقة
    'BCHUSDT',    # +4.56% | WR: 56% | 16 صفقة
    'FTMUSDT',    # +3.41% | WR: 52% | 23 صفقة
    'APTUSDT',    # +3.17% | WR: 63% | 19 صفقة
    'SUIUSDT',    # +2.65% | WR: 57% | 21 صفقة
    'APEUSDT',    # +2.55% | WR: 59% | 22 صفقة
    'NEARUSDT',   # +2.10% | WR: 56% | 18 صفقة
    'ARBUSDT',    # +0.60% | WR: 58% | 19 صفقة
    'LTCUSDT',    # +0.42% | WR: 63% | 19 صفقة
]

# ========== القائمة السوداء - عملات خاسرة مُثبتة ==========
# معايير الاستبعاد: PnL < -10% OR Win Rate < 45%
BLACKLIST_COINS = [
    'XMRUSDT',    # -27.31% | WR: 40% ❌
    'MATICUSDT',  # -19.86% | WR: 35% ❌
    'XLMUSDT',    # -17.59% | WR: 41% ❌
    'SANDUSDT',   # -15.92% | WR: 47% ❌
    'HBARUSDT',   # -15.04% | WR: 44% ❌
    'GALAUSDT',   # -14.63% | WR: 45% ❌
    'INJUSDT',    # -12.71% | WR: 42% ❌
    'LINKUSDT',   # -12.34% | WR: 43% ❌
    'AVAXUSDT',   # -11.89% | WR: 47% ❌
    'XRPUSDT',    # -10.08% | WR: 53% ❌
    'SOLUSDT',    # -8.66%  | WR: 33% ❌
    'DOGEUSDT',   # -7.76%  | WR: 44% ❌
]

# ========== قائمة محايدة - تحتاج مراقبة ==========
NEUTRAL_COINS = [
    'BTCUSDT',    # -5.92% | WR: 58% - يحتاج مراقبة
    'ETHUSDT',    # -6.38% | WR: 60% - يحتاج مراقبة
    'BNBUSDT',    # -4.95% | WR: 58% - يحتاج مراقبة
    'ADAUSDT',    # -3.05% | WR: 56% - يحتاج مراقبة
    'DOTUSDT',    # -3.22% | WR: 53% - يحتاج مراقبة
    'UNIUSDT',    # -4.66% | WR: 56% - يحتاج مراقبة
    'AAVEUSDT',   # -1.39% | WR: 53% - قريب من الربح
    'CRVUSDT',    # -2.45% | WR: 57% - قريب من الربح
    'OPUSDT',     # -2.25% | WR: 53% - قريب من الربح
]

# ========== القائمة الموسعة للمسح ==========
# كل العملات التي يمكن فحصها
ALL_SCANNABLE_COINS = [
    # Top Market Cap
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT',
    # DeFi
    'LINKUSDT', 'UNIUSDT', 'AAVEUSDT', 'CRVUSDT', 'SUSHIUSDT',
    # Layer 2 & New
    'ARBUSDT', 'OPUSDT', 'APTUSDT', 'SUIUSDT', 'INJUSDT',
    # Infrastructure
    'ATOMUSDT', 'NEARUSDT', 'ALGOUSDT', 'FTMUSDT', 'ICPUSDT',
    # Classic
    'LTCUSDT', 'BCHUSDT', 'ETCUSDT', 'XLMUSDT', 'XMRUSDT',
    # Mid Cap
    'FILUSDT', 'HBARUSDT', 'VETUSDT', 'EGLDUSDT', 'SANDUSDT',
    # Volatile
    'GALAUSDT', 'APEUSDT', 'GMTUSDT', 'LRCUSDT', 'IMXUSDT',
    # Additional
    'TRXUSDT', 'XTZUSDT', 'EOSUSDT', 'NEOUSDT', 'QNTUSDT',
]


def get_tradeable_coins():
    """الحصول على العملات القابلة للتداول"""
    return WHITELIST_COINS.copy()


def get_scannable_coins():
    """الحصول على كل العملات للمسح"""
    return ALL_SCANNABLE_COINS.copy()


def is_blacklisted(symbol: str) -> bool:
    """فحص إذا العملة في القائمة السوداء"""
    return symbol in BLACKLIST_COINS


def is_whitelisted(symbol: str) -> bool:
    """فحص إذا العملة في القائمة البيضاء"""
    return symbol in WHITELIST_COINS


# ========== إحصائيات الاختبار ==========
TEST_STATS = {
    'test_date': '2026-01-30',
    'test_period_days': 42,
    'total_coins_tested': 40,
    'total_trades': 710,
    'overall_win_rate': 53.1,
    'profit_factor': 0.83,
    'avg_pnl_per_trade': -0.24,
    'trades_per_day': 16.9,
    'best_strategy': 'SUPPORT_BOUNCE',
    'best_strategy_avg_pnl': 0.73,
}
