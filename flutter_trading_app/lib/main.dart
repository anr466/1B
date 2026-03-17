import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:trading_app/app.dart';
import 'package:trading_app/core/services/storage_service.dart';
import 'package:trading_app/design/skins/skin_manager.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  // ignore: avoid_print
  print('[FCM] background message: ${message.messageId}');
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
