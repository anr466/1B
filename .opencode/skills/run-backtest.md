# Skill: run-backtest
# تشغيل اختبار رجعي (Backtest)

## Available Scripts
```bash
python scripts/backtest_v8_comparison.py
python scripts/real_backtest_v8.py
python scripts/real_case_backtest.py
```

## Before Running
- تأكد من أن بيانات السوق متاحة (Binance API)
- تحقق من وضع dual_mode_router (backtest = Demo mode)
- سجل النتائج للمقارنة

## What to Check
- Win rate, avg win/loss
- Kelly Criterion thresholds: WR=63.9%, avg_win=1.35%, avg_loss=1.62%
- Max drawdown vs portfolio heat (6% cap)
- Strategy performance under different MarketRegimes
