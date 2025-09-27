/**
 * CacheManager - Advanced Caching System
 * Provides multi-level caching with memory, localStorage, sessionStorage,
 * and IndexedDB support, with TTL, size limits, and cache strategies
 */

export class CacheManager {
  constructor(config = {}) {
    this.config = {
      defaultTTL: config.defaultTTL || 300000, // 5 minutes
      maxMemorySize: config.maxMemorySize || 50 * 1024 * 1024, // 50MB
      maxLocalStorageSize: config.maxLocalStorageSize || 10 * 1024 * 1024, // 10MB
      maxSessionStorageSize: config.maxSessionStorageSize || 5 * 1024 * 1024, // 5MB
      enableCompression: config.enableCompression !== false,
      compressionThreshold: config.compressionThreshold || 1024, // 1KB
      enablePersistence: config.enablePersistence !== false,
      enableMetrics: config.enableMetrics !== false,
      debug: config.debug || false,
      ...config
    };

    this.memoryCache = new Map();
    this.memorySize = 0;
    this.localStorageCache = new Map();
    this.sessionStorageCache = new Map();
    this.indexedDBCache = null;
    this.metrics = {
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0,
      evictions: 0
    };

    this._initializeIndexedDB();
    this._loadPersistedCaches();
  }

  async _initializeIndexedDB() {
    if (typeof indexedDB === 'undefined') return;

    try {
      const request = indexedDB.open('PyservCache', 1);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains('cache')) {
          const store = db.createObjectStore('cache', { keyPath: 'key' });
          store.createIndex('expires', 'expires', { unique: false });
        }
      };

      request.onsuccess = (event) => {
        this.indexedDBCache = event.target.result;
        this._cleanupExpiredEntries();
      };

