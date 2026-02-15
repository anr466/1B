/**
 * 🧪 اختبارات DatabaseApiService
 * تغطي: Auth, User, Admin, ML, FCM, Trading, Notifications
 */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Mock UnifiedConnectionService
jest.mock('services/UnifiedConnectionService', () => ({
  __esModule: true,
  default: {
    initialize: jest.fn(() => Promise.resolve({ success: true })),
    getBaseURL: jest.fn(() => 'http://localhost:3002'),
    getStatus: jest.fn(() => ({ isConnected: true })),
  },
  unifiedConnectionService: {
    initialize: jest.fn(() => Promise.resolve({ success: true })),
    getBaseURL: jest.fn(() => 'http://localhost:3002'),
    getStatus: jest.fn(() => ({ isConnected: true })),
  },
}));

// Mock UnifiedErrorHandler
jest.mock('services/UnifiedErrorHandler', () => ({
  __esModule: true,
  default: {
    handle: jest.fn(),
    handleSmart: jest.fn(() => ({ success: false })),
    handleSystemError: jest.fn(),
    handleUserError: jest.fn(),
  },
}));

// Mock TempStorageService
jest.mock('services/TempStorageService', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(() => Promise.resolve(null)),
    setItem: jest.fn(() => Promise.resolve()),
    removeItem: jest.fn(() => Promise.resolve()),
  },
}));

// Mock LoggerService
jest.mock('services/LoggerService', () => ({
  __esModule: true,
  default: {
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    debug: jest.fn(),
  },
}));

