/**
 * Router - Client-side Routing for Pyserv Client Framework
 * Provides declarative routing with nested routes, guards, lazy loading,
 * and seamless integration with the component system
 */

export class Router {
  constructor(options = {}) {
    this.routes = [];
    this.currentRoute = null;
    this.history = [];
    this.historyIndex = -1;
    this.container = null;
    this.params = {};
    this.query = {};
    this.hash = '';
    this.beforeEachHooks = [];
    this.afterEachHooks = [];
    this.beforeResolveHooks = [];
    this.afterResolveHooks = [];
    this.notFoundHandler = null;
    this.errorHandler = null;
    this.loadingComponent = null;
    this.scrollBehavior = options.scrollBehavior || 'auto';
    this.mode = options.mode || 'history'; // 'history' or 'hash'
    this.base = options.base || '/';
    this.lazyLoadDelay = options.lazyLoadDelay || 200;

    // Bind methods
    this.navigate = this.navigate.bind(this);
    this.go = this.go.bind(this);
    this.back = this.back.bind(this);
    this.forward = this.forward.bind(this);
    this.push = this.push.bind(this);
    this.replace = this.replace.bind(this);
  }

  // Route definition
  addRoute(route) {
    if (Array.isArray(route)) {
      route.forEach(r => this.addRoute(r));
      return;
    }

    // Normalize route
    const normalizedRoute = {
      path: route.path,
      name: route.name,
      component: route.component,
      components: route.components,
      redirect: route.redirect,
      alias: route.alias,
      props: route.props || false,
      meta: route.meta || {},
      children: route.children || [],
      beforeEnter: route.beforeEnter,
      beforeLeave: route.beforeLeave,
      ...route
    };

    this.routes.push(normalizedRoute);
    return this;
  }

  // Route matching
  matchRoute(path) {
    const cleanPath = this._cleanPath(path);

    for (const route of this.routes) {
      const match = this._matchPath(route.path, cleanPath);
      if (match) {
        return { route, match, params: match.params };
      }
    }

    return null;
  }

  _matchPath(pattern, path) {
    const paramNames = [];
    const regexPattern = pattern
      .replace(/:([^/]+)/g, (match, paramName) => {
        paramNames.push(paramName);
        return '([^/]+)';
      })
      .replace(/\*/g, '.*');

    const regex = new RegExp(`^${regexPattern}$`);
    const match = path.match(regex);

    if (!match) return null;

    const params = {};
    paramNames.forEach((name, index) => {
      params[name] = decodeURIComponent(match[index + 1]);
    });

    return { params, path: match[0] };
  }

  _cleanPath(path) {
    return path.replace(/\/+/g, '/').replace(/^\/|\/$/g, '') || '/';
  }

  // Navigation
  async navigate(path, options = {}) {
    const { replace = false, state = {}, force = false } = options;

    if (!force && this.currentRoute && this.currentRoute.path === path) {
      return;
    }

    try {
      // Find matching route
      const match = this.matchRoute(path);
      if (!match) {
        if (this.notFoundHandler) {
          await this.notFoundHandler(path, options);
        }
        return;
      }

      const { route, params } = match;

      // Run beforeEach hooks
      for (const hook of this.beforeEachHooks) {
        const result = await hook(route, this.currentRoute, options);
        if (result === false) {
          return; // Navigation cancelled
        }
      }

      // Check beforeEnter guard
      if (route.beforeEnter) {
        const result = await route.beforeEnter(route, this.currentRoute, options);
        if (result === false) {
          return; // Navigation cancelled
        }
      }

      // Handle redirect
      if (route.redirect) {
        const redirectPath = typeof route.redirect === 'function'
          ? await route.redirect(route, this.currentRoute)
          : route.redirect;
        return this.navigate(redirectPath, { ...options, replace: true });
      }

      // Run beforeResolve hooks
      for (const hook of this.beforeResolveHooks) {
        await hook(route, this.currentRoute, options);
      }

      // Load components
      const components = await this._loadComponents(route);

      // Update current route
      const prevRoute = this.currentRoute;
      this.currentRoute = {
        ...route,
        params,
        query: this._parseQuery(options.query || ''),
        hash: options.hash || '',
        fullPath: path,
        matched: [route],
        meta: route.meta || {}
      };

      // Update browser history
      this._updateHistory(path, replace, state);

      // Update URL
      this._updateURL(path);

      // Render components
      await this._renderRoute(components, params);

      // Run afterResolve hooks
      for (const hook of this.afterResolveHooks) {
        await hook(this.currentRoute, prevRoute);
      }

      // Run afterEach hooks
      for (const hook of this.afterEachHooks) {
        await hook(this.currentRoute, prevRoute);
      }

      // Handle scroll behavior
      this._handleScrollBehavior();

      // Emit navigation event
      this.emit('route:changed', {
        route: this.currentRoute,
        prevRoute,
        options
      });

    } catch (error) {
      console.error('Navigation error:', error);

      if (this.errorHandler) {
        await this.errorHandler(error, path, options);
      } else {
        throw error;
      }
    }
  }

