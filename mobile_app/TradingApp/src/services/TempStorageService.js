/**
 * خدمة تخزين محسنة تدعم AsyncStorage مع fallback
 * ✅ إنتاج: بدون console.logs حساسة
 * ✅ آمن: لا يكشف أسماء المفاتيح
 * ✅ مستقر: fallback تلقائي للذاكرة المؤقتة
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

class TempStorageService {
  constructor() {
    this.storage = new Map(); // fallback storage
    this.useAsyncStorage = false;
    this.isInitialized = false;
    this._initPromise = this.initializeStorage();
  }

  async initializeStorage() {
    if (this.isInitialized) {return;}

    try {
      await AsyncStorage.setItem('@test_key', 'test_value');
      await AsyncStorage.removeItem('@test_key');
      this.useAsyncStorage = true;
    } catch (error) {
      this.useAsyncStorage = false;
    }

    this.isInitialized = true;
  }

  // ✅ انتظار التهيئة قبل أي عملية
  async _ensureInitialized() {
    if (!this.isInitialized) {
      await this._initPromise;
    }
  }

  async setItem(key, value) {
    await this._ensureInitialized();

    try {
      const stringValue = typeof value === 'string' ? value : JSON.stringify(value);

      if (this.useAsyncStorage) {
        await AsyncStorage.setItem(key, stringValue);
      } else {
        this.storage.set(key, stringValue);
      }
    } catch (error) {
      // fallback للذاكرة المؤقتة - صامت
      const stringValue = typeof value === 'string' ? value : JSON.stringify(value);
      this.storage.set(key, stringValue);
    }
  }

  async getItem(key) {
    await this._ensureInitialized();

    try {
      if (this.useAsyncStorage) {
        return await AsyncStorage.getItem(key);
      } else {
        return this.storage.get(key) || null;
      }
    } catch (error) {
      return this.storage.get(key) || null;
    }
  }

  async removeItem(key) {
    await this._ensureInitialized();

    try {
      if (this.useAsyncStorage) {
        await AsyncStorage.removeItem(key);
      } else {
        this.storage.delete(key);
      }
    } catch (error) {
      this.storage.delete(key);
    }
  }

  async multiRemove(keys) {
    await this._ensureInitialized();

    try {
      if (this.useAsyncStorage) {
        await AsyncStorage.multiRemove(keys);
      } else {
        keys.forEach(key => this.storage.delete(key));
      }
    } catch (error) {
      keys.forEach(key => this.storage.delete(key));
    }
  }

  async clear() {
    await this._ensureInitialized();

    try {
      if (this.useAsyncStorage) {
        await AsyncStorage.clear();
      } else {
        this.storage.clear();
      }
    } catch (error) {
      this.storage.clear();
    }
  }

  async getAllKeys() {
    await this._ensureInitialized();

    try {
      if (this.useAsyncStorage) {
        return await AsyncStorage.getAllKeys();
      } else {
        return Array.from(this.storage.keys());
      }
    } catch (error) {
      return Array.from(this.storage.keys());
    }
  }

  async hasItem(key) {
    await this._ensureInitialized();

    try {
      if (this.useAsyncStorage) {
        const value = await AsyncStorage.getItem(key);
        return value !== null;
      } else {
        return this.storage.has(key);
      }
    } catch (error) {
      return this.storage.has(key);
    }
  }

  async getStorageSize() {
    await this._ensureInitialized();

    try {
      if (this.useAsyncStorage) {
        const keys = await AsyncStorage.getAllKeys();
        return keys.length;
      } else {
        return this.storage.size;
      }
    } catch (error) {
      return this.storage.size;
    }
  }

  // ✅ Debug فقط في وضع التطوير
  async debugStorage() {
    if (!__DEV__) {return;}

    await this._ensureInitialized();

    try {
      if (this.useAsyncStorage) {
        const keys = await AsyncStorage.getAllKeys();
        const values = await AsyncStorage.multiGet(keys);
        console.log('[DEV] Storage:', Object.fromEntries(values));
      } else {
        console.log('[DEV] Memory:', Object.fromEntries(this.storage));
      }
    } catch (error) {
      // صامت
    }
  }

  getStorageStatus() {
    return {
      useAsyncStorage: this.useAsyncStorage,
      storageType: this.useAsyncStorage ? 'AsyncStorage' : 'Memory',
      memorySize: this.storage.size,
      isInitialized: this.isInitialized,
    };
  }
}

// إنشاء instance واحد للاستخدام في التطبيق
const tempStorageService = new TempStorageService();

export default tempStorageService;
