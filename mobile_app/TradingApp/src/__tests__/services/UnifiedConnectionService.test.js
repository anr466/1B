/**
 * 🧪 اختبارات UnifiedConnectionService
 * تغطي: التهيئة، اختبار الاتصال، اكتشاف URL، إعادة المحاولة
 */

// Mock LoggerService
jest.mock('services/LoggerService', () => ({
  __esModule: true,
  default: { info: jest.fn(), warn: jest.fn(), error: jest.fn() },
}));

// Must define mock functions BEFORE jest.mock factory (hoisting issue)
const mockInitialize = jest.fn(() => Promise.resolve(true));
const mockGetBaseURL = jest.fn(() => 'http://192.168.1.100:3002');
const mockGetConfig = jest.fn(() => ({ ip: '192.168.1.100' }));
const mockSetConnection = jest.fn();
const mockSetConnectionError = jest.fn();
const mockReset = jest.fn(() => Promise.resolve());
const mockGetConnectionInfo = jest.fn(() => ({
  isConnected: true, method: 'usb_port_forwarding', baseURL: 'http://localhost:3002',
}));

jest.mock('config/ServerConfig', () => ({
  __esModule: true,
  default: {
    initialize: mockInitialize,
    getBaseURL: mockGetBaseURL,
    getConfig: mockGetConfig,
    setConnection: mockSetConnection,
    setConnectionError: mockSetConnectionError,
    reset: mockReset,
    getConnectionInfo: mockGetConnectionInfo,
  },
}));

// Mock global fetch
global.fetch = jest.fn();

// Import AFTER all mocks
const UCS = require('services/UnifiedConnectionService').default;

describe('UnifiedConnectionService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch.mockReset();
    // Re-set mock return values (resetMocks:true in jest.config strips them)
    mockInitialize.mockResolvedValue(true);
    mockGetBaseURL.mockReturnValue('http://192.168.1.100:3002');
    mockGetConfig.mockReturnValue({ ip: '192.168.1.100' });
    mockReset.mockResolvedValue(undefined);
    mockGetConnectionInfo.mockReturnValue({
      isConnected: true, method: 'usb_port_forwarding', baseURL: 'http://localhost:3002',
    });
    // Reset internal state
    UCS.isInitializing = false;
    UCS.initializationPromise = null;
    UCS.retryCount = 0;
  });

  describe('Constructor', () => {
    test('initializes with correct defaults', () => {
      expect(UCS.retryCount).toBe(0);
      expect(UCS.maxRetries).toBe(3);
    });
  });

  describe('initialize()', () => {
    test('connects via USB port forwarding when localhost is reachable', async () => {
      global.fetch.mockResolvedValueOnce({ ok: true });
      const result = await UCS.initialize();
      expect(result.success).toBe(true);
      expect(result.method).toBe('usb_port_forwarding');
      expect(result.baseURL).toBe('http://localhost:3002');
      expect(mockSetConnection).toHaveBeenCalledWith('usb_port_forwarding', 'http://localhost:3002');
    });

    test('falls back to local network when USB fails', async () => {
      global.fetch
        .mockRejectedValueOnce(new Error('refused'))
        .mockResolvedValueOnce({ ok: true });
      const result = await UCS.initialize();
      expect(result.success).toBe(true);
      expect(result.method).toBe('local_network');
    });

    test('tries emulator when USB and local network fail', async () => {
      global.fetch
        .mockRejectedValueOnce(new Error('refused'))
        .mockRejectedValueOnce(new Error('refused'))
        .mockResolvedValueOnce({ ok: true });
      const result = await UCS.initialize();
      expect(result.success).toBe(true);
      expect(result.method).toBe('android_emulator');
    });

    test('returns failure when all methods fail', async () => {
      global.fetch.mockRejectedValue(new Error('refused'));
      const result = await UCS.initialize();
      expect(result.success).toBe(false);
      expect(result).toHaveProperty('error');
    });

    test('prevents concurrent initialization', async () => {
      global.fetch.mockResolvedValue({ ok: true });
      const p1 = UCS.initialize();
      const p2 = UCS.initialize();
      const [r1, r2] = await Promise.all([p1, p2]);
      expect(r1).toEqual(r2);
    });
  });

  describe('_testConnection()', () => {
    test('returns true for ok response', async () => {
      global.fetch.mockResolvedValue({ ok: true });
      expect(await UCS._testConnection('http://localhost:3002')).toBe(true);
    });

    test('returns false on error', async () => {
      global.fetch.mockRejectedValue(new Error('Timeout'));
      expect(await UCS._testConnection('http://localhost:3002')).toBe(false);
    });

    test('returns false for non-ok response', async () => {
      global.fetch.mockResolvedValue({ ok: false, status: 500 });
      expect(await UCS._testConnection('http://localhost:3002')).toBe(false);
    });

    test('calls /api/system/status endpoint', async () => {
      global.fetch.mockResolvedValue({ ok: true });
      await UCS._testConnection('http://localhost:3002');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:3002/api/system/status',
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  describe('getBaseURL()', () => {
    test('delegates to serverConfig', () => {
      const url = UCS.getBaseURL();
      expect(mockGetBaseURL).toHaveBeenCalled();
      expect(url).toBe('http://192.168.1.100:3002');
    });
  });

  describe('retry()', () => {
    test('increments retry count and resets config', async () => {
      global.fetch.mockResolvedValue({ ok: true });
      await UCS.retry();
      expect(UCS.retryCount).toBe(1);
      expect(mockReset).toHaveBeenCalled();
    });

    test('throws after max retries', async () => {
      UCS.retryCount = 3;
      await expect(UCS.retry()).rejects.toThrow('Max retries exceeded');
    });
  });

  describe('reset()', () => {
    test('resets state and calls serverConfig.reset()', () => {
      UCS.retryCount = 2;
      UCS.reset();
      expect(UCS.retryCount).toBe(0);
      expect(mockReset).toHaveBeenCalled();
    });
  });

  describe('getStatus()', () => {
    test('returns connection info', () => {
      const status = UCS.getStatus();
      expect(mockGetConnectionInfo).toHaveBeenCalled();
      expect(status).toHaveProperty('isConnected', true);
    });
  });
});
