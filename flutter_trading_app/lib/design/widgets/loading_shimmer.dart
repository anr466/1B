import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';

/// Loading Shimmer — هيكل بطاقات وهمية متحركة أثناء التحميل
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class LoadingShimmer extends StatelessWidget {
  final int itemCount;
  final double itemHeight;
  final bool isCard;

  const LoadingShimmer({
    super.key,
    this.itemCount = 3,
    this.itemHeight = 80,
    this.isCard = true,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Shimmer.fromColors(
      baseColor: cs.surfaceContainerHighest,
      highlightColor: cs.outline.withValues(alpha: 0.3),
      child: Column(
        children: List.generate(itemCount, (i) {
          return Padding(
            padding: const EdgeInsets.only(bottom: SpacingTokens.md),
            child: Container(
              height: itemHeight,
              decoration: BoxDecoration(
                color: cs.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(
                  isCard ? SpacingTokens.radiusXl : SpacingTokens.radiusSm,
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}

/// Shimmer Box — صندوق shimmer واحد بأبعاد مخصصة
class ShimmerBox extends StatelessWidget {
  final double width;
  final double height;
  final double borderRadius;

  const ShimmerBox({
    super.key,
    required this.width,
    required this.height,
    this.borderRadius = SpacingTokens.radiusSm,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Shimmer.fromColors(
      baseColor: cs.surfaceContainerHighest,
      highlightColor: cs.outline.withValues(alpha: 0.3),
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: cs.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(borderRadius),
        ),
      ),
    );
  }
}
