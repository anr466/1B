import 'react-native-gesture-handler/jestSetup';

// Mock للخدمات الخارجية
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);

// Mock للـ react-native-linear-gradient
jest.mock('react-native-linear-gradient', () => 'LinearGradient');

// Mock للـ react-native-fs
jest.mock('react-native-fs', () => ({
  writeFile: jest.fn(() => Promise.resolve()),
  readFile: jest.fn(() => Promise.resolve('')),
  exists: jest.fn(() => Promise.resolve(true)),
  unlink: jest.fn(() => Promise.resolve()),
  mkdir: jest.fn(() => Promise.resolve()),
  DocumentDirectoryPath: '/mock/documents',
  CachesDirectoryPath: '/mock/caches',
}));

// Mock للـ encrypted-storage
jest.mock('react-native-encrypted-storage', () => ({
  setItem: jest.fn(() => Promise.resolve()),
  getItem: jest.fn(() => Promise.resolve(null)),
  removeItem: jest.fn(() => Promise.resolve()),
  clear: jest.fn(() => Promise.resolve()),
}));

jest.mock('react-native-vector-icons/MaterialIcons', () => 'Icon');
jest.mock('react-native-vector-icons/Ionicons', () => 'Icon');

// Mock للـ Firebase
jest.mock('@react-native-firebase/app', () => ({
  utils: () => ({
    FilePath: {
      PICTURES_DIRECTORY: '/tmp/',
    },
  }),
}));

jest.mock('@react-native-firebase/messaging', () => ({
  hasPermission: jest.fn(() => Promise.resolve(true)),
  subscribeToTopic: jest.fn(),
  unsubscribeFromTopic: jest.fn(),
  requestPermission: jest.fn(() => Promise.resolve(true)),
  getToken: jest.fn(() => Promise.resolve('myMockToken')),
}));

// Mock للـ React Navigation
jest.mock('@react-navigation/native', () => {
  const actualNav = jest.requireActual('@react-navigation/native');
  return {
    ...actualNav,
    useNavigation: () => ({
      navigate: jest.fn(),
      dispatch: jest.fn(),
      goBack: jest.fn(),
      setOptions: jest.fn(),
      addListener: jest.fn(() => ({ remove: jest.fn() })),
      removeListener: jest.fn(),
      isFocused: jest.fn(() => true),
      canGoBack: jest.fn(() => true),
      reset: jest.fn(),
      replace: jest.fn(),
    }),
    useRoute: () => ({
      params: {},
      key: 'test-route',
      name: 'TestScreen',
    }),
    useFocusEffect: jest.fn((callback) => {
      return () => { };
    }),
    useIsFocused: jest.fn(() => true),
  };
});

// Mock للـ Biometrics
jest.mock('react-native-biometrics', () => ({
  isSensorAvailable: jest.fn(() => Promise.resolve({ available: true })),
  createKeys: jest.fn(() => Promise.resolve({ publicKey: 'mockKey' })),
  biometricKeysExist: jest.fn(() => Promise.resolve({ keysExist: true })),
}));

// Mock للـ Device Info
jest.mock('react-native-device-info', () => ({
  getUniqueId: jest.fn(() => Promise.resolve('mock-device-id')),
  getSystemName: jest.fn(() => 'iOS'),
  getSystemVersion: jest.fn(() => '14.0'),
  getModel: jest.fn(() => 'iPhone 15'),
  getBrand: jest.fn(() => 'Apple'),
  getVersion: jest.fn(() => '1.0.0'),
  getBuildNumber: jest.fn(() => '1'),
}));

// ============================================
// Comprehensive Mock للـ React Native Animated
// ============================================
jest.mock('react-native/Libraries/Animated/Animated', () => {
  const mockValue = {
    setValue: jest.fn(),
    setOffset: jest.fn(),
    flattenOffset: jest.fn(),
    extractOffset: jest.fn(),
    addListener: jest.fn(),
    removeListener: jest.fn(),
    removeAllListeners: jest.fn(),
    getValue: jest.fn(() => 0),
  };

  return {
    Value: jest.fn(() => mockValue),
    timing: jest.fn(() => ({ start: jest.fn() })),
    spring: jest.fn(() => ({ start: jest.fn() })),
    decay: jest.fn(() => ({ start: jest.fn() })),
    loop: jest.fn(() => ({ start: jest.fn(), stop: jest.fn() })),
    sequence: jest.fn(() => []),
    parallel: jest.fn(() => []),
    delay: jest.fn(() => []),
    race: jest.fn(() => []),
    add: jest.fn(() => ({})),
    subtract: jest.fn(() => ({})),
    multiply: jest.fn(() => ({})),
    divide: jest.fn(() => ({})),
    modulo: jest.fn(() => ({})),
    diff: jest.fn(() => ({})),
    diffClamp: jest.fn(() => ({})),
    clamp: jest.fn((v) => v),
    event: jest.fn(() => ({})),
    createAnimatedNode: jest.fn(),
    interpolate: jest.fn(() => ({})),
    ColorAnimatedValue: jest.fn(() => mockValue),
  };
});

