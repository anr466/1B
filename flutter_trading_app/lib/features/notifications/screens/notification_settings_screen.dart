import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/core/models/notification_settings_model.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';

/// Notification Settings Screen — إعدادات إشعارات المستخدم (Self-service)
class NotificationSettingsScreen extends ConsumerStatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  ConsumerState<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState
    extends ConsumerState<NotificationSettingsScreen> {
  NotificationSettingsModel? _settings;
  bool _loading = true;
  bool _saving = false;
  bool _hasChanges = false;

  static const _reportTimeOptions = ['21:00', '22:00', '23:00', '00:00'];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final repo = ref.read(notificationsRepositoryProvider);
      final settings = await repo.getNotificationSettings();
      if (!mounted) return;
      setState(() {
        _settings = settings;
        _loading = false;
        _hasChanges = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _settings = null;
        _loading = false;
      });
      AppSnackbar.show(
        context,
        message: 'تعذر تحميل الإعدادات من الخادم',
        type: SnackType.error,
      );
    }
  }

  Future<void> _save() async {
    final current = _settings;
    if (current == null) return;

    setState(() => _saving = true);
    try {
      final repo = ref.read(notificationsRepositoryProvider);
      final next = await repo.updateNotificationSettings(current);
      if (!mounted) return;
      setState(() {
        _settings = next;
        _hasChanges = false;
      });
      AppSnackbar.show(
        context,
        message: UxMessages.success,
        type: SnackType.success,
      );
    } catch (e) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: e.toString().replaceFirst('Exception: ', ''),
        type: SnackType.error,
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _update(NotificationSettingsModel next) {
    setState(() {
      _settings = next;
      _hasChanges = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        appBar: AppBar(
          title: Text(
            'إعدادات الإشعارات',
            style: TypographyTokens.h3(cs.onSurface),
          ),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _settings == null
            ? Center(
                child: Text(
                  'تعذر تحميل البيانات',
                  style: TypographyTokens.body(cs.error),
                ),
              )
            : ListView(
                padding: const EdgeInsets.all(SpacingTokens.base),
                children: [
                  AppCard(
                    padding: const EdgeInsets.all(SpacingTokens.md),
                    child: Text(
                      'أنت المسؤول عن حسابك: اختر نوع الإشعارات التي تريدها وتوقيت تقرير نهاية اليوم.',
                      style: TypographyTokens.bodySmall(
                        cs.onSurface.withValues(alpha: 0.7),
                      ),
                    ),
                  ),
                  const SizedBox(height: SpacingTokens.md),
                  _switchCard(
                    cs,
                    title: 'تفعيل الإشعارات',
                    subtitle: 'إيقاف/تشغيل كل الإشعارات من التطبيق',
                    value: _settings!.pushEnabled,
                    onChanged: (v) =>
                        _update(_settings!.copyWith(pushEnabled: v)),
                  ),
                  _switchCard(
                    cs,
                    title: 'صفقة جديدة',
                    subtitle: 'عند فتح صفقة جديدة',
                    value: _settings!.notifyNewDeal,
                    onChanged: _settings!.pushEnabled
                        ? (v) => _update(_settings!.copyWith(notifyNewDeal: v))
                        : null,
                  ),
                  _switchCard(
                    cs,
                    title: 'إغلاق صفقة رابحة',
                    subtitle: 'إشعار عند الإغلاق على ربح',
                    value: _settings!.notifyDealProfit,
                    onChanged: _settings!.pushEnabled
                        ? (v) =>
                              _update(_settings!.copyWith(notifyDealProfit: v))
                        : null,
                  ),
                  _switchCard(
                    cs,
                    title: 'إغلاق صفقة خاسرة',
                    subtitle: 'إشعار عند الإغلاق على خسارة',
                    value: _settings!.notifyDealLoss,
                    onChanged: _settings!.pushEnabled
                        ? (v) => _update(_settings!.copyWith(notifyDealLoss: v))
                        : null,
                  ),
                  const SizedBox(height: SpacingTokens.sm),
                  _switchCard(
                    cs,
                    title: 'تقرير نهاية اليوم',
                    subtitle: 'ملخص الأداء اليومي تلقائيًا',
                    value: _settings!.endOfDayReportEnabled,
                    onChanged: _settings!.pushEnabled
                        ? (v) => _update(
                            _settings!.copyWith(
                              endOfDayReportEnabled: v,
                              dailySummary: v,
                            ),
                          )
                        : null,
                  ),
                  if (_settings!.endOfDayReportEnabled) ...[
                    const SizedBox(height: SpacingTokens.xs),
                    AppCard(
                      padding: const EdgeInsets.all(SpacingTokens.md),
                      child: DropdownButtonFormField<String>(
                        initialValue:
                            _reportTimeOptions.contains(
                              _settings!.endOfDayReportTime,
                            )
                            ? _settings!.endOfDayReportTime
                            : '23:00',
                        decoration: const InputDecoration(
                          labelText: 'وقت تقرير نهاية اليوم',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: '21:00',
                            child: Text('09:00 مساءً'),
                          ),
                          DropdownMenuItem(
                            value: '22:00',
                            child: Text('10:00 مساءً'),
                          ),
                          DropdownMenuItem(
                            value: '23:00',
                            child: Text('11:00 مساءً'),
                          ),
                          DropdownMenuItem(
                            value: '00:00',
                            child: Text('12:00 منتصف الليل'),
                          ),
                        ],
                        onChanged: _settings!.pushEnabled
                            ? (v) {
                                if (v == null) return;
                                _update(
                                  _settings!.copyWith(endOfDayReportTime: v),
                                );
                              }
                            : null,
                      ),
                    ),
                  ],
                  const SizedBox(height: SpacingTokens.xl),
                  AppButton(
                    label: 'حفظ الإعدادات',
                    isLoading: _saving,
                    onPressed: _hasChanges ? _save : null,
                  ),
                  const SizedBox(height: SpacingTokens.xl),
                ],
              ),
      ),
    );
  }

  Widget _switchCard(
    ColorScheme cs, {
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool>? onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.base,
          vertical: SpacingTokens.sm,
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: TypographyTokens.body(cs.onSurface)),
                  const SizedBox(height: SpacingTokens.xxs),
                  Text(
                    subtitle,
                    style: TypographyTokens.caption(
                      cs.onSurface.withValues(alpha: 0.45),
                    ),
                  ),
                ],
              ),
            ),
            Switch(value: value, onChanged: onChanged),
          ],
        ),
      ),
    );
  }
}
