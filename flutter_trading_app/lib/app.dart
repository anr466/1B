import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:trading_app/core/providers/notifications_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/core/services/push_notification_service.dart';
import 'package:trading_app/design/skins/skin_manager.dart';
import 'package:trading_app/navigation/app_router.dart';

/// App — MaterialApp.router wrapper with skin system + GoRouter
class TradingApp extends ConsumerWidget {
  const TradingApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final skin = ref.watch(skinProvider);
    final themeMode = ref.watch(themeModeProvider);
    final router = ref.watch(appRouterProvider);
    final pushService = ref.read(pushNotificationServiceProvider);

    // Load notification settings and pass to push service
    final notificationSettingsAsync = ref.watch(notificationSettingsProvider);
    notificationSettingsAsync.whenData((settings) {
      pushService.updateSettings(settings.toJson());
    });

    pushService.onNotificationTapped = (data) {
      final action = PushNotificationService.parseAction(data);
      router.goNamed(action.routeName, queryParameters: action.params);
    };

    pushService.onNotificationReceived = (data) {
      ref.invalidate(unreadCountProvider);
      ref.invalidate(notificationsListProvider);
      ref.invalidate(recentTradesProvider);
      ref.invalidate(activePositionsProvider);
      ref.invalidate(portfolioProvider);
      ref.invalidate(statsProvider);
    };

    return ScreenUtilInit(
      designSize: const Size(375, 812),
      minTextAdapt: true,
      builder: (context, child) {
        return MaterialApp.router(
          title: '1B Trading',
          debugShowCheckedModeBanner: false,
          scrollBehavior: const MaterialScrollBehavior().copyWith(
            overscroll: false,
          ),

          // ─── Locale & Direction ────────────────────
          locale: const Locale('ar'),
          supportedLocales: const [Locale('ar')],
          localizationsDelegates: const [
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],

          // ─── Theme from Skin ───────────────────────
          theme: skin.buildLightTheme(),
          darkTheme: skin.buildDarkTheme(),
          themeMode: themeMode,

          // ─── GoRouter ──────────────────────────────
          routerConfig: router,
        );
      },
    );
  }
}
