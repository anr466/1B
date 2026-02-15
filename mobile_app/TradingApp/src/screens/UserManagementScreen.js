/**
 * 👥 شاشة إدارة المستخدمين - User Management Screen
 * ✅ عرض جميع المستخدمين مع إحصائياتهم
 * ✅ تبديل حالة المستخدم (نشط/غير نشط)
 * ✅ تعديل نوع المستخدم (admin/regular/support)
 * ✅ حذف (تعطيل) المستخدم
 * ✅ التنقل لشاشة إضافة مستخدم جديد
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    RefreshControl,
    TouchableOpacity,
    ActivityIndicator,
    Alert,
} from 'react-native';
import { theme } from '../theme/theme';
import { colors, spacing, typography } from '../theme/designSystem';
import ModernCard from '../components/ModernCard';
import ModernButton from '../components/ModernButton';
import ModernInput from '../components/ModernInput';
import BrandIcon from '../components/BrandIcons';
import DatabaseApiService from '../services/DatabaseApiService';
import ToastService from '../services/ToastService';

// ترجمة أنواع المستخدمين
const USER_TYPE_LABELS = {
    admin: { label: 'مدير / دعم فني', color: colors.semantic.error, icon: 'shield' },
    regular: { label: 'مستخدم', color: colors.brand.primary, icon: 'user' },
};

const UserManagementScreen = ({ navigation }) => {
    const [users, setUsers] = useState([]);
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [actionLoading, setActionLoading] = useState({});
    const isMountedRef = useRef(true);

    useEffect(() => {
        isMountedRef.current = true;
        loadUsers();
        return () => { isMountedRef.current = false; };
    }, []);

    const loadUsers = useCallback(async () => {
        if (!isMountedRef.current) return;
        try {
            setLoading(true);
            const response = await DatabaseApiService.request('/admin/users/all', 'GET');

            if (isMountedRef.current && response?.success && response?.data) {
                setUsers(response.data.users || []);
                setStats(response.data.stats || {});
            }
        } catch (error) {
            if (isMountedRef.current) {
                ToastService.showError('فشل تحميل قائمة المستخدمين');
            }
        } finally {
            if (isMountedRef.current) setLoading(false);
        }
    }, []);

    const onRefresh = useCallback(async () => {
        if (!isMountedRef.current) return;
        setRefreshing(true);
        await loadUsers();
        if (isMountedRef.current) setRefreshing(false);
    }, [loadUsers]);

    const handleToggleStatus = useCallback(async (userId, currentStatus) => {
        const newStatus = !currentStatus;
        const actionText = newStatus ? 'تفعيل' : 'تعطيل';

        Alert.alert(
            `${actionText} المستخدم`,
            `هل أنت متأكد من ${actionText} هذا المستخدم؟`,
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'تأكيد',
                    style: newStatus ? 'default' : 'destructive',
                    onPress: async () => {
                        try {
                            setActionLoading(prev => ({ ...prev, [userId]: true }));
                            const response = await DatabaseApiService.request(
                                `/admin/users/${userId}/update`,
                                'PUT',
                                { is_active: newStatus ? 1 : 0 }
                            );

                            if (response?.success) {
                                ToastService.showSuccess(`تم ${actionText} المستخدم بنجاح`);
                                setUsers(prev => prev.map(u =>
                                    u.id === userId ? { ...u, is_active: newStatus } : u
                                ));
                            } else {
                                ToastService.showError(response?.error || `فشل ${actionText} المستخدم`);
                            }
                        } catch (error) {
                            ToastService.showError(`فشل ${actionText} المستخدم`);
                        } finally {
                            setActionLoading(prev => ({ ...prev, [userId]: false }));
                        }
                    },
                },
            ]
        );
    }, []);

    const handleChangeUserType = useCallback(async (userId, currentType) => {
        const types = ['regular', 'admin'];
        const typeLabels = { regular: 'مستخدم عادي', admin: 'مدير / دعم فني' };

        const buttons = types
            .filter(t => t !== currentType)
            .map(t => ({
                text: typeLabels[t],
                onPress: async () => {
                    try {
                        setActionLoading(prev => ({ ...prev, [`type_${userId}`]: true }));
                        const response = await DatabaseApiService.request(
                            `/admin/users/${userId}/update`,
                            'PUT',
                            { user_type: t }
                        );

                        if (response?.success) {
                            ToastService.showSuccess(`تم تغيير النوع إلى ${typeLabels[t]}`);
                            setUsers(prev => prev.map(u =>
                                u.id === userId ? { ...u, user_type: t } : u
                            ));
                        } else {
                            ToastService.showError(response?.error || 'فشل تغيير النوع');
                        }
                    } catch (error) {
                        ToastService.showError('فشل تغيير النوع');
                    } finally {
                        setActionLoading(prev => ({ ...prev, [`type_${userId}`]: false }));
                    }
                },
            }));

        buttons.push({ text: 'إلغاء', style: 'cancel' });

        Alert.alert('تغيير نوع المستخدم', `النوع الحالي: ${typeLabels[currentType]}`, buttons);
    }, []);

    const handleDeleteUser = useCallback(async (userId, username) => {
        Alert.alert(
            'تعطيل المستخدم',
            `هل أنت متأكد من تعطيل "${username}"؟\n\nلن يتم حذف البيانات نهائياً.`,
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'تعطيل',
                    style: 'destructive',
                    onPress: async () => {
                        try {
                            setActionLoading(prev => ({ ...prev, [`del_${userId}`]: true }));
                            const response = await DatabaseApiService.request(
                                `/admin/users/${userId}/delete`,
                                'DELETE'
                            );

                            if (response?.success) {
                                ToastService.showSuccess('تم تعطيل المستخدم');
                                setUsers(prev => prev.map(u =>
                                    u.id === userId ? { ...u, is_active: false } : u
                                ));
                            } else {
                                ToastService.showError(response?.error || 'فشل تعطيل المستخدم');
                            }
                        } catch (error) {
                            ToastService.showError('فشل تعطيل المستخدم');
                        } finally {
                            setActionLoading(prev => ({ ...prev, [`del_${userId}`]: false }));
                        }
                    },
                },
            ]
        );
    }, []);

    // فلترة المستخدمين حسب البحث
    const filteredUsers = users.filter(u => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        return (
            (u.username || '').toLowerCase().includes(q) ||
            (u.email || '').toLowerCase().includes(q) ||
            (u.full_name || '').toLowerCase().includes(q)
        );
    });

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={colors.brand.primary} />
                <Text style={styles.loadingText}>جاري تحميل المستخدمين...</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={
                    <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.brand.primary} />
                }
            >
                {/* إحصائيات عامة */}
                <ModernCard style={styles.statsCard}>
                    <View style={styles.statsRow}>
                        <View style={styles.statItem}>
                            <Text style={styles.statValue}>{stats.total_users || 0}</Text>
                            <Text style={styles.statLabel}>إجمالي</Text>
                        </View>
                        <View style={styles.statDivider} />
                        <View style={styles.statItem}>
                            <Text style={[styles.statValue, { color: colors.semantic.success }]}>{stats.active_users || 0}</Text>
                            <Text style={styles.statLabel}>نشط</Text>
                        </View>
                        <View style={styles.statDivider} />
                        <View style={styles.statItem}>
                            <Text style={[styles.statValue, { color: colors.semantic.error }]}>{stats.inactive_users || 0}</Text>
                            <Text style={styles.statLabel}>غير نشط</Text>
                        </View>
                        <View style={styles.statDivider} />
                        <View style={styles.statItem}>
                            <Text style={[styles.statValue, { color: colors.semantic.warning }]}>{stats.admin_users || 0}</Text>
                            <Text style={styles.statLabel}>مدير</Text>
                        </View>
                    </View>
                </ModernCard>

                {/* بحث + إضافة مستخدم */}
                <View style={styles.actionsRow}>
                    <View style={styles.searchContainer}>
                        <ModernInput
                            placeholder="ابحث بالاسم أو الإيميل..."
                            value={searchQuery}
                            onChangeText={setSearchQuery}
                            icon="search"
                        />
                    </View>
                </View>

                <ModernButton
                    title="➕ إضافة مستخدم جديد"
                    onPress={() => navigation.navigate('CreateUser')}
                    variant="primary"
                    size="medium"
                    fullWidth
                    style={styles.addButton}
                />

                {/* قائمة المستخدمين */}
                {filteredUsers.length === 0 ? (
                    <ModernCard style={styles.emptyCard}>
                        <BrandIcon name="user" size={48} color={colors.text.tertiary} />
                        <Text style={styles.emptyText}>
                            {searchQuery.trim() ? 'لا توجد نتائج للبحث' : 'لا يوجد مستخدمون'}
                        </Text>
                    </ModernCard>
                ) : (
                    filteredUsers.map((user) => (
                        <UserCard
                            key={user.id}
                            user={user}
                            actionLoading={actionLoading}
                            onToggleStatus={handleToggleStatus}
                            onChangeType={handleChangeUserType}
                            onDelete={handleDeleteUser}
                        />
                    ))
                )}

                <View style={{ height: 40 }} />
            </ScrollView>
        </View>
    );
};

