import 'package:flutter/material.dart';

/// Responsive helpers for phone/tablet layouts.
class ResponsiveUtils {
  ResponsiveUtils._();

  static double width(BuildContext context) => MediaQuery.sizeOf(context).width;

  static bool isSmallPhone(BuildContext context) => width(context) < 360;

  static bool isTablet(BuildContext context) => width(context) >= 700;

  static double pageHorizontalPadding(BuildContext context) {
    if (isTablet(context)) return 24;
    if (isSmallPhone(context)) return 12;
    return 16;
  }

  static double cardPadding(BuildContext context) {
    if (isTablet(context)) return 20;
    if (isSmallPhone(context)) return 12;
    return 16;
  }

  static double maxContentWidth(BuildContext context) {
    if (isTablet(context)) return 760;
    return double.infinity;
  }

  static int statsColumns(BuildContext context) {
    return isSmallPhone(context) ? 2 : 3;
  }
}
