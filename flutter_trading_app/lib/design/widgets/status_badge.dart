import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Status Badge — success/warning/error/info badge
/// تصميم صافي — لا يعتمد على أي منطق أعمال
enum BadgeType { success, warning, error, info }

class StatusBadge extends StatelessWidget {
  final String text;
  final BadgeType type;
  final bool showDot;

  const StatusBadge({
    super.key,
    required this.text,
    this.type = BadgeType.info,
    this.showDot = true,
  });

  @override
  Widget build(BuildContext context) {
    final colors = _badgeColors(context, type);

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.sm,
        vertical: SpacingTokens.xs,
      ),
      decoration: BoxDecoration(
        color: colors.bg,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusBadge),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showDot) ...[
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: colors.fg,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: SpacingTokens.xs),
          ],
          Text(text, style: TypographyTokens.caption(colors.fg)),
        ],
      ),
    );
  }

  static _BadgeColors _badgeColors(BuildContext context, BadgeType type) {
    final sem = SemanticColors.of(context);
    final cs = Theme.of(context).colorScheme;
    switch (type) {
      case BadgeType.success:
        return _BadgeColors(sem.success, sem.successContainer);
      case BadgeType.warning:
        return _BadgeColors(sem.warning, sem.warningContainer);
      case BadgeType.error:
        return _BadgeColors(cs.error, cs.errorContainer);
      case BadgeType.info:
        return _BadgeColors(sem.info, sem.infoContainer);
    }
  }
}

class _BadgeColors {
  final Color fg;
  final Color bg;
  const _BadgeColors(this.fg, this.bg);
}
