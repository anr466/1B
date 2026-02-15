/**
 * نظام رسائل مخصص يتناسق مع Dark Theme
 * بديل احترافي لـ Alert.alert()
 */

import React from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Dimensions,
  BackHandler,
} from 'react-native';
import { theme as Theme } from '../theme/theme';

const { width } = Dimensions.get('window');

class CustomAlertService {
  constructor() {
    this.alertRef = null;
  }

  setAlertRef(ref) {
    this.alertRef = ref;
  }

  show(title, message, buttons = [], options = {}) {
    if (this.alertRef) {
      this.alertRef.show(title, message, buttons, options);
    }
  }

  success(title, message, onPress) {
    this.show(title, message, [{ text: 'موافق', onPress }], { type: 'success' });
  }

  error(title, message, onPress) {
    this.show(title, message, [{ text: 'موافق', onPress }], { type: 'error' });
  }

  warning(title, message, buttons) {
    this.show(title, message, buttons, { type: 'warning' });
  }

  confirm(title, message, onConfirm, onCancel) {
    this.show(title, message, [
      { text: 'إلغاء', style: 'cancel', onPress: onCancel },
      { text: 'تأكيد', onPress: onConfirm },
    ], { type: 'warning' });
  }
}

export const AlertService = new CustomAlertService();

export default class CustomAlert extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      visible: false,
      title: '',
      message: '',
      buttons: [],
      type: 'default',
    };
    this.fadeAnim = new Animated.Value(0);
    this.scaleAnim = new Animated.Value(0.8);
  }

  componentDidMount() {
    AlertService.setAlertRef(this);
    this.backHandler = BackHandler.addEventListener('hardwareBackPress', this.handleBackPress);
  }

  componentWillUnmount() {
    this.backHandler?.remove();
  }

  handleBackPress = () => {
    if (this.state.visible) {
      this.hide();
      return true;
    }
    return false;
  };

  show = (title, message, buttons = [], options = {}) => {
    const defaultButtons = buttons.length > 0 ? buttons : [{ text: 'موافق', onPress: () => { } }];

    this.setState({
      visible: true,
      title,
      message,
      buttons: defaultButtons,
      type: options.type || 'default',
    }, () => {
      Animated.parallel([
        Animated.timing(this.fadeAnim, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.spring(this.scaleAnim, {
          toValue: 1,
          tension: 50,
          friction: 7,
          useNativeDriver: true,
        }),
      ]).start();
    });
  };

  hide = (callback) => {
    Animated.parallel([
      Animated.timing(this.fadeAnim, {
        toValue: 0,
        duration: 150,
        useNativeDriver: true,
      }),
      Animated.timing(this.scaleAnim, {
        toValue: 0.8,
        duration: 150,
        useNativeDriver: true,
      }),
    ]).start(() => {
      this.setState({ visible: false });
      if (callback) {callback();}
    });
  };

  handleButtonPress = (button) => {
    this.hide(() => {
      if (button.onPress) {
        button.onPress();
      }
    });
  };

  getIconAndColor = () => {
    switch (this.state.type) {
      case 'success':
        return { icon: '✓', color: Theme.colors.success };
      case 'error':
        return { icon: '✕', color: Theme.colors.error };
      case 'warning':
        return { icon: '⚠', color: Theme.colors.warning };
      case 'info':
        return { icon: 'ℹ', color: Theme.colors.info };
      default:
        return { icon: null, color: Theme.colors.primary };
    }
  };

  render() {
    const { visible, title, message, buttons } = this.state;
    const { icon, color } = this.getIconAndColor();

    return (
      <Modal
        visible={visible}
        transparent
        animationType="none"
        statusBarTranslucent
        onRequestClose={this.handleBackPress}
      >
        <TouchableOpacity
          activeOpacity={1}
          onPress={() => this.hide()}
          style={styles.overlay}
        >
          <Animated.View
            style={[
              styles.overlayBackground,
              { opacity: this.fadeAnim },
            ]}
          />
        </TouchableOpacity>

        <View style={styles.container} pointerEvents="box-none">
          <Animated.View
            style={[
              styles.alertBox,
              {
                opacity: this.fadeAnim,
                transform: [{ scale: this.scaleAnim }],
              },
            ]}
          >
            {icon && (
              <View style={[styles.iconContainer, { backgroundColor: `${color}15` }]}>
                <Text style={[styles.icon, { color }]}>{icon}</Text>
              </View>
            )}

            <Text style={styles.title}>{title}</Text>

            {message ? (
              <Text style={styles.message}>{message}</Text>
            ) : null}

            <View style={styles.buttonsContainer}>
              {buttons.map((button, index) => {
                const isCancel = button.style === 'cancel';
                const isPrimary = !isCancel && index === buttons.length - 1;

                return (
                  <TouchableOpacity
                    key={index}
                    onPress={() => this.handleButtonPress(button)}
                    style={[
                      styles.button,
                      isPrimary && styles.buttonPrimary,
                      isCancel && styles.buttonCancel,
                      buttons.length === 1 && styles.buttonSingle,
                    ]}
                    activeOpacity={0.8}
                  >
                    <Text
                      style={[
                        styles.buttonText,
                        isPrimary && styles.buttonTextPrimary,
                        isCancel && styles.buttonTextCancel,
                      ]}
                    >
                      {button.text}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </Animated.View>
        </View>
      </Modal>
    );
  }
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 999,
  },
  overlayBackground: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  container: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
    paddingHorizontal: 24,
  },
  alertBox: {
    backgroundColor: '#161925',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 340,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    shadowColor: '#000000', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.37, shadowRadius: 7.49, elevation: 12,
  },
  iconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    alignSelf: 'center',
    marginBottom: 12,
  },
  icon: {
    fontSize: 28,
    fontWeight: '700',
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 8,
  },
  message: {
    fontSize: 15,
    color: '#A0A0A0',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 16,
  },
  buttonsContainer: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 12,
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    backgroundColor: '#1E2235',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    minHeight: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonSingle: {
    flex: 1,
  },
  buttonPrimary: {
    backgroundColor: Theme.colors.primary,
    borderColor: Theme.colors.primary,
  },
  buttonCancel: {
    backgroundColor: 'transparent',
    borderColor: '#2A3250',
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  buttonTextPrimary: {
    color: '#FFFFFF',
  },
  buttonTextCancel: {
    color: '#A0A0A0',
  },
});
