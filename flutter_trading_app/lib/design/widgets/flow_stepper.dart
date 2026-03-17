import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

class FlowStepper extends StatelessWidget {
  final List<String> steps;
  final int currentStep;
  final String title;

  const FlowStepper({
    super.key,
    required this.steps,
    required this.currentStep,
    required this.title,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final total = steps.isEmpty ? 1 : steps.length;
    final safeCurrent = currentStep.clamp(0, total - 1);

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.base,
        vertical: SpacingTokens.md,
      ),
      decoration: BoxDecoration(
        color: cs.surfaceContainerLowest,
        border: Border(
          bottom: BorderSide(
            color: cs.outline.withValues(alpha: 0.12),
            width: 1,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title,
                style: TypographyTokens.caption(
                  cs.onSurface.withValues(alpha: 0.6),
                ),
              ),
              Text(
                'الخطوة ${safeCurrent + 1} من $total',
                style: TypographyTokens.caption(cs.primary),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.sm),
          Row(
            children: [
              for (int i = 0; i < total; i++) ...[
                if (i > 0)
                  Expanded(
                    child: Container(
                      height: 2,
                      margin: const EdgeInsets.only(bottom: 22),
                      color: i <= safeCurrent
                          ? cs.primary.withValues(alpha: 0.65)
                          : cs.outline.withValues(alpha: 0.2),
                    ),
                  ),
                _FlowStepNode(
                  index: i,
                  label: steps[i],
                  isDone: i < safeCurrent,
                  isActive: i == safeCurrent,
                ),
              ],
            ],
          ),
          const SizedBox(height: SpacingTokens.xs),
          ClipRRect(
            borderRadius: BorderRadius.circular(SpacingTokens.radiusFull),
            child: LinearProgressIndicator(
              value: (safeCurrent + 1) / total,
              minHeight: 4,
              backgroundColor: cs.outline.withValues(alpha: 0.15),
              color: cs.primary,
            ),
          ),
        ],
      ),
    );
  }
}

class _FlowStepNode extends StatelessWidget {
  final int index;
  final String label;
  final bool isDone;
  final bool isActive;

  const _FlowStepNode({
    required this.index,
    required this.label,
    required this.isDone,
    required this.isActive,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final active = isDone || isActive;

    return SizedBox(
      width: 58,
      child: Column(
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: active ? cs.primary : cs.surfaceContainerHighest,
              border: Border.all(
                color: active ? cs.primary : cs.outline.withValues(alpha: 0.3),
              ),
            ),
            child: Center(
              child: isDone
                  ? Icon(Icons.check_rounded, size: 14, color: cs.onPrimary)
                  : Text(
                      '${index + 1}',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: active
                            ? cs.onPrimary
                            : cs.onSurface.withValues(alpha: 0.5),
                      ),
                    ),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            maxLines: 2,
            textAlign: TextAlign.center,
            style: TypographyTokens.caption(
              active ? cs.primary : cs.onSurface.withValues(alpha: 0.45),
            ),
          ),
        ],
      ),
    );
  }
}
