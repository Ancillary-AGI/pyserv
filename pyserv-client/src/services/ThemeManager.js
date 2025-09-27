/**
 * ThemeManager - Theme and Styling Management
 * Provides comprehensive theme management with CSS variables,
 * dark/light mode support, and dynamic theme switching
 */

export class ThemeManager {
  constructor(config = {}) {
    this.config = {
      defaultTheme: config.defaultTheme || 'light',
      storageKey: config.storageKey || 'pyserv_theme',
      autoDetect: config.autoDetect !== false,
      persist: config.persist !== false,
      debug: config.debug || false,
      ...config
    };

    this.currentTheme = this.config.defaultTheme;
    this.themes = new Map();
    this.cssVariables = new Map();
    this.listeners = new Set();

    this._initializeThemes();
    this._loadPersistedTheme();

    // Auto-detect system theme
    if (this.config.autoDetect) {
      this._detectSystemTheme();
    }
  }

  _initializeThemes() {
    // Light theme
    this.registerTheme('light', {
      name: 'Light',
      description: 'Default light theme',
      colors: {
        // Primary colors
        primary: '#3b82f6',
        'primary-hover': '#2563eb',
        'primary-light': '#dbeafe',
        'primary-dark': '#1d4ed8',

        // Secondary colors
        secondary: '#6b7280',
        'secondary-hover': '#4b5563',
        'secondary-light': '#f3f4f6',
        'secondary-dark': '#374151',

        // Background colors
        background: '#ffffff',
        'background-secondary': '#f9fafb',
        'background-tertiary': '#f3f4f6',
        surface: '#ffffff',
        card: '#ffffff',

        // Text colors
        'text-primary': '#111827',
        'text-secondary': '#6b7280',
        'text-tertiary': '#9ca3af',
        'text-inverse': '#ffffff',

        // Status colors
        success: '#10b981',
        'success-light': '#d1fae5',
        'success-dark': '#059669',

        error: '#ef4444',
        'error-light': '#fee2e2',
        'error-dark': '#dc2626',

        warning: '#f59e0b',
        'warning-light': '#fef3c7',
        'warning-dark': '#d97706',

        info: '#3b82f6',
        'info-light': '#dbeafe',
        'info-dark': '#2563eb',

        // Border colors
        border: '#e5e7eb',
        'border-light': '#f3f4f6',
        'border-dark': '#d1d5db',

        // Shadow colors
        shadow: 'rgba(0, 0, 0, 0.1)',
        'shadow-light': 'rgba(0, 0, 0, 0.05)',
        'shadow-dark': 'rgba(0, 0, 0, 0.25)',

        // Special colors
        focus: '#3b82f6',
        overlay: 'rgba(0, 0, 0, 0.5)',
        disabled: '#d1d5db',
        placeholder: '#9ca3af'
      },
      spacing: {
        xs: '0.25rem',
        sm: '0.5rem',
        md: '1rem',
        lg: '1.5rem',
        xl: '2rem',
        '2xl': '3rem',
        '3xl': '4rem'
      },
      typography: {
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: {
          xs: '0.75rem',
          sm: '0.875rem',
          base: '1rem',
          lg: '1.125rem',
          xl: '1.25rem',
          '2xl': '1.5rem',
          '3xl': '1.875rem',
          '4xl': '2.25rem'
        },
        fontWeight: {
          normal: '400',
          medium: '500',
          semibold: '600',
          bold: '700'
        },
        lineHeight: {
          tight: '1.25',
          normal: '1.5',
          relaxed: '1.75'
        }
      },
      borderRadius: {
        none: '0',
        sm: '0.125rem',
        md: '0.375rem',
        lg: '0.5rem',
        xl: '0.75rem',
        '2xl': '1rem',
        full: '9999px'
      },
      shadows: {
        none: 'none',
        sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
      },
      transitions: {
        fast: '150ms ease',
        normal: '300ms ease',
        slow: '500ms ease'
      }
    });

    // Dark theme
    this.registerTheme('dark', {
      name: 'Dark',
      description: 'Dark theme for low-light environments',
      colors: {
        // Primary colors
        primary: '#60a5fa',
        'primary-hover': '#3b82f6',
        'primary-light': '#1e3a8a',
        'primary-dark': '#93c5fd',

        // Secondary colors
        secondary: '#9ca3af',
        'secondary-hover': '#d1d5db',
        'secondary-light': '#374151',
        'secondary-dark': '#f3f4f6',

        // Background colors
        background: '#111827',
        'background-secondary': '#1f2937',
        'background-tertiary': '#374151',
        surface: '#1f2937',
        card: '#374151',

        // Text colors
        'text-primary': '#f9fafb',
        'text-secondary': '#d1d5db',
        'text-tertiary': '#9ca3af',
        'text-inverse': '#111827',

        // Status colors
        success: '#34d399',
        'success-light': '#064e3b',
        'success-dark': '#10b981',

        error: '#f87171',
        'error-light': '#7f1d1d',
        'error-dark': '#ef4444',

        warning: '#fbbf24',
        'warning-light': '#78350f',
        'warning-dark': '#f59e0b',

        info: '#60a5fa',
        'info-light': '#1e3a8a',
        'info-dark': '#3b82f6',

        // Border colors
        border: '#374151',
        'border-light': '#4b5563',
        'border-dark': '#6b7280',

        // Shadow colors
        shadow: 'rgba(0, 0, 0, 0.3)',
        'shadow-light': 'rgba(0, 0, 0, 0.1)',
        'shadow-dark': 'rgba(0, 0, 0, 0.5)',

        // Special colors
        focus: '#60a5fa',
        overlay: 'rgba(0, 0, 0, 0.7)',
        disabled: '#6b7280',
        placeholder: '#9ca3af'
      },
      spacing: {
        xs: '0.25rem',
        sm: '0.5rem',
        md: '1rem',
        lg: '1.5rem',
        xl: '2rem',
        '2xl': '3rem',
        '3xl': '4rem'
      },
      typography: {
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: {
          xs: '0.75rem',
          sm: '0.875rem',
          base: '1rem',
          lg: '1.125rem',
          xl: '1.25rem',
          '2xl': '1.5rem',
          '3xl': '1.875rem',
          '4xl': '2.25rem'
        },
        fontWeight: {
          normal: '400',
          medium: '500',
          semibold: '600',
          bold: '700'
        },
        lineHeight: {
          tight: '1.25',
          normal: '1.5',
          relaxed: '1.75'
        }
      },
      borderRadius: {
        none: '0',
        sm: '0.125rem',
        md: '0.375rem',
        lg: '0.5rem',
        xl: '0.75rem',
        '2xl': '1rem',
        full: '9999px'
      },
      shadows: {
        none: 'none',
        sm: '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
        md: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
        lg: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
        xl: '0 20px 25px -5px rgba(0, 0, 0, 0.3)',
        '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
      },
      transitions: {
        fast: '150ms ease',
        normal: '300ms ease',
        slow: '500ms ease'
      }
    });

    // High contrast theme
    this.registerTheme('high-contrast', {
      name: 'High Contrast',
      description: 'High contrast theme for accessibility',
      colors: {
        primary: '#0000ff',
        'primary-hover': '#0000cc',
        secondary: '#000000',
        'secondary-hover': '#333333',
        background: '#ffffff',
        'background-secondary': '#ffffff',
        surface: '#ffffff',
        card: '#ffffff',
        'text-primary': '#000000',
        'text-secondary': '#000000',
        'text-tertiary': '#666666',
        'text-inverse': '#ffffff',
        success: '#008000',
        error: '#ff0000',
        warning: '#ff8000',
        info: '#0000ff',
        border: '#000000',
        'border-light': '#cccccc',
        'border-dark': '#000000',
        shadow: 'rgba(0, 0, 0, 0.5)',
        focus: '#0000ff',
        overlay: 'rgba(0, 0, 0, 0.8)',
        disabled: '#999999',
        placeholder: '#666666'
      }
    });
  }

