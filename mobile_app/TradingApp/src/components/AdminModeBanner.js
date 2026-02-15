import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Icon from './CustomIcons';
import { theme } from '../theme/theme';

/**
 * مكون موحد لعرض Banner تحذيري للأدمن
 * ✅ يظهر فقط في الأعلى - غير مكرر
 * ✅ نص مختصر وواضح
 */
const AdminModeBanner = ({ style }) => {
    return (
        <View style={[styles.container, style]}>
            <Icon name="warning" size={18} color="#FFA500" />
            <Text style={styles.text}>
                وضع الأدمن - جميع الصفقات تجريبية
            </Text>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(255, 165, 0, 0.1)',
        borderBottomWidth: 1,
        borderBottomColor: 'rgba(255, 165, 0, 0.3)',
        paddingHorizontal: 16,
        paddingVertical: 8,
        gap: 8,
    },
    text: {
        fontSize: 13,
        fontWeight: '500',
        color: '#FFA500',
    },
});

export default AdminModeBanner;
