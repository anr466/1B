#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binance Utilities — Precision, Filters, and OCO Management
==========================================================
يحتوي على دوال مساعدة لضمان دقة الأرقام، توافق الفلاتر، وإدارة أوامر OCO.
"""

import logging
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)


def round_step_size(quantity, step_size):
    """تقريب الكمية لتتوافق مع STEP_SIZE الخاص بـ Binance"""
    precision = len(step_size.rstrip('0').split('.')[-1])
    return round(quantity - (quantity % float(step_size)), precision)


def round_price(price, tick_size):
    """تقريب السعر لتتوافق مع TICK_SIZE الخاص بـ Binance"""
    precision = len(tick_size.rstrip('0').split('.')[-1])
    return round(price - (price % float(tick_size)), precision)


def get_symbol_filters(client, symbol):
    """جلب فلاتر الرمز (Step Size, Tick Size, Min Notional)"""
    try:
        info = client.get_symbol_info(symbol)
        filters = {f['filterType']: f for f in info['filters']}
        return filters
    except Exception as e:
        logger.error(f"❌ Failed to get filters for {symbol}: {e}")
        return {}


def prepare_order_params(client, symbol, side, quantity, price=None, stop_price=None, stop_limit_price=None):
    """
    تحضير معاملات الطلب لضمان توافقها مع فلاتر Binance.
    يرجع قاموس المعاملات الجاهزة للإرسال أو None في حال الخطأ.
    """
    filters = get_symbol_filters(client, symbol)
    if not filters:
        return None

    lot_size = filters.get('LOT_SIZE', {})
    tick_size = filters.get('PRICE_FILTER', {})
    min_notional = filters.get('MIN_NOTIONAL', {})
    
    # 1. Validate Min Notional
    min_qty = float(lot_size.get('minQty', 0))
    if quantity < min_qty:
        logger.warning(f"⚠️ Quantity {quantity} < Min Qty {min_qty} for {symbol}")
        return None

    # 2. Round Quantity
    step_size = lot_size.get('stepSize', '0.00000001')
    quantity = round_step_size(quantity, step_size)

    # 3. Round Prices
    tick = tick_size.get('tickSize', '0.01')
    if price:
        price = round_price(price, tick)
    if stop_price:
        stop_price = round_price(stop_price, tick)
    if stop_limit_price:
        stop_limit_price = round_price(stop_limit_price, tick)

    # 4. Final Check Notional
    notional = quantity * (price or stop_price or 0)
    min_notional_val = float(min_notional.get('minNotional', 5.0)) # Default 5$
    if notional < min_notional_val:
        logger.warning(f"⚠️ Notional {notional:.2f} < Min Notional {min_notional_val} for {symbol}")
        return None

    params = {
        'symbol': symbol,
        'side': side,
        'quantity': quantity
    }
    if price: params['price'] = price
    if stop_price: params['stopPrice'] = stop_price
    if stop_limit_price: params['stopLimitPrice'] = stop_limit_price

    return params


def place_oco_order(client, symbol, side, quantity, take_profit_price, stop_loss_price):
    """
    وضع أمر OCO (One-Cancels-the-Other) على Binance.
    هذا الأمر يحمي الصفقة حتى لو انقطع البوت.
    
    Args:
        side: 'SELL' or 'BUY'
        quantity: الكمية
        take_profit_price: سعر الهدف
        stop_loss_price: سعر وقف الخسارة
    """
    try:
        # Stop Limit Price يجب أن يكون أسوأ قليلاً من Stop Price لضمان التنفيذ
        # للـ Sell: Stop Limit < Stop Price
        # للـ Buy: Stop Limit > Stop Price
        buffer_pct = 0.002 # 0.2% buffer
        if side == 'SELL':
            stop_limit = stop_loss_price * (1 - buffer_pct)
        else:
            stop_limit = stop_loss_price * (1 + buffer_pct)

        params = prepare_order_params(
            client, symbol, side, quantity,
            price=take_profit_price,
            stop_price=stop_loss_price,
            stop_limit_price=stop_limit
        )
        
        if not params:
            return None

        # Binance OCO API
        order = client.create_oco_order(
            symbol=params['symbol'],
            side=params['side'],
            quantity=params['quantity'],
            price=str(params['price']),
            stopPrice=str(params['stopPrice']),
            stopLimitPrice=str(params['stopLimitPrice']),
            stopLimitTimeInForce='GTC'
        )
        
        logger.info(f"✅ OCO Order placed for {symbol} | TP: {params['price']} | SL: {params['stopPrice']}")
        return order

    except BinanceAPIException as e:
        logger.error(f"❌ Binance OCO Error for {symbol}: {e.message}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected Error placing OCO for {symbol}: {e}")
        return None


def cancel_oco_order(client, symbol, order_list_id):
    """إلغاء أمر OCO محدد"""
    try:
        client.cancel_oco_order(symbol=symbol, orderListId=order_list_id)
        logger.info(f"🚫 OCO Order {order_list_id} cancelled for {symbol}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to cancel OCO {order_list_id}: {e}")
        return False