  _detectSystemTheme() {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

      const handleChange = (e) => {
        if (e.matches) {
          this.setTheme('dark');
        } else {
          this.setTheme('light');
        }
      };

      mediaQuery.addEventListener('change', handleChange);

      // Set initial theme based on system preference
      if (mediaQuery.matches) {
        this.currentTheme = 'dark';
      }
    }
  }

  // Theme management
  registerTheme(name, theme) {
    this.themes.set(name, {
      name: theme.name || name,
      description: theme.description || '',
      colors: theme.colors || {},
      spacing: theme.spacing || {},
      typography: theme.typography || {},
      borderRadius: theme.borderRadius || {},
      shadows: theme.shadows || {},
      transitions: theme.transitions || {},
      ...theme
    });
  }

  unregisterTheme(name) {
    this.themes.delete(name);
  }

  getTheme(name) {
    return this.themes.get(name);
  }

  getCurrentTheme() {
    return this.getTheme(this.currentTheme);
  }

  getThemes() {
    return Array.from(this.themes.entries()).map(([key, theme]) => ({
      key,
      ...theme
    }));
  }

  // Theme switching
  setTheme(themeName) {
    const theme = this.themes.get(themeName);
    if (!theme) {
      console.warn(`Theme '${themeName}' not found`);
      return false;
    }

    const previousTheme = this.currentTheme;
    this.currentTheme = themeName;

    this._applyTheme(theme);
    this._persistTheme();

    this.emit('theme:changed', {
      theme: themeName,
      previousTheme,
      themeData: theme
    });

    if (this.config.debug) {
      console.log(`Theme changed from '${previousTheme}' to '${themeName}'`);
    }

    return true;
  }

  _applyTheme(theme) {
    if (typeof document === 'undefined') return;

    const root = document.documentElement;

    // Apply CSS variables
    Object.entries(theme.colors || {}).forEach(([key, value]) => {
      root.style.setProperty(`--pyserv-${key}`, value);
    });

    Object.entries(theme.spacing || {}).forEach(([key, value]) => {
      root.style.setProperty(`--pyserv-spacing-${key}`, value);
    });

    Object.entries(theme.typography || {}).forEach(([category, values]) => {
      if (typeof values === 'object') {
        Object.entries(values).forEach(([key, value]) => {
          root.style.setProperty(`--pyserv-${category}-${key}`, value);
        });
      } else {
        root.style.setProperty(`--pyserv-${category}`, values);
      }
    });

    Object.entries(theme.borderRadius || {}).forEach(([key, value]) => {
      root.style.setProperty(`--pyserv-radius-${key}`, value);
    });

    Object.entries(theme.shadows || {}).forEach(([key, value]) => {
      root.style.setProperty(`--pyserv-shadow-${key}`, value);
    });

    Object.entries(theme.transitions || {}).forEach(([key, value]) => {
      root.style.setProperty(`--pyserv-transition-${key}`, value);
    });

    // Add theme class to body
    document.body.className = document.body.className.replace(/pyserv-theme-\w+/g, '');
    document.body.classList.add(`pyserv-theme-${themeName}`);

    // Update meta theme-color for mobile browsers
    this._updateMetaThemeColor(theme.colors?.primary);
  }

  _updateMetaThemeColor(color) {
    if (typeof document === 'undefined' || !color) return;

    let metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (!metaThemeColor) {
      metaThemeColor = document.createElement('meta');
      metaThemeColor.name = 'theme-color';
      document.head.appendChild(metaThemeColor);
    }

    metaThemeColor.content = color;
  }

  // CSS variable management
  setCSSVariable(name, value) {
    if (typeof document !== 'undefined') {
      document.documentElement.style.setProperty(name, value);
      this.cssVariables.set(name, value);
    }
  }

  getCSSVariable(name) {
    if (typeof document !== 'undefined') {
      return getComputedStyle(document.documentElement).getPropertyValue(name);
    }
    return this.cssVariables.get(name);
  }

  // Color manipulation
  lightenColor(color, amount = 0.1) {
    // Simple color lightening - in a real implementation, you'd use a color library
    return color;
  }

  darkenColor(color, amount = 0.1) {
    // Simple color darkening - in a real implementation, you'd use a color library
    return color;
  }

  // Persistence
  _persistTheme() {
    if (!this.config.persist) return;

    try {
      localStorage.setItem(this.config.storageKey, this.currentTheme);
    } catch (error) {
      console.error('Failed to persist theme:', error);
    }
  }

  _loadPersistedTheme() {
    if (!this.config.persist) return;

    try {
      const persisted = localStorage.getItem(this.config.storageKey);
      if (persisted && this.themes.has(persisted)) {
        this.currentTheme = persisted;
      }
    } catch (error) {
      console.error('Failed to load persisted theme:', error);
    }
  }

  // Event system
  emit(event, data) {
    if (this.config.debug) {
      console.log(`[ThemeManager] Event: ${event}`, data);
    }

    this.listeners.forEach(listener => {
      try {
        listener(event, data);
      } catch (error) {
        console.error('Theme listener error:', error);
      }
    });

    // Emit to global event system
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(`pyserv:theme:${event}`, { detail: data }));
    }
  }

  on(event, handler) {
    this.listeners.add(handler);

    return () => {
      this.listeners.delete(handler);
    };
  }

  // Utility methods
  isDarkTheme() {
    const theme = this.getCurrentTheme();
    return theme?.colors?.background?.toLowerCase().includes('#111827') ||
           theme?.colors?.background?.toLowerCase().includes('#000000') ||
           this.currentTheme === 'dark';
  }

  getThemeColors() {
    const theme = this.getCurrentTheme();
    return theme?.colors || {};
  }

  // Debug utilities
  getDebugInfo() {
    return {
      currentTheme: this.currentTheme,
      availableThemes: Array.from(this.themes.keys()),
      themeCount: this.themes.size,
      persistEnabled: this.config.persist,
      autoDetectEnabled: this.config.autoDetect,
      listenerCount: this.listeners.size
    };
  }

  // Cleanup
  destroy() {
    this.listeners.clear();
    this.themes.clear();
    this.cssVariables.clear();

    // Remove theme class from body
    if (typeof document !== 'undefined') {
      document.body.className = document.body.className.replace(/pyserv-theme-\w+/g, '');
    }
  }
}

