/**
 * Pyserv Client - Modern Frontend Framework
 * Main entry point for the pyserv-client framework
 */

import { PyservClient } from './core/PyservClient.js';
import { Component } from './core/Component.js';
import { Store } from './core/Store.js';
import { Router } from './core/Router.js';
import { Auth } from './core/Auth.js';
import { ApiClient } from './services/ApiClient.js';
import { WebSocketClient } from './services/WebSocketClient.js';
import { NotificationManager } from './services/NotificationManager.js';
import { ThemeManager } from './services/ThemeManager.js';
import { CacheManager } from './services/CacheManager.js';

// Core framework class
class PyservClientFramework {
  constructor(config = {}) {
    this.config = {
      baseURL: config.baseURL || 'http://localhost:8000',
      apiVersion: config.apiVersion || 'v1',
      enableWebSocket: config.enableWebSocket !== false,
      enableAuth: config.enableAuth !== false,
      enableNotifications: config.enableNotifications !== false,
      enableTheme: config.enableTheme !== false,
      enableCache: config.enableCache !== false,
      debug: config.debug || false,
      ...config
    };

    this.initialized = false;
    this.components = new Map();
    this.stores = new Map();
    this.services = new Map();

    this._initializeCore();
  }

  async _initializeCore() {
    try {
      // Initialize core services
      await this._initializeServices();

      // Initialize stores
      this._initializeStores();

      // Initialize components
      this._initializeComponents();

      this.initialized = true;
      console.log('✅ Pyserv Client Framework initialized successfully');

      // Emit ready event
      this.emit('framework:ready', { framework: this });

    } catch (error) {
      console.error('❌ Failed to initialize Pyserv Client Framework:', error);
      throw error;
    }
  }

  async _initializeServices() {
    // API Client
    const apiClient = new ApiClient({
      baseURL: `${this.config.baseURL}/api/${this.config.apiVersion}`,
      timeout: this.config.apiTimeout || 10000,
      retries: this.config.apiRetries || 3
    });
    this.services.set('api', apiClient);

    // WebSocket Client (if enabled)
    if (this.config.enableWebSocket) {
      const wsClient = new WebSocketClient({
        url: this.config.baseURL.replace('http', 'ws'),
        reconnectInterval: this.config.wsReconnectInterval || 5000,
        maxReconnectAttempts: this.config.wsMaxReconnectAttempts || 5
      });
      this.services.set('websocket', wsClient);
    }

    // Authentication (if enabled)
    if (this.config.enableAuth) {
      const auth = new Auth({
        apiClient,
        storageKey: this.config.authStorageKey || 'pyserv_auth',
        refreshThreshold: this.config.authRefreshThreshold || 300000 // 5 minutes
      });
      this.services.set('auth', auth);
    }

    // Notification Manager (if enabled)
    if (this.config.enableNotifications) {
      const notifications = new NotificationManager({
        position: this.config.notificationPosition || 'top-right',
        duration: this.config.notificationDuration || 5000,
        maxNotifications: this.config.maxNotifications || 5
      });
      this.services.set('notifications', notifications);
    }

    // Theme Manager (if enabled)
    if (this.config.enableTheme) {
      const theme = new ThemeManager({
        defaultTheme: this.config.defaultTheme || 'light',
        storageKey: this.config.themeStorageKey || 'pyserv_theme'
      });
      this.services.set('theme', theme);
    }

    // Cache Manager (if enabled)
    if (this.config.enableCache) {
      const cache = new CacheManager({
        defaultTTL: this.config.cacheTTL || 300000, // 5 minutes
        maxSize: this.config.cacheMaxSize || 1000
      });
      this.services.set('cache', cache);
    }
  }

  _initializeStores() {
    // Global app store
    const appStore = new Store({
      name: 'app',
      initialState: {
        loading: false,
        error: null,
        user: null,
        settings: {},
        navigation: {
          currentRoute: '/',
          history: [],
          breadcrumbs: []
        }
      }
    });
    this.stores.set('app', appStore);

    // UI store
    const uiStore = new Store({
      name: 'ui',
      initialState: {
        sidebar: {
          open: false,
          collapsed: false
        },
        modal: {
          open: false,
          content: null
        },
        drawer: {
          open: false,
          content: null
        },
        theme: 'light',
        locale: 'en'
      }
    });
    this.stores.set('ui', uiStore);
  }

