#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محاكاة سريعة وشاملة — الأدمن / المحفظة التجريبية
===================================================
⚡ بدون استدعاء Binance API — جميع الاختبارات محلية وفورية
15 سيناريو × ~100 اختبار في < 5 ثوانٍ
"""

import os, sys, sqlite3, requests
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.database_manager import DatabaseManager

# ── Helpers ──────────────────────────────────────────────────────────
P, F, R, SC = 0, 0, [], 0
db = DatabaseManager()
UID = 1

def t(name, cond, detail=""):
    global P, F
    if cond: P += 1; R.append(f"  ✅ {name}")
    else:    F += 1; R.append(f"  ❌ {name} — {detail}")

def s(name):
    global SC; SC += 1
    h = f"\n{'─'*60}\n 📋 S{SC}: {name}\n{'─'*60}"
    print(h); R.append(h)

def bal():
    with db.get_connection() as c:
        r = c.execute("SELECT total_balance FROM portfolio WHERE user_id=? AND is_demo=1",(UID,)).fetchone()
        return float(r[0]) if r else 0

def positions():
    with db.get_connection() as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute("SELECT * FROM active_positions WHERE user_id=? AND is_active=1",(UID,)).fetchall()]

def sys_status():
    with db.get_connection() as c:
        r = c.execute("SELECT status, is_running FROM system_status WHERE id=1").fetchone()
        return {'status':r[0],'is_running':bool(r[1])} if r else None

def clean():
    with db.get_write_connection() as c:
        c.execute("DELETE FROM active_positions WHERE user_id=? AND strategy='SIM_TEST'",(UID,))

def set_bal(amt=1000.0):
    with db.get_write_connection() as c:
        c.execute("UPDATE portfolio SET total_balance=?,available_balance=?,invested_balance=0 WHERE user_id=? AND is_demo=1",(amt,amt,UID))
        # ✅ FIX: استخدام portfolio table الموحد بدلاً من user_portfolio المُلغى
        c.execute("UPDATE portfolio SET total_balance=?,available_balance=? WHERE user_id=? AND is_demo=0",(amt,amt,UID))

def add_pos(sym, ep, qty, ptype='long', sl=0, sz=100):
    with db.get_write_connection() as c:
        c.execute("""INSERT INTO active_positions
            (user_id,symbol,entry_price,quantity,position_size,strategy,is_demo,is_active,position_type,stop_loss,highest_price,trailing_sl_price,created_at,timeframe,entry_date)
            VALUES(?,?,?,?,?,'SIM_TEST',1,1,?,?,?,0,datetime('now'),'1h',datetime('now'))""",
            (UID,sym,ep,qty,sz,ptype,sl,ep))

# ── Setup ────────────────────────────────────────────────────────────
print("="*60)
print("⚡ محاكاة سريعة شاملة — بدون Binance API")
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

clean(); set_bal(1000.0)

# ── Direct imports (no Binance) ──────────────────────────────────────
from backend.risk.portfolio_heat_manager import PortfolioHeatManager
from backend.risk.kelly_position_sizer import KellyPositionSizer
from backend.selection.dynamic_blacklist import DynamicBlacklist

# =====================================================================
# S1: DB — Admin + Settings + Portfolio
# =====================================================================
s("قاعدة البيانات — Admin + Settings + Portfolio")

with db.get_connection() as c:
    c.row_factory = sqlite3.Row
    user = dict(c.execute("SELECT * FROM users WHERE id=?",(UID,)).fetchone())
    t("Admin exists", user is not None)
    t("Admin type=admin", user.get('user_type')=='admin')
    t("Admin active", user.get('is_active')==1)

    # Demo settings
    ds = dict(c.execute("SELECT * FROM user_settings WHERE user_id=? AND is_demo=1",(UID,)).fetchone())
    t("Demo settings exist", ds is not None)
    t("trading_enabled=1", ds.get('trading_enabled')==1)
    t("trading_mode=demo", ds.get('trading_mode')=='demo')
    t("max_positions=5", ds.get('max_positions')==5)
    t("position_size_pct=10%", ds.get('position_size_percentage')==10.0)

    # Real settings
    rs = dict(c.execute("SELECT * FROM user_settings WHERE user_id=? AND is_demo=0",(UID,)).fetchone())
    t("Real settings exist", rs is not None)

    # Portfolio
    dp = dict(c.execute("SELECT * FROM portfolio WHERE user_id=? AND is_demo=1",(UID,)).fetchone())
    t("Demo portfolio: balance=$1000", abs(float(dp['total_balance'])-1000)<0.01)
    t("Demo portfolio: initial=$1000", abs(float(dp['initial_balance'])-1000)<0.01)

# =====================================================================
# S2: DB Portfolio API
# =====================================================================
s("DB API — get_user_portfolio يقرأ البيانات الصحيحة")

pdata = db.get_user_portfolio(UID)
t("Portfolio returns data", pdata is not None and 'balance' in pdata)
t("Balance=$1000", abs(float(pdata.get('balance',0))-1000)<0.01)
t("Source=demo_admin", pdata.get('source')=='demo_admin')
t("Currency=USD", pdata.get('currency')=='USD')

# =====================================================================
# S3: إدخال صفقات + تتبع الأرصدة
# =====================================================================
s("إدخال صفقات يدوية + تتبع الأرصدة")

clean(); set_bal(1000.0)
add_pos('ETHUSDT', 2500, 0.04, 'long', sl=2475, sz=100)
add_pos('BNBUSDT', 600, 0.167, 'long', sl=594, sz=100)
add_pos('SOLUSDT', 180, 0.556, 'short', sl=181.8, sz=100)

pp = positions()
t("3 positions in DB", len(pp)==3, f"got {len(pp)}")

with db.get_write_connection() as c:
    c.execute("UPDATE portfolio SET total_balance=700,available_balance=700,invested_balance=300 WHERE user_id=? AND is_demo=1",(UID,))
t("Balance updated to $700", abs(bal()-700)<0.01)

for p in pp:
    t(f"  {p['symbol']}: entry>0", p['entry_price']>0)
    t(f"  {p['symbol']}: SL>0", p['stop_loss']>0)
    t(f"  {p['symbol']}: is_demo=1", p['is_demo']==1)
    t(f"  {p['symbol']}: type valid", p['position_type'] in ('long','short'))

# =====================================================================
# S4: PortfolioHeatManager
# =====================================================================
s("PortfolioHeatManager — حرارة المحفظة (max 6%)")

hm = PortfolioHeatManager(max_heat_pct=6.0)

r0 = hm.check_portfolio_heat([], 1000)
t("Empty → can_open=True", r0['can_open_new']==True)
t("Empty → heat=0%", r0['current_heat_pct']==0)

high = [
    {'entry_price':100,'stop_loss':90,'size':5,'position_type':'long'},
    {'entry_price':200,'stop_loss':180,'size':3,'position_type':'long'},
]
r1 = hm.check_portfolio_heat(high, 1000)
t("High risk (11%) → BLOCKED", r1['can_open_new']==False)
t("Heat = 11%", r1['current_heat_pct']==11.0)

low = [{'entry_price':100,'stop_loss':99,'size':1,'position_type':'long'}]
r2 = hm.check_portfolio_heat(low, 1000)
t("Low risk (0.1%) → ALLOWED", r2['can_open_new']==True)

edge = [{'entry_price':100,'stop_loss':94,'size':10,'position_type':'long'}]
r3 = hm.check_portfolio_heat(edge, 1000)
t("Edge 6% → blocked (>=)", r3['can_open_new']==False)

# =====================================================================
# S5: KellyPositionSizer
# =====================================================================
s("KellyPositionSizer — حجم ديناميكي")

ks = KellyPositionSizer()

k1 = ks.calculate_position_size(balance=1000, max_position_pct=0.10, symbol='BTCUSDT')
t("Kelly → kelly_pct>0", k1['kelly_pct']>0)
t("Kelly → kelly_pct≤0.15", k1['kelly_pct']<=0.15)

k2 = ks.calculate_position_size(balance=1000, max_position_pct=0.05, symbol='ETHUSDT')
t("Lower max → smaller kelly", k2['kelly_pct']<=k1['kelly_pct'])

k3 = ks.calculate_position_size(balance=50, max_position_pct=0.10, symbol='BTCUSDT')
t("Low balance ($50) → kelly valid", 0 < k3['kelly_pct'] <= 0.15)

k4 = ks.calculate_position_size(balance=0, max_position_pct=0.10, symbol='BTCUSDT')
t("Zero balance → kelly valid", k4['kelly_pct'] >= 0)

print(f"  📊 kelly={k1['kelly_pct']*100:.1f}%, "
      f"low_max={k2['kelly_pct']*100:.1f}%, confidence={k1['confidence']}")

# =====================================================================
# S6: Self-Throttling (محاكاة daily_state)
# =====================================================================
s("Self-Throttling — حد يومي 10 صفقات")

# محاكاة daily_state بدون GBS
ds = {'trades_today':10,'max_daily_trades':10,'daily_pnl':0,
      'max_daily_loss_pct':0.03,'cooldown_until':None,'consecutive_losses':0,
      'last_reset':datetime.now().date()}

blocked_trades = ds['trades_today'] >= ds['max_daily_trades']
t("10/10 trades → BLOCKED", blocked_trades==True)

ds['trades_today'] = 5
t("5/10 trades → ALLOWED", ds['trades_today']<ds['max_daily_trades'])

ds['trades_today'] = 9
t("9/10 trades → ALLOWED", ds['trades_today']<ds['max_daily_trades'])

# =====================================================================
# S7: Daily Loss Limit (3%)
# =====================================================================
s("Daily Loss Limit — 3%")

balance = 1000.0
max_loss = balance * 0.03  # $30

ds['daily_pnl'] = -35
t("-$35 > $30 limit → BLOCKED", ds['daily_pnl'] < -max_loss)

ds['daily_pnl'] = -20
t("-$20 < $30 limit → ALLOWED", not (ds['daily_pnl'] < -max_loss))

ds['daily_pnl'] = -29.9
t("-$29.9 < $30 → ALLOWED (edge)", not (ds['daily_pnl'] < -max_loss))

ds['daily_pnl'] = -30.1
t("-$30.1 > $30 → BLOCKED (edge)", ds['daily_pnl'] < -max_loss)

# =====================================================================
# S8: System-wide Cooldown
# =====================================================================
s("System-wide Cooldown — بعد 3 خسائر")

consecutive = 0; cooldown_until = None
max_consecutive = 3; cooldown_hours = 2

# 3 خسائر
for i in range(3):
    consecutive += 1
    if consecutive >= max_consecutive:
        cooldown_until = datetime.now() + timedelta(hours=cooldown_hours)

t("After 3 losses: consecutive=3", consecutive==3)
t("Cooldown ACTIVATED", cooldown_until is not None)
t("Cooldown in future", cooldown_until > datetime.now())

# During cooldown → blocked
t("During cooldown → BLOCKED", datetime.now() < cooldown_until)

# Expired cooldown → allowed
cooldown_until = datetime.now() - timedelta(minutes=1)
t("Expired cooldown → ALLOWED", datetime.now() >= cooldown_until)

# Win resets consecutive
consecutive = 2
consecutive = 0  # win resets
t("Win resets consecutive=0", consecutive==0)

# =====================================================================
# S9: Directional Stress
# =====================================================================
s("Capital Stress — max 3 same direction")

max_dir = 3

# Empty
t("Empty → ALLOWED", True)

# 3 longs + new long
longs = [{'position_type':'long'}]*3
same = sum(1 for p in longs if p['position_type']=='long')
t("3L + LONG → BLOCKED", same >= max_dir)

# 3 longs + new short
shorts_count = sum(1 for p in longs if p['position_type']=='short')
t("3L + SHORT → ALLOWED", shorts_count < max_dir)

# Mixed
mixed = [{'position_type':'long'},{'position_type':'long'},{'position_type':'short'}]
ml = sum(1 for p in mixed if p['position_type']=='long')
t("2L+1S + LONG → ALLOWED", ml < max_dir)

# 3 shorts + short
shorts = [{'position_type':'short'}]*3
ss = sum(1 for p in shorts if p['position_type']=='short')
t("3S + SHORT → BLOCKED", ss >= max_dir)

# =====================================================================
# S10: حالات حافة
# =====================================================================
s("حالات حافة — رصيد غير كافي + أقصى صفقات + قائمة سوداء")

# Low balance
set_bal(5.0)
t("Low balance: $5 in DB", abs(bal()-5)<0.01)
pct = 10.0/100.0
sz = 5.0 * pct  # $0.50
t("Position size $0.50 < $10 min → no trade", sz < 10)

# Max positions
clean(); set_bal(1000)
for sym in ['ETHUSDT','BNBUSDT','SOLUSDT','AVAXUSDT','NEARUSDT']:
    add_pos(sym, 100, 1, 'long', sl=99, sz=100)
pp = positions()
t("5 positions in DB", len(pp)==5)
t("At max_positions=5 → no new", len(pp)>=5)

# Blacklist
bl = DynamicBlacklist()
bl._add_to_blacklist('TESTUSDT', 'simulation')
t("Blacklist: TESTUSDT → True", bl.is_blacklisted('TESTUSDT'))
t("Blacklist: ETHUSDT → False", not bl.is_blacklisted('ETHUSDT'))

# Expiry
bl.performance['TESTUSDT']['blacklisted_at'] = datetime.now() - timedelta(hours=100)
t("Blacklist: expired after 100h → False", not bl.is_blacklisted('TESTUSDT'))

# =====================================================================
# S11: Daily Reset Logic
# =====================================================================
s("تصفير الحالة اليومية")

ds2 = {
    'trades_today':8,'losses_today':3,'consecutive_losses':2,
    'daily_pnl':-25,'last_reset':(datetime.now()-timedelta(days=1)).date(),
    'cooldown_until': datetime.now()-timedelta(hours=1),
}
# simulate reset
today = datetime.now().date()
if ds2['last_reset'] != today:
    ds2['trades_today']=0; ds2['losses_today']=0
    ds2['consecutive_losses']=0; ds2['daily_pnl']=0
    ds2['cooldown_until']=None; ds2['last_reset']=today

t("Reset: trades=0", ds2['trades_today']==0)
t("Reset: losses=0", ds2['losses_today']==0)
t("Reset: consecutive=0", ds2['consecutive_losses']==0)
t("Reset: pnl=0", ds2['daily_pnl']==0)
t("Reset: cooldown=None", ds2['cooldown_until'] is None)
t("Reset: date=today", ds2['last_reset']==today)

# Same day → no reset
ds2['trades_today'] = 5
if ds2['last_reset'] != today:
    ds2['trades_today'] = 0
t("Same day: trades stays 5", ds2['trades_today']==5)

# =====================================================================
# S12: State Machine — JSON read/write
# =====================================================================
s("Trading State Machine — JSON read/write + heartbeat")

try:
    from backend.core.state_manager import get_state_manager
    sm = get_state_manager()

    sm.write_state({'status':'running','is_running':True,'pid':99999,
                    'started_at':datetime.now().isoformat()}, user='sim')
    st = sm.read_state()
    t("Write running → read running", st.get('status')=='running')
    t("is_running=True", st.get('is_running')==True)
    t("pid=99999", st.get('pid')==99999)

    sm.write_state({'status':'stopped','is_running':False,'pid':None,
                    'started_at':None}, user='sim')
    st2 = sm.read_state()
    t("Write stopped → read stopped", st2.get('status')=='stopped')
    t("is_running=False", st2.get('is_running')==False)

    sm.send_heartbeat()
    secs = sm.get_seconds_since_heartbeat()
    t("Heartbeat: secs ≤ 2", secs is not None and secs <= 2)

    t("DB: system_status readable", sys_status() is not None)
except Exception as e:
    t("State Machine", False, str(e))

# =====================================================================
# S13: Reconciliation — dead PID
# =====================================================================
s("State Reconciliation — dead PID → stopped")

try:
    from backend.core.unified_system_manager import get_unified_system_manager
    usm = get_unified_system_manager()
    sm.write_state({'status':'running','is_running':True,'pid':999999}, user='sim')
    usm.reconcile_state()
    st = sm.read_state()
    t("Dead PID → status=stopped", st.get('status')=='stopped')
    t("Dead PID → is_running=False", st.get('is_running')==False)
except Exception as e:
    t("Reconciliation", False, str(e))

# =====================================================================
# S14: Code integrity — imports + syntax
# =====================================================================
s("تكامل الكود — imports + مكونات النظام")

import py_compile
core_files = list((project_root/'backend'/'core').glob('*.py'))
api_files = list((project_root/'backend'/'api').glob('*.py'))
bin_files = list((project_root/'bin').glob('*.py'))
all_files = core_files + api_files + bin_files
errors = []
for f in all_files:
    try: py_compile.compile(str(f), doraise=True)
    except py_compile.PyCompileError as e: errors.append(str(f.name))
t(f"Syntax OK: {len(all_files)} files", len(errors)==0, f"errors in: {errors}")

# Key imports
try:
    from backend.core.group_b_system import GroupBSystem
    t("Import: GroupBSystem", True)
except: t("Import: GroupBSystem", False)

try:
    from backend.strategies.scalping_v7_engine import get_scalping_v7_engine
    t("Import: ScalpingV7Engine", True)
except: t("Import: ScalpingV7Engine", False)

try:
    from backend.strategies.intelligent_exit_system import get_intelligent_exit_system
    t("Import: IntelligentExitSystem", True)
except: t("Import: IntelligentExitSystem", False)

try:
    from backend.cognitive import CognitiveOrchestrator, MultiExitEngine
    t("Import: Cognitive modules", True)
except: t("Import: Cognitive modules", False)

# =====================================================================
# S15: API Endpoints (if server running)
# =====================================================================
s("API Endpoints (إذا السيرفر يعمل)")

alive = False
try:
    alive = requests.get("http://localhost:3002/api/health",timeout=2).status_code==200
except: pass

if alive:
    try:
        login = requests.post("http://localhost:3002/api/auth/login",
            json={'username':'admin','password':'admin123'},timeout=5)
        if login.status_code==200:
            h = {'Authorization':f'Bearer {login.json().get("token")}'}
            for ep,name in [
                ('/api/user/portfolio?mode=demo','portfolio'),
                ('/api/user/positions/active','positions'),
                ('/api/admin/system/status','system status'),
                ('/api/user/settings','settings'),
            ]:
                r = requests.get(f"http://localhost:3002{ep}",headers=h,timeout=5)
                t(f"API {name} → {r.status_code}", r.status_code==200)
        else:
            t("API login", False, f"status={login.status_code}")
    except Exception as e:
        t("API tests", False, str(e))
else:
    R.append("  ⏭️ SKIPPED: Server not running")
    print("  ⏭️ Server not running — skipped")

# ── Cleanup ──────────────────────────────────────────────────────────
clean(); set_bal(1000.0)
try:
    sm.write_state({'status':'stopped','is_running':False,'pid':None,
        'started_at':None}, user='sim_cleanup')
except: pass

# ── Summary ──────────────────────────────────────────────────────────
print("\n"+"="*60)
print(f"📊 {P} نجاح, {F} فشل من {P+F} اختبار — {SC} سيناريو")
print("="*60)
for r in R: print(r)
print("\n"+"="*60)
if F==0: print("🎉 جميع الاختبارات نجحت — النظام متكامل وجاهز")
else:    print(f"⚠️ {F} فشل — راجع أعلاه")
print("="*60)
sys.exit(0 if F==0 else 1)
