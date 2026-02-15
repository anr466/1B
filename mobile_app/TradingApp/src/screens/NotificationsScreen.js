/**
 * 🔔 شاشة الإشعارات - NotificationsScreen
 * عرض قائمة الإشعارات للمستخدم
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
    View,
    Text,
    FlatList,
    TouchableOpacity,
    StyleSheet,
    RefreshControl,
    ActivityIndicator,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernCard from '../components/ModernCard';
import BrandIcon from '../components/BrandIcons';
import DatabaseApiService from '../services/DatabaseApiService';
import ToastService from '../services/ToastService';
import NotificationService from '../services/NotificationService';
import TempStorageService from '../services/TempStorageService';
import { useBackHandler } from '../utils/BackHandlerUtil';
// ✅ GlobalHeader يأتي من Navigator
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTradingModeContext } from '../context/TradingModeContext';
import { useIsAdmin } from '../hooks/useIsAdmin';

const NotificationsScreen = ({ navigation, user, onBack }) => {
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);

    // ✅ استخدام Context
    const { tradingMode } = useTradingModeContext();
    const isAdmin = useIsAdmin(user);

    // ✅ تحديد نوع البيانات (حقيقي/وهمي)
    const isDemoData = tradingMode === 'demo' || isAdmin;

    useBackHandler(() => {
        onBack ? onBack() : navigation?.goBack();
    });

    const loadNotifications = useCallback(async (isRefresh = false) => {
        try {
            if (isRefresh) {
                setRefreshing(true);
                setPage(1);
            } else if (!hasMore && !isRefresh) {
                return;
            }

            const currentPage = isRefresh ? 1 : page;

            // ✅ جلب الإشعارات من الخادم
            const response = await DatabaseApiService.getNotifications?.(user?.id, currentPage, 20);

            let serverNotifications = [];
            if (response?.success) {
                serverNotifications = response.data?.notifications || response.data || [];
            }

            // ✅ دمج مع الإشعارات المحلية فقط في الصفحة الأولى
            if (isRefresh && currentPage === 1) {
                const localNotifications = await NotificationService.getLocalNotifications();

                // دمج وإزالة التكرار بناءً على ID أو timestamp
                const allNotifications = [...serverNotifications];
                const serverIds = new Set(serverNotifications.map(n => n.id));

                localNotifications.forEach(local => {
                    // إضافة الإشعارات المحلية التي ليست في الخادم
                    if (!serverIds.has(local.id)) {
                        allNotifications.push({
                            ...local,
                            isRead: local.read || false,
                            createdAt: local.receivedAt,
                            type: local.data?.type || 'system',
                        });
                    }
                });

                // ترتيب حسب التاريخ (الأحدث أولاً)
                allNotifications.sort((a, b) =>
                    new Date(b.createdAt || b.receivedAt) - new Date(a.createdAt || a.receivedAt)
                );

                setNotifications(allNotifications);
            } else if (isRefresh) {
                setNotifications(serverNotifications);
            } else {
                setNotifications(prev => [...prev, ...serverNotifications]);
            }

            setHasMore(serverNotifications.length >= 20);
            if (!isRefresh) { setPage(prev => prev + 1); }
        } catch (error) {
            // ✅ معالجة صامتة للأخطاء - لا نعرض رسائل خطأ للمستخدم
            console.log('[NotificationsScreen] Error loading notifications:', error.message);
            if (isRefresh) { setNotifications([]); }
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [user?.id, page, hasMore]);

    useEffect(() => {
        loadNotifications(true);
    }, []);

    const getNotificationIcon = (type) => {
        switch (type) {
            case 'trade':
            case 'trade_opened':
            case 'trade_closed':
                return 'chart-line';
            case 'profit':
            case 'win':
                return 'trending-up';
            case 'loss':
                return 'trending-down';
            case 'alert':
            case 'warning':
                return 'alert-triangle';
            case 'system':
                return 'settings';
            case 'security':
                return 'shield';
            default:
                return 'notification';
        }
    };

    const getNotificationColor = (type) => {
        switch (type) {
            case 'profit':
            case 'win':
            case 'trade_closed':
                return theme.colors.success;
            case 'loss':
                return theme.colors.error;
            case 'alert':
            case 'warning':
                return theme.colors.warning;
            case 'security':
                return theme.colors.error;
            default:
                return theme.colors.primary;
        }
    };

    const formatTime = (timestamp) => {
        if (!timestamp) { return ''; }
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) { return 'الآن'; }
        if (diff < 3600000) { return `منذ ${Math.floor(diff / 60000)} دقيقة`; }
        if (diff < 86400000) { return `منذ ${Math.floor(diff / 3600000)} ساعة`; }
        if (diff < 604800000) { return `منذ ${Math.floor(diff / 86400000)} يوم`; }

        return date.toLocaleDateString('ar-SA');
    };

    const markAsRead = async (notificationId) => {
        try {
            // ✅ تحديث في Backend
            const response = await DatabaseApiService.markNotificationRead?.(notificationId);

            if (response?.success !== false) {
                // ✅ تحديث الحالة المحلية
                setNotifications(prev =>
                    prev.map(n => n.id === notificationId ? { ...n, isRead: true, read: true } : n)
                );

                // ✅ تحديث التخزين المحلي
                await NotificationService.markNotificationAsRead(notificationId);

                // ✅ إعادة تحميل من الخادم للتأكد من التزامن
                setTimeout(() => loadNotifications(true), 500);
            }
        } catch (error) {
            console.log('[NotificationsScreen] Mark read error:', error);
        }
    };

    // ✅ مسح جميع الإشعارات
    const clearAllNotifications = async () => {
        try {
            await NotificationService.clearAllNotifications();
            setNotifications([]);
            ToastService.showSuccess('تم مسح جميع الإشعارات');
        } catch (error) {
            console.log('[NotificationsScreen] Clear all error:', error);
            ToastService.showError('فشل مسح الإشعارات');
        }
    };

    const renderNotification = ({ item }) => {
        // التوافق مع API: isRead من Backend
        const isRead = item.isRead || item.read || false;

        return (
            <TouchableOpacity
                style={[styles.notificationItem, !isRead && styles.unreadItem]}
                onPress={() => markAsRead(item.id)}
                activeOpacity={0.7}
            >
                <View style={[styles.iconContainer, { backgroundColor: getNotificationColor(item.type) + '20' }]}>
                    <BrandIcon
                        name={getNotificationIcon(item.type)}
                        size={24}
                        color={getNotificationColor(item.type)}
                    />
                </View>
                <View style={styles.contentContainer}>
                    <Text style={styles.notificationTitle}>{item.title || 'إشعار'}</Text>
                    <Text style={styles.notificationMessage} numberOfLines={2}>
                        {item.message || item.body || ''}
                    </Text>
                    <Text style={styles.notificationTime}>{formatTime(item.createdAt || item.created_at || item.timestamp)}</Text>
                </View>
                {!isRead && <View style={styles.unreadDot} />}
            </TouchableOpacity>
        );
    };

    const renderEmpty = () => (
        <View style={styles.emptyContainer}>
            <BrandIcon name="notification" size={64} color={theme.colors.textSecondary} />
            <Text style={styles.emptyTitle}>لا توجد إشعارات</Text>
            <Text style={styles.emptySubtitle}>
                {isDemoData ? '📊 لا توجد إشعارات تجريبية حالياً' : '💰 لا توجد إشعارات حقيقية حالياً'}
            </Text>
            {/* ✅ شارة توضيحية لنوع البيانات */}
            <Text style={styles.dataTypeBadge}>
                ({isDemoData ? 'بيانات تجريبية' : 'بيانات حقيقية'})
            </Text>
        </View>
    );

    if (loading) {
        return (
            <View style={styles.container}>
                {/* ✅ Header يأتي من Navigator */}
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color={theme.colors.primary} />
                </View>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            {/* ✅ Header يأتي من Navigator */}
            <FlatList
                data={notifications}
                renderItem={renderNotification}
                keyExtractor={(item, index) => item.id?.toString() || index.toString()}
                contentContainerStyle={[
                    styles.listContent,
                    notifications.length === 0 && styles.emptyList,
                ]}
                ListEmptyComponent={renderEmpty}
                refreshControl={
                    <RefreshControl
                        refreshing={refreshing}
                        onRefresh={() => loadNotifications(true)}
                        tintColor={theme.colors.primary}
                    />
                }
                onEndReached={() => loadNotifications(false)}
                onEndReachedThreshold={0.5}
                showsVerticalScrollIndicator={false}
            />
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingVertical: 12,
        paddingTop: 50,
        backgroundColor: theme.colors.surface,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    backButton: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: theme.colors.background,
        alignItems: 'center',
        justifyContent: 'center',
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: theme.colors.text,
    },
    headerRight: {
        minWidth: 40,
    },
    markAllButton: {
        padding: 8,
    },
    markAllText: {
        fontSize: 12,
        color: theme.colors.primary,
    },
    loadingContainer: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    listContent: {
        padding: 16,
    },
    emptyList: {
        flex: 1,
    },
    notificationItem: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    unreadItem: {
        backgroundColor: theme.colors.primary + '08',
        borderColor: theme.colors.primary + '30',
    },
    iconContainer: {
        width: 48,
        height: 48,
        borderRadius: 24,
        alignItems: 'center',
        justifyContent: 'center',
        marginLeft: 12,
    },
    contentContainer: {
        flex: 1,
    },
    notificationTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 4,
        textAlign: 'right',
    },
    notificationMessage: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        lineHeight: 20,
        textAlign: 'right',
    },
    notificationTime: {
        fontSize: 11,
        color: theme.colors.textMuted,
        marginTop: 8,
        textAlign: 'right',
    },
    unreadDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: theme.colors.primary,
        position: 'absolute',
        top: 16,
        right: 16,
    },
    emptyContainer: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: 60,
    },
    emptyTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: theme.colors.text,
        marginTop: 16,
    },
    emptySubtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        marginTop: 8,
    },
    clearButton: {
        paddingHorizontal: 12,
        paddingVertical: 6,
    },
    clearButtonText: {
        fontSize: 13,
        color: theme.colors.error,
        fontWeight: '500',
    },
});

export default NotificationsScreen;
