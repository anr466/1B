import 'package:flutter/material.dart';

/// Bento Grid — شبكة غير متماثلة لعرض البطاقات
/// مستوحى من تصميمات Apple Health و Linear
///
/// الاستخدام:
/// ```dart
/// BentoGrid(
///   children: [
///     BentoItem(span: const BentoSpan(rows: 2, cols: 2), child: BalanceCard()),
///     BentoItem(span: const BentoSpan(rows: 1, cols: 2), child: PnLCard()),
///     BentoItem(span: const BentoSpan(rows: 1, cols: 1), child: StatusCard()),
///     BentoItem(span: const BentoSpan(rows: 1, cols: 1), child: StatsCard()),
///   ],
/// )
/// ```
class BentoGrid extends StatelessWidget {
  final List<BentoItem> children;
  final double gap;
  final EdgeInsetsGeometry? padding;

  const BentoGrid({
    super.key,
    required this.children,
    this.gap = 12,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding ?? EdgeInsets.zero,
      child: _BentoLayout(gap: gap, children: children),
    );
  }
}

/// عنصر في Bento Grid
class BentoItem extends StatelessWidget {
  final Widget child;
  final BentoSpan span;

  const BentoItem({
    super.key,
    required this.child,
    this.span = const BentoSpan(rows: 1, cols: 1),
  });

  @override
  Widget build(BuildContext context) => child;
}

/// حجم العنصر في الشبكة
class BentoSpan {
  final int rows;
  final int cols;

  const BentoSpan({this.rows = 1, this.cols = 1});
}

/// التخطيط الداخلي — يستخدم SliverGrid مع custom delegate
class _BentoLayout extends StatelessWidget {
  final List<BentoItem> children;
  final double gap;

  const _BentoLayout({required this.children, required this.gap});

  @override
  Widget build(BuildContext context) {
    // نحسب الـ crossAxisCount بناءً على أعرض عنصر
    final maxCols = children.fold<int>(
      1,
      (max, item) => item.span.cols > max ? item.span.cols : max,
    );

    return CustomScrollView(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      slivers: [
        SliverPadding(
          padding: EdgeInsets.zero,
          sliver: SliverGrid(
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: maxCols,
              mainAxisSpacing: gap,
              crossAxisSpacing: gap,
              // الـ childAspectRatio يُحسب ديناميكياً
              childAspectRatio: 1.0,
            ),
            delegate: SliverChildListDelegate(
              children.map((item) {
                return _BentoCell(
                  span: item.span,
                  maxCols: maxCols,
                  child: item.child,
                );
              }).toList(),
            ),
          ),
        ),
      ],
    );
  }
}

/// خلية فردية في الشبكة
class _BentoCell extends StatelessWidget {
  final BentoSpan span;
  final int maxCols;
  final Widget child;

  const _BentoCell({
    required this.span,
    required this.maxCols,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    // نحسب الـ aspect ratio بناءً على span
    // كل خلية أساسية تأخذ مساحة متساوية
    // العناصر الأكبر تأخذ مساحة مضاعفة
    final aspectRatio = (span.cols / span.rows);

    return LayoutBuilder(
      builder: (context, constraints) {
        // نحسب ارتفاع الخلية بناءً على العرض
        final cellWidth = constraints.maxWidth;
        final cellHeight = cellWidth / aspectRatio;

        return SizedBox(width: cellWidth, height: cellHeight, child: child);
      },
    );
  }
}

/// Bento Grid بسيط — للتخطيطات الثابتة
/// يستخدم Column مع Cards بدلاً من Grid معقد
class BentoSimple extends StatelessWidget {
  final List<Widget> children;
  final double gap;
  final EdgeInsetsGeometry? padding;

  const BentoSimple({
    super.key,
    required this.children,
    this.gap = 12,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding ?? EdgeInsets.zero,
      child: Column(
        children:
            children
                .map(
                  (child) => Padding(
                    padding: EdgeInsets.only(bottom: gap),
                    child: child,
                  ),
                )
                .toList()
              ..removeLast(), // إزالة padding من آخر عنصر
      ),
    );
  }
}

/// صف Bento — عنصران بجانب بعض
class BentoRow extends StatelessWidget {
  final Widget left;
  final Widget right;
  final double gap;
  final double? leftFlex;
  final double? rightFlex;

  const BentoRow({
    super.key,
    required this.left,
    required this.right,
    this.gap = 12,
    this.leftFlex,
    this.rightFlex,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(flex: (leftFlex ?? 1).toInt(), child: left),
        SizedBox(width: gap),
        Expanded(flex: (rightFlex ?? 1).toInt(), child: right),
      ],
    );
  }
}

/// شبكة Bento 2x2
class BentoGrid2x2 extends StatelessWidget {
  final Widget topLeft;
  final Widget topRight;
  final Widget bottomLeft;
  final Widget bottomRight;
  final double gap;

  const BentoGrid2x2({
    super.key,
    required this.topLeft,
    required this.topRight,
    required this.bottomLeft,
    required this.bottomRight,
    this.gap = 12,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        BentoRow(left: topLeft, right: topRight, gap: gap),
        SizedBox(height: gap),
        BentoRow(left: bottomLeft, right: bottomRight, gap: gap),
      ],
    );
  }
}