jest.mock('react-native/Libraries/Animated/Easing', () => ({
  bezier: jest.fn(() => 'mock-easing'),
  linear: () => ({}),
  ease: () => ({}),
  quad: () => ({}),
  cubic: () => ({}),
  sin: () => ({}),
  exp: () => ({}),
  circle: () => ({}),
  elastic: () => ({}),
  bounce: () => ({}),
  in: () => ({}),
  out: () => ({}),
  inOut: () => ({}),
}));

jest.mock('react-native/Libraries/Animated/NativeAnimatedHelper', () => ({
  default: {
    startOperationBatch: jest.fn(),
    finishOperationBatch: jest.fn(),
    createAnimatedNode: jest.fn(),
    getValue: jest.fn(() => 0),
    connectAnimatedNodes: jest.fn(),
    disconnectAnimatedNodes: jest.fn(),
    setAnimatedNodeValue: jest.fn(),
    setAnimatedNodeOffset: jest.fn(),
    flattenAnimatedNodeOffset: jest.fn(),
    extractAnimatedNodeOffset: jest.fn(),
    dropAnimatedNode: jest.fn(),
    addAnimatedEventToView: jest.fn(),
    removeAnimatedEventFromView: jest.fn(),
  },
}));

// Mock للـ react-native-svg
jest.mock('react-native-svg', () => ({
  Svg: 'Svg',
  Circle: 'Circle',
  Rect: 'Rect',
  Text: 'Text',
  Path: 'Path',
  G: 'G',
  Line: 'Line',
  Polyline: 'Polyline',
  Polygon: 'Polygon',
  Defs: 'Defs',
  LinearGradient: 'LinearGradient',
  RadialGradient: 'RadialGradient',
  ClipPath: 'ClipPath',
  Mask: 'Mask',
  Pattern: 'Pattern',
}));

// Mock للـ Safe Area Context
jest.mock('react-native-safe-area-context', () => ({
  SafeAreaProvider: ({ children }) => children,
  SafeAreaView: ({ children }) => children,
  useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }),
  useSafeArea: () => ({ top: 0, bottom: 0, left: 0, right: 0 }),
}));

// Mock للـ React Native Chart Kit
jest.mock('react-native-chart-kit', () => ({
  LineChart: 'LineChart',
  BarChart: 'BarChart',
  PieChart: 'PieChart',
  ProgressChart: 'ProgressChart',
  ContributionGraph: 'ContributionGraph',
}));

// Mock للـ React Native Gesture Handler
jest.mock('react-native-gesture-handler', () => ({
  PanGestureHandler: 'PanGestureHandler',
  TapGestureHandler: 'TapGestureHandler',
  LongPressGestureHandler: 'LongPressGestureHandler',
  GestureHandlerRootView: 'GestureHandlerRootView',
  Swipeable: 'Swipeable',
  DrawerLayout: 'DrawerLayout',
}));

// Mock للـ NetInfo
jest.mock('@react-native-community/netinfo', () => ({
  addEventListener: jest.fn(),
  fetch: jest.fn(() => Promise.resolve({ isConnected: true, connectionType: 'wifi' })),
  getCurrentState: jest.fn(() => Promise.resolve({ isConnected: true, connectionType: 'wifi' })),
}));

// Mock للـ Slider
jest.mock('@react-native-community/slider', () => 'Slider');

// Mock لـ crypto-js
jest.mock('crypto-js', () => ({
  AES: {
    encrypt: jest.fn(() => 'encrypted'),
    decrypt: jest.fn(() => 'decrypted'),
  },
  SHA256: jest.fn(() => 'sha256'),
  enc: {
    Utf8: { stringify: jest.fn(), parse: jest.fn() },
    Base64: { stringify: jest.fn(), parse: jest.fn() },
  },
}));

// Mock لـ Axios
const mockAxiosInstance = {
  get: jest.fn(() => Promise.resolve({ data: {} })),
  post: jest.fn(() => Promise.resolve({ data: {} })),
  put: jest.fn(() => Promise.resolve({ data: {} })),
  delete: jest.fn(() => Promise.resolve({ data: {} })),
  patch: jest.fn(() => Promise.resolve({ data: {} })),
  interceptors: {
    request: { use: jest.fn(), eject: jest.fn() },
    response: { use: jest.fn(), eject: jest.fn() },
  },
  defaults: { headers: { common: {} } },
};

jest.mock('axios', () => {
  const axiosMock = {
    create: jest.fn(() => ({ ...mockAxiosInstance })),
    get: jest.fn(() => Promise.resolve({ data: {} })),
    post: jest.fn(() => Promise.resolve({ data: {} })),
    put: jest.fn(() => Promise.resolve({ data: {} })),
    delete: jest.fn(() => Promise.resolve({ data: {} })),
    defaults: { headers: { common: {} } },
    isAxiosError: jest.fn((err) => !!err?.isAxiosError),
  };
  return axiosMock;
});

// تعطيل console warnings في الاختبارات
global.console = {
  ...console,
  warn: jest.fn(),
  error: jest.fn(),
};

// إصلاح مشاكل Jest Environment
afterEach(() => {
  jest.clearAllMocks();
});

afterAll(() => {
  // تنظيف البيئة
  if (global.gc) {
    global.gc();
  }
});
