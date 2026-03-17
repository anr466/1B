import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:trading_app/app.dart';
import 'package:trading_app/core/services/storage_service.dart';
import 'package:trading_app/design/skins/skin_manager.dart';

/// Global FlutterLocalNotificationsPlugin instance — initialized in main()
final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
    FlutterLocalNotificationsPlugin();

/// Android notification channel for trading alerts
const AndroidNotificationChannel tradingAlertsChannel = AndroidNotificationChannel(
  'trading_alerts',
  '1B Trading Alerts',
  description: 'إشعارات الصفقات والتنبيهات',
  importance: Importance.high,
  playSound: true,
  enableVibration: true,
);

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  // Background messages are displayed automatically by FCM when app is closed/background
  // No additional work needed here — FCM uses the default channel configured in AndroidManifest
  // ignore: avoid_print
  print('[FCM] background: ${message.messageId} type=${message.data["type"]}');
}

/// Global StorageService instance
final storageServiceProvider = Provider<StorageService>((ref) {
  throw UnimplementedError('StorageService must be overridden at startup');
});

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  GoogleFonts.config.allowRuntimeFetching = false;

  await Firebase.initializeApp();
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  // Initialize flutter_local_notifications
  const AndroidInitializationSettings androidSettings =
      AndroidInitializationSettings('@drawable/ic_notification');
  await flutterLocalNotificationsPlugin.initialize(
    const InitializationSettings(android: androidSettings),
  );

  // Create the high-importance Android notification channel
  await flutterLocalNotificationsPlugin
      .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>()
      ?.createNotificationChannel(tradingAlertsChannel);

  // Force portrait orientation
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Initialize storage
  final storage = StorageService();
  await storage.init();

  // Load saved skin & theme preferences
  final savedSkin = storage.skinName;
  final savedThemeMode = storage.themeMode;

  runApp(
    ProviderScope(
      overrides: [
        storageServiceProvider.overrideWithValue(storage),
        skinNameProvider.overrideWith((ref) => savedSkin),
        themeModeProvider.overrideWith((ref) {
          switch (savedThemeMode) {
            case 'light':
              return ThemeMode.light;
            case 'system':
              return ThemeMode.system;
            default:
              return ThemeMode.dark;
          }
        }),
      ],
      child: const TradingApp(),
    ),
  );
}
