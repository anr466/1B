import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:trading_app/core/providers/privacy_provider.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Money Text — أرقام مالية بتنسيق + لون PnL
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class MoneyText extends ConsumerWidget {
  final double amount;
  final bool showSign;
  final bool showColor;
  final bool isSensitive;
  final bool isHero;
  final double? fontSize;
  final String prefix;
  final String suffix;

  const MoneyText({
    super.key,
    required this.amount,
    this.showSign = false,
    this.showColor = false,
    this.isSensitive = false,
    this.isHero = false,
    this.fontSize,
    this.prefix = '\$',
    this.suffix = '',
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isHidden = ref.watch(balanceVisibilityProvider);
    final cs = Theme.of(context).colorScheme;
    final formatter = NumberFormat('#,##0.00');

    Color textColor;
    if (showColor) {
      final sem = SemanticColors.of(context);
      if (amount > 0) {
        textColor = sem.positive;
      } else if (amount < 0) {
        textColor = sem.negative;
      } else {
        textColor = cs.onSurface;
      }
    } else {
      textColor = cs.onSurface;
    }

    String sign = '';
    if (showSign && amount > 0) sign = '+';

    final text = (isHidden && isSensitive)
        ? '$prefix••••••$suffix'
        : '$sign$prefix${formatter.format(amount.abs())}$suffix';

    final style = isHero
        ? TypographyTokens.hero(textColor)
        : TypographyTokens.mono(textColor, fontSize: fontSize ?? 15);

    return Text(text, style: style);
  }
}
