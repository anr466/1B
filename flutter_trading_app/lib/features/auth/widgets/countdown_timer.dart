import 'dart:async';
import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Countdown Timer — عداد تنازلي لإعادة إرسال OTP
class CountdownTimer extends StatefulWidget {
  final int seconds;
  final VoidCallback? onFinished;

  const CountdownTimer({super.key, this.seconds = 60, this.onFinished});

  @override
  State<CountdownTimer> createState() => _CountdownTimerState();
}

class _CountdownTimerState extends State<CountdownTimer> {
  late int _remaining;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _remaining = widget.seconds;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_remaining <= 1) {
        _timer?.cancel();
        widget.onFinished?.call();
      }
      if (mounted) {
        setState(() => _remaining--);
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final minutes = (_remaining ~/ 60).toString().padLeft(2, '0');
    final secs = (_remaining % 60).toString().padLeft(2, '0');

    return Text(
      'إعادة الإرسال بعد $minutes:$secs',
      style: TypographyTokens.bodySmall(cs.onSurface.withValues(alpha: 0.4)),
    );
  }
}