// Theme utilities
export function useTheme() {
  return window.__PYSERV_THEME__;
}

export function useThemeColors() {
  const theme = useTheme();
  return theme ? theme.getThemeColors() : {};
}

export function useIsDarkTheme() {
  const theme = useTheme();
  return theme ? theme.isDarkTheme() : false;
}

// Global theme instance
let globalTheme = null;

export function setGlobalTheme(theme) {
  globalTheme = theme;
  window.__PYSERV_THEME__ = theme;
}

export function getGlobalTheme() {
  return globalTheme;
}

// Convenience functions
export function setTheme(themeName) {
  const theme = getGlobalTheme();
  if (theme) {
    return theme.setTheme(themeName);
  }
}

export function toggleTheme() {
  const theme = getGlobalTheme();
  if (theme) {
    const isDark = theme.isDarkTheme();
    return theme.setTheme(isDark ? 'light' : 'dark');
  }
}

// CSS-in-JS support
export function createThemeStyles(themeName) {
  const theme = getGlobalTheme();
  if (!theme) return {};

  const themeData = theme.getTheme(themeName);
  if (!themeData) return {};

  const styles = {};

  // Convert theme to CSS variables
  Object.entries(themeData.colors || {}).forEach(([key, value]) => {
    styles[`--pyserv-${key}`] = value;
  });

  return styles;
}

// Theme transitions
export function createThemeTransition(fromTheme, toTheme, duration = 300) {
  return {
    transition: `all ${duration}ms ease`,
    transitionProperty: 'background-color, border-color, color, fill, stroke'
  };
}
