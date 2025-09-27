/**
 * App - Main Application Component
 * Root component that provides the application shell with layout,
 * navigation, and global state management
 */

import { Component } from '../core/Component.js';
import { useRouter, useRoute } from '../core/Router.js';
import { useAuth, useUser, useIsAuthenticated } from '../core/Auth.js';
import { useTheme, useIsDarkTheme } from '../services/ThemeManager.js';
import { useNotifications } from '../services/NotificationManager.js';
import { useCache } from '../services/CacheManager.js';

export class App extends Component {
  constructor(props = {}) {
    super(props);

    this.state = {
      initialized: false,
      sidebarOpen: false,
      loading: true,
      error: null,
      breadcrumbs: []
    };

    this.router = props.router;
    this.auth = props.auth;
    this.theme = props.theme;
    this.notifications = props.notifications;
    this.cache = props.cache;

    this._initializeApp();
  }

  async _initializeApp() {
    try {
      // Wait for framework initialization
      await this._waitForFrameworkReady();

      // Initialize user session
      await this._initializeUserSession();

      // Set up global error handling
      this._setupErrorHandling();

      // Set up keyboard shortcuts
      this._setupKeyboardShortcuts();

      this.setState({ initialized: true, loading: false });

    } catch (error) {
      console.error('App initialization failed:', error);
      this.setState({ error: error.message, loading: false });
    }
  }

  async _waitForFrameworkReady() {
    return new Promise((resolve) => {
      const checkReady = () => {
        if (window.PyservClient?.initialized) {
          resolve();
        } else {
          setTimeout(checkReady, 100);
        }
      };
      checkReady();
    });
  }

  async _initializeUserSession() {
    if (this.auth?.isAuthenticated) {
      try {
        // Refresh user data
        await this.auth.updateProfile();
      } catch (error) {
        console.warn('Failed to refresh user data:', error);
      }
    }
  }

  _setupErrorHandling() {
    window.addEventListener('error', (event) => {
      this._handleGlobalError(event.error);
    });

    window.addEventListener('unhandledrejection', (event) => {
      this._handleGlobalError(event.reason);
    });
  }

  _handleGlobalError(error) {
    console.error('Global error:', error);

    if (this.notifications) {
      this.notifications.error('An unexpected error occurred', {
        title: 'Application Error',
        persistent: true,
        actions: [
          {
            key: 'reload',
            label: 'Reload Page',
            handler: () => window.location.reload()
          }
        ]
      });
    }
  }

