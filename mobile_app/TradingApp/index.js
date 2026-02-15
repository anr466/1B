/**
 * @format
 */

import { AppRegistry, LogBox } from 'react-native';
import App from './App';
import ConsoleMonitor from './src/utils/ConsoleMonitor';

// ✅ تفعيل مراقبة Console في وضع التطوير
ConsoleMonitor.init();

// ✅ إخفاء الأخطاء غير الحرجة من المستخدم
LogBox.ignoreLogs([
    'Get qualified coins failed',
    'Request failed with status code 404',
    'Request failed with status code 500',
    'Network request failed',
    'Possible Unhandled Promise Rejection',
    'VirtualizedLists should never be nested',
    'Non-serializable values were found',
    '[messaging/unknown]',
    'firebase',
    'Firebase',
    'VIBRATE',
]);

// تسجيل التطبيق باسم ثابت لتجنب مشاكل التسجيل
AppRegistry.registerComponent('TradingApp', () => App);