describe('DatabaseApiService', () => {
  let DatabaseApiService;
  let mockApiClient;

  beforeEach(() => {
    jest.clearAllMocks();

    // Re-set mock implementations (resetMocks:true in jest.config strips them)
    const errorHandler = require('services/UnifiedErrorHandler').default;
    errorHandler.handle.mockImplementation(() => { });
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

    const connService = require('services/UnifiedConnectionService').default;
    connService.initialize.mockResolvedValue({ success: true });
    connService.getBaseURL.mockReturnValue('http://localhost:3002');

    // Setup axios mock instance with interceptors
    mockApiClient = {
      get: jest.fn(() => Promise.resolve({ data: { success: true } })),
      post: jest.fn(() => Promise.resolve({ data: { success: true } })),
      put: jest.fn(() => Promise.resolve({ data: { success: true } })),
      delete: jest.fn(() => Promise.resolve({ data: { success: true } })),
      patch: jest.fn(() => Promise.resolve({ data: { success: true } })),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
      defaults: { headers: { common: {} } },
    };

    axios.create.mockReturnValue(mockApiClient);
    axios.get.mockImplementation(() => Promise.resolve({ data: { success: true } }));
    axios.post.mockImplementation(() => Promise.resolve({ data: { success: true } }));
    axios.put.mockImplementation(() => Promise.resolve({ data: { success: true } }));
    axios.delete.mockImplementation(() => Promise.resolve({ data: { success: true } }));

    // Reset module to get fresh instance
    jest.isolateModules(() => {
      DatabaseApiService = require('services/DatabaseApiService').default;
    });
  });

  // ═══════════════════════════════════════════
  // INITIALIZATION
  // ═══════════════════════════════════════════
  describe('Initialization', () => {
    test('should initialize successfully', async () => {
      const result = await DatabaseApiService.initialize();
      expect(result).toBe(true);
      expect(DatabaseApiService.isInitialized).toBe(true);
    });

    test('should create axios instance with correct baseURL', async () => {
      await DatabaseApiService.initialize();
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: 'http://localhost:3002/api/user',
          timeout: expect.any(Number),
        })
      );
    });

    test('should setup interceptors after initialization', async () => {
      await DatabaseApiService.initialize();
      expect(mockApiClient.interceptors.request.use).toHaveBeenCalled();
    });

    test('should not initialize twice', async () => {
      await DatabaseApiService.initialize();
      await DatabaseApiService.initialize();
      // axios.create should only be called once
      expect(axios.create).toHaveBeenCalledTimes(1);
    });
  });

  // ═══════════════════════════════════════════
  // DATA CONVERSION (camelCase ↔ snake_case)
  // ═══════════════════════════════════════════
  describe('Data Conversion', () => {
    test('camelToSnake converts correctly', () => {
      const input = { userId: 1, userName: 'test', isActive: true };
      const expected = { user_id: 1, user_name: 'test', is_active: true };
      expect(DatabaseApiService._camelToSnake(input)).toEqual(expected);
    });

    test('camelToSnake handles nested objects', () => {
      const input = { userData: { firstName: 'John', lastName: 'Doe' } };
      const expected = { user_data: { first_name: 'John', last_name: 'Doe' } };
      expect(DatabaseApiService._camelToSnake(input)).toEqual(expected);
    });

    test('camelToSnake handles arrays', () => {
      const input = [{ userId: 1 }, { userId: 2 }];
      const expected = [{ user_id: 1 }, { user_id: 2 }];
      expect(DatabaseApiService._camelToSnake(input)).toEqual(expected);
    });

    test('snakeToCamel converts correctly', () => {
      const input = { user_id: 1, user_name: 'test', is_active: true };
      const expected = { userId: 1, userName: 'test', isActive: true };
      expect(DatabaseApiService._snakeToCamel(input)).toEqual(expected);
    });

    test('snakeToCamel handles nested objects', () => {
      const input = { user_data: { first_name: 'John' } };
      const expected = { userData: { firstName: 'John' } };
      expect(DatabaseApiService._snakeToCamel(input)).toEqual(expected);
    });

    test('handles null and primitive values', () => {
      expect(DatabaseApiService._camelToSnake(null)).toBeNull();
      expect(DatabaseApiService._camelToSnake(42)).toBe(42);
      expect(DatabaseApiService._camelToSnake('string')).toBe('string');
      expect(DatabaseApiService._snakeToCamel(null)).toBeNull();
      expect(DatabaseApiService._snakeToCamel(42)).toBe(42);
    });
  });

  // ═══════════════════════════════════════════
  // RETRY LOGIC
  // ═══════════════════════════════════════════
  describe('Retry Logic', () => {
    test('_isRetryableError returns true for network errors', () => {
      expect(DatabaseApiService._isRetryableError({})).toBe(true);
      expect(DatabaseApiService._isRetryableError({ message: 'Network Error' })).toBe(true);
    });

    test('_isRetryableError returns true for 5xx errors', () => {
      expect(DatabaseApiService._isRetryableError({ response: { status: 500 } })).toBe(true);
      expect(DatabaseApiService._isRetryableError({ response: { status: 502 } })).toBe(true);
      expect(DatabaseApiService._isRetryableError({ response: { status: 503 } })).toBe(true);
      expect(DatabaseApiService._isRetryableError({ response: { status: 504 } })).toBe(true);
    });

    test('_isRetryableError returns true for 408 and false for 429', () => {
      expect(DatabaseApiService._isRetryableError({ response: { status: 408 } })).toBe(true);
      expect(DatabaseApiService._isRetryableError({ response: { status: 429 } })).toBe(false);
    });

    test('_isRetryableError returns false for 4xx client errors', () => {
      expect(DatabaseApiService._isRetryableError({ response: { status: 400 } })).toBe(false);
      expect(DatabaseApiService._isRetryableError({ response: { status: 401 } })).toBe(false);
      expect(DatabaseApiService._isRetryableError({ response: { status: 403 } })).toBe(false);
      expect(DatabaseApiService._isRetryableError({ response: { status: 404 } })).toBe(false);
    });

    test('_retryWithBackoff retries on retryable errors', async () => {
      let callCount = 0;
      const fn = jest.fn(() => {
        callCount++;
        if (callCount < 3) {
          return Promise.reject({ response: { status: 500 } });
        }
        return Promise.resolve({ data: { success: true } });
      });

      DatabaseApiService.retryDelay = 10; // Speed up test
      const result = await DatabaseApiService._retryWithBackoff(fn, 3);
      expect(result).toEqual({ data: { success: true } });
      expect(fn).toHaveBeenCalledTimes(3);
    });

    test('_retryWithBackoff throws on non-retryable errors', async () => {
      const fn = jest.fn(() => Promise.reject({ response: { status: 403 } }));
      DatabaseApiService.retryDelay = 10;

      await expect(DatabaseApiService._retryWithBackoff(fn, 3))
        .rejects.toEqual({ response: { status: 403 } });
      expect(fn).toHaveBeenCalledTimes(1);
    });
  });

  // ═══════════════════════════════════════════
  // AUTH API METHODS
  // ═══════════════════════════════════════════
  describe('Auth Methods', () => {
    beforeEach(async () => {
      await DatabaseApiService.initialize();
    });

    test('login() calls POST /auth/login', async () => {
      mockApiClient.post.mockResolvedValue({
        data: { success: true, token: 'test-token', user: { id: 1 } },
      });

      const result = await DatabaseApiService.login('admin@test.com', 'pass123');

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/auth/login',
        expect.objectContaining({ email: 'admin@test.com', password: 'pass123' })
      );
      expect(result).toHaveProperty('token');
    });

    test('login() saves token to AsyncStorage', async () => {
      mockApiClient.post.mockResolvedValue({
        data: { success: true, token: 'my-jwt-token' },
      });

      await DatabaseApiService.login('user@test.com', 'pass');
      expect(AsyncStorage.setItem).toHaveBeenCalledWith('authToken', 'my-jwt-token');
    });

    test('validateSession() uses direct axios to /api/auth/validate-session', async () => {
      AsyncStorage.getItem.mockResolvedValue('test-token');
      await DatabaseApiService.validateSession();
      expect(axios.get).toHaveBeenCalledWith(
        'http://localhost:3002/api/auth/validate-session',
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
        })
      );
    });

    test('register() calls POST /auth/register', async () => {
      const userData = { email: 'new@test.com', password: 'pass', username: 'newuser' };
      await DatabaseApiService.register(userData);
      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/auth/register',
        expect.any(Object)
      );
    });

    test('checkAvailability() calls POST /auth/check-availability', async () => {
      await DatabaseApiService.checkAvailability('test@test.com', 'username1');
      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/auth/check-availability',
        expect.objectContaining({ email: 'test@test.com', username: 'username1' })
      );
    });

    test('login() throws error on failure (re-throws for screen handling)', async () => {
      const loginError = { response: { status: 401, data: { error: 'Invalid credentials' } } };
      mockApiClient.post.mockRejectedValue(loginError);
      DatabaseApiService.retryDelay = 10;

      await expect(DatabaseApiService.login('bad@test.com', 'wrong')).rejects.toEqual(loginError);
    });
  });

  // ═══════════════════════════════════════════
  // USER DATA METHODS
  // ═══════════════════════════════════════════
  describe('User Data Methods', () => {
    beforeEach(async () => {
      await DatabaseApiService.initialize();
    });

    test('getPortfolio() calls GET /portfolio/:userId', async () => {
      mockApiClient.get.mockResolvedValue({
        data: { success: true, data: { totalBalance: 10000 } },
      });

      const result = await DatabaseApiService.getPortfolio(1, 'demo');
      expect(mockApiClient.get).toHaveBeenCalledWith('/portfolio/1?mode=demo');
      expect(result).toHaveProperty('success', true);
    });

    test('getPortfolio() defaults to demo mode', async () => {
      await DatabaseApiService.getPortfolio(1);
      expect(mockApiClient.get).toHaveBeenCalledWith('/portfolio/1?mode=demo');
    });

    test('getStats() calls GET /stats/:userId', async () => {
      await DatabaseApiService.getStats(1);
      expect(mockApiClient.get).toHaveBeenCalledWith('/stats/1');
    });

    test('getTrades() calls GET /trades/:userId with params', async () => {
      await DatabaseApiService.getTrades(1, 50, 0, 'demo');
      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/trades/1')
      );
    });

    test('getActivePositions() calls GET /active-positions/:userId', async () => {
      await DatabaseApiService.getActivePositions(1);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/active-positions/1')
      );
    });

    test('getSettings() calls GET /settings/:userId', async () => {
      await DatabaseApiService.getSettings(1);
      expect(mockApiClient.get).toHaveBeenCalledWith('/settings/1');
    });

    test('getProfile() calls GET /profile/:userId', async () => {
      await DatabaseApiService.getProfile(1);
      expect(mockApiClient.get).toHaveBeenCalledWith('/profile/1');
    });

    test('getPortfolioHistory() calls GET /portfolio-growth/:userId', async () => {
      await DatabaseApiService.getPortfolioHistory(1, 30);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/portfolio-growth/1')
      );
    });

    test('getDailyPnL() calls GET /daily-pnl/:userId', async () => {
      await DatabaseApiService.getDailyPnL(1, 90);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/daily-pnl/1')
      );
    });

    test('getQualifiedCoins() calls GET /successful-coins/:userId', async () => {
      await DatabaseApiService.getQualifiedCoins(1);
      expect(mockApiClient.get).toHaveBeenCalledWith('/successful-coins/1');
    });

    test('getBinanceKeys() calls GET /binance-keys/:userId', async () => {
      await DatabaseApiService.getBinanceKeys(1);
      expect(mockApiClient.get).toHaveBeenCalledWith('/binance-keys/1');
    });

    test('updateSettings() calls PUT /settings/:userId', async () => {
      const settings = { maxPositions: 5 };
      await DatabaseApiService.updateSettings(1, settings);
      expect(mockApiClient.put).toHaveBeenCalledWith(
        '/settings/1',
        expect.any(Object)
      );
    });

    test('updateProfile() calls PUT /profile/:userId', async () => {
      const profile = { displayName: 'Test User' };
      await DatabaseApiService.updateProfile(1, profile);
      expect(mockApiClient.put).toHaveBeenCalledWith(
        '/profile/1',
        expect.any(Object)
      );
    });
  });

  // ═══════════════════════════════════════════
  // TRADING MODE METHODS
  // ═══════════════════════════════════════════
  describe('Trading Mode Methods', () => {
    beforeEach(async () => {
      await DatabaseApiService.initialize();
    });

    test('getTradingMode() calls GET /settings/trading-mode/:userId', async () => {
      await DatabaseApiService.getTradingMode(1);
      expect(mockApiClient.get).toHaveBeenCalledWith('/settings/trading-mode/1');
    });

    test('updateTradingMode() calls PUT /settings/trading-mode/:userId', async () => {
      await DatabaseApiService.updateTradingMode(1, 'demo');
      expect(mockApiClient.put).toHaveBeenCalledWith(
        '/settings/trading-mode/1',
        expect.objectContaining({ mode: 'demo' })
      );
    });
  });

  // ═══════════════════════════════════════════
  // NOTIFICATIONS METHODS
  // ═══════════════════════════════════════════
  describe('Notifications Methods', () => {
    beforeEach(async () => {
      await DatabaseApiService.initialize();
    });

    test('getNotifications() calls GET /notifications/:userId', async () => {
      await DatabaseApiService.getNotifications(1);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/notifications/1')
      );
    });

    test('registerFCMToken() uses direct axios to /api/notifications/fcm-token', async () => {
      await DatabaseApiService.registerFCMToken('test-fcm-token');
      expect(axios.post).toHaveBeenCalledWith(
        'http://localhost:3002/api/notifications/fcm-token',
        expect.objectContaining({ fcm_token: 'test-fcm-token', platform: 'android' }),
        expect.any(Object)
      );
    });

    test('unregisterFCMToken() uses direct axios DELETE to /api/notifications/fcm-token', async () => {
      await DatabaseApiService.unregisterFCMToken(1, 'test-fcm-token');
      expect(axios.delete).toHaveBeenCalledWith(
        'http://localhost:3002/api/notifications/fcm-token',
        expect.objectContaining({
          data: expect.objectContaining({ user_id: 1, fcm_token: 'test-fcm-token' }),
        })
      );
    });

    test('getNotificationSettings() calls correct path (no double /user/)', async () => {
      await DatabaseApiService.getNotificationSettings(1);
      // Should call /notifications/settings NOT /user/notifications/settings
      expect(mockApiClient.get).toHaveBeenCalledWith('/notifications/settings');
    });

    test('updateNotificationSettings() calls correct path (no double /user/)', async () => {
      await DatabaseApiService.updateNotificationSettings(1, { tradeAlerts: true });
      expect(mockApiClient.put).toHaveBeenCalledWith(
        '/notifications/settings',
        expect.any(Object)
      );
    });
  });

  // ═══════════════════════════════════════════
  // ADMIN METHODS
  // ═══════════════════════════════════════════
  describe('Admin Methods', () => {
    beforeEach(async () => {
      await DatabaseApiService.initialize();
    });

    test('getBackgroundSystemStatus() calls GET /admin/system/status', async () => {
      axios.get.mockResolvedValue({ data: { success: true, status: 'running' } });
      await DatabaseApiService.getBackgroundSystemStatus();
      expect(axios.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/admin/system/status'),
        expect.any(Object)
      );
    });

    test('startSystem() delegates to state-machine start endpoint', async () => {
      axios.post.mockResolvedValue({ data: { success: true } });
      await DatabaseApiService.startSystem();
      expect(axios.post).toHaveBeenCalledWith(
        'http://localhost:3002/api/admin/trading/start',
        expect.any(Object),
        expect.any(Object)
      );
    });

    test('stopSystem() delegates to state-machine stop endpoint', async () => {
      axios.post.mockResolvedValue({ data: { success: true } });
      await DatabaseApiService.stopSystem();
      expect(axios.post).toHaveBeenCalledWith(
        'http://localhost:3002/api/admin/trading/stop',
        expect.any(Object),
        expect.any(Object)
      );
    });

    test('getSystemStats() calls GET /admin/system/stats', async () => {
      await DatabaseApiService.getSystemStats();
      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/system/stats');
    });

    test('getUsersStats() derives stats from GET /admin/users/all', async () => {
      await DatabaseApiService.getUsersStats();
      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/users/all');
    });

    test('getTradingStats() calls GET /admin/trades/stats', async () => {
      await DatabaseApiService.getTradingStats();
      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/trades/stats');
    });

    test('getPortfolioStats() derives from GET /api/admin/system/ml-status', async () => {
      axios.get.mockResolvedValue({ data: { success: true, portfolio: {} } });
      await DatabaseApiService.getPortfolioStats();
      expect(axios.get).toHaveBeenCalledWith(
        'http://localhost:3002/api/admin/system/ml-status',
        expect.any(Object)
      );
    });

    test('getAdminNotificationSettings() calls GET /admin/notification-settings', async () => {
      await DatabaseApiService.getAdminNotificationSettings();
      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/notification-settings');
    });

    test('getAllUsers() calls GET /admin/users/all', async () => {
      await DatabaseApiService.getAllUsers();
      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/users/all');
    });

    test('getUserDetails() calls GET /admin/users/:userId', async () => {
      await DatabaseApiService.getUserDetails(1);
      expect(mockApiClient.get).toHaveBeenCalledWith('/admin/users/1');
    });

    test('createUser() calls POST /admin/users/create', async () => {
      await DatabaseApiService.createUser({ email: 'new@test.com' });
      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/admin/users/create',
        expect.any(Object)
      );
    });

    test('getAdminErrors() calls GET /admin/errors', async () => {
      await DatabaseApiService.getAdminErrors();
      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/admin/errors',
        expect.any(Object)
      );
    });
  });

  // ═══════════════════════════════════════════
  // ML METHODS
  // ═══════════════════════════════════════════
  describe('ML Methods', () => {
    beforeEach(async () => {
      await DatabaseApiService.initialize();
    });

    test('getMLFullStatus() uses direct axios to /api/ml/status', async () => {
      axios.get.mockResolvedValue({ data: { success: true, status: 'active' } });
      await DatabaseApiService.getMLFullStatus();
      expect(axios.get).toHaveBeenCalledWith(
        'http://localhost:3002/api/ml/status',
        expect.any(Object)
      );
    });

    test('getMLPatterns() uses direct axios to /api/ml/patterns', async () => {
      axios.get.mockResolvedValue({ data: { success: true, patterns: [] } });
      await DatabaseApiService.getMLPatterns();
      expect(axios.get).toHaveBeenCalledWith(
        'http://localhost:3002/api/ml/patterns',
        expect.any(Object)
      );
    });

    test('getMLLearningProgress() uses direct axios to /api/ml/learning/progress/:userId', async () => {
      axios.get.mockResolvedValue({ data: { success: true } });
      await DatabaseApiService.getMLLearningProgress(1);
      expect(axios.get).toHaveBeenCalledWith(
        'http://localhost:3002/api/ml/learning/progress/1',
        expect.any(Object)
      );
    });
  });

  // ═══════════════════════════════════════════
  // FAVORITES & DISTRIBUTION (no double /user/)
  // ═══════════════════════════════════════════
  describe('Favorites & Distribution (path correctness)', () => {
    beforeEach(async () => {
      await DatabaseApiService.initialize();
    });

    test('toggleTradeFavorite() calls /trades/favorite (NOT /user/trades/favorite)', async () => {
      await DatabaseApiService.toggleTradeFavorite(1, true);
      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/trades/favorite',
        expect.any(Object)
      );
      // Ensure NO double /user/ prefix
      const callArg = mockApiClient.post.mock.calls[0][0];
      expect(callArg).not.toContain('/user/');
    });

    test('getFavoriteTrades() calls /trades/favorites/:userId (NOT /user/trades/...)', async () => {
      await DatabaseApiService.getFavoriteTrades(1, 'demo');
      expect(mockApiClient.get).toHaveBeenCalledWith('/trades/favorites/1?mode=demo');
      const callArg = mockApiClient.get.mock.calls[0][0];
      expect(callArg).not.toContain('/user/');
    });

    test('getTradesWithDistribution() calls /trades/distribution/:userId', async () => {
      await DatabaseApiService.getTradesWithDistribution(1, 'demo');
      expect(mockApiClient.get).toHaveBeenCalledWith('/trades/distribution/1?mode=demo');
      const callArg = mockApiClient.get.mock.calls[0][0];
      expect(callArg).not.toContain('/user/');
    });
  });

  // ═══════════════════════════════════════════
  // CACHE & INTEGRATION (no double /user/)
  // ═══════════════════════════════════════════
  describe('Cache & Integration (path correctness)', () => {
    beforeEach(async () => {
      await DatabaseApiService.initialize();
    });

    test('getCacheStatus() calls /cache/status (NOT /user/cache/status)', async () => {
      await DatabaseApiService.getCacheStatus();
      expect(mockApiClient.get).toHaveBeenCalledWith('/cache/status');
    });

    test('clearCache() calls /cache/clear (NOT /user/cache/clear)', async () => {
      await DatabaseApiService.clearCache();
      expect(mockApiClient.post).toHaveBeenCalledWith('/cache/clear');
    });

    test('getIntegrationStatus() calls /integration/status (NOT /user/integration/status)', async () => {
      await DatabaseApiService.getIntegrationStatus();
      expect(mockApiClient.get).toHaveBeenCalledWith('/integration/status');
    });
  });

  // ═══════════════════════════════════════════
  // ERROR HANDLING
  // ═══════════════════════════════════════════
  describe('Error Handling', () => {
    beforeEach(async () => {
      await DatabaseApiService.initialize();
    });

    test('getPortfolio() returns graceful error on failure', async () => {
      mockApiClient.get.mockRejectedValue({
        response: { status: 400, data: { error: 'Bad Request' } },
      });
      DatabaseApiService.retryDelay = 10;

      const result = await DatabaseApiService.getPortfolio(1);
      expect(result).toHaveProperty('success', false);
    });

    test('getTrades() returns graceful error on 400', async () => {
      mockApiClient.get.mockRejectedValue({
        response: { status: 400, data: { error: 'Bad Request' } },
      });
      DatabaseApiService.retryDelay = 10;

      const result = await DatabaseApiService.getTrades(1);
      expect(result).toHaveProperty('success', false);
    });

    test('login() re-throws auth errors for screen-level handling', async () => {
      const authError = { response: { status: 401, data: { error: 'Bad credentials' } } };
      mockApiClient.post.mockRejectedValue(authError);
      DatabaseApiService.retryDelay = 10;

      await expect(DatabaseApiService.login('test@test.com', 'pass')).rejects.toEqual(authError);
    });
  });
});
