const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');
const fs = require('fs');
const path = require('path');

/**
 * Metro configuration
 * https://facebook.github.io/metro/docs/configuration
 *
 * @type {import('metro-config').MetroConfig}
 */

// ✅ الحصول على IP المحلي من ConnectionConfig
function getMetroHost() {
  try {
    const configPath = path.join(__dirname, 'src/config/ConnectionConfig.js');
    if (fs.existsSync(configPath)) {
      const content = fs.readFileSync(configPath, 'utf8');
      const match = content.match(/localIP: '([\d.]+)'/);
      if (match && match[1]) {
        return match[1];
      }
    }
  } catch (e) {
    console.warn('⚠️ تحذير: لم يتمكن من قراءة ConnectionConfig.js');
  }
  return '127.0.0.1'; // fallback
}

const METRO_HOST = getMetroHost();

const config = {
  server: {
    port: 8081,
    // ✅ إزالة host و rejectUnauthorized (غير مدعومة في Metro)
    // Metro يستمع تلقائياً على 0.0.0.0
    enhanceMiddleware: (middleware) => {
      return (req, res, next) => {
        // ✅ Add /status endpoint for React Native 0.72 dev support compatibility
        if (req.url === '/status') {
          res.writeHead(200, { 'Content-Type': 'text/plain' });
          res.end('packager-status:running');
          return;
        }
        // ✅ Log all Metro requests for debugging
        const start = Date.now();
        const origEnd = res.end;
        res.end = function (...args) {
          const duration = Date.now() - start;
          const status = res.statusCode;
          if (!req.url.includes('hot') && !req.url.includes('symbolicate')) {
            console.log(`[Metro] ${req.method} ${req.url} → ${status} (${duration}ms)`);
          }
          origEnd.apply(res, args);
        };
        res.setHeader('X-Metro-Host', METRO_HOST);
        return middleware(req, res, next);
      };
    },
  },
  resolver: {
    alias: {
      'react-native-vector-icons': 'react-native-vector-icons',
    },
    // ✅ ترتيب صحيح: ملفات المنصة أولاً
    sourceExts: ['android.js', 'ios.js', 'native.js', 'js', 'jsx', 'json', 'mjs', 'ts', 'tsx'],
    assetExts: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'ttf', 'otf', 'woff', 'woff2'],
  },
  // ✅ تحسينات الأداء
  transformer: {
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: false,
        inlineRequires: true,
      },
    }),
  },
};

console.log(`\n📡 Metro Host: ${METRO_HOST}:8081\n`);

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