  async _loadComponents(route) {
    const components = {};

    if (route.component) {
      components.default = await this._loadComponent(route.component);
    }

    if (route.components) {
      for (const [name, component] of Object.entries(route.components)) {
        components[name] = await this._loadComponent(component);
      }
    }

    return components;
  }

  async _loadComponent(component) {
    if (typeof component === 'function') {
      // Lazy load component
      return await new Promise((resolve) => {
        setTimeout(async () => {
          const loadedComponent = await component();
          resolve(loadedComponent.default || loadedComponent);
        }, this.lazyLoadDelay);
      });
    }

    return component;
  }

  async _renderRoute(components, params) {
    if (!this.container) return;

    // Clear container
    this.container.innerHTML = '';

    // Render each component
    for (const [name, component] of Object.entries(components)) {
      if (component) {
        const element = document.createElement('div');
        element.setAttribute('data-router-view', name);

        // Create component instance
        const componentInstance = new component({
          router: this,
          route: this.currentRoute,
          params,
          query: this.currentRoute.query,
          ...this.currentRoute.props
        });

        // Mount component
        componentInstance.mount(element);
        this.container.appendChild(element);
      }
    }
  }

  _updateHistory(path, replace = false, state = {}) {
    const entry = {
      path,
      state,
      timestamp: Date.now()
    };

    if (replace) {
      // Replace current entry
      if (this.historyIndex >= 0) {
        this.history[this.historyIndex] = entry;
      } else {
        this.history.push(entry);
        this.historyIndex = 0;
      }
    } else {
      // Remove any forward history
      this.history = this.history.slice(0, this.historyIndex + 1);
      this.history.push(entry);
      this.historyIndex++;
    }
  }

  _updateURL(path) {
    if (this.mode === 'history') {
      const url = this.base + path;
      if (replace) {
        window.history.replaceState(null, '', url);
      } else {
        window.history.pushState(null, '', url);
      }
    } else if (this.mode === 'hash') {
      const hash = this.base + '#' + path;
      window.location.hash = hash;
    }
  }

  _handleScrollBehavior() {
    if (this.scrollBehavior === 'auto') {
      window.scrollTo(0, 0);
    } else if (typeof this.scrollBehavior === 'function') {
      this.scrollBehavior(this.currentRoute, this.currentRoute);
    }
  }

  _parseQuery(queryString) {
    const query = {};
    if (queryString) {
      const params = new URLSearchParams(queryString);
      for (const [key, value] of params.entries()) {
        query[key] = value;
      }
    }
    return query;
  }

  // History navigation
  go(n) {
    const newIndex = this.historyIndex + n;
    if (newIndex >= 0 && newIndex < this.history.length) {
      this.historyIndex = newIndex;
      const entry = this.history[newIndex];
      this.navigate(entry.path, { replace: true, state: entry.state });
    }
  }

  back() {
    this.go(-1);
  }

  forward() {
    this.go(1);
  }

  push(path, state = {}) {
    this.navigate(path, { state });
  }

  replace(path, state = {}) {
    this.navigate(path, { replace: true, state });
  }

  // Hook management
  beforeEach(hook) {
    this.beforeEachHooks.push(hook);
  }

  afterEach(hook) {
    this.afterEachHooks.push(hook);
  }

  beforeResolve(hook) {
    this.beforeResolveHooks.push(hook);
  }

  afterResolve(hook) {
    this.afterResolveHooks.push(hook);
  }

  // Route guards
  canActivate(route, from) {
    // Check if route requires authentication
    if (route.meta?.requiresAuth) {
      // Check if user is authenticated
      return this._isAuthenticated();
    }

    // Check if route requires specific roles
    if (route.meta?.requiresRole) {
      return this._hasRole(route.meta.requiresRole);
    }

    return true;
  }

  _isAuthenticated() {
    // Check authentication state
    return !!localStorage.getItem('auth_token');
  }

  _hasRole(requiredRole) {
    const userRole = localStorage.getItem('user_role');
    if (Array.isArray(requiredRole)) {
      return requiredRole.includes(userRole);
    }
    return userRole === requiredRole;
  }

  // Route helpers
  resolve(path, params = {}) {
    let resolvedPath = path;

    // Replace parameters
    Object.entries(params).forEach(([key, value]) => {
      resolvedPath = resolvedPath.replace(`:${key}`, encodeURIComponent(value));
    });

    return resolvedPath;
  }

  getRoute(name, params = {}) {
    const route = this.routes.find(r => r.name === name);
    if (!route) return null;

    return {
      ...route,
      path: this.resolve(route.path, params)
    };
  }

  // URL utilities
  getCurrentPath() {
    if (this.mode === 'history') {
      return window.location.pathname.replace(this.base, '');
    } else {
      return window.location.hash.replace('#', '');
    }
  }

  getCurrentQuery() {
    return this._parseQuery(window.location.search);
  }

  getCurrentHash() {
    return window.location.hash;
  }

  // Event system
  emit(event, data) {
    window.dispatchEvent(new CustomEvent(`router:${event}`, { detail: data }));
  }

  on(event, handler) {
    const eventHandler = (e) => handler(e.detail);
    window.addEventListener(`router:${event}`, eventHandler);

    return () => {
      window.removeEventListener(`router:${event}`, eventHandler);
    };
  }

