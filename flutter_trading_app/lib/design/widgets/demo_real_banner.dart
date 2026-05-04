import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/core/providers/admin_provider.dart';

class DemoRealBanner extends ConsumerWidget {
  const DemoRealBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(adminPortfolioModeProvider);
    final isDemo = mode == 'demo';
    final cs = Theme.of(context).colorScheme;
    final color = isDemo ? Colors.blue : cs.error;
    final icon = isDemo ? Icons.science_outlined : Icons.shield_outlined;
    final label = isDemo ? 'الوضع التجريبي — البيانات والمحفظة تجريبية' : 'الوضع الحقيقي — تداول حقيقي على Binance';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.md,
        vertical: SpacingTokens.xs,
      ),
      color: color.withValues(alpha: 0.08),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: SpacingTokens.xs),
          Text(
            label,
            textAlign: TextAlign.center,
            style: TypographyTokens.caption(color).copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
