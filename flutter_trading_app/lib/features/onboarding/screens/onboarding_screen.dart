import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/main.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Onboarding Screen — 3 صفحات تعريفية
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _pageController = PageController();
  int _currentPage = 0;

  static const _pages = [
    _OnboardingPage(
      icon: BrandIcons.chart,
      title: 'تداول ذكي',
      subtitle:
          'نظام تداول آلي يعتمد على الذكاء الاصطناعي لتحليل السوق واتخاذ القرارات',
    ),
    _OnboardingPage(
      icon: BrandIcons.shield,
      title: 'إدارة المخاطر',
      subtitle: 'وقف خسارة وجني أرباح تلقائي مع حماية متقدمة لرأس المال',
    ),
    _OnboardingPage(
      icon: BrandIcons.wallet,
      title: 'متابعة مباشرة',
      subtitle: 'تابع محفظتك وصفقاتك وإحصائياتك في الوقت الحقيقي',
    ),
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _completeOnboarding() async {
    final storage = ref.read(storageServiceProvider);
    await storage.setOnboardingDone(true);
    if (!mounted) return;
    context.go(RouteNames.login);
  }

  Future<void> _next() async {
    if (_currentPage < _pages.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    } else {
      await _completeOnboarding();
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              // ─── Skip ──────────────────────────────
              Align(
                alignment: AlignmentDirectional.topStart,
                child: Padding(
                  padding: const EdgeInsets.all(SpacingTokens.base),
                  child: TextButton(
                    onPressed: _completeOnboarding,
                    child: Text(
                      'تخطي',
                      style: TypographyTokens.bodySmall(
                        cs.onSurface.withValues(alpha: 0.5),
                      ),
                    ),
                  ),
                ),
              ),

              // ─── Pages ─────────────────────────────
              Expanded(
                child: PageView.builder(
                  controller: _pageController,
                  itemCount: _pages.length,
                  onPageChanged: (i) => setState(() => _currentPage = i),
                  itemBuilder: (_, i) {
                    final page = _pages[i];
                    return Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: SpacingTokens.xl,
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          // Logo on first page, icon on others
                          if (i == 0) ...[
                            const BrandLogo(size: 80),
                          ] else ...[
                            Container(
                              width: 80,
                              height: 80,
                              decoration: BoxDecoration(
                                color: cs.primary.withValues(alpha: 0.1),
                                shape: BoxShape.circle,
                              ),
                              child: Center(
                                child: BrandIcon(
                                  page.icon,
                                  size: 40,
                                  color: cs.primary,
                                ),
                              ),
                            ),
                          ],
                          const SizedBox(height: SpacingTokens.xl),
                          Text(
                            page.title,
                            style: TypographyTokens.h1(cs.onSurface),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: SpacingTokens.md),
                          Text(
                            page.subtitle,
                            style: TypographyTokens.body(
                              cs.onSurface.withValues(alpha: 0.6),
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),

              // ─── Page Indicator ────────────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(_pages.length, (i) {
                  final isActive = i == _currentPage;
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 300),
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: isActive ? 24 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: isActive
                          ? cs.primary
                          : cs.outline.withValues(alpha: 0.3),
                      borderRadius: BorderRadius.circular(4),
                    ),
                  );
                }),
              ),

              const SizedBox(height: SpacingTokens.xl),

              // ─── Action Button ─────────────────────
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: SpacingTokens.lg,
                ),
                child: AppButton(
                  label: _currentPage < _pages.length - 1
                      ? 'التالي'
                      : 'ابدأ الآن',
                  isFullWidth: true,
                  onPressed: _next,
                ),
              ),

              const SizedBox(height: SpacingTokens.xl),
            ],
          ),
        ),
      ),
    );
  }
}

class _OnboardingPage {
  final BrandIconData icon;
  final String title;
  final String subtitle;

  const _OnboardingPage({
    required this.icon,
    required this.title,
    required this.subtitle,
  });
}