  // Initialization
  init(containerSelector = '[data-router-view]') {
    this.container = document.querySelector(containerSelector);
    if (!this.container) {
      throw new Error(`Router container '${containerSelector}' not found`);
    }

    // Listen for browser navigation
    window.addEventListener('popstate', (e) => {
      const path = this.getCurrentPath();
      this.navigate(path, { replace: true });
    });

    // Listen for hash changes
    if (this.mode === 'hash') {
      window.addEventListener('hashchange', (e) => {
        const path = this.getCurrentPath();
        this.navigate(path, { replace: true });
      });
    }

    // Initial navigation
    const initialPath = this.getCurrentPath() || '/';
    this.navigate(initialPath, { replace: true });

    console.log('✅ Router initialized');
  }

  // Error handling
  setNotFoundHandler(handler) {
    this.notFoundHandler = handler;
  }

  setErrorHandler(handler) {
    this.errorHandler = handler;
  }

  setLoadingComponent(component) {
    this.loadingComponent = component;
  }

  // Utility methods
  isActive(path, exact = false) {
    const currentPath = this.getCurrentPath();
    if (exact) {
      return currentPath === path;
    }
    return currentPath.startsWith(path);
  }

  getBreadcrumbs() {
    // Generate breadcrumbs from current route
    const breadcrumbs = [];
    let current = this.currentRoute;

    while (current) {
      breadcrumbs.unshift({
        name: current.name,
        path: current.path,
        meta: current.meta
      });
      current = current.parent;
    }

    return breadcrumbs;
  }

  // Route introspection
  getRoutes() {
    return [...this.routes];
  }

  getCurrentRoute() {
    return this.currentRoute;
  }

  getRouteParams() {
    return { ...this.params };
  }

  getRouteQuery() {
    return { ...this.query };
  }

  getRouteHash() {
    return this.hash;
  }

  // Cleanup
  destroy() {
    // Clear routes
    this.routes = [];

    // Clear hooks
    this.beforeEachHooks = [];
    this.afterEachHooks = [];
    this.beforeResolveHooks = [];
    this.afterResolveHooks = [];

    // Clear history
    this.history = [];
    this.historyIndex = -1;

    // Clear current route
    this.currentRoute = null;

    // Remove event listeners
    window.removeEventListener('popstate', this._popStateHandler);
    window.removeEventListener('hashchange', this._hashChangeHandler);

    console.log('✅ Router destroyed');
  }
}

// Route builder
export class RouteBuilder {
  constructor() {
    this.route = {
      path: '',
      name: '',
      component: null,
      components: {},
      redirect: null,
      alias: [],
      props: false,
      meta: {},
      children: [],
      beforeEnter: null,
      beforeLeave: null
    };
  }

  path(path) {
    this.route.path = path;
    return this;
  }

  name(name) {
    this.route.name = name;
    return this;
  }

  component(component) {
    this.route.component = component;
    return this;
  }

  components(components) {
    this.route.components = components;
    return this;
  }

  redirect(redirect) {
    this.route.redirect = redirect;
    return this;
  }

  alias(alias) {
    this.route.alias.push(alias);
    return this;
  }

  props(props) {
    this.route.props = props;
    return this;
  }

  meta(meta) {
    this.route.meta = { ...this.route.meta, ...meta };
    return this;
  }

  beforeEnter(guard) {
    this.route.beforeEnter = guard;
    return this;
  }

  beforeLeave(guard) {
    this.route.beforeLeave = guard;
    return this;
  }

  children(routes) {
    this.route.children = routes;
    return this;
  }

  build() {
    return { ...this.route };
  }
}

// Route guards
export const authGuard = (to, from, next) => {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    // Redirect to login
    return '/login';
  }
  return true;
};

export const roleGuard = (requiredRole) => {
  return (to, from, next) => {
    const userRole = localStorage.getItem('user_role');
    if (userRole !== requiredRole) {
      // Redirect to unauthorized page
      return '/unauthorized';
    }
    return true;
  };
};

export const guestGuard = (to, from, next) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    // Redirect to dashboard if already authenticated
    return '/dashboard';
  }
  return true;
};

// Route helpers
export function createRoute(config) {
  return new RouteBuilder().path(config.path).component(config.component).build();
}

export function createNestedRoute(parentPath, config) {
  return new RouteBuilder()
    .path(`${parentPath}/${config.path}`)
    .component(config.component)
    .build();
}

// Router utilities
export function useRouter() {
  return window.__PYSERV_ROUTER__;
}

export function useRoute() {
  const router = useRouter();
  return {
    path: router.getCurrentPath(),
    params: router.getRouteParams(),
    query: router.getRouteQuery(),
    hash: router.getRouteHash(),
    name: router.getCurrentRoute()?.name,
    meta: router.getCurrentRoute()?.meta
  };
}

// Global router instance
let globalRouter = null;

export function setGlobalRouter(router) {
  globalRouter = router;
  window.__PYSERV_ROUTER__ = router;
}

export function getGlobalRouter() {
  return globalRouter;
}
