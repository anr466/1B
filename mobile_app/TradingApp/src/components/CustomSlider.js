/**
 * Custom Slider Component
 * مكون Slider مخصص يعمل بشكل موثوق على Android
 */

import React, { useState, useRef, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    PanResponder,
} from 'react-native';
import { theme } from '../theme/theme';
import { hapticLight, hapticSelection } from '../utils/HapticFeedback';

const THUMB_SIZE = 28;
const TRACK_HEIGHT = 6;

const CustomSlider = ({
    minimumValue = 0,
    maximumValue = 100,
    value = 50,
    step = 1,
    onValueChange,
    onSlidingComplete,
    minimumTrackTintColor = theme.colors.primary,
    maximumTrackTintColor = '#444',
    thumbTintColor = theme.colors.primary,
    disabled = false,
    unit = '',
    showValue = true,
    style,
}) => {
    const [containerWidth, setContainerWidth] = useState(0);
    const [localValue, setLocalValue] = useState(value);

    // Refs للقيم التي نحتاجها داخل PanResponder
    const widthRef = useRef(0);
    const valueRef = useRef(value);
    const startValueRef = useRef(value);
    const lastHapticValue = useRef(value);
    const onValueChangeRef = useRef(onValueChange);
    const onSlidingCompleteRef = useRef(onSlidingComplete);

    // تحديث القيمة المحلية عند تغيير القيمة من الخارج
    useEffect(() => {
        setLocalValue(value);
        valueRef.current = value;
    }, [value]);

    // تحديث refs
    useEffect(() => {
        widthRef.current = containerWidth;
        onValueChangeRef.current = onValueChange;
        onSlidingCompleteRef.current = onSlidingComplete;
    });

    // إنشاء PanResponder
    const panResponder = useRef(
        PanResponder.create({
            onStartShouldSetPanResponder: () => true,
            onMoveShouldSetPanResponder: () => true,
            onPanResponderTerminationRequest: () => false,

            onPanResponderGrant: () => {
                hapticLight();
                startValueRef.current = valueRef.current;
                lastHapticValue.current = valueRef.current;
            },

            onPanResponderMove: (_, gestureState) => {
                const width = widthRef.current;
                if (width <= 0) {return;}

                // سحب لليمين (dx موجب) = زيادة القيمة
                const deltaValue = (gestureState.dx / width) * (maximumValue - minimumValue);
                let newValue = startValueRef.current + deltaValue;

                if (step > 0) {
                    newValue = Math.round(newValue / step) * step;
                }

                newValue = Math.max(minimumValue, Math.min(maximumValue, newValue));

                // اهتزاز عند تغيير القيمة
                if (newValue !== lastHapticValue.current) {
                    hapticSelection();
                    lastHapticValue.current = newValue;
                }

                valueRef.current = newValue;
                setLocalValue(newValue);
                onValueChangeRef.current && onValueChangeRef.current(newValue);
            },

            onPanResponderRelease: (_, gestureState) => {
                const width = widthRef.current;
                if (width <= 0) {return;}

                const deltaValue = (gestureState.dx / width) * (maximumValue - minimumValue);
                let finalValue = startValueRef.current + deltaValue;

                if (step > 0) {
                    finalValue = Math.round(finalValue / step) * step;
                }

                finalValue = Math.max(minimumValue, Math.min(maximumValue, finalValue));

                valueRef.current = finalValue;
                setLocalValue(finalValue);
                onSlidingCompleteRef.current && onSlidingCompleteRef.current(finalValue);
            },
        })
    ).current;

    // حساب النسبة للعرض
    const percentage = (localValue - minimumValue) / (maximumValue - minimumValue);
    // عكس موقع المؤشر: القيمة الصغيرة على اليسار، الكبيرة على اليمين
    const thumbPosition = (1 - percentage) * (containerWidth - THUMB_SIZE);

    // تنسيق القيمة للعرض
    const formatValue = (val) => {
        if (step < 1) {
            return val.toFixed(1);
        }
        return Math.round(val).toString();
    };

    const displayValue = `${formatValue(localValue)}${unit}`;

    return (
        <View style={[styles.wrapper, style]}>
            <View
                style={styles.container}
                onLayout={(e) => setContainerWidth(e.nativeEvent.layout.width)}
                {...panResponder.panHandlers}
            >
                {/* Track الخلفي */}
                <View style={[styles.track, { backgroundColor: maximumTrackTintColor }]}>
                    {/* Track الملون - يبدأ من اليمين */}
                    <View
                        style={[
                            styles.filledTrack,
                            {
                                backgroundColor: minimumTrackTintColor,
                                width: `${percentage * 100}%`,
                                right: 0,
                            },
                        ]}
                    />
                </View>

                {/* Thumb مع القيمة */}
                {containerWidth > 0 && (
                    <View
                        style={[
                            styles.thumb,
                            {
                                backgroundColor: thumbTintColor,
                                left: thumbPosition,
                            },
                        ]}
                    >
                        {showValue && (
                            <View style={styles.valueContainer}>
                                <Text style={styles.valueText}>{formatValue(localValue)}</Text>
                            </View>
                        )}
                    </View>
                )}
            </View>

            {/* عرض القيمة أسفل Slider */}
            {showValue && (
                <View style={styles.labelContainer}>
                    <Text style={styles.minLabel}>{minimumValue}{unit}</Text>
                    <Text style={styles.currentValueLabel}>{displayValue}</Text>
                    <Text style={styles.maxLabel}>{maximumValue}{unit}</Text>
                </View>
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    wrapper: {
        marginVertical: 8,
    },
    container: {
        height: 50,
        justifyContent: 'center',
        marginBottom: 8,
    },
    track: {
        height: TRACK_HEIGHT,
        borderRadius: TRACK_HEIGHT / 2,
        width: '100%',
    },
    filledTrack: {
        position: 'absolute',
        height: '100%',
        borderRadius: TRACK_HEIGHT / 2,
    },
    thumb: {
        position: 'absolute',
        width: THUMB_SIZE,
        height: THUMB_SIZE,
        borderRadius: THUMB_SIZE / 2,
        elevation: 6,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.3,
        shadowRadius: 4,
        top: (50 - THUMB_SIZE) / 2,
        alignItems: 'center',
        justifyContent: 'center',
    },
    valueContainer: {
        position: 'absolute',
        top: -32,
        backgroundColor: theme.colors.primary,
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 6,
        minWidth: 40,
        alignItems: 'center',
    },
    valueText: {
        color: '#FFF',
        fontSize: 12,
        fontWeight: '700',
    },
    labelContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 4,
    },
    minLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        fontWeight: '500',
    },
    maxLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        fontWeight: '500',
    },
    currentValueLabel: {
        fontSize: 14,
        color: theme.colors.primary,
        fontWeight: '700',
    },
});

export default CustomSlider;
