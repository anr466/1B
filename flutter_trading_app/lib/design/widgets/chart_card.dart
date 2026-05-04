import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';

/// Chart Card — بطاقة رسم بياني ناعمة
///
/// الاستخدام:
/// ```dart
/// ChartCard(
///   title: 'أداء المحفظة',
///   data: [10, 20, 15, 30, 25, 35, 40],
///   labels: ['سبت', 'أحد', 'إثن', 'ثلا', 'أرب', 'خمي', 'جمع'],
/// )
/// ```
class ChartCard extends StatelessWidget {
  final String title;
  final List<double> data;
  final List<String>? labels;
  final String? currentValue;
  final String? change;
  final bool? isPositive;
  final Color? lineColor;
  final double height;

  const ChartCard({
    super.key,
    required this.title,
    required this.data,
    this.labels,
    this.currentValue,
    this.change,
    this.isPositive,
    this.lineColor,
    this.height = 200,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final isDark = cs.brightness == Brightness.dark;

    final effectiveColor =
        lineColor ??
        (isPositive == true
            ? semantic.positive
            : isPositive == false
            ? semantic.negative
            : cs.primary);

    return Container(
      padding: const EdgeInsets.all(SpacingTokens.md),
      decoration: BoxDecoration(
        color: isDark ? cs.surfaceContainerHigh : cs.surfaceContainerLow,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
        border: Border.all(
          color: cs.outline.withValues(alpha: isDark ? 0.10 : 0.08),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title.toUpperCase(),
                style: TypographyTokens.overline(
                  cs.onSurface.withValues(alpha: 0.5),
                ).copyWith(letterSpacing: 1.5, fontSize: 10),
              ),
              if (currentValue != null || change != null)
                Row(
                  children: [
                    if (currentValue != null)
                      Text(
                        currentValue!,
                        style: TypographyTokens.body(
                          cs.onSurface,
                        ).copyWith(fontWeight: FontWeight.w700),
                      ),
                    if (change != null) ...[
                      const SizedBox(width: SpacingTokens.xs),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: effectiveColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          change!,
                          style: TypographyTokens.caption(
                            effectiveColor,
                          ).copyWith(fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ],
                ),
            ],
          ),
          const SizedBox(height: SpacingTokens.md),
          // Chart
          SizedBox(
            height: height,
            child: LineChart(
              LineChartData(
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: _calculateInterval(data),
                  getDrawingHorizontalLine: (value) {
                    return FlLine(
                      color: cs.outline.withValues(alpha: isDark ? 0.08 : 0.06),
                      strokeWidth: 1,
                    );
                  },
                ),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: labels != null && labels!.isNotEmpty,
                      reservedSize: 24,
                      interval: 1,
                      getTitlesWidget: (value, meta) {
                        if (labels == null || value.toInt() >= labels!.length) {
                          return const SizedBox.shrink();
                        }
                        return Text(
                          labels![value.toInt()],
                          style: TypographyTokens.caption(
                            cs.onSurface.withValues(alpha: 0.4),
                          ).copyWith(fontSize: 10),
                        );
                      },
                    ),
                  ),
                ),
                borderData: FlBorderData(show: false),
                minX: 0,
                maxX: data.length.toDouble() - 1,
                minY: _minValue(data),
                maxY: _maxValue(data),
                lineBarsData: [
                  LineChartBarData(
                    spots: data
                        .asMap()
                        .entries
                        .map((e) => FlSpot(e.key.toDouble(), e.value))
                        .toList(),
                    isCurved: true,
                    curveSmoothness: 0.3,
                    color: effectiveColor,
                    barWidth: 2.5,
                    isStrokeCapRound: true,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          effectiveColor.withValues(alpha: 0.15),
                          effectiveColor.withValues(alpha: 0.0),
                        ],
                      ),
                    ),
                  ),
                ],
                lineTouchData: LineTouchData(
                  enabled: true,
                  touchTooltipData: LineTouchTooltipData(
                    getTooltipColor: (touchedSpot) =>
                        isDark ? cs.surfaceContainerHighest : cs.surfaceContainerHighest,
                    tooltipPadding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    getTooltipItems: (touchedSpots) {
                      return touchedSpots.map((spot) {
                        return LineTooltipItem(
                          spot.y.toStringAsFixed(2),
                          TypographyTokens.bodySmall(
                            cs.onSurface,
                          ).copyWith(fontWeight: FontWeight.w600),
                        );
                      }).toList();
                    },
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  double _minValue(List<double> data) {
    if (data.isEmpty) return 0;
    final min = data.reduce((a, b) => a < b ? a : b);
    return min > 0 ? min * 0.9 : min * 1.1;
  }

  double _maxValue(List<double> data) {
    if (data.isEmpty) return 0;
    final max = data.reduce((a, b) => a > b ? a : b);
    return max > 0 ? max * 1.1 : max * 0.9;
  }

  double _calculateInterval(List<double> data) {
    if (data.isEmpty) return 1;
    final min = data.reduce((a, b) => a < b ? a : b);
    final max = data.reduce((a, b) => a > b ? a : b);
    final range = max - min;
    if (range == 0) return 1;
    return range / 4;
  }
}
