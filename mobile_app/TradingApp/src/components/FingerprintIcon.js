/**
 * أيقونة بصمة الإصبع المخصصة
 * تصميم بسيط بدون SVG
 */

import React from 'react';
import { View, StyleSheet } from 'react-native';

const FingerprintIcon = ({ size = 24, color = '#a78bfa', style }) => {
  const iconSize = size;
  const lineWidth = size * 0.08;

  return (
    <View style={[styles.container, style, { width: iconSize, height: iconSize }]}>
      {/* دوائر متداخلة لتمثيل البصمة */}
      <View style={[styles.circle, styles.outer, {
        width: iconSize,
        height: iconSize,
        borderRadius: iconSize / 2,
        borderWidth: lineWidth,
        borderColor: color,
        borderTopColor: 'transparent',
        borderLeftColor: 'transparent',
      }]} />

      <View style={[styles.circle, styles.middle, {
        width: iconSize * 0.7,
        height: iconSize * 0.7,
        borderRadius: (iconSize * 0.7) / 2,
        borderWidth: lineWidth,
        borderColor: color,
        borderBottomColor: 'transparent',
        borderRightColor: 'transparent',
      }]} />

      <View style={[styles.circle, styles.inner, {
        width: iconSize * 0.45,
        height: iconSize * 0.45,
        borderRadius: (iconSize * 0.45) / 2,
        borderWidth: lineWidth,
        borderColor: color,
        borderTopColor: 'transparent',
      }]} />

      <View style={[styles.circle, styles.center, {
        width: iconSize * 0.25,
        height: iconSize * 0.25,
        borderRadius: (iconSize * 0.25) / 2,
        borderWidth: lineWidth,
        borderColor: color,
        borderBottomColor: 'transparent',
      }]} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  circle: {
    position: 'absolute',
  },
  outer: {},
  middle: {},
  inner: {},
  center: {},
});

export default FingerprintIcon;
