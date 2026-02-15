/**
 * 🧪 اختبارات ServerConfig
 * تغطي: التهيئة، إدارة IP، إدارة الاتصال، نقاط النهاية
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

describe('ServerConfig', () => {
  let ServerConfig;

  beforeEach(() => {
    jest.clearAllMocks();
    AsyncStorage.getItem.mockResolvedValue(null);
    AsyncStorage.setItem.mockResolvedValue(undefined);
    AsyncStorage.multiRemove.mockResolvedValue(undefined);

    jest.isolateModules(() => {
      ServerConfig = require('config/ServerConfig').default;
    });
  });

  // ═══════════════════════════════════════════
  // CONSTRUCTOR & DEFAULTS
  // ═══════════════════════════════════════════
  describe('Constructor & Defaults', () => {
    test('has correct default port', () => {
      expect(ServerConfig.SERVER.PORT).toBe(3002);
    });

    test('has correct default protocol', () => {
      expect(ServerConfig.SERVER.PROTOCOL).toBe('http');
    });

    test('has correct default timeout', () => {
      expect(ServerConfig.SERVER.TIMEOUT).toBe(10000);
    });

    test('connection starts disconnected', () => {
      expect(ServerConfig.connection.isConnected).toBe(false);
      expect(ServerConfig.connection.baseURL).toBeNull();
    });
  });

  // ═══════════════════════════════════════════
  // ENDPOINTS STRUCTURE
  // ═══════════════════════════════════════════
  describe('Endpoints Structure', () => {
    test('AUTH endpoints are correctly defined', () => {
      const auth = ServerConfig.ENDPOINTS.AUTH;
      expect(auth.LOGIN).toBe('/api/auth/login');
      expect(auth.REGISTER).toBe('/api/auth/register');
      expect(auth.LOGOUT).toBe('/api/auth/logout');
      expect(auth.REFRESH).toBe('/api/auth/refresh');
      expect(auth.VALIDATE_SESSION).toBe('/api/auth/validate-session');
      expect(auth.FORGOT_PASSWORD).toBe('/api/auth/forgot-password');
      expect(auth.RESET_PASSWORD).toBe('/api/auth/reset-password');
    });

    test('USER endpoints are correctly defined', () => {
      const user = ServerConfig.ENDPOINTS.USER;
      expect(user.PORTFOLIO).toBe('/api/user/portfolio');
      expect(user.STATS).toBe('/api/user/stats');
      expect(user.TRADES).toBe('/api/user/trades');
      expect(user.SETTINGS).toBe('/api/user/settings');
      expect(user.PROFILE).toBe('/api/user/profile');
      expect(user.BINANCE_KEYS).toBe('/api/user/binance-keys');
    });

    test('ADMIN endpoints are correctly defined', () => {
      const admin = ServerConfig.ENDPOINTS.ADMIN;
      expect(admin.SYSTEM_STATUS).toBe('/api/admin/system/status');
      expect(admin.SYSTEM_STATS).toBe('/api/admin/system/stats');
      expect(admin.USERS).toBe('/api/admin/users');
      expect(admin.ERRORS).toBe('/api/admin/errors');
    });

    test('STATUS endpoint is defined', () => {
      expect(ServerConfig.ENDPOINTS.STATUS).toBe('/api/system/status');
    });
  });

  // ═══════════════════════════════════════════
  // BASE URL GENERATION
  // ═══════════════════════════════════════════
  describe('Base URL Generation', () => {
    test('getBaseURL() returns connection.baseURL when set', () => {
      ServerConfig.connection.baseURL = 'http://192.168.1.50:3002';
      expect(ServerConfig.getBaseURL()).toBe('http://192.168.1.50:3002');
    });

    test('getBaseURL() builds URL from hostIP when no connection', () => {
      ServerConfig.connection.baseURL = null;
      ServerConfig.ipConfig.hostIP = '192.168.1.100';
      expect(ServerConfig.getBaseURL()).toBe('http://192.168.1.100:3002');
    });

    test('getEndpointURL() combines base URL with endpoint', () => {
      ServerConfig.connection.baseURL = 'http://localhost:3002';
      const url = ServerConfig.getEndpointURL('/api/auth/login');
      expect(url).toBe('http://localhost:3002/api/auth/login');
    });
  });

  // ═══════════════════════════════════════════
  // CONNECTION MANAGEMENT
  // ═══════════════════════════════════════════
  describe('Connection Management', () => {
    test('setConnection() updates connection state', () => {
      ServerConfig.setConnection('usb_port_forwarding', 'http://localhost:3002');

      expect(ServerConfig.connection.method).toBe('usb_port_forwarding');
      expect(ServerConfig.connection.baseURL).toBe('http://localhost:3002');
      expect(ServerConfig.connection.isConnected).toBe(true);
      expect(ServerConfig.connection.error).toBeNull();
    });

    test('setConnectionError() updates error state', () => {
      const error = new Error('Connection failed');
      ServerConfig.setConnectionError(error);

      expect(ServerConfig.connection.isConnected).toBe(false);
      expect(ServerConfig.connection.error).toBe(error);
    });
  });

  // ═══════════════════════════════════════════
  // IP MANAGEMENT
  // ═══════════════════════════════════════════
  describe('IP Management', () => {
    test('setHostIP() saves IP to AsyncStorage', async () => {
      await ServerConfig.setHostIP('192.168.1.200');

      expect(ServerConfig.ipConfig.hostIP).toBe('192.168.1.200');
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        '@server_config_last_known_ip',
        '192.168.1.200'
      );
    });

    test('initialize() loads saved IP from AsyncStorage', async () => {
      AsyncStorage.getItem.mockResolvedValue('192.168.1.50');

      await ServerConfig.initialize();

      expect(AsyncStorage.getItem).toHaveBeenCalledWith('@server_config_last_known_ip');
    });
  });

  // ═══════════════════════════════════════════
  // RESET
  // ═══════════════════════════════════════════
  describe('Reset', () => {
    test('reset() clears all state', async () => {
      ServerConfig.connection.baseURL = 'http://localhost:3002';
      ServerConfig.connection.isConnected = true;
      ServerConfig.ipConfig.hostIP = '192.168.1.100';

      await ServerConfig.reset();

      expect(ServerConfig.connection.baseURL).toBeNull();
      expect(ServerConfig.connection.isConnected).toBe(false);
      expect(ServerConfig.ipConfig.hostIP).toBeNull();
      expect(AsyncStorage.multiRemove).toHaveBeenCalled();
    });
  });

  // ═══════════════════════════════════════════
  // POSSIBLE URLS
  // ═══════════════════════════════════════════
  describe('Possible URLs', () => {
    test('getPossibleURLs() always includes port_forwarding', () => {
      const urls = ServerConfig.getPossibleURLs();
      const portForwarding = urls.find(u => u.method === 'port_forwarding');
      expect(portForwarding).toBeDefined();
      expect(portForwarding.url).toBe('http://localhost:3002');
      expect(portForwarding.priority).toBe(1);
    });

    test('getPossibleURLs() includes local_network when hostIP is set', () => {
      ServerConfig.ipConfig.hostIP = '192.168.1.100';
      const urls = ServerConfig.getPossibleURLs();
      const localNet = urls.find(u => u.method === 'local_network');
      expect(localNet).toBeDefined();
      expect(localNet.url).toBe('http://192.168.1.100:3002');
    });
  });

  // ═══════════════════════════════════════════
  // CONNECTION INFO
  // ═══════════════════════════════════════════
  describe('Connection Info', () => {
    test('getConnectionInfo() returns complete state', () => {
      ServerConfig.setConnection('local_network', 'http://192.168.1.100:3002');
      ServerConfig.ipConfig.hostIP = '192.168.1.100';

      const info = ServerConfig.getConnectionInfo();
      expect(info.method).toBe('local_network');
      expect(info.baseURL).toBe('http://192.168.1.100:3002');
      expect(info.isConnected).toBe(true);
      expect(info.hostIP).toBe('192.168.1.100');
      expect(info.port).toBe(3002);
      expect(info.protocol).toBe('http');
      expect(info.possibleURLs).toBeInstanceOf(Array);
    });

    test('getConfig() returns full configuration', () => {
      const config = ServerConfig.getConfig();
      expect(config).toHaveProperty('server');
      expect(config).toHaveProperty('endpoints');
      expect(config).toHaveProperty('ip');
      expect(config).toHaveProperty('connection');
      expect(config).toHaveProperty('debug');
    });
  });
});