      request.onerror = (error) => {
        console.warn('Failed to initialize IndexedDB cache:', error);
      };
    } catch (error) {
      console.warn('IndexedDB not available:', error);
    }
  }

  _loadPersistedCaches() {
    if (!this.config.enablePersistence) return;

    try {
      // Load localStorage cache
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith('pyserv_cache_')) {
          const value = localStorage.getItem(key);
          try {
            const parsed = JSON.parse(value);
            if (parsed.expires > Date.now()) {
              this.localStorageCache.set(key, parsed);
            } else {
              localStorage.removeItem(key);
            }
          } catch (error) {
            localStorage.removeItem(key);
          }
        }
      }

      // Load sessionStorage cache
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (key?.startsWith('pyserv_cache_')) {
          const value = sessionStorage.getItem(key);
          try {
            const parsed = JSON.parse(value);
            if (parsed.expires > Date.now()) {
              this.sessionStorageCache.set(key, parsed);
            } else {
              sessionStorage.removeItem(key);
            }
          } catch (error) {
            sessionStorage.removeItem(key);
          }
        }
      }
    } catch (error) {
      console.warn('Failed to load persisted caches:', error);
    }
  }

  // Core cache operations
  async get(key, options = {}) {
    const cacheKey = this._normalizeKey(key);
    const strategy = options.strategy || 'memory'; // memory, localStorage, sessionStorage, indexedDB

    let value = null;
    let hit = false;

    // Try memory cache first
    if (strategy === 'memory' || strategy === 'all') {
      value = this._getFromMemory(cacheKey);
      if (value !== null) {
        hit = true;
        this.metrics.hits++;
      }
    }

    // Try localStorage cache
    if (!hit && (strategy === 'localStorage' || strategy === 'all')) {
      value = this._getFromLocalStorage(cacheKey);
      if (value !== null) {
        hit = true;
        this.metrics.hits++;
        // Also store in memory for faster access
        this._setInMemory(cacheKey, value);
      }
    }

    // Try sessionStorage cache
    if (!hit && (strategy === 'sessionStorage' || strategy === 'all')) {
      value = this._getFromSessionStorage(cacheKey);
      if (value !== null) {
        hit = true;
        this.metrics.hits++;
        this._setInMemory(cacheKey, value);
      }
    }

    // Try IndexedDB cache
    if (!hit && (strategy === 'indexedDB' || strategy === 'all')) {
      value = await this._getFromIndexedDB(cacheKey);
      if (value !== null) {
        hit = true;
        this.metrics.hits++;
        this._setInMemory(cacheKey, value);
      }
    }

    if (!hit) {
      this.metrics.misses++;
    }

    if (this.config.debug && hit) {
      console.log(`[Cache] Hit for key: ${cacheKey}`);
    }

    return value;
  }

  async set(key, value, options = {}) {
    const cacheKey = this._normalizeKey(key);
    const ttl = options.ttl || this.config.defaultTTL;
    const strategy = options.strategy || 'memory';
    const compress = options.compress || (this.config.enableCompression && this._shouldCompress(value));

    let processedValue = value;
    if (compress) {
      processedValue = this._compress(value);
    }

    const cacheEntry = {
      value: processedValue,
      expires: Date.now() + ttl,
      created: Date.now(),
      ttl,
      compressed: compress,
      size: this._estimateSize(processedValue)
    };

    // Store in memory cache
    if (strategy === 'memory' || strategy === 'all') {
      this._setInMemory(cacheKey, cacheEntry);
    }

    // Store in localStorage
    if (strategy === 'localStorage' || strategy === 'all') {
      this._setInLocalStorage(cacheKey, cacheEntry);
    }

    // Store in sessionStorage
    if (strategy === 'sessionStorage' || strategy === 'all') {
      this._setInSessionStorage(cacheKey, cacheEntry);
    }

    // Store in IndexedDB
    if (strategy === 'indexedDB' || strategy === 'all') {
      await this._setInIndexedDB(cacheKey, cacheEntry);
    }

    this.metrics.sets++;

    if (this.config.debug) {
      console.log(`[Cache] Set key: ${cacheKey} (${strategy})`);
    }
  }

  async delete(key, options = {}) {
    const cacheKey = this._normalizeKey(key);
    const strategy = options.strategy || 'all';

    if (strategy === 'memory' || strategy === 'all') {
      this._deleteFromMemory(cacheKey);
    }

    if (strategy === 'localStorage' || strategy === 'all') {
      this._deleteFromLocalStorage(cacheKey);
    }

    if (strategy === 'sessionStorage' || strategy === 'all') {
      this._deleteFromSessionStorage(cacheKey);
    }

    if (strategy === 'indexedDB' || strategy === 'all') {
      await this._deleteFromIndexedDB(cacheKey);
    }

    this.metrics.deletes++;

    if (this.config.debug) {
      console.log(`[Cache] Deleted key: ${cacheKey}`);
    }
  }

  async clear(options = {}) {
    const strategy = options.strategy || 'all';

    if (strategy === 'memory' || strategy === 'all') {
      this.memoryCache.clear();
      this.memorySize = 0;
    }

    if (strategy === 'localStorage' || strategy === 'all') {
      this.localStorageCache.clear();
      this._clearLocalStorage();
    }

    if (strategy === 'sessionStorage' || strategy === 'all') {
      this.sessionStorageCache.clear();
      this._clearSessionStorage();
    }

    if (strategy === 'indexedDB' || strategy === 'all') {
      await this._clearIndexedDB();
    }

    if (this.config.debug) {
      console.log(`[Cache] Cleared cache (${strategy})`);
    }
  }

  // Memory cache operations
  _getFromMemory(key) {
    const entry = this.memoryCache.get(key);
    if (entry && entry.expires > Date.now()) {
      return this._decompress(entry.value);
    }

    if (entry) {
      this.memoryCache.delete(key);
      this.memorySize -= entry.size;
    }

    return null;
  }

  _setInMemory(key, entry) {
    // Check size limit
    if (this.memorySize + entry.size > this.config.maxMemorySize) {
      this._evictMemoryCache(entry.size);
    }

    this.memoryCache.set(key, entry);
    this.memorySize += entry.size;
  }

  _deleteFromMemory(key) {
    const entry = this.memoryCache.get(key);
    if (entry) {
      this.memoryCache.delete(key);
      this.memorySize -= entry.size;
    }
  }

  _evictMemoryCache(neededSize) {
    const entries = Array.from(this.memoryCache.entries());
    entries.sort((a, b) => a[1].created - b[1].created); // LRU eviction

    let freedSize = 0;
    for (const [key, entry] of entries) {
      this.memoryCache.delete(key);
      this.memorySize -= entry.size;
      freedSize += entry.size;

      if (freedSize >= neededSize) break;
    }

    this.metrics.evictions += freedSize > 0 ? 1 : 0;
  }

  // localStorage operations
  _getFromLocalStorage(key) {
    const entry = this.localStorageCache.get(key);
    if (entry && entry.expires > Date.now()) {
      return this._decompress(entry.value);
    }

    if (entry) {
      this.localStorageCache.delete(key);
      localStorage.removeItem(key);
    }

    return null;
  }

  _setInLocalStorage(key, entry) {
    this.localStorageCache.set(key, entry);
    try {
      localStorage.setItem(key, JSON.stringify(entry));
    } catch (error) {
      console.warn('Failed to store in localStorage:', error);
    }
  }

  _deleteFromLocalStorage(key) {
    this.localStorageCache.delete(key);
    localStorage.removeItem(key);
  }

  _clearLocalStorage() {
    const keys = Object.keys(localStorage).filter(key => key.startsWith('pyserv_cache_'));
    keys.forEach(key => localStorage.removeItem(key));
  }

  // sessionStorage operations
  _getFromSessionStorage(key) {
    const entry = this.sessionStorageCache.get(key);
    if (entry && entry.expires > Date.now()) {
      return this._decompress(entry.value);
    }

    if (entry) {
      this.sessionStorageCache.delete(key);
      sessionStorage.removeItem(key);
    }

    return null;
  }

  _setInSessionStorage(key, entry) {
    this.sessionStorageCache.set(key, entry);
    try {
      sessionStorage.setItem(key, JSON.stringify(entry));
    } catch (error) {
      console.warn('Failed to store in sessionStorage:', error);
    }
  }

  _deleteFromSessionStorage(key) {
    this.sessionStorageCache.delete(key);
    sessionStorage.removeItem(key);
  }

  _clearSessionStorage() {
    const keys = Object.keys(sessionStorage).filter(key => key.startsWith('pyserv_cache_'));
    keys.forEach(key => sessionStorage.removeItem(key));
  }

  // IndexedDB operations
  async _getFromIndexedDB(key) {
    if (!this.indexedDBCache) return null;

    return new Promise((resolve) => {
      const transaction = this.indexedDBCache.transaction(['cache'], 'readonly');
      const store = transaction.objectStore('cache');
      const request = store.get(key);

      request.onsuccess = (event) => {
        const entry = event.target.result;
        if (entry && entry.expires > Date.now()) {
          resolve(this._decompress(entry.value));
        } else {
          resolve(null);
        }
      };

      request.onerror = () => resolve(null);
    });
  }

  async _setInIndexedDB(key, entry) {
    if (!this.indexedDBCache) return;

    return new Promise((resolve) => {
      const transaction = this.indexedDBCache.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const request = store.put({ key, ...entry });

      request.onsuccess = () => resolve();
      request.onerror = () => resolve();
    });
  }

  async _deleteFromIndexedDB(key) {
    if (!this.indexedDBCache) return;

    return new Promise((resolve) => {
      const transaction = this.indexedDBCache.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const request = store.delete(key);

      request.onsuccess = () => resolve();
      request.onerror = () => resolve();
    });
  }

  async _clearIndexedDB() {
    if (!this.indexedDBCache) return;

    return new Promise((resolve) => {
      const transaction = this.indexedDBCache.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const request = store.clear();

      request.onsuccess = () => resolve();
      request.onerror = () => resolve();
    });
  }

  // Utility methods
  _normalizeKey(key) {
    return `pyserv_cache_${key}`;
  }

  _shouldCompress(value) {
    const size = this._estimateSize(value);
    return size > this.config.compressionThreshold;
  }

  _compress(value) {
    // Simple compression using JSON.stringify with space removal
    // In a real implementation, you'd use a proper compression library
    return JSON.stringify(value).replace(/\s+/g, '');
  }

  _decompress(value) {
    if (typeof value === 'string' && value.includes('{') && value.includes('}')) {
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    }
    return value;
  }

  _estimateSize(value) {
    return new Blob([JSON.stringify(value)]).size;
  }

  _cleanupExpiredEntries() {
    // Clean up memory cache
    for (const [key, entry] of this.memoryCache.entries()) {
      if (entry.expires <= Date.now()) {
        this.memoryCache.delete(key);
        this.memorySize -= entry.size;
      }
    }

    // Clean up localStorage
    for (const [key, entry] of this.localStorageCache.entries()) {
      if (entry.expires <= Date.now()) {
        this.localStorageCache.delete(key);
        localStorage.removeItem(key);
      }
    }

    // Clean up sessionStorage
    for (const [key, entry] of this.sessionStorageCache.entries()) {
      if (entry.expires <= Date.now()) {
        this.sessionStorageCache.delete(key);
        sessionStorage.removeItem(key);
      }
    }

    // Clean up IndexedDB
    if (this.indexedDBCache) {
      this._cleanupIndexedDB();
    }
  }

  async _cleanupIndexedDB() {
    if (!this.indexedDBCache) return;

    return new Promise((resolve) => {
      const transaction = this.indexedDBCache.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const index = store.index('expires');
      const request = index.openCursor();

      request.onsuccess = (event) => {
        const cursor = event.target.result;
        if (cursor) {
          const entry = cursor.value;
          if (entry.expires <= Date.now()) {
            cursor.delete();
          }
          cursor.continue();
        }
      };

      request.onerror = () => resolve();
    });
  }

  // Cache strategies
  async getOrSet(key, factory, options = {}) {
    let value = await this.get(key, options);
    if (value === null) {
      value = await factory();
      await this.set(key, value, options);
    }
    return value;
  }

  async invalidate(pattern) {
    const keys = this._findKeysByPattern(pattern);

    for (const key of keys) {
      await this.delete(key);
    }

    return keys.length;
  }

  _findKeysByPattern(pattern) {
    const keys = [];

    // Search in all caches
    const allKeys = [
      ...this.memoryCache.keys(),
      ...this.localStorageCache.keys(),
      ...this.sessionStorageCache.keys()
    ];

    const regex = new RegExp(pattern.replace('*', '.*'));
    for (const key of allKeys) {
      if (regex.test(key)) {
        keys.push(key);
      }
    }

    return keys;
  }

  // Batch operations
  async batchGet(keys, options = {}) {
    const promises = keys.map(key => this.get(key, options));
    return await Promise.all(promises);
  }

  async batchSet(keyValuePairs, options = {}) {
    const promises = keyValuePairs.map(([key, value]) =>
      this.set(key, value, options)
    );
    return await Promise.all(promises);
  }

  async batchDelete(keys, options = {}) {
    const promises = keys.map(key => this.delete(key, options));
    return await Promise.all(promises);
  }

  // Cache statistics
  getStats() {
    return {
      memory: {
        size: this.memorySize,
        maxSize: this.config.maxMemorySize,
        entries: this.memoryCache.size,
        utilization: (this.memorySize / this.config.maxMemorySize) * 100
      },
      localStorage: {
        entries: this.localStorageCache.size,
        maxSize: this.config.maxLocalStorageSize
      },
      sessionStorage: {
        entries: this.sessionStorageCache.size,
        maxSize: this.config.maxSessionStorageSize
      },
      metrics: { ...this.metrics },
      config: { ...this.config }
    };
  }

  getHitRate() {
    const total = this.metrics.hits + this.metrics.misses;
    return total > 0 ? (this.metrics.hits / total) * 100 : 0;
  }

  // Debug utilities
  getDebugInfo() {
    return {
      config: this.config,
      stats: this.getStats(),
      hitRate: this.getHitRate(),
      memoryCacheKeys: Array.from(this.memoryCache.keys()),
      localStorageCacheKeys: Array.from(this.localStorageCache.keys()),
      sessionStorageCacheKeys: Array.from(this.sessionStorageCache.keys())
    };
  }

  // Cleanup
  destroy() {
    this.clear();
    this.metrics = {
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0,
      evictions: 0
    };

    if (this.indexedDBCache) {
      this.indexedDBCache.close();
    }
  }
}

