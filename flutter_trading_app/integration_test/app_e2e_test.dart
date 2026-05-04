// ignore_for_file: avoid_print, dangling_library_doc_comments, unintended_html_in_doc_comment, unused_element
/// Flutter Integration E2E Tests — Trading App
/// =============================================
/// اختبارات تكاملية حقيقية تشغّل التطبيق الفعلي على الجهاز/المحاكي
///
/// الاستخدام:
///   flutter test integration_test/app_e2e_test.dart -d <device_id>
///
/// المتطلبات:
///   - الخادم شغال على 10.0.2.2:3002
///   - محاكي Android أو جهاز حقيقي

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:trading_app/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  // ─── Constants ─────────────────────────────────────────────────
  const adminEmail    = 'admin@tradingbot.com';
  const adminPassword = 'admin123';

  // ─── Helpers ───────────────────────────────────────────────────

  Future<void> waitFor(WidgetTester tester, Finder finder, {
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final deadline = DateTime.now().add(timeout);
    while (!tester.any(finder)) {
      if (DateTime.now().isAfter(deadline)) {
        throw TestFailure(
          'Timed out waiting for: $finder\n'
          'Current tree: ${tester.allWidgets.map((w) => w.runtimeType).toSet()}',
        );
      }
      await tester.pump(const Duration(milliseconds: 300));
    }
  }

  Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
    await tester.tap(finder);
    await tester.pumpAndSettle(const Duration(milliseconds: 500));
  }

  Future<void> pumpFor(
    WidgetTester tester,
    Duration duration, {
    Duration step = const Duration(milliseconds: 250),
  }) async {
    var elapsed = Duration.zero;
    while (elapsed < duration) {
      await tester.pump(step);
      elapsed += step;
    }
  }

  Future<void> activateControl(WidgetTester tester, Finder finder) async {
    final widget = tester.widget(finder.first);

    if (widget is TextButton && widget.onPressed != null) {
      widget.onPressed!.call();
      await pumpFor(tester, const Duration(seconds: 1));
      return;
    }

    if (widget is ElevatedButton && widget.onPressed != null) {
      widget.onPressed!.call();
      await pumpFor(tester, const Duration(seconds: 1));
      return;
    }

    await tester.tap(finder.first, warnIfMissed: false);
    await pumpFor(tester, const Duration(seconds: 1));
  }

  Future<void> submitLogin(WidgetTester tester) async {
    final loginBtn = find.byKey(const Key('login_submit_button'));
    final elevatedLoginBtn = find.widgetWithText(ElevatedButton, 'تسجيل الدخول');
    final appButtonLabel = find.text('تسجيل الدخول');

    if (tester.any(loginBtn)) {
      await activateControl(tester, loginBtn);
      await pumpFor(tester, const Duration(seconds: 8));
      return;
    }

    if (tester.any(elevatedLoginBtn)) {
      await activateControl(tester, elevatedLoginBtn);
      await pumpFor(tester, const Duration(seconds: 8));
      return;
    }

    if (tester.any(appButtonLabel)) {
      await activateControl(tester, appButtonLabel);
      await pumpFor(tester, const Duration(seconds: 8));
      return;
    }

    final widgetTypes = tester.allWidgets
        .map((w) => w.runtimeType.toString())
        .toSet()
        .take(80)
        .toList();
    final visibleTexts = find
        .byType(Text)
        .evaluate()
        .map((e) => (e.widget as Text).data)
        .whereType<String>()
        .where((text) => text.trim().isNotEmpty)
        .take(40)
        .toList();
    print('⚠️ login debug widgetTypes=$widgetTypes');
    print('⚠️ login debug visibleTexts=$visibleTexts');
    throw TestFailure('Login button not found on login screen.');
  }

  Future<bool> skipOnboardingIfVisible(WidgetTester tester) async {
    final skipByKey = find.byKey(
      const Key('onboarding_skip_button'),
      skipOffstage: false,
    );
    final skipByText = find.text('تخطي', skipOffstage: false);
    final nextByText = find.text('التالي', skipOffstage: false);
    final startNowByText = find.text('ابدأ الآن', skipOffstage: false);

    if (tester.any(skipByKey)) {
      await tester.ensureVisible(skipByKey.first);
      await activateControl(tester, skipByKey);
      await pumpFor(tester, const Duration(seconds: 2));
      return true;
    }

    if (tester.any(skipByText)) {
      await tester.ensureVisible(skipByText.first);
      await activateControl(tester, skipByText);
      await pumpFor(tester, const Duration(seconds: 2));
      return true;
    }

    if (tester.any(nextByText) || tester.any(startNowByText)) {
      final action = tester.any(startNowByText) ? startNowByText : nextByText;
      await tester.ensureVisible(action.first);
      await activateControl(tester, action);
      await pumpFor(tester, const Duration(seconds: 1));
      return true;
    }

    return false;
  }

  Future<String> waitForStartupState(WidgetTester tester) async {
    final deadline = DateTime.now().add(const Duration(seconds: 20));
    while (DateTime.now().isBefore(deadline)) {
      if (tester.any(find.byKey(const Key('main_shell'))) ||
          tester.any(find.byKey(const Key('dashboard_screen')))) {
        return 'dashboard';
      }
      if (tester.any(find.byKey(const Key('onboarding_screen'))) ||
          tester.any(find.byKey(const Key('onboarding_skip_button'))) ||
          tester.any(find.text('تخطي', skipOffstage: false)) ||
          tester.any(find.text('التالي', skipOffstage: false)) ||
          tester.any(find.text('ابدأ الآن', skipOffstage: false))) {
        return 'onboarding';
      }
      if (tester.any(find.byKey(const Key('login_screen')))) {
        return 'login';
      }
      if (tester.any(find.byKey(const Key('splash_screen')))) {
        await tester.pump(const Duration(milliseconds: 300));
        continue;
      }
      await tester.pump(const Duration(milliseconds: 300));
    }
    return 'unknown';
  }

  Future<void> completeOnboardingIfNeeded(WidgetTester tester) async {
    for (var i = 0; i < 3; i++) {
      if (await skipOnboardingIfVisible(tester)) {
        continue;
      }

      final startupState = await waitForStartupState(tester);
      if (startupState != 'onboarding') {
        return;
      }

      final skipButton = find.byKey(const Key('onboarding_skip_button'));
      if (tester.any(skipButton)) {
        await tapAndSettle(tester, skipButton.first);
        await tester.pumpAndSettle(const Duration(seconds: 2));
        continue;
      }

      throw TestFailure('Onboarding is visible but no skip control was found.');
    }
  }

  Future<void> loginIfNeeded(WidgetTester tester) async {
    for (var i = 0; i < 4; i++) {
      await completeOnboardingIfNeeded(tester);
      final startupState = await waitForStartupState(tester);
      if (startupState == 'dashboard') return;
      if (startupState == 'onboarding') {
        await tester.pumpAndSettle(const Duration(seconds: 1));
        continue;
      }
      if (startupState != 'login') {
        throw TestFailure('Expected login or dashboard state, got: $startupState');
      }

      if (!tester.any(find.byKey(const Key('login_screen')))) {
        await tester.pumpAndSettle(const Duration(seconds: 1));
        continue;
      }

      await waitFor(
        tester,
        find.byKey(const Key('login_screen')),
        timeout: const Duration(seconds: 10),
      );

      final textFields = find.byType(TextFormField);
      await waitFor(tester, textFields, timeout: const Duration(seconds: 10));

      await tester.enterText(textFields.first, adminEmail);
      await tester.pumpAndSettle();

      if (textFields.evaluate().length > 1) {
        await tester.enterText(textFields.at(1), adminPassword);
        await tester.pumpAndSettle();
      }

      await submitLogin(tester);
    }
    throw TestFailure('Bootstrap did not stabilize on dashboard after onboarding/login attempts.');
  }

  Future<void> ensureDashboardReady(WidgetTester tester) async {
    await loginIfNeeded(tester);
    final deadline = DateTime.now().add(const Duration(seconds: 20));
    while (DateTime.now().isBefore(deadline)) {
      if (tester.any(find.byKey(const Key('main_shell'))) ||
          tester.any(find.byKey(const Key('dashboard_screen')))) {
        return;
      }
      await tester.pump(const Duration(milliseconds: 300));
    }

    throw TestFailure('Timed out waiting for dashboard/main shell after bootstrap.');
  }

  Future<void> bootstrapToDashboard(WidgetTester tester) async {
    final deadline = DateTime.now().add(const Duration(seconds: 45));
    while (DateTime.now().isBefore(deadline)) {
      if (await skipOnboardingIfVisible(tester)) {
        continue;
      }

      final state = await waitForStartupState(tester);
      if (state == 'dashboard') {
        return;
      }

      if (state == 'onboarding') {
        final advanced = await skipOnboardingIfVisible(tester);
        if (!advanced) {
          await tester.pumpAndSettle(const Duration(seconds: 1));
        }
        continue;
      }

      if (state == 'login') {
        final loginScreen = find.byKey(const Key('login_screen'));
        await waitFor(tester, loginScreen, timeout: const Duration(seconds: 10));
        final textFields = find.byType(TextFormField);
        await waitFor(tester, textFields, timeout: const Duration(seconds: 10));
        await tester.enterText(textFields.first, adminEmail);
        await pumpFor(tester, const Duration(milliseconds: 500));
        if (textFields.evaluate().length > 1) {
          await tester.enterText(textFields.at(1), adminPassword);
          await pumpFor(tester, const Duration(milliseconds: 500));
        }
        await submitLogin(tester);
        continue;
      }

      await tester.pump(const Duration(milliseconds: 500));
    }

    throw TestFailure('Bootstrap did not reach dashboard before timeout.');
  }

  // ═══════════════════════════════════════════════════════════════
  // 1. App Launch
  // ═══════════════════════════════════════════════════════════════

  testWidgets('App launches without crash', (tester) async {
    app.main();
    final startupState = await waitForStartupState(tester);

    final hasLoginScreen  = startupState == 'login';
    final hasDashboard    = startupState == 'dashboard';
    final hasOnboarding   = startupState == 'onboarding';
    final hasAnyContent   = tester.any(find.byType(Scaffold));

    expect(hasLoginScreen || hasDashboard || hasOnboarding || hasAnyContent, isTrue,
        reason: 'App should show at least a Scaffold on launch');

    print('✅ App launched successfully (state=$startupState)');
  });

  // ═══════════════════════════════════════════════════════════════
  // 2. Login Flow
  // ═══════════════════════════════════════════════════════════════

  testWidgets('Full app flow reaches dashboard and survives primary interactions', (
    tester,
  ) async {
    app.main();

    var startupState = await waitForStartupState(tester);
    expect(
      startupState == 'login' || startupState == 'dashboard' || startupState == 'onboarding',
      isTrue,
      reason: 'App should stabilize on onboarding, login, or dashboard',
    );

    await bootstrapToDashboard(tester);
    startupState = await waitForStartupState(tester);

    expect(find.text('بيانات غير صحيحة'), findsNothing,
        reason: 'Valid credentials should not produce auth error');
    expect(startupState, 'dashboard', reason: 'App should reach dashboard after bootstrap');

    final shell = find.byKey(const Key('main_shell'));
    final navBar = find.byKey(const Key('main_shell_nav'));
    final dashboard = find.byKey(const Key('dashboard_screen'));
    final refreshIndicator = find.byKey(const Key('dashboard_refresh'));

    expect(shell, findsOneWidget);
    expect(navBar, findsOneWidget);
    expect(dashboard, findsOneWidget);
    expect(refreshIndicator, findsOneWidget);

    final navItems = find.byWidgetPredicate(
      (widget) => widget.key is Key &&
          (widget.key as Key).toString().contains('main_shell_tab_'),
    );
    final count = navItems.evaluate().length;
    expect(count, greaterThanOrEqualTo(5));

    for (int i = 0; i < count; i++) {
      await tester.tap(navItems.at(i), warnIfMissed: false);
      await pumpFor(tester, const Duration(seconds: 2));
      expect(find.byType(Scaffold), findsAtLeastNWidgets(1));
    }

    await tester.tap(navItems.at(0), warnIfMissed: false);
    await pumpFor(tester, const Duration(seconds: 2));

    final dashboardRefresh = find.byKey(const Key('dashboard_refresh'));
    if (dashboardRefresh.evaluate().isNotEmpty) {
      await tester.drag(dashboardRefresh.first, const Offset(0, 300));
      await tester.pump(const Duration(milliseconds: 500));
      await pumpFor(tester, const Duration(seconds: 5));
    }

    expect(find.byType(Scaffold), findsAtLeastNWidgets(1));
    print('✅ Full app flow completed');
  });

  // ═══════════════════════════════════════════════════════════════
  // 3. Dashboard Screen
  // ═══════════════════════════════════════════════════════════════

}