  _initializeComponents() {
    // Register built-in components
    this.registerComponent('App', () => import('./components/App.js'));
    this.registerComponent('Layout', () => import('./components/Layout.js'));
    this.registerComponent('Header', () => import('./components/Header.js'));
    this.registerComponent('Sidebar', () => import('./components/Sidebar.js'));
    this.registerComponent('Footer', () => import('./components/Footer.js'));
    this.registerComponent('Button', () => import('./components/Button.js'));
    this.registerComponent('Input', () => import('./components/Input.js'));
    this.registerComponent('Form', () => import('./components/Form.js'));
    this.registerComponent('Table', () => import('./components/Table.js'));
    this.registerComponent('Modal', () => import('./components/Modal.js'));
    this.registerComponent('Card', () => import('./components/Card.js'));
    this.registerComponent('Alert', () => import('./components/Alert.js'));
    this.registerComponent('Loading', () => import('./components/Loading.js'));
    this.registerComponent('Notification', () => import('./components/Notification.js'));
  }

  // Public API methods
  getService(name) {
    return this.services.get(name);
  }

  getStore(name) {
    return this.stores.get(name);
  }

  registerComponent(name, componentFactory) {
    this.components.set(name, componentFactory);
  }

  async getComponent(name) {
    const factory = this.components.get(name);
    if (!factory) {
      throw new Error(`Component '${name}' not found`);
    }
    return await factory();
  }

  registerStore(name, store) {
    this.stores.set(name, store);
  }

  registerService(name, service) {
    this.services.set(name, service);
  }

  emit(event, data) {
    if (this.config.debug) {
      console.log(`[PyservClient] Event: ${event}`, data);
    }

    // Emit to all stores
    this.stores.forEach(store => {
      if (store.emit) {
        store.emit(event, data);
      }
    });

    // Emit to all services
    this.services.forEach(service => {
      if (service.emit) {
        service.emit(event, data);
      }
    });
  }

  on(event, handler) {
    // Subscribe to events from stores and services
    const unsubscribers = [];

    this.stores.forEach(store => {
      if (store.on) {
        unsubscribers.push(store.on(event, handler));
      }
    });

    this.services.forEach(service => {
      if (service.on) {
        unsubscribers.push(service.on(event, handler));
      }
    });

    // Return unsubscribe function
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
    };
  }

  // Utility methods
  async fetch(url, options = {}) {
    const apiClient = this.getService('api');
    if (apiClient) {
      return await apiClient.request(url, options);
    }
    throw new Error('API client not available');
  }

  navigate(path, state = {}) {
    const router = this.getService('router');
    if (router) {
      router.navigate(path, state);
    } else {
      // Fallback to browser navigation
      window.history.pushState(state, '', path);
      window.dispatchEvent(new PopStateEvent('popstate', { state }));
    }
  }

  showNotification(message, type = 'info', options = {}) {
    const notifications = this.getService('notifications');
    if (notifications) {
      notifications.show(message, type, options);
    }
  }

  setTheme(theme) {
    const themeManager = this.getService('theme');
    if (themeManager) {
      themeManager.setTheme(theme);
    }
  }

  // Lifecycle methods
  async mount(selector) {
    if (!this.initialized) {
      await this._initializeCore();
    }

    const container = document.querySelector(selector);
    if (!container) {
      throw new Error(`Mount point '${selector}' not found`);
    }

    // Create root component
    const RootComponent = await this.getComponent('App');
    const rootInstance = new RootComponent();

    // Render and mount
    const html = rootInstance.render();
    container.innerHTML = html;

    // Initialize router if available
    const router = this.getService('router');
    if (router) {
      router.init();
    }

    console.log('✅ Pyserv Client Framework mounted successfully');
  }

  destroy() {
    // Clean up all services and stores
    this.services.forEach(service => {
      if (service.destroy) {
        service.destroy();
      }
    });

    this.stores.forEach(store => {
      if (store.destroy) {
        store.destroy();
      }
    });

    this.components.clear();
    this.services.clear();
    this.stores.clear();
    this.initialized = false;

    console.log('✅ Pyserv Client Framework destroyed');
  }
}

// Export framework instance
const framework = new PyservClientFramework();

// Export for global usage
window.PyservClient = framework;

// Export for module usage
export { PyservClientFramework, framework };
export default framework;

// Auto-initialize if not in module environment
if (typeof window !== 'undefined' && !window.PyservClient) {
  window.PyservClient = framework;
}
