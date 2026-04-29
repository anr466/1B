# Skill: add-strategy
# إضافة استراتيجية تداول جديدة

## Contract
- أنشئ ملف جديد في `backend/strategies/`
- وراثة من `BaseStrategy` (الموجود في `backend/strategies/base_strategy.py`)
- نفذ 4 دوال: `prepare_data(df)`, `detect_entry(df)`, `check_exit(df, position)`, `get_config()`
- حدد `name`, `version`, `description` كـ class attributes
- لا تعدل `base_strategy.py` أبداً
- لا تعدل أي استراتيجية موجودة

## Verification
```bash
python -c "from backend.strategies.new_strategy import NewStrategy; s = NewStrategy(); print(s.get_config())"
```
