import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// PnL Indicator — ربح/خسارة بلون + سهم
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class PnlIndicator extends StatelessWidget {
  final double amount;
  final double? percentage;
  final double fontSize;
  final bool compact;

  const PnlIndicator({
    super.key,
    required this.amount,
    this.percentage,
    this.fontSize = 14,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final isPositive = amount >= 0;
    final sem = SemanticColors.of(context);
    final color = isPositive ? sem.positive : sem.negative;

    final formatter = NumberFormat('#,##0.00');
    final sign = isPositive ? '+' : '';
    final arrow = isPositive ? '▲' : '▼';

    final amountText = '$sign\$${formatter.format(amount.abs())}';
    final pctText = percentage != null
        ? ' ($sign${percentage!.toStringAsFixed(1)}%)'
        : '';

    if (compact) {
      return Text(
        '$arrow $amountText$pctText',
        style: TypographyTokens.mono(color, fontSize: fontSize),
      );
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          arrow,
          style: TextStyle(color: color, fontSize: fontSize - 2),
        ),
        const SizedBox(width: SpacingTokens.xs),
        Flexible(
          child: FittedBox(
            fit: BoxFit.scaleDown,
            alignment: AlignmentDirectional.centerStart,
            child: Text(
              '$amountText$pctText',
              style: TypographyTokens.mono(color, fontSize: fontSize),
            ),
          ),
        ),
      ],
    );
  }
}