  _setupKeyboardShortcuts() {
    document.addEventListener('keydown', (event) => {
      // Ctrl/Cmd + K - Focus search
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        this._focusSearch();
      }

      // Ctrl/Cmd + Shift + T - Toggle theme
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'T') {
        event.preventDefault();
        this._toggleTheme();
      }

      // Escape - Close modals/overlays
      if (event.key === 'Escape') {
        this._closeOverlays();
      }
    });
  }

  _focusSearch() {
    const searchInput = document.querySelector('[data-search-input]');
    if (searchInput) {
      searchInput.focus();
    }
  }

  _toggleTheme() {
    if (this.theme) {
      const isDark = this.theme.isDarkTheme();
      this.theme.setTheme(isDark ? 'light' : 'dark');
    }
  }

  _closeOverlays() {
    // Close any open modals, dropdowns, etc.
    document.dispatchEvent(new CustomEvent('pyserv:close-overlays'));
  }

  componentDidMount() {
    // Set up route change listener
    if (this.router) {
      this.router.on('route:changed', (event) => {
        this._updateBreadcrumbs(event.route);
      });
    }

    // Set up theme change listener
    if (this.theme) {
      this.theme.on('theme:changed', (event) => {
        this.setState({ theme: event.theme });
      });
    }

    // Set up auth change listener
    if (this.auth) {
      this.auth.on('auth:login', () => {
        this.setState({ user: this.auth.user });
      });

      this.auth.on('auth:logout', () => {
        this.setState({ user: null });
      });
    }

    // Initial breadcrumb update
    if (this.router) {
      this._updateBreadcrumbs(this.router.getCurrentRoute());
    }
  }

  _updateBreadcrumbs(route) {
    if (!route) return;

    const breadcrumbs = [];

    // Add home breadcrumb
    breadcrumbs.push({
      label: 'Home',
      path: '/',
      icon: '🏠'
    });

    // Add current route breadcrumb
    if (route.path !== '/') {
      breadcrumbs.push({
        label: route.name || route.path,
        path: route.path,
        icon: this._getRouteIcon(route.path)
      });
    }

    this.setState({ breadcrumbs });
  }

  _getRouteIcon(path) {
    const icons = {
      '/dashboard': '📊',
      '/users': '👥',
      '/settings': '⚙️',
      '/profile': '👤',
      '/notifications': '🔔',
      '/files': '📁',
      '/reports': '📈',
      '/analytics': '📊'
    };

    return icons[path] || '📄';
  }

  render() {
    if (this.state.loading) {
      return this.renderLoading();
    }

    if (this.state.error) {
      return this.renderError();
    }

    return this.createElement('div', {
      className: `app app-theme-${this.theme?.currentTheme || 'light'} ${this.state.sidebarOpen ? 'app--sidebar-open' : ''}`
    },
      // Header
      this.renderHeader(),

      // Main content area
      this.createElement('main', { className: 'app__main' },
        // Sidebar
        this.renderSidebar(),

        // Content
        this.createElement('div', { className: 'app__content' },
          // Breadcrumbs
          this.renderBreadcrumbs(),

          // Page content
          this.createElement('div', {
            className: 'app__page',
            'data-router-view': 'default'
          })
        )
      ),

      // Footer
      this.renderFooter(),

      // Global components
      this.renderGlobalComponents()
    );
  }

  renderLoading() {
    return this.createElement('div', { className: 'app-loading' },
      this.createElement('div', { className: 'app-loading__spinner' }),
      this.createElement('div', { className: 'app-loading__text' }, 'Loading application...')
    );
  }

  renderError() {
    return this.createElement('div', { className: 'app-error' },
      this.createElement('div', { className: 'app-error__icon' }, '⚠️'),
      this.createElement('h1', { className: 'app-error__title' }, 'Application Error'),
      this.createElement('p', { className: 'app-error__message' }, this.state.error),
      this.createElement('button', {
        className: 'app-error__retry',
        onClick: () => window.location.reload()
      }, 'Reload Application')
    );
  }

  renderHeader() {
    const isAuthenticated = this.auth?.isAuthenticated;
    const user = this.auth?.user;

    return this.createElement('header', { className: 'app-header' },
      this.createElement('div', { className: 'app-header__left' },
        // Mobile menu button
        this.createElement('button', {
          className: 'app-header__menu-toggle',
          onClick: () => this.setState({ sidebarOpen: !this.state.sidebarOpen }),
          'aria-label': 'Toggle menu'
        }, '☰'),

        // Logo
        this.createElement('div', { className: 'app-header__logo' },
          this.createElement('span', { className: 'app-header__logo-text' }, 'Pyserv Client')
        ),

        // Search
        this.createElement('div', { className: 'app-header__search' },
          this.createElement('input', {
            type: 'text',
            placeholder: 'Search...',
            className: 'app-header__search-input',
            'data-search-input': true
          }),
          this.createElement('span', { className: 'app-header__search-icon' }, '🔍')
        )
      ),

      this.createElement('div', { className: 'app-header__right' },
        // Theme toggle
        this.createElement('button', {
          className: 'app-header__theme-toggle',
          onClick: () => this._toggleTheme(),
          'aria-label': 'Toggle theme'
        }, this.theme?.isDarkTheme() ? '☀️' : '🌙'),

        // Notifications
        isAuthenticated && this.notifications ? this.createElement('button', {
          className: 'app-header__notifications',
          onClick: () => this._toggleNotifications(),
          'aria-label': 'Notifications'
        }, '🔔') : null,

        // User menu
        isAuthenticated ? this.renderUserMenu(user) : this.renderAuthButtons()
      )
    );
  }

  renderUserMenu(user) {
    return this.createElement('div', { className: 'app-header__user-menu' },
      this.createElement('div', { className: 'app-header__user-info' },
        this.createElement('span', { className: 'app-header__user-name' }, user?.name || user?.username || 'User'),
        this.createElement('span', { className: 'app-header__user-role' }, user?.role || 'User')
      ),
      this.createElement('div', { className: 'app-header__user-avatar' },
        user?.avatar ? this.createElement('img', { src: user.avatar, alt: 'Avatar' }) :
        this.createElement('span', {}, user?.name?.charAt(0) || user?.username?.charAt(0) || 'U')
      ),
      this.createElement('button', {
        className: 'app-header__user-menu-toggle',
        onClick: () => this._toggleUserMenu(),
        'aria-label': 'User menu'
      }, '▼')
    );
  }

  renderAuthButtons() {
    return this.createElement('div', { className: 'app-header__auth-buttons' },
      this.createElement('button', {
        className: 'app-header__login',
        onClick: () => this.router?.navigate('/login')
      }, 'Login'),
      this.createElement('button', {
        className: 'app-header__register',
        onClick: () => this.router?.navigate('/register')
      }, 'Register')
    );
  }

  renderSidebar() {
    const isAuthenticated = this.auth?.isAuthenticated;

    return this.createElement('aside', {
      className: `app-sidebar ${this.state.sidebarOpen ? 'app-sidebar--open' : ''}`
    },
      // Sidebar header
      this.createElement('div', { className: 'app-sidebar__header' },
        this.createElement('h2', { className: 'app-sidebar__title' }, 'Navigation'),
        this.createElement('button', {
          className: 'app-sidebar__close',
          onClick: () => this.setState({ sidebarOpen: false }),
          'aria-label': 'Close sidebar'
        }, '×')
      ),

      // Navigation menu
      this.createElement('nav', { className: 'app-sidebar__nav' },
        this.renderNavigationItems()
      ),

      // Sidebar footer
      isAuthenticated ? this.createElement('div', { className: 'app-sidebar__footer' },
        this.createElement('button', {
          className: 'app-sidebar__logout',
          onClick: () => this.auth?.logout()
        }, 'Logout')
      ) : null
    );
  }

  renderNavigationItems() {
    const isAuthenticated = this.auth?.isAuthenticated;
    const currentPath = this.router?.getCurrentPath();

    const navigationItems = [
      { path: '/', label: 'Dashboard', icon: '📊', requiresAuth: false },
      { path: '/users', label: 'Users', icon: '👥', requiresAuth: true },
      { path: '/files', label: 'Files', icon: '📁', requiresAuth: true },
      { path: '/reports', label: 'Reports', icon: '📈', requiresAuth: true },
      { path: '/settings', label: 'Settings', icon: '⚙️', requiresAuth: true }
    ];

    return navigationItems.map(item => {
      if (item.requiresAuth && !isAuthenticated) return null;

      const isActive = currentPath === item.path;

      return this.createElement('a', {
        key: item.path,
        href: item.path,
        className: `app-sidebar__nav-item ${isActive ? 'app-sidebar__nav-item--active' : ''}`,
        onClick: (e) => {
          e.preventDefault();
          this.router?.navigate(item.path);
          this.setState({ sidebarOpen: false });
        }
      },
        this.createElement('span', { className: 'app-sidebar__nav-icon' }, item.icon),
        this.createElement('span', { className: 'app-sidebar__nav-label' }, item.label)
      );
    });
  }

  renderBreadcrumbs() {
    if (this.state.breadcrumbs.length <= 1) return null;

    return this.createElement('nav', { className: 'app-breadcrumbs' },
      this.createElement('ol', { className: 'app-breadcrumbs__list' },
        this.state.breadcrumbs.map((crumb, index) => {
          const isLast = index === this.state.breadcrumbs.length - 1;

          return this.createElement('li', {
            key: crumb.path,
            className: 'app-breadcrumbs__item'
          },
            !isLast ? this.createElement('a', {
              href: crumb.path,
              className: 'app-breadcrumbs__link',
              onClick: (e) => {
                e.preventDefault();
                this.router?.navigate(crumb.path);
              }
            },
              this.createElement('span', { className: 'app-breadcrumbs__icon' }, crumb.icon),
              this.createElement('span', { className: 'app-breadcrumbs__label' }, crumb.label)
            ) : this.createElement('span', { className: 'app-breadcrumbs__current' },
              this.createElement('span', { className: 'app-breadcrumbs__icon' }, crumb.icon),
              this.createElement('span', { className: 'app-breadcrumbs__label' }, crumb.label)
            ),
            !isLast && this.createElement('span', { className: 'app-breadcrumbs__separator' }, '>')
          );
        })
      )
    );
  }

  renderFooter() {
    return this.createElement('footer', { className: 'app-footer' },
      this.createElement('div', { className: 'app-footer__content' },
        this.createElement('p', { className: 'app-footer__copyright' },
          '© 2024 Pyserv Client. Built with modern web technologies.'
        ),
        this.createElement('div', { className: 'app-footer__links' },
          this.createElement('a', { href: '/privacy' }, 'Privacy Policy'),
          this.createElement('a', { href: '/terms' }, 'Terms of Service'),
          this.createElement('a', { href: '/help' }, 'Help')
        )
      )
    );
  }

  renderGlobalComponents() {
    return this.createElement('div', { className: 'app-global-components' },
      // Global notification container
      this.createElement('div', { 'data-notification-container': true }),

      // Global modal container
      this.createElement('div', { 'data-modal-container': true }),

      // Global loading overlay
      this.state.loading && this.createElement('div', { className: 'app-global-loading' },
        this.createElement('div', { className: 'app-global-loading__spinner' })
      )
    );
  }

  _toggleNotifications() {
    // Implementation for notification dropdown
    console.log('Toggle notifications');
  }

  _toggleUserMenu() {
    // Implementation for user menu dropdown
    console.log('Toggle user menu');
  }
}

