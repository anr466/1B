import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/services/trading_toggle_service.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';

/// ────────────────────────────────────────────────────────────────
/// TradingToggleButton — زر تفعيل التداول الموحد
/// ────────────────────────────────────────────────────────────────
/// يعمل في سياقين:
/// • Self mode: المستخدم يفعّل/يعطّل تداوله الخاص (مع بابة بيومترية اختيارية)
/// • Admin mode: الأدمن يفعّل/يعطّل تداول مستخدم آخر
/// ────────────────────────────────────────────────────────────────
class TradingToggleButton extends ConsumerStatefulWidget {
  /// القيمة الحالية (null = غير معروف/جاري التحميل)
  final bool? value;

  /// في وضع الأدمن: معرف المستخدم المستهدف
  final int? targetUserId;

  /// في وضع الذاتي: دالة البيومترية (اختيارية)
  final Future<bool> Function(String reason)? biometricAuth;

  /// حجم الزر: compact للقوائم، normal للبطاقات
  final TradingToggleSize size;

  /// نص توضيحي إضافي يظهر تحت الزر
  final String? subtitle;

  /// عند تغيير الحالة (للتحديثات التفاؤلية)
  final ValueChanged<bool>? onChanged;

  const TradingToggleButton({
    super.key,
    this.value,
    this.targetUserId,
    this.biometricAuth,
    this.size = TradingToggleSize.normal,
    this.subtitle,
    this.onChanged,
  });

  bool get isAdminMode => targetUserId != null;

  @override
  ConsumerState<TradingToggleButton> createState() => _TradingToggleButtonState();
}

class _TradingToggleButtonState extends ConsumerState<TradingToggleButton> {
  bool _isLoading = false;

  Future<void> _handleToggle(bool newValue) async {
    if (_isLoading) return;
    if (widget.value == null) return;

    setState(() => _isLoading = true);
    widget.onChanged?.call(newValue);

    final service = ref.read(tradingToggleServiceProvider);

    void showMessage(String msg, String type) {
      final snackType = switch (type) {
        'success' => SnackType.success,
        'error' => SnackType.error,
        'warning' => SnackType.warning,
        _ => SnackType.info,
      };
      AppSnackbar.show(context, message: msg, type: snackType);
    }

    final bool success;
    if (widget.isAdminMode) {
      success = await service.toggleUser(
        targetUserId: widget.targetUserId!,
        enabled: newValue,
        showMessage: showMessage,
      );
    } else {
      success = await service.toggleSelf(
        enabled: newValue,
        biometricAuth: widget.biometricAuth,
        showMessage: showMessage,
      );
    }

    if (!success && mounted) {
      // Rollback optimistic update
      widget.onChanged?.call(!newValue);
    }

    if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final active = widget.value ?? false;
    final isUnknown = widget.value == null;

    if (widget.size == TradingToggleSize.compact) {
      return _buildCompact(cs, active, isUnknown);
    }

    return _buildNormal(cs, active, isUnknown);
  }

  Widget _buildCompact(ColorScheme cs, bool active, bool isUnknown) {
    if (_isLoading || isUnknown) {
      return SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(strokeWidth: 2, color: cs.primary),
      );
    }
    return Switch(
      value: active,
      onChanged: _handleToggle,
      activeTrackColor: cs.primary,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  Widget _buildNormal(ColorScheme cs, bool active, bool isUnknown) {
    final statusColor = active ? cs.primary : cs.tertiary;
    final label = active ? 'مفعّل' : 'معطّل';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            if (_isLoading || isUnknown)
              SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: cs.primary,
                ),
              )
            else
              Switch(
                value: active,
                onChanged: _handleToggle,
                activeTrackColor: cs.primary,
              ),
            const SizedBox(width: SpacingTokens.xs),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: SpacingTokens.sm,
                vertical: 4,
              ),
              decoration: BoxDecoration(
                color: statusColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
              ),
              child: Text(
                label,
                style: TypographyTokens.bodySmall(statusColor).copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        if (widget.subtitle != null) ...[
          const SizedBox(height: 4),
          Text(
            widget.subtitle!,
            style: TypographyTokens.caption(
              cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
        ],
      ],
    );
  }
}

enum TradingToggleSize { compact, normal }
