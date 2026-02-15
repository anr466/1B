/**
 * 🎨 مكتبة الأيقونات المخصصة - 1B Trading
 * أيقونات SVG احترافية مخصصة بدون مكتبات خارجية
 * ✅ يستخدم BrandIcons للأيقونات الرسومية
 */

import React from 'react';
import BrandIcon from './BrandIcons';
import FingerprintIcon from './FingerprintIcon';

/**
 * تحويل أسماء الأيقونات القديمة للجديدة
 */
const NAME_MAPPING = {
  // أيقونات التنقل
  'arrowLeft': 'arrow-back',
  'arrowRight': 'arrow-forward',

  // أيقونات المصادقة
  'security': 'shield',
  'face': 'user',
  'person': 'user',

  // أيقونات البريد
  'mark-email-read': 'email',

  // أيقونات الحالة
  'loading': 'refresh',
  'success': 'check-circle',
  'error': 'close',

  // أيقونات التداول
  'chart-line': 'chart',
  'trending-neutral': 'swap',
  'document': 'list',
  'brain': 'robot',

  // أيقونات الإدارة
  'users': 'user',
  'trades': 'list',
  'positions': 'chart',
  'server': 'dashboard',
  'database': 'dashboard',
  'emergency': 'warning',
  'activity': 'chart',
  'chart-up': 'trending-up',
  'chart-down': 'trending-down',

  // أيقونات إضافية
  'filter': 'menu',
  'sort': 'swap',
  'download': 'arrow-back',
  'upload': 'arrow-forward',
  'share': 'link',
  'bookmark': 'star',
};

const CustomIcons = ({ name, size = 24, color = '#FFFFFF', style }) => {
  // استخدام أيقونة البصمة المخصصة
  if (name === 'fingerprint') {
    return <FingerprintIcon size={size} color={color} style={style} />;
  }

  // تحويل الاسم القديم للجديد
  const mappedName = NAME_MAPPING[name] || name;

  return (
    <BrandIcon
      name={mappedName}
      size={size}
      color={color}
      style={style}
    />
  );
};

export default CustomIcons;