// CSS Styles
const styles = `
  .app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background: var(--pyserv-background);
    color: var(--pyserv-text-primary);
    transition: background-color 0.3s ease, color 0.3s ease;
  }

  .app-header {
    background: var(--pyserv-surface);
    border-bottom: 1px solid var(--pyserv-border);
    padding: 0 1rem;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 1000;
  }

  .app-header__left {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .app-header__menu-toggle {
    display: none;
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: var(--pyserv-radius-md);
  }

  .app-header__logo {
    font-weight: bold;
    font-size: 1.25rem;
    color: var(--pyserv-primary);
  }

  .app-header__search {
    position: relative;
    display: flex;
    align-items: center;
  }

  .app-header__search-input {
    padding: 0.5rem 2.5rem 0.5rem 1rem;
    border: 1px solid var(--pyserv-border);
    border-radius: var(--pyserv-radius-md);
    background: var(--pyserv-background-secondary);
    color: var(--pyserv-text-primary);
    font-size: 0.875rem;
    width: 200px;
  }

  .app-header__search-icon {
    position: absolute;
    right: 0.75rem;
    color: var(--pyserv-text-tertiary);
  }

  .app-header__right {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .app-header__theme-toggle,
  .app-header__notifications {
    background: none;
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: var(--pyserv-radius-md);
    transition: background-color 0.2s ease;
  }

  .app-header__theme-toggle:hover,
  .app-header__notifications:hover {
    background: var(--pyserv-background-secondary);
  }

  .app-header__auth-buttons {
    display: flex;
    gap: 0.5rem;
  }

  .app-header__login,
  .app-header__register {
    padding: 0.5rem 1rem;
    border: 1px solid var(--pyserv-border);
    border-radius: var(--pyserv-radius-md);
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .app-header__login {
    background: var(--pyserv-surface);
    color: var(--pyserv-text-primary);
  }

  .app-header__register {
    background: var(--pyserv-primary);
    color: white;
    border-color: var(--pyserv-primary);
  }

  .app-header__login:hover {
    background: var(--pyserv-background-secondary);
  }

  .app-header__register:hover {
    background: var(--pyserv-primary-hover);
  }

  .app-main {
    display: flex;
    flex: 1;
    min-height: 0;
  }

  .app-sidebar {
    width: 250px;
    background: var(--pyserv-surface);
    border-right: 1px solid var(--pyserv-border);
    display: flex;
    flex-direction: column;
    transition: transform 0.3s ease;
  }

  .app-sidebar--open {
    transform: translateX(0);
  }

  .app-sidebar__header {
    padding: 1rem;
    border-bottom: 1px solid var(--pyserv-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .app-sidebar__title {
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0;
  }

  .app-sidebar__close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: var(--pyserv-radius-sm);
  }

  .app-sidebar__nav {
    flex: 1;
    padding: 1rem 0;
  }

  .app-sidebar__nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    color: var(--pyserv-text-secondary);
    text-decoration: none;
    transition: all 0.2s ease;
  }

  .app-sidebar__nav-item:hover {
    background: var(--pyserv-background-secondary);
    color: var(--pyserv-text-primary);
  }

  .app-sidebar__nav-item--active {
    background: var(--pyserv-primary-light);
    color: var(--pyserv-primary-dark);
  }

  .app-sidebar__nav-icon {
    font-size: 1.125rem;
  }

  .app-sidebar__nav-label {
    font-size: 0.875rem;
  }

  .app-sidebar__footer {
    padding: 1rem;
    border-top: 1px solid var(--pyserv-border);
  }

  .app-sidebar__logout {
    width: 100%;
    padding: 0.75rem;
    background: var(--pyserv-error);
    color: white;
    border: none;
    border-radius: var(--pyserv-radius-md);
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .app-sidebar__logout:hover {
    background: var(--pyserv-error-dark);
  }

  .app-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .app-breadcrumbs {
    padding: 1rem;
    background: var(--pyserv-background-secondary);
    border-bottom: 1px solid var(--pyserv-border-light);
  }

  .app-breadcrumbs__list {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .app-breadcrumbs__item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .app-breadcrumbs__link {
    color: var(--pyserv-text-secondary);
    text-decoration: none;
    transition: color 0.2s ease;
  }

  .app-breadcrumbs__link:hover {
    color: var(--pyserv-primary);
  }

  .app-breadcrumbs__current {
    color: var(--pyserv-text-primary);
    font-weight: 500;
  }

  .app-breadcrumbs__separator {
    color: var(--pyserv-text-tertiary);
    margin: 0 0.25rem;
  }

  .app-page {
    flex: 1;
    padding: 2rem;
    overflow: auto;
  }

  .app-footer {
    background: var(--pyserv-surface);
    border-top: 1px solid var(--pyserv-border);
    padding: 1rem;
  }

  .app-footer__content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    max-width: 1200px;
    margin: 0 auto;
  }

  .app-footer__copyright {
    font-size: 0.875rem;
    color: var(--pyserv-text-secondary);
    margin: 0;
  }

  .app-footer__links {
    display: flex;
    gap: 1rem;
  }

  .app-footer__links a {
    font-size: 0.875rem;
    color: var(--pyserv-text-secondary);
    text-decoration: none;
    transition: color 0.2s ease;
  }

  .app-footer__links a:hover {
    color: var(--pyserv-primary);
  }

  .app-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: var(--pyserv-background);
    color: var(--pyserv-text-primary);
  }

  .app-loading__spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--pyserv-border);
    border-top: 3px solid var(--pyserv-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  .app-loading__text {
    font-size: 1rem;
    color: var(--pyserv-text-secondary);
  }

  .app-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: var(--pyserv-background);
    color: var(--pyserv-text-primary);
    padding: 2rem;
    text-align: center;
  }

  .app-error__icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .app-error__title {
    font-size: 2rem;
    margin-bottom: 1rem;
  }

  .app-error__message {
    font-size: 1.125rem;
    color: var(--pyserv-text-secondary);
    margin-bottom: 2rem;
    max-width: 500px;
  }

  .app-error__retry {
    padding: 0.75rem 1.5rem;
    background: var(--pyserv-primary);
    color: white;
    border: none;
    border-radius: var(--pyserv-radius-md);
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .app-error__retry:hover {
    background: var(--pyserv-primary-hover);
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  @media (max-width: 768px) {
    .app-header__menu-toggle {
      display: block;
    }

    .app-header__search-input {
      width: 150px;
    }

    .app-sidebar {
      position: fixed;
      top: 60px;
      left: 0;
      height: calc(100vh - 60px);
      transform: translateX(-100%);
      z-index: 999;
    }

    .app-sidebar--open {
      transform: translateX(0);
    }

    .app-page {
      padding: 1rem;
    }

    .app-footer__content {
      flex-direction: column;
      gap: 1rem;
      text-align: center;
    }
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = styles;
  document.head.appendChild(style);
}