// Cache strategies
export const CACHE_STRATEGIES = {
  MEMORY: 'memory',
  LOCAL_STORAGE: 'localStorage',
  SESSION_STORAGE: 'sessionStorage',
  INDEXED_DB: 'indexedDB',
  ALL: 'all'
};

// Cache utilities
export function useCache() {
  return window.__PYSERV_CACHE__;
}

// Global cache instance
let globalCache = null;

export function setGlobalCache(cache) {
  globalCache = cache;
  window.__PYSERV_CACHE__ = cache;
}

export function getGlobalCache() {
  return globalCache;
}

// Convenience functions
export async function cacheGet(key, options = {}) {
  const cache = getGlobalCache();
  return cache ? await cache.get(key, options) : null;
}

export async function cacheSet(key, value, options = {}) {
  const cache = getGlobalCache();
  if (cache) {
    await cache.set(key, value, options);
  }
}

export async function cacheDelete(key, options = {}) {
  const cache = getGlobalCache();
  if (cache) {
    await cache.delete(key, options);
  }
}

export async function cacheClear(options = {}) {
  const cache = getGlobalCache();
  if (cache) {
    await cache.clear(options);
  }
}

export async function cacheGetOrSet(key, factory, options = {}) {
  const cache = getGlobalCache();
  return cache ? await cache.getOrSet(key, factory, options) : await factory();
}
