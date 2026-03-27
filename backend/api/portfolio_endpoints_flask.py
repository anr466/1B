from flask import Blueprint, jsonify, request
from backend.infrastructure.db_access import get_db_manager
from backend.utils.trading_context import get_effective_is_demo

portfolio_bp = Blueprint("portfolio", __name__)


@portfolio_bp.route("/portfolio", methods=["GET"])
def get_portfolio():
    """
    Portfolio endpoint - يحلل mode من query parameter ويعيد المحفظة المناسبة.
    مسار التطبيق: GET /api/portfolio?user_id=X&mode=demo|real
    """
    # الحصول على user_id من header أو query parameter
    user_id_header = request.headers.get("X-User-Id")
    user_id = None

    if user_id_header:
        try:
            user_id = int(user_id_header)
        except ValueError:
            pass

    if user_id is None:
        user_id_param = request.args.get("user_id")
        if user_id_param:
            try:
                user_id = int(user_id_param)
            except ValueError:
                return jsonify({"error": "invalid_user", "code": "BAD_REQUEST"}), 400

    if user_id is None:
        return jsonify({"error": "unauthenticated", "code": "UNAUTH"}), 401

    # الحصول على mode من query parameter
    requested_mode = request.args.get("mode", None)

    try:
        db = get_db_manager()

        # تحديد is_demo بناءً على mode والصلاحيات
        from backend.utils.trading_context import is_admin_user

        is_admin = is_admin_user(db, user_id)

        if is_admin and requested_mode in ("demo", "real"):
            is_demo = requested_mode == "demo"
        elif is_admin:
            is_demo = get_effective_is_demo(db, user_id)
        else:
            is_demo = False  # المستخدم العادي = real فقط

        is_demo_bool = bool(is_demo)

        with db.get_connection() as conn:
            row = conn.execute(
                """SELECT balance, available_balance, total_profit_loss, is_demo 
                   FROM portfolio 
                   WHERE user_id = %s AND is_demo = %s
                   LIMIT 1""",
                (user_id, is_demo_bool),
            ).fetchone()

        if row:
            bal, avail, pnl, row_is_demo = row
            payload = {
                "user_id": user_id,
                "balance": float(bal or 0.0),
                "available_balance": float(avail or 0.0),
                "total_profit_loss": float(pnl or 0.0),
                "is_demo": bool(row_is_demo),
                "mode": "demo" if is_demo_bool else "real",
            }
        else:
            payload = {
                "user_id": user_id,
                "balance": 0.0,
                "available_balance": 0.0,
                "total_profit_loss": 0.0,
                "is_demo": is_demo_bool,
                "mode": "demo" if is_demo_bool else "real",
            }
        return jsonify(payload)
    except Exception:
        return jsonify({"error": "portfolio_fetch_error", "code": "SERVER_ERROR"}), 500
