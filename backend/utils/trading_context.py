from typing import Any, Dict, Optional


def is_admin_user(db, user_id: int) -> bool:
    user_data = db.get_user_by_id(user_id)
    return bool(user_data and user_data.get("user_type") == "admin")


def get_effective_trading_mode(db, user_id: int) -> str:
    if not is_admin_user(db, user_id):
        return "real"

    mode_query = """
        SELECT is_demo, trading_mode
        FROM user_settings
        WHERE user_id = %s
        ORDER BY
          CASE WHEN trading_enabled = TRUE THEN 0 ELSE 1 END,
          COALESCE(updated_at, created_at) DESC
        LIMIT 1
    """
    mode_result = db.execute_query(mode_query, (user_id,))
    if mode_result:
        row = mode_result[0]
        if row.get("is_demo") in (1, True):
            return "demo"
        if row.get("is_demo") in (0, False):
            return "real"
        if row.get("trading_mode") in {"demo", "real"}:
            return row["trading_mode"]
    return "demo"


def get_effective_is_demo(
    db, user_id: int, requested_mode: Optional[str] = None
) -> bool:
    """Returns boolean True for demo mode, False for real mode."""
    if not is_admin_user(db, user_id):
        return False

    if requested_mode in {"demo", "real"}:
        return requested_mode == "demo"

    return get_effective_trading_mode(db, user_id) == "demo"


def get_trading_context(
    db, user_id: int, requested_mode: Optional[str] = None
) -> Dict[str, Any]:
    is_admin = is_admin_user(db, user_id)
    effective_is_demo = get_effective_is_demo(
        db, user_id, requested_mode=requested_mode
    )
    trading_mode = (
        requested_mode
        if requested_mode in {"demo", "real"}
        else get_effective_trading_mode(db, user_id)
    )
    portfolio_owner_id = user_id
    return {
        "is_admin": is_admin,
        "trading_mode": trading_mode,
        "is_demo": effective_is_demo,
        "active_portfolio": "demo" if effective_is_demo else "real",
        "can_toggle": is_admin,
        "portfolio_owner_id": portfolio_owner_id,
        "current_admin_user_id": user_id if is_admin else None,
    }
