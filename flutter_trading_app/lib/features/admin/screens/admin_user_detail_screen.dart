import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/empty_state.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/status_badge.dart';
import 'package:trading_app/design/widgets/demo_real_banner.dart';
import 'package:trading_app/design/widgets/trading_toggle_button.dart';

/// ────────────────────────────────────────────────────────────────
/// Admin User Detail Screen — عرض تفاصيل المستخدم (للقراءة فقط)
/// ────────────────────────────────────────────────────────────────
class AdminUserDetailScreen extends ConsumerStatefulWidget {
  final int userId;
  final Map<String, dynamic>? initialData;

  const AdminUserDetailScreen({
    super.key,
    required this.userId,
    this.initialData,
  });

  @override
  ConsumerState<AdminUserDetailScreen> createState() =>
      _AdminUserDetailScreenState();
}

class _AdminUserDetailScreenState
    extends ConsumerState<AdminUserDetailScreen> {
  bool _isLoading = false;
  Map<String, dynamic>? _userData;
  String? _error;

  @override
  void initState() {
    super.initState();
    _userData = widget.initialData;
    _loadUserDetails();
  }

  Future<void> _loadUserDetails() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final repo = ref.read(adminRepositoryProvider);
      final data = await repo.getUserDetails(widget.userId);
      if (mounted) {
        setState(() {
          _userData = {...?_userData, ...data};
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: Column(
          children: [
            AppScreenHeader(
              title: 'تفاصيل المستخدم',
              showBack: true,
              trailing: IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: _isLoading ? null : _loadUserDetails,
              ),
              padding: const EdgeInsets.symmetric(
                horizontal: SpacingTokens.lg,
                vertical: SpacingTokens.sm,
              ),
            ),
            const DemoRealBanner(),
            Expanded(child: _buildBody(cs)),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(ColorScheme cs) {
    if (_isLoading && _userData == null) {
      return const LoadingShimmer(itemCount: 6, itemHeight: 80);
    }
    if (_error != null && _userData == null) {
      return ErrorState(
        message: _error!,
        onRetry: _loadUserDetails,
      );
    }
    if (_userData == null) {
      return const EmptyState(
        icon: Icons.person_off,
        message: 'لا توجد بيانات للمستخدم',
      );
    }

    final user = _userData!;
    final name = user['fullName'] ?? user['name'] ?? user['username'] ?? 'مستخدم';
    final email = user['email'] ?? '—';
    final phone = user['phoneNumber'] ?? user['phone'] ?? '—';
    final userType = user['userType'] ?? user['user_type'] ?? 'user';
    final isActive = user['isActive'] ?? user['is_active'] ?? true;
    final tradingEnabled = user['tradingEnabled'] ?? user['trading_enabled'] ?? false;
    final totalTrades = user['totalTrades'] ?? user['total_trades'] ?? 0;
    final winningTrades = user['winningTrades'] ?? user['winning_trades'] ?? 0;
    final winRate = totalTrades > 0 ? (winningTrades / totalTrades * 100).toStringAsFixed(1) : '0.0';

    return RefreshIndicator(
      onRefresh: _loadUserDetails,
      child: ListView(
        padding: const EdgeInsets.all(SpacingTokens.lg),
        children: [
          // ─── User Header ───────────────────────
          AppCard(
            child: Column(
              children: [
                CircleAvatar(
                  radius: 32,
                  backgroundColor: cs.primary.withValues(alpha: 0.15),
                  child: Icon(Icons.person, size: 32, color: cs.primary),
                ),
                const SizedBox(height: SpacingTokens.sm),
                Text(
                  name,
                  style: TypographyTokens.h3(cs.onSurface),
                ),
                const SizedBox(height: 4),
                Text(
                  '@${user['username'] ?? ''}',
                  style: TypographyTokens.bodySmall(
                    cs.onSurface.withValues(alpha: 0.6),
                  ),
                ),
                const SizedBox(height: SpacingTokens.sm),
                Wrap(
                  spacing: SpacingTokens.xs,
                  children: [
                    StatusBadge(
                      text: userType == 'admin' ? 'أدمن' : 'مستخدم',
                      type: userType == 'admin' ? BadgeType.info : BadgeType.info,
                    ),
                    StatusBadge(
                      text: isActive ? 'نشط' : 'محظور',
                      type: isActive ? BadgeType.success : BadgeType.error,
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: SpacingTokens.lg),

          // ─── Contact Info ──────────────────────
          _SectionTitle(title: 'معلومات التواصل', cs: cs),
          const SizedBox(height: SpacingTokens.sm),
          AppCard(
            child: Column(
              children: [
                _InfoRow(icon: Icons.email, label: 'البريد', value: email),
                const Divider(height: 1),
                _InfoRow(icon: Icons.phone, label: 'الهاتف', value: phone),
                const Divider(height: 1),
                _InfoRow(
                  icon: Icons.calendar_today,
                  label: 'تاريخ التسجيل',
                  value: _formatDate(user['createdAt'] ?? user['created_at']),
                ),
                const Divider(height: 1),
                _InfoRow(
                  icon: Icons.access_time,
                  label: 'آخر دخول',
                  value: _formatDate(user['lastLogin'] ?? user['last_login']),
                ),
              ],
            ),
          ),

          const SizedBox(height: SpacingTokens.lg),

          // ─── Trading Toggle ────────────────────
          _SectionTitle(title: 'حالة التداول', cs: cs),
          const SizedBox(height: SpacingTokens.sm),
          AppCard(
            child: TradingToggleButton(
              targetUserId: widget.userId,
              value: tradingEnabled,
              subtitle: tradingEnabled
                  ? 'المستخدم يمكنه فتح صفقات جديدة'
                  : 'لن يفتح المستخدم صفقات جديدة',
              onChanged: (v) {
                setState(() {
                  _userData = {..._userData!, 'tradingEnabled': v};
                });
              },
            ),
          ),

          const SizedBox(height: SpacingTokens.lg),

          // ─── Trading Stats ─────────────────────
          _SectionTitle(title: 'إحصائيات التداول', cs: cs),
          const SizedBox(height: SpacingTokens.sm),
          AppCard(
            child: Row(
              children: [
                Expanded(
                  child: _StatBox(
                    label: 'إجمالي الصفقات',
                    value: '$totalTrades',
                    color: cs.primary,
                  ),
                ),
                Container(width: 1, height: 50, color: cs.outline.withValues(alpha: 0.2)),
                Expanded(
                  child: _StatBox(
                    label: 'نسبة الفوز',
                    value: '$winRate%',
                    color: cs.tertiary,
                  ),
                ),
                Container(width: 1, height: 50, color: cs.outline.withValues(alpha: 0.2)),
                Expanded(
                  child: _StatBox(
                    label: 'الصفقات الرابحة',
                    value: '$winningTrades',
                    color: cs.secondary,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: SpacingTokens.lg),

          // ─── Identity Verification ─────────────
          _SectionTitle(title: 'التحقق من الهوية', cs: cs),
          const SizedBox(height: SpacingTokens.sm),
          AppCard(
            child: Column(
              children: [
                _VerificationRow(
                  label: 'البريد الإلكتروني',
                  verified: user['emailVerified'] == true || user['email_verified'] == true,
                  cs: cs,
                ),
                const Divider(height: 1),
                _VerificationRow(
                  label: 'رقم الهاتف',
                  verified: user['phoneVerified'] == true || user['phone_verified'] == true,
                  cs: cs,
                ),
                const Divider(height: 1),
                _VerificationRow(
                  label: 'رقم الهوية',
                  verified: user['identityVerified'] == true || user['identity_verified'] == true,
                  cs: cs,
                ),
              ],
            ),
          ),

          const SizedBox(height: SpacingTokens.xl),
        ],
      ),
    );
  }

  String _formatDate(dynamic value) {
    if (value == null) return '—';
    try {
      final dt = DateTime.parse(value.toString());
      return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';
    } catch (_) {
      return value.toString();
    }
  }
}

// ─── Helper Widgets ───────────────────────────────

class _SectionTitle extends StatelessWidget {
  final String title;
  final ColorScheme cs;
  const _SectionTitle({required this.title, required this.cs});

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: TypographyTokens.bodySmall(
        cs.onSurface.withValues(alpha: 0.6),
      ).copyWith(fontWeight: FontWeight.w700),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _InfoRow({required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.md),
      child: Row(
        children: [
          Icon(icon, size: 18, color: cs.primary),
          const SizedBox(width: SpacingTokens.sm),
          Expanded(
            child: Text(
              label,
              style: TypographyTokens.bodySmall(cs.onSurface.withValues(alpha: 0.6)),
            ),
          ),
          Text(
            value,
            style: TypographyTokens.bodySmall(cs.onSurface).copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatBox extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _StatBox({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.md),
      child: Column(
        children: [
          Text(
            value,
            style: TypographyTokens.h2(color).copyWith(fontSize: 20),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TypographyTokens.caption(
              Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.5),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _VerificationRow extends StatelessWidget {
  final String label;
  final bool verified;
  final ColorScheme cs;
  const _VerificationRow({required this.label, required this.verified, required this.cs});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.md),
      child: Row(
        children: [
          Icon(
            verified ? Icons.verified : Icons.pending,
            size: 20,
            color: verified ? Colors.green : cs.outline,
          ),
          const SizedBox(width: SpacingTokens.sm),
          Expanded(
            child: Text(
              label,
              style: TypographyTokens.bodySmall(cs.onSurface),
            ),
          ),
          StatusBadge(
            text: verified ? 'تم التحقق' : 'معلق',
            type: verified ? BadgeType.success : BadgeType.warning,
          ),
        ],
      ),
    );
  }
}


