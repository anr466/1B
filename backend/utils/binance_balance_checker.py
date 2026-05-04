"""
Binance Balance Checker - Verifies Binance account balances
"""

import logging

logger = logging.getLogger(__name__)


def check_binance_balance(api_key, api_secret):
    """Check Binance spot account balance"""
    try:
        from binance.spot import Spot
        client = Spot(api_key=api_key, api_secret=api_secret)
        account = client.account()
        balances = account.get("balances", [])
        result = {}
        for b in balances:
            free = float(b.get("free", 0))
            locked = float(b.get("locked", 0))
            if free > 0 or locked > 0:
                result[b["asset"]] = {"free": free, "locked": locked, "total": free + locked}
        return {"success": True, "balances": result}
    except ImportError:
        logger.warning("binance library not installed, cannot check balance")
        return {"success": False, "error": "binance lib not installed"}
    except Exception as e:
        logger.error(f"Balance check error: {e}")
        return {"success": False, "error": str(e)}


def check_futures_balance(api_key, api_secret):
    """Check Binance futures account balance"""
    try:
        from binance.um_futures import UMFutures
        client = UMFutures(key=api_key, secret=api_secret)
        account = client.account()
        assets = account.get("assets", [])
        result = {}
        for a in assets:
            balance = float(a.get("walletBalance", 0))
            if balance > 0:
                result[a["asset"]] = {
                    "wallet_balance": balance,
                    "unrealized_pnl": float(a.get("unrealizedProfit", 0)),
                }
        return {"success": True, "balances": result}
    except ImportError:
        return {"success": False, "error": "binance-futures lib not installed"}
    except Exception as e:
        logger.error(f"Futures balance error: {e}")
        return {"success": False, "error": str(e)}


def get_balance_summary(api_key, api_secret):
    """Get combined spot + futures balance summary"""
    spot = check_binance_balance(api_key, api_secret)
    futures = check_futures_balance(api_key, api_secret)
    return {"spot": spot, "futures": futures}


def validate_api_keys(api_key, api_secret, testnet=False):
    """Validate Binance API keys are working"""
    try:
        from binance.spot import Spot
        base_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        client = Spot(api_key=api_key, api_secret=api_secret, base_url=base_url)
        client.account()
        return {"valid": True, "testnet": testnet}
    except ImportError:
        return {"valid": False, "error": "binance lib not installed"}
    except Exception as e:
        return {"valid": False, "error": str(e)}
