"""
Scanner Mixin — البحث عن فرص دخول جديدة وفحص حالة السوق
==========================================================
Extracted from group_b_system.py (God Object split)

Methods:
    _scan_for_entries, _check_market_regime, _add_indicators
"""

from datetime import datetime
from typing import Dict, List
import pandas as pd

# Cognitive imports (optional)
try:
    from backend.cognitive.cognitive_orchestrator import CognitiveAction
    COGNITIVE_IMPORT_OK = True
except ImportError:
    COGNITIVE_IMPORT_OK = False


class ScannerMixin:
    """Mixin for market scanning and entry signal detection"""

    def _scan_for_entries(self) -> List[Dict]:
        """
        البحث عن فرص دخول جديدة
        ===== Strategy Interface (BaseStrategy) =====
        النظام يستدعي self.strategy فقط — لا يعرف أي استراتيجية يشغّل
        
        ✅ Phase 0+1: Risk Protection مفعّلة
        """
        entries = []
        symbols_to_scan = self.config['symbols_pool']
        strategy_name = self.strategy.name if self.strategy else 'none'
        self.logger.info(f"\n🔍 [{strategy_name}] Scanning {len(symbols_to_scan)} symbols for entries...")
        
        # ===== Phase 0+1: فحص بوابات الحماية قبل أي شيء =====
        portfolio = self._load_user_portfolio()
        balance = portfolio.get('balance', 0)
        open_positions = self._get_open_positions()
        
        can_trade, gate_reason = self._check_risk_gates(open_positions, balance)
        if not can_trade:
            self.logger.info(f"   🛡️ Risk Gate BLOCKED: {gate_reason}")
            return entries
        
        # فحص حالة السوق العامة أولاً (عبر BTC)
        market_ok = self._check_market_regime()
        if not market_ok:
            self.logger.info("   ⚠️ Market regime unfavorable - skipping new entries")
            return entries
        
        # 📈 فلتر ساعات التداول (التعلم التكيّفي)
        if self.optimizer:
            try:
                hour_ok, hour_reason = self.optimizer.is_good_trading_hour()
                if not hour_ok:
                    self.logger.info(f"   📈 Adaptive BLOCKED: {hour_reason}")
                    return entries
            except Exception as e:
                self.logger.warning(f"⚠️ Hour filter error: {e}")
        
        # 📈 ترتيب العملات بالأداء (التعلم التكيّفي)
        if self.optimizer:
            try:
                symbols_to_scan = self.optimizer.get_preferred_symbols(
                    symbols_to_scan, top_n=len(symbols_to_scan)
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Symbol ranking error: {e}")
        
        # ========== Strategy Entry Detection (via BaseStrategy interface) ==========
        # ✅ النظام يستدعي self.strategy فقط — لا يعرف أي استراتيجية يشغّل
        if self.strategy:
            qualified_signals = []  # [(symbol, signal, predicted_wr, score)]
            timeframe = self.config.get('execution_timeframe', '1h')
            
            for symbol in symbols_to_scan:
                try:
                    # فحص القائمة السوداء
                    if self.dynamic_blacklist.is_blacklisted(symbol):
                        continue
                    
                    # جلب البيانات بالإطار الزمني المحدد من الاستراتيجية
                    df = self.data_provider.get_historical_data(symbol, timeframe, limit=200)
                    if df is None or len(df) < 70:
                        continue
                    
                    # تحضير البيانات (إضافة المؤشرات — عبر الواجهة الموحدة)
                    df = self.strategy.prepare_data(df)
                    
                    # تحديد اتجاه السوق (عبر الواجهة الموحدة)
                    trend = self.strategy.get_market_trend(df)
                    
                    # كشف إشارة الدخول (عبر الواجهة الموحدة)
                    signal = self.strategy.detect_entry(df, {'trend': trend})
                    
                    if signal:
                        # ===== Phase 1: Capital Stress — فحص تكدس الاتجاه =====
                        dir_ok, dir_reason = self._check_directional_stress(open_positions, signal['side'])
                        if not dir_ok:
                            self.logger.info(f"   🛡️ [{symbol}] Directional Stress BLOCKED: {dir_reason}")
                            continue
                        
                        # 📈 استخراج المؤشرات للتعلم (عبر الواجهة الموحدة)
                        entry_indicators = self.strategy.extract_entry_indicators(df)
                        entry_indicators['trend_4h'] = trend
                        entry_indicators['score'] = signal.get('score', 0)
                        signal['_entry_indicators'] = entry_indicators
                        
                        # 📈 تقييم جودة الإشارة (التعلم التكيّفي)
                        predicted_wr = 0.5
                        if self.optimizer and entry_indicators:
                            try:
                                sig_score = self.optimizer.score_signal(symbol, entry_indicators)
                                predicted_wr = sig_score.get('predicted_wr', 0.5)
                                if not sig_score.get('should_trade', True):
                                    self.logger.info(
                                        f"   📈 [{symbol}] Signal REJECTED: "
                                        f"{sig_score.get('reason', '?')} "
                                        f"(WR={predicted_wr:.0%})")
                                    continue
                            except Exception as e:
                                self.logger.warning(f"⚠️ Signal scoring error: {e}")
                        
                        # ✅ إضافة للمرشحين بدلاً من الدخول فوراً
                        sig_score_val = signal.get('score', 0)
                        qualified_signals.append((symbol, signal, predicted_wr, sig_score_val))
                        self.logger.info(
                            f"   🎯 [{symbol}] {signal['side']} QUALIFIED: "
                            f"{signal.get('strategy', strategy_name)} | Score={sig_score_val} | "
                            f"WR={predicted_wr:.0%} | Trend: {trend}"
                        )
                    
                except Exception as e:
                    self.logger.error(f"Error scanning {symbol}: {e}")
            
            # ✅ اختيار الأفضل من المرشحين
            if qualified_signals:
                # ترتيب: الأولوية لـ predicted_wr ثم score
                qualified_signals.sort(
                    key=lambda x: (x[2], x[3]),  # (predicted_wr, score)
                    reverse=True
                )
                
                self.logger.info(
                    f"   📊 {len(qualified_signals)} qualified signals — "
                    f"picking best (max 2):"
                )
                for i, (sym, sig, wr, sc) in enumerate(qualified_signals):
                    marker = "→ ✅" if i < 2 else "  ⏭️"
                    self.logger.info(
                        f"   {marker} #{i+1} {sym}: WR={wr:.0%} Score={sc} "
                        f"{sig['side']} {sig.get('strategy', strategy_name)}"
                    )
                
                # فتح أفضل 1-2 إشارات
                for sym, sig, wr, sc in qualified_signals:
                    if len(entries) >= 2:
                        break
                    entry = self._open_position(sym, sig)
                    if entry:
                        entries.append(entry)
                        open_positions = self._get_open_positions()
            else:
                self.logger.info("   📊 No qualified signals this cycle")
            
            return entries
        
        # ========== Fallback: النظام المعرفي (إذا V7 غير متاح) ==========
        exec_tf = self.config.get('execution_timeframe', '4h')
        conf_tf = self.config.get('confirmation_timeframe', '1h')
        min_confidence = self.config.get('min_entry_confidence', 60)
        
        for symbol in symbols_to_scan:
            try:
                if self.dynamic_blacklist.is_blacklisted(symbol):
                    continue
                
                df_4h = self.data_provider.get_historical_data(symbol, exec_tf, limit=100)
                if df_4h is None or len(df_4h) < 50:
                    continue
                
                df_1h = self.data_provider.get_historical_data(symbol, conf_tf, limit=50)
                
                if self.cognitive_orchestrator:
                    cognitive_decision = self.cognitive_orchestrator.analyze_entry(
                        symbol=symbol, df_4h=df_4h, df_1h=df_1h
                    )
                    
                    if COGNITIVE_IMPORT_OK and cognitive_decision.action == CognitiveAction.ENTER:
                        signal = {
                            'signal_type': cognitive_decision.entry_strategy.value,
                            'confidence': cognitive_decision.confidence,
                            'entry_price': cognitive_decision.entry_price,
                            'stop_loss': cognitive_decision.stop_loss,
                            'take_profit': cognitive_decision.take_profit,
                            'side': 'LONG',
                            'reasons': [cognitive_decision.entry_logic],
                        }
                        
                        entry = self._open_position(symbol, signal)
                        if entry:
                            entries.append(entry)
                            if len(entries) >= 2:
                                break
                
            except Exception as e:
                self.logger.error(f"Error scanning {symbol}: {e}")
        
        return entries

    def _check_market_regime(self) -> bool:
        """
        فحص حالة السوق العامة عبر BTC
        لا ندخل صفقات جديدة إذا كان السوق في حالة هبوط حاد أو تقلب شديد
        """
        try:
            df = self.data_provider.get_historical_data('BTCUSDT', '1h', limit=50)
            if df is None or len(df) < 30:
                return True  # في حال عدم توفر بيانات BTC، نسمح بالدخول
            
            df = self._add_indicators(df)
            
            last = df.iloc[-1]
            rsi = last.get('rsi', 50)
            
            # فحص RSI المتطرف
            if rsi < 25:
                self.logger.info(f"   🌡️ BTC RSI={rsi:.1f} (extreme oversold) - cautious entry")
            
            # فحص الانهيار الحاد (أكثر من 5% هبوط في 24 ساعة)
            if len(df) >= 24:
                price_24h_ago = df.iloc[-24]['close']
                price_now = df.iloc[-1]['close']
                change_24h = (price_now - price_24h_ago) / price_24h_ago
                
                if change_24h < -0.05:
                    self.logger.warning(f"   🚨 BTC crashed {change_24h*100:.1f}% in 24h - blocking entries")
                    return False
                
                if change_24h < -0.03:
                    self.logger.info(f"   ⚠️ BTC down {change_24h*100:.1f}% in 24h - reduced entries")
            
            # فحص التقلب العالي (ATR > 3% من السعر)
            if len(df) >= 14:
                atr = df['close'].diff().abs().rolling(14).mean().iloc[-1]
                atr_pct = atr / df.iloc[-1]['close']
                if atr_pct > 0.03:
                    self.logger.warning(f"   🌊 BTC volatility too high (ATR={atr_pct*100:.1f}%) - blocking entries")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️ Market regime check failed: {e} — blocking entries (No classification → No trade)")
            return False  # قانون: لا تصنيف = لا تداول

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """إضافة المؤشرات الفنية"""
        df = df.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['std'] = df['close'].rolling(window=20).std()
        df['bb_lower'] = df['sma_20'] - (2 * df['std'])
        df['bb_upper'] = df['sma_20'] + (2 * df['std'])
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df
