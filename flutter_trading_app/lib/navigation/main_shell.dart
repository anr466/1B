import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/utils/responsive_utils.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Main Shell — Scaffold + BottomNavigationBar (5 tabs — أيقونات فقط)
class MainShell extends ConsumerStatefulWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  int _currentIndex = 0;

  static const _userRoutes = [
    RouteNames.dashboard,
    RouteNames.portfolio,
    RouteNames.trades,
    RouteNames.analytics,
    RouteNames.profile,
  ];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final location = GoRouterState.of(context).matchedLocation;
    final idx = _userRoutes.indexOf(location);
    if (idx >= 0 && idx != _currentIndex) {
      setState(() => _currentIndex = idx);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final isAdmin = auth.isAdmin;
    final cs = Theme.of(context).colorScheme;
    final barHeight = ResponsiveUtils.isTablet(context)
        ? SpacingTokens.tabBarHeight + 8
        : SpacingTokens.tabBarHeight;

    return Scaffold(
      key: const Key('main_shell'),
      body: widget.child,
      bottomNavigationBar: Container(
        key: const Key('main_shell_nav'),
        decoration: BoxDecoration(
          color: cs.surfaceContainerHighest,
          border: Border(
            top: BorderSide(
              color: cs.outline.withValues(alpha: 0.3),
              width: 0.5,
            ),
          ),
        ),
        child: SafeArea(
          child: SizedBox(
            height: barHeight,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: List.generate(4, (i) {
                final isActive = _currentIndex == i;
                return _buildTab(
                  index: i,
                  isActive: isActive,
                  isAdmin: isAdmin,
                  cs: cs,
                );
              }),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTab({
    required int index,
    required bool isActive,
    required bool isAdmin,
    required ColorScheme cs,
  }) {
    final iconData = _getIconData(index, isAdmin);
    final color = isActive ? cs.primary : cs.onSurface.withValues(alpha: 0.4);
    final size = isActive
        ? SpacingTokens.tabIconActive
        : SpacingTokens.tabIconInactive;

    return GestureDetector(
      key: Key('main_shell_tab_$index'),
      onTap: () => _onTabTap(index),
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: ResponsiveUtils.isTablet(context) ? 78 : 64,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                BrandIcon(iconData, size: size, color: color),
                // Admin persistent dot — tab 5 only, always visible when admin
                if (isAdmin && index == 4 && !isActive)
                  Positioned(
                    top: -1,
                    right: -3,
                    child: Container(
                      width: 5,
                      height: 5,
                      decoration: BoxDecoration(
                        color: cs.primary,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
              ],
            ),
            if (isActive) ...[
              const SizedBox(height: SpacingTokens.xs),
              Container(
                width: SpacingTokens.tabIndicatorDot,
                height: SpacingTokens.tabIndicatorDot,
                decoration: BoxDecoration(
                  color: cs.primary,
                  shape: BoxShape.circle,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  BrandIconData _getIconData(int index, bool isAdmin) {
    switch (index) {
      case 0: return BrandIcons.home;
      case 1: return BrandIcons.wallet;
      case 2: return BrandIcons.history;
      case 3: return isAdmin ? BrandIcons.shield : BrandIcons.user;
      default: return BrandIcons.home;
    }
  }

  void _onTabTap(int index) {
    if (index == _currentIndex) return;
    final auth = ref.read(authProvider);
    
    // Redirect Admin to Admin Dashboard on Tab 3
    if (index == 3 && auth.isAdmin) {
      // Use push() so MainShell stays in the nav stack;
      // admin screens can then pop() back to the app.
      context.push(RouteNames.adminDashboard);
      return;
    }
    
    setState(() => _currentIndex = index);
    context.go(_userRoutes[index]);
  }
}
