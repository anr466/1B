import 'package:flutter/material.dart';

/// AppIconButton — زر أيقونة موحد للرؤوس والشرائط
/// يدعم IconData أو أي Widget مخصص (مثل BrandIcon)
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class AppIconButton extends StatelessWidget {
  final IconData? icon;
  final Widget? child;
  final VoidCallback? onTap;
  final Color? color;
  final double size;
  final double tapAreaSize;
  final String? tooltip;

  const AppIconButton({
    super.key,
    this.icon,
    this.child,
    this.onTap,
    this.color,
    this.size = 22,
    this.tapAreaSize = 36,
    this.tooltip,
  }) : assert(icon != null || child != null, 'icon or child is required');

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final iconColor = color ?? cs.onSurface.withValues(alpha: 0.5);

    Widget iconWidget = child ??
        Icon(icon!, size: size, color: iconColor);

    Widget content = SizedBox(
      width: tapAreaSize,
      height: tapAreaSize,
      child: Center(child: iconWidget),
    );

    if (tooltip != null) {
      content = Tooltip(message: tooltip!, child: content);
    }

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: content,
    );
  }
}
