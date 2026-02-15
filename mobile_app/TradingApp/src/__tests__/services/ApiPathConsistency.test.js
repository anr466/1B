/**
 * 🧪 اختبارات اتساق مسارات API
 * تتحقق أن كل دالة في DatabaseApiService تستخدم المسار الصحيح
 * وأنه لا يوجد تكرار /user/user/ أو مسارات خاطئة
 *
 * هذا الملف يقرأ الكود المصدري مباشرة ويحلل المسارات
 */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Mock dependencies
jest.mock('services/UnifiedConnectionService', () => ({
  __esModule: true,
  default: {
    initialize: jest.fn(() => Promise.resolve({ success: true })),
    getBaseURL: jest.fn(() => 'http://localhost:3002'),
  },
  unifiedConnectionService: {
    initialize: jest.fn(() => Promise.resolve({ success: true })),
    getBaseURL: jest.fn(() => 'http://localhost:3002'),
  },
}));

jest.mock('services/UnifiedErrorHandler', () => ({
  __esModule: true,
  default: { handle: jest.fn(), handleSmart: jest.fn(), handleSystemError: jest.fn(), handleUserError: jest.fn() },
}));

jest.mock('services/TempStorageService', () => ({
  __esModule: true,
  default: { getItem: jest.fn(), setItem: jest.fn(), removeItem: jest.fn() },
}));

jest.mock('services/LoggerService', () => ({
  __esModule: true,
  default: { info: jest.fn(), warn: jest.fn(), error: jest.fn(), debug: jest.fn() },
}));

