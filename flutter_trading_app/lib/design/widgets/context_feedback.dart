import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Context Feedback — Micro-Interaction widget
/// flash خفيف + رسالة تشجيعية سياقية
enum FeedbackType { success, error, warning, info }

class ContextFeedback extends StatefulWidget {
  final String message;
  final FeedbackType type;
  final Duration duration;
  final VoidCallback? onDismissed;

  const ContextFeedback({
    super.key,
    required this.message,
    this.type = FeedbackType.info,
    this.duration = const Duration(seconds: 2),
    this.onDismissed,
  });

  @override
  State<ContextFeedback> createState() => _ContextFeedbackState();
}

class _ContextFeedbackState extends State<ContextFeedback>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnimation;
  late final Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.3),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));

    _controller.forward();

    Future.delayed(widget.duration, () {
      if (mounted) {
        _controller.reverse().then((_) {
          widget.onDismissed?.call();
        });
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = _feedbackColors(context, widget.type);

    return SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: Container(
          margin: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.base,
            vertical: SpacingTokens.sm,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.base,
            vertical: SpacingTokens.md,
          ),
          decoration: BoxDecoration(
            color: colors.bg,
            borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
            border: Border.all(
              color: colors.fg.withValues(alpha: 0.3),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Icon(colors.icon, color: colors.fg, size: 20),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: Text(
                  widget.message,
                  style: TypographyTokens.bodySmall(colors.fg),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static _FeedbackColors _feedbackColors(
    BuildContext context,
    FeedbackType type,
  ) {
    final sem = SemanticColors.of(context);
    final cs = Theme.of(context).colorScheme;
    switch (type) {
      case FeedbackType.success:
        return _FeedbackColors(
          sem.success,
          sem.successContainer,
          Icons.check_circle_outline_rounded,
        );
      case FeedbackType.error:
        return _FeedbackColors(
          cs.error,
          cs.errorContainer,
          Icons.error_outline_rounded,
        );
      case FeedbackType.warning:
        return _FeedbackColors(
          sem.warning,
          sem.warningContainer,
          Icons.warning_amber_rounded,
        );
      case FeedbackType.info:
        return _FeedbackColors(
          sem.info,
          sem.infoContainer,
          Icons.info_outline_rounded,
        );
    }
  }
}

class _FeedbackColors {
  final Color fg;
  final Color bg;
  final IconData icon;
  const _FeedbackColors(this.fg, this.bg, this.icon);
}