// بطاقة المستخدم
const UserCard = ({ user, actionLoading, onToggleStatus, onChangeType, onDelete }) => {
    const typeInfo = USER_TYPE_LABELS[user.user_type] || USER_TYPE_LABELS.regular;
    const isLoading = actionLoading[user.id] || actionLoading[`type_${user.id}`] || actionLoading[`del_${user.id}`];

    return (
        <ModernCard style={[styles.userCard, !user.is_active && styles.userCardInactive]}>
            {/* الصف الأول: الاسم + النوع + الحالة */}
            <View style={styles.userRow1}>
                <View style={styles.userInfo}>
                    <View style={[styles.avatarCircle, { backgroundColor: typeInfo.color + '20' }]}>
                        <BrandIcon name={typeInfo.icon} size={18} color={typeInfo.color} />
                    </View>
                    <View style={styles.userNameSection}>
                        <Text style={styles.userName}>
                            {user.username} {user.user_type === 'admin' && '👑'}
                        </Text>
                        <Text style={styles.userEmail}>{user.email}</Text>
                    </View>
                </View>
                <View style={styles.userBadges}>
                    <View style={[styles.typeBadge, { backgroundColor: typeInfo.color + '15' }]}>
                        <Text style={[styles.typeBadgeText, { color: typeInfo.color }]}>{typeInfo.label}</Text>
                    </View>
                    <View style={[styles.statusDot, { backgroundColor: user.is_active ? colors.semantic.success : colors.semantic.error }]} />
                </View>
            </View>

            {/* الصف الثاني: إحصائيات */}
            <View style={styles.userRow2}>
                <View style={styles.userStat}>
                    <Text style={styles.userStatLabel}>الصفقات</Text>
                    <Text style={styles.userStatValue}>{user.total_trades || 0}</Text>
                </View>
                <View style={styles.userStat}>
                    <Text style={styles.userStatLabel}>الرابحة</Text>
                    <Text style={[styles.userStatValue, { color: colors.semantic.success }]}>{user.winning_trades || 0}</Text>
                </View>
                <View style={styles.userStat}>
                    <Text style={styles.userStatLabel}>معدل النجاح</Text>
                    <Text style={[styles.userStatValue, { color: (user.win_rate || 0) >= 50 ? colors.semantic.success : colors.semantic.error }]}>
                        {user.win_rate || 0}%
                    </Text>
                </View>
                <View style={styles.userStat}>
                    <Text style={styles.userStatLabel}>آخر دخول</Text>
                    <Text style={styles.userStatValue}>
                        {user.last_login ? new Date(user.last_login).toLocaleDateString('ar-SA') : '—'}
                    </Text>
                </View>
            </View>

            {/* الصف الثالث: الإجراءات */}
            <View style={styles.userRow3}>
                {isLoading ? (
                    <ActivityIndicator size="small" color={colors.brand.primary} />
                ) : (
                    <>
                        <TouchableOpacity
                            style={[styles.actionBtn, { backgroundColor: user.is_active ? colors.semantic.error + '15' : colors.semantic.success + '15' }]}
                            onPress={() => onToggleStatus(user.id, user.is_active)}
                        >
                            <BrandIcon
                                name={user.is_active ? 'x' : 'check-circle'}
                                size={14}
                                color={user.is_active ? colors.semantic.error : colors.semantic.success}
                            />
                            <Text style={[styles.actionBtnText, { color: user.is_active ? colors.semantic.error : colors.semantic.success }]}>
                                {user.is_active ? 'تعطيل' : 'تفعيل'}
                            </Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={[styles.actionBtn, { backgroundColor: colors.brand.primary + '15' }]}
                            onPress={() => onChangeType(user.id, user.user_type)}
                        >
                            <BrandIcon name="shield" size={14} color={colors.brand.primary} />
                            <Text style={[styles.actionBtnText, { color: colors.brand.primary }]}>تغيير الدور</Text>
                        </TouchableOpacity>

                        {user.user_type !== 'admin' && (
                            <TouchableOpacity
                                style={[styles.actionBtn, { backgroundColor: colors.semantic.error + '10' }]}
                                onPress={() => onDelete(user.id, user.username)}
                            >
                                <BrandIcon name="trash" size={14} color={colors.semantic.error} />
                            </TouchableOpacity>
                        )}
                    </>
                )}
            </View>
        </ModernCard>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    scrollContent: {
        padding: spacing.md,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: theme.colors.background,
    },
    loadingText: {
        ...typography.body2,
        color: colors.text.secondary,
        marginTop: spacing.md,
    },

    // إحصائيات
    statsCard: {
        marginBottom: spacing.md,
    },
    statsRow: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        alignItems: 'center',
    },
    statItem: {
        alignItems: 'center',
        flex: 1,
    },
    statValue: {
        ...typography.h3,
        color: colors.text.primary,
        fontWeight: '700',
    },
    statLabel: {
        ...typography.caption,
        color: colors.text.secondary,
        marginTop: 2,
    },
    statDivider: {
        width: 1,
        height: 30,
        backgroundColor: colors.border.default,
    },

    // بحث + إضافة
    actionsRow: {
        marginBottom: spacing.sm,
    },
    searchContainer: {
        flex: 1,
    },
    addButton: {
        marginBottom: spacing.md,
    },

    // حالة فارغة
    emptyCard: {
        alignItems: 'center',
        paddingVertical: spacing.xl,
    },
    emptyText: {
        ...typography.body1,
        color: colors.text.secondary,
        marginTop: spacing.md,
    },

    // بطاقة المستخدم
    userCard: {
        marginBottom: spacing.sm,
    },
    userCardInactive: {
        opacity: 0.7,
    },

    // الصف 1
    userRow1: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: spacing.sm,
    },
    userInfo: {
        flexDirection: 'row',
        alignItems: 'center',
        flex: 1,
        gap: spacing.sm,
    },
    avatarCircle: {
        width: 36,
        height: 36,
        borderRadius: 18,
        justifyContent: 'center',
        alignItems: 'center',
    },
    userNameSection: {
        flex: 1,
    },
    userName: {
        ...typography.body1,
        color: colors.text.primary,
        fontWeight: '600',
    },
    userEmail: {
        ...typography.caption,
        color: colors.text.secondary,
    },
    userBadges: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    typeBadge: {
        borderRadius: 6,
        paddingHorizontal: 8,
        paddingVertical: 3,
    },
    typeBadgeText: {
        fontSize: 11,
        fontWeight: '600',
    },
    statusDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
    },

    // الصف 2: إحصائيات
    userRow2: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        backgroundColor: colors.background.elevated,
        borderRadius: 8,
        paddingVertical: spacing.xs,
        marginBottom: spacing.sm,
    },
    userStat: {
        alignItems: 'center',
        flex: 1,
    },
    userStatLabel: {
        fontSize: 10,
        color: colors.text.tertiary,
        marginBottom: 2,
    },
    userStatValue: {
        ...typography.caption,
        color: colors.text.primary,
        fontWeight: '600',
    },

    // الصف 3: الإجراءات
    userRow3: {
        flexDirection: 'row',
        gap: 8,
        justifyContent: 'flex-end',
    },
    actionBtn: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingHorizontal: 10,
        paddingVertical: 6,
        borderRadius: 6,
    },
    actionBtnText: {
        fontSize: 11,
        fontWeight: '600',
    },
});

export default UserManagementScreen;