describe('API Path Consistency', () => {
  let service;
  let mockApiClient;
  let apiClientCalls;
  let directAxiosCalls;

  beforeEach(() => {
    jest.clearAllMocks();

    // Re-set mock implementations (resetMocks:true strips them)
    const connService = require('services/UnifiedConnectionService').default;
    connService.initialize.mockResolvedValue({ success: true });
    connService.getBaseURL.mockReturnValue('http://localhost:3002');

    const errorHandler = require('services/UnifiedErrorHandler').default;
    errorHandler.handleSmart.mockReturnValue({ success: false });
    errorHandler.handleSystemError.mockImplementation(() => { });
    errorHandler.handleUserError.mockImplementation(() => { });

    const TempStorage = require('services/TempStorageService').default;
    TempStorage.getItem.mockResolvedValue(null);
    TempStorage.setItem.mockResolvedValue(undefined);
    TempStorage.removeItem.mockResolvedValue(undefined);

    const Logger = require('services/LoggerService').default;
    Logger.info.mockImplementation(() => { });
    Logger.warn.mockImplementation(() => { });
    Logger.error.mockImplementation(() => { });
    Logger.debug.mockImplementation(() => { });

    apiClientCalls = [];
    directAxiosCalls = [];

    // Track all apiClient calls
    mockApiClient = {
      get: jest.fn((url, config) => {
        apiClientCalls.push({ method: 'GET', url, via: 'apiClient' });
        return Promise.resolve({ data: { success: true } });
      }),
      post: jest.fn((url, data, config) => {
        apiClientCalls.push({ method: 'POST', url, via: 'apiClient' });
        return Promise.resolve({ data: { success: true } });
      }),
      put: jest.fn((url, data, config) => {
        apiClientCalls.push({ method: 'PUT', url, via: 'apiClient' });
        return Promise.resolve({ data: { success: true } });
      }),
      delete: jest.fn((url, config) => {
        apiClientCalls.push({ method: 'DELETE', url, via: 'apiClient' });
        return Promise.resolve({ data: { success: true } });
      }),
      patch: jest.fn((url, data, config) => {
        apiClientCalls.push({ method: 'PATCH', url, via: 'apiClient' });
        return Promise.resolve({ data: { success: true } });
      }),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
      defaults: { headers: { common: {} } },
    };

    axios.create.mockReturnValue(mockApiClient);

    // Track direct axios calls
    axios.get.mockImplementation((url, config) => {
      directAxiosCalls.push({ method: 'GET', url, via: 'directAxios' });
      return Promise.resolve({ data: { success: true } });
    });
    axios.post.mockImplementation((url, data, config) => {
      directAxiosCalls.push({ method: 'POST', url, via: 'directAxios' });
      return Promise.resolve({ data: { success: true } });
    });
    axios.put.mockImplementation((url, data, config) => {
      directAxiosCalls.push({ method: 'PUT', url, via: 'directAxios' });
      return Promise.resolve({ data: { success: true } });
    });
    axios.delete.mockImplementation((url, config) => {
      directAxiosCalls.push({ method: 'DELETE', url, via: 'directAxios' });
      return Promise.resolve({ data: { success: true } });
    });

    jest.isolateModules(() => {
      service = require('services/DatabaseApiService').default;
    });
  });

  // Helper: initialize service before each API call
  async function init() {
    await service.initialize();
    apiClientCalls = [];
    directAxiosCalls = [];
  }

  // ═══════════════════════════════════════════
  // RULE 1: No double /user/ prefix in apiClient calls
  // apiClient baseURL = /api/user, so paths must NOT start with /user/
  // ═══════════════════════════════════════════
  describe('RULE: No double /user/ prefix', () => {
    const userMethods = [
      { name: 'getPortfolio', call: (s) => s.getPortfolio(1, 'demo') },
      { name: 'getStats', call: (s) => s.getStats(1) },
      { name: 'getTrades', call: (s) => s.getTrades(1) },
      { name: 'getActivePositions', call: (s) => s.getActivePositions(1) },
      { name: 'getSettings', call: (s) => s.getSettings(1) },
      { name: 'getProfile', call: (s) => s.getProfile(1) },
      { name: 'getPortfolioHistory', call: (s) => s.getPortfolioHistory(1, 30) },
      { name: 'getDailyPnL', call: (s) => s.getDailyPnL(1, 90) },
      { name: 'getQualifiedCoins', call: (s) => s.getQualifiedCoins(1) },
      { name: 'getBinanceKeys', call: (s) => s.getBinanceKeys(1) },
      { name: 'getNotifications', call: (s) => s.getNotifications(1) },
      { name: 'getTradingMode', call: (s) => s.getTradingMode(1) },
      { name: 'getNotificationSettings', call: (s) => s.getNotificationSettings(1) },
      { name: 'toggleTradeFavorite', call: (s) => s.toggleTradeFavorite(1, true) },
      { name: 'getFavoriteTrades', call: (s) => s.getFavoriteTrades(1) },
      { name: 'getTradesWithDistribution', call: (s) => s.getTradesWithDistribution(1) },
      { name: 'getCacheStatus', call: (s) => s.getCacheStatus() },
      { name: 'clearCache', call: (s) => s.clearCache() },
      { name: 'getIntegrationStatus', call: (s) => s.getIntegrationStatus() },
    ];

    test.each(userMethods)('$name: no /user/ prefix in apiClient path', async ({ call }) => {
      await init();
      await call(service);

      for (const c of apiClientCalls) {
        expect(c.url).not.toMatch(/^\/user\//);
      }
    });
  });

  // ═══════════════════════════════════════════
  // RULE 2: Auth paths start with /auth/
  // ═══════════════════════════════════════════
  describe('RULE: Auth paths use /auth/ prefix', () => {
    test('login() uses /auth/login via apiClient', async () => {
      await init();
      // login uses apiClient.post which we track
      await service.login('a@b.com', 'pass');
      const loginCall = apiClientCalls.find(c => c.url === '/auth/login');
      expect(loginCall).toBeDefined();
      expect(loginCall.method).toBe('POST');
    });

    test('validateSession() uses direct axios to /api/auth/validate-session', async () => {
      await init();
      // validateSession requires a token to proceed
      const AsyncStorage = require('@react-native-async-storage/async-storage');
      AsyncStorage.getItem.mockResolvedValue('test-token');
      await service.validateSession();
      // validateSession uses direct axios, not apiClient
      const valCall = directAxiosCalls.find(c => c.url.includes('/auth/validate-session'));
      expect(valCall).toBeDefined();
      expect(valCall.url).toBe('http://localhost:3002/api/auth/validate-session');
    });

    test('checkAvailability() uses /auth/check-availability', async () => {
      await init();
      await service.checkAvailability('a@b.com');
      expect(apiClientCalls[0].url).toBe('/auth/check-availability');
    });
  });

  // ═══════════════════════════════════════════
  // RULE 3: Admin paths start with /admin/
  // ═══════════════════════════════════════════
  describe('RULE: Admin paths use /admin/ prefix', () => {
    const adminMethods = [
      { name: 'getSystemStats', call: (s) => s.getSystemStats(), path: '/admin/system/stats' },
      { name: 'getTradingStats', call: (s) => s.getTradingStats(), path: '/admin/trades/stats' },
      { name: 'getAdminErrors', call: (s) => s.getAdminErrors(), path: '/admin/errors' },
      { name: 'getAdminNotificationSettings', call: (s) => s.getAdminNotificationSettings(), path: '/admin/notification-settings' },
      { name: 'getAllUsers', call: (s) => s.getAllUsers(), path: '/admin/users/all' },
    ];

    test.each(adminMethods)('$name → $path', async ({ call, path }) => {
      await init();
      await call(service);

      const allPaths = apiClientCalls.map(c => c.url);
      expect(allPaths).toContain(path);
    });
  });

  // ═══════════════════════════════════════════
  // RULE 4: ML paths use direct axios (NOT apiClient)
  // ML endpoints are at /api/ml/* not /api/user/ml/*
  // ═══════════════════════════════════════════
  describe('RULE: ML paths use direct axios', () => {
    test('getMLFullStatus() calls /api/ml/status via direct axios', async () => {
      await init();
      await service.getMLFullStatus();

      expect(directAxiosCalls.length).toBeGreaterThan(0);
      const mlCall = directAxiosCalls.find(c => c.url.includes('/api/ml/status'));
      expect(mlCall).toBeDefined();
      expect(mlCall.url).toBe('http://localhost:3002/api/ml/status');

      // Should NOT use apiClient for ML
      const apiClientML = apiClientCalls.find(c => c.url.includes('ml'));
      expect(apiClientML).toBeUndefined();
    });

    test('getMLPatterns() calls /api/ml/patterns via direct axios', async () => {
      await init();
      await service.getMLPatterns();

      const mlCall = directAxiosCalls.find(c => c.url.includes('/api/ml/patterns'));
      expect(mlCall).toBeDefined();
      expect(mlCall.url).toBe('http://localhost:3002/api/ml/patterns');
    });
  });

  // ═══════════════════════════════════════════
  // RULE 5: FCM paths use direct axios to /api/notifications/
  // ═══════════════════════════════════════════
  describe('RULE: FCM paths use direct axios to /notifications/', () => {
    test('registerFCMToken() → POST /api/notifications/fcm-token', async () => {
      await init();
      await service.registerFCMToken('test-token');

      const fcmCall = directAxiosCalls.find(c => c.url.includes('/notifications/fcm-token'));
      expect(fcmCall).toBeDefined();
      expect(fcmCall.method).toBe('POST');
      expect(fcmCall.url).toBe('http://localhost:3002/api/notifications/fcm-token');
    });

    test('unregisterFCMToken() → DELETE /api/notifications/fcm-token', async () => {
      await init();
      await service.unregisterFCMToken(1, 'test-token');

      const fcmCall = directAxiosCalls.find(c => c.url.includes('/notifications/fcm-token'));
      expect(fcmCall).toBeDefined();
      expect(fcmCall.method).toBe('DELETE');
      expect(fcmCall.url).toBe('http://localhost:3002/api/notifications/fcm-token');
    });
  });

  // ═══════════════════════════════════════════
  // RULE 6: System control uses direct axios with full URLs
  // ═══════════════════════════════════════════
  describe('RULE: System control uses direct axios', () => {
    test('getBackgroundSystemStatus() → GET .../api/admin/system/status', async () => {
      await init();
      await service.getBackgroundSystemStatus();

      const sysCall = directAxiosCalls.find(c => c.url.includes('/admin/system/status'));
      expect(sysCall).toBeDefined();
      expect(sysCall.url).toBe('http://localhost:3002/api/admin/system/status');
    });

    test('startSystem() → POST .../api/admin/trading/start', async () => {
      await init();
      await service.startSystem();

      const startCall = directAxiosCalls.find(c => c.url.includes('/admin/trading/start'));
      expect(startCall).toBeDefined();
      expect(startCall.url).toBe('http://localhost:3002/api/admin/trading/start');
    });

    test('stopSystem() → POST .../api/admin/trading/stop', async () => {
      await init();
      await service.stopSystem();

      const stopCall = directAxiosCalls.find(c => c.url.includes('/admin/trading/stop'));
      expect(stopCall).toBeDefined();
      expect(stopCall.url).toBe('http://localhost:3002/api/admin/trading/stop');
    });
  });

  // ═══════════════════════════════════════════
  // RULE 7: Exact path mapping for critical user endpoints
  // ═══════════════════════════════════════════
  describe('RULE: Exact paths for user endpoints', () => {
    const exactPaths = [
      { name: 'getPortfolio(1, demo)', call: (s) => s.getPortfolio(1, 'demo'), expected: '/portfolio/1?mode=demo' },
      { name: 'getStats(1)', call: (s) => s.getStats(1), expected: '/stats/1' },
      { name: 'getSettings(1)', call: (s) => s.getSettings(1), expected: '/settings/1' },
      { name: 'getProfile(1)', call: (s) => s.getProfile(1), expected: '/profile/1' },
      { name: 'getTradingMode(1)', call: (s) => s.getTradingMode(1), expected: '/settings/trading-mode/1' },
      { name: 'getBinanceKeys(1)', call: (s) => s.getBinanceKeys(1), expected: '/binance-keys/1' },
      { name: 'getQualifiedCoins(1)', call: (s) => s.getQualifiedCoins(1), expected: '/successful-coins/1' },
    ];

    test.each(exactPaths)('$name → $expected', async ({ call, expected }) => {
      await init();
      await call(service);
      expect(apiClientCalls[0].url).toBe(expected);
    });
  });

  // ═══════════════════════════════════════════
  // REGRESSION: Previously broken paths
  // ═══════════════════════════════════════════
  describe('REGRESSION: Previously fixed path bugs', () => {
    test('No /user/user/ double prefix in any apiClient call', async () => {
      await init();

      // Call every method that was previously broken
      await service.toggleTradeFavorite(1, true);
      await service.getFavoriteTrades(1);
      await service.getTradesWithDistribution(1);
      await service.getNotificationSettings(1);
      await service.updateNotificationSettings(1, {});
      await service.getCacheStatus();
      await service.clearCache();
      await service.getIntegrationStatus();

      // None should have /user/ prefix (since apiClient already has /api/user base)
      for (const call of apiClientCalls) {
        expect(call.url).not.toMatch(/^\/user\//);
      }
    });

    test('ML methods do NOT use apiClient (would cause /api/user/ml/...)', async () => {
      await init();
      await service.getMLFullStatus();
      await service.getMLPatterns();

      // No apiClient calls for ML
      const mlApiClient = apiClientCalls.filter(c => c.url.includes('ml'));
      expect(mlApiClient).toHaveLength(0);

      // Direct axios calls for ML
      const mlDirect = directAxiosCalls.filter(c => c.url.includes('/ml/'));
      expect(mlDirect).toHaveLength(2);
    });

    test('FCM methods do NOT use apiClient (would cause /api/user/fcm-token)', async () => {
      await init();
      await service.registerFCMToken('test');
      await service.unregisterFCMToken(1, 'test');

      // No apiClient calls for FCM
      const fcmApiClient = apiClientCalls.filter(c => c.url.includes('fcm'));
      expect(fcmApiClient).toHaveLength(0);

      // Direct axios calls for FCM
      const fcmDirect = directAxiosCalls.filter(c => c.url.includes('/notifications/fcm'));
      expect(fcmDirect).toHaveLength(2);
    });
  });
});
