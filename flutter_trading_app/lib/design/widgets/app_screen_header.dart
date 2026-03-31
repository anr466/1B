import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// AppScreenHeader — unified header for all screens
///
/// Replaces raw AppBar and scattered `h1` Text calls.
/// Supports: title + optional subtitle + optional back + optional trailing.
class AppScreenHeader extends StatelessWidget {
  final String title;
  final String? subtitle;
  final bool showBack;
  final Widget? trailing;
  final EdgeInsetsGeometry? padding;

  const AppScreenHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.showBack = false,
    this.trailing,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final effectivePadding =
        padding ??
        const EdgeInsets.symmetric(
          horizontal: SpacingTokens.lg,
          vertical: SpacingTokens.sm,
        );

    return Padding(
      padding: effectivePadding,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // ─── Back button ────────────────────────
          if (showBack) ...[
            GestureDetector(
              onTap: () {
                // Use GoRouter's pop if available, otherwise use Navigator
                if (context.canPop()) {
                  context.pop();
                } else {
                  Navigator.of(context).maybePop();
                }
              },
              behavior: HitTestBehavior.opaque,
              child: SizedBox(
                width: 44,
                height: 44,
                child: Center(
                  child: Padding(
                    padding: const EdgeInsetsDirectional.only(
                      end: SpacingTokens.sm,
                    ),
                    child: Icon(
                      Icons.arrow_back_ios_new_rounded,
                      size: 18,
                      color: cs.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                ),
              ),
            ),
          ],

          // ─── Title + optional subtitle ──────────
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(title, style: TypographyTokens.h2(cs.onSurface)),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle!,
                    style: TypographyTokens.caption(
                      cs.onSurface.withValues(alpha: 0.45),
                    ),
                  ),
                ],
              ],
            ),
          ),

          // ─── Trailing actions ───────────────────
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}
