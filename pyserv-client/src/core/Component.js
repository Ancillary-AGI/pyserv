/**
 * Component - Modern Function-Based Component System
 * Provides signal-based reactivity with hooks and lifecycle management
 */

import { signal, computed, effect, batch, isSignal, unwrap } from './Signal.js';

// Component context for tracking current component
let currentComponent = null;
const componentStack = [];

// JSX Element interface
export class JSXElement {
  constructor(tagName, props = {}, children = []) {
    this.$$typeof = Symbol.for('pyserv.element');
    this.tagName = tagName;
    this.props = props;
    this.children = children.flat();
    this.key = props?.key || null;
    this.ref = props?.ref || null;
  }
}

// JSX Fragment
export class JSXFragment {
  constructor(children = [], props = {}) {
    this.$$typeof = Symbol.for('pyserv.fragment');
    this.children = children.flat();
    this.props = props;
    this.key = props?.key || null;
  }
}

// Component instance
export class ComponentInstance {
  constructor(renderFn, props = {}) {
    this.renderFn = renderFn;
    this.props = this.createProps(props);
    this.state = signal({});
    this.hooks = [];
    this.hookIndex = 0;
    this.element = null;
    this.mounted = false;
    this.cleanup = null;
    this.effects = new Set();

    // Track this component as current
    const prevComponent = currentComponent;
    currentComponent = this;
    componentStack.push(this);

    try {
      // Initialize component
      this.initialize();
    } finally {
      componentStack.pop();
      currentComponent = prevComponent;
    }
  }

  createProps(props) {
    const propsSignal = signal(props);

    // Make props reactive
    Object.keys(props).forEach(key => {
      if (isSignal(props[key])) {
        // Subscribe to signal changes
        effect(() => {
          const newValue = props[key].value;
          propsSignal.update(p => ({ ...p, [key]: newValue }));
        });
      }
    });

    return propsSignal;
  }

  initialize() {
    // Create computed render function
    this.rendered = computed(() => {
      this.hookIndex = 0;
      return this.renderFn(this.props.value);
    });

    // Set up effect to handle DOM updates
    this.setupRenderEffect();
  }

  setupRenderEffect() {
    const renderEffect = effect(() => {
      const vdom = this.rendered.value;
      if (this.element && this.mounted) {
        this.updateDOM(vdom);
      }
    });

    this.effects.add(renderEffect);
  }

  updateDOM(vdom) {
    if (!this.element) return;

    // Simple DOM update - in real implementation would use diffing
    const newHTML = this.vdomToHTML(vdom);
    if (this.element.innerHTML !== newHTML) {
      this.element.innerHTML = newHTML;
    }
  }

  vdomToHTML(vdom) {
    if (typeof vdom === 'string' || typeof vdom === 'number') {
      return String(vdom);
    }

    if (Array.isArray(vdom)) {
      return vdom.map(child => this.vdomToHTML(child)).join('');
    }

    if (vdom && vdom.$$typeof === Symbol.for('pyserv.element')) {
      const { tagName, props, children } = vdom;
      const attrs = Object.entries(props || {})
        .filter(([key]) => key !== 'children' && key !== 'key' && key !== 'ref')
        .map(([key, value]) => {
          if (key === 'className') return `class="${value}"`;
          if (key.startsWith('on') && typeof value === 'function') {
            return `${key.toLowerCase()}="${value.toString()}"`;
          }
          return `${key}="${value}"`;
        })
        .join(' ');

      const childrenHTML = (children || []).map(child => this.vdomToHTML(child)).join('');

      return `<${tagName}${attrs ? ' ' + attrs : ''}>${childrenHTML}</${tagName}>`;
    }

    if (vdom && vdom.$$typeof === Symbol.for('pyserv.fragment')) {
      return (vdom.children || []).map(child => this.vdomToHTML(child)).join('');
    }

    return '';
  }

  mount(container) {
    if (typeof container === 'string') {
      container = document.querySelector(container);
    }

    if (!container) {
      throw new Error('Mount container not found');
    }

    // Call onMount hook if provided
    if (this.props.value.onMount) {
      this.props.value.onMount.call(this);
    }

    // Create initial DOM
    const vdom = this.rendered.value;
    const html = this.vdomToHTML(vdom);
    container.innerHTML = html;
    this.element = container;

    this.mounted = true;

    // Call onMounted hook if provided
    if (this.props.value.onMounted) {
      this.props.value.onMounted.call(this);
    }
  }

  unmount() {
    // Call onUnmount hook
    if (this.props.value.onUnmount) {
      this.props.value.onUnmount.call(this);
    }

    // Clean up effects
    this.effects.forEach(effect => effect.stop());
    this.effects.clear();

    if (this.element && this.element.parentNode) {
      this.element.innerHTML = '';
    }

    this.mounted = false;
  }

  // Hooks
  useState(initialValue) {
    const hookIndex = this.hookIndex++;

    if (!this.hooks[hookIndex]) {
      this.hooks[hookIndex] = signal(initialValue);
    }

    const stateSignal = this.hooks[hookIndex];

    return [
      stateSignal.value,
      (value) => {
        const newValue = typeof value === 'function' ? value(stateSignal.value) : value;
        stateSignal.value = newValue;
      }
    ];
  }

  useEffect(fn, deps) {
    const hookIndex = this.hookIndex++;

    if (!this.hooks[hookIndex]) {
      this.hooks[hookIndex] = { deps: null, cleanup: null };
    }

    const hook = this.hooks[hookIndex];
    const depsChanged = !deps ||
      !hook.deps ||
      deps.some((dep, i) => !Object.is(dep, hook.deps[i]));

    if (depsChanged) {
      // Clean up previous effect
      if (hook.cleanup && typeof hook.cleanup === 'function') {
        hook.cleanup();
      }

      // Execute new effect
      const effectInstance = effect(() => {
        hook.cleanup = fn();
      });

      hook.deps = deps;
      hook.effect = effectInstance;
      this.effects.add(effectInstance);
    }
  }

  useMemo(compute, deps) {
    const hookIndex = this.hookIndex++;

    if (!this.hooks[hookIndex]) {
      this.hooks[hookIndex] = { deps: null, value: undefined };
    }

    const hook = this.hooks[hookIndex];
    const depsChanged = !deps ||
      !hook.deps ||
      deps.some((dep, i) => !Object.is(dep, hook.deps[i]));

    if (depsChanged) {
      hook.value = compute();
      hook.deps = deps;
    }

    return hook.value;
  }

  useCallback(callback, deps) {
    const hookIndex = this.hookIndex++;

    if (!this.hooks[hookIndex]) {
      this.hooks[hookIndex] = { deps: null, callback: null };
    }

    const hook = this.hooks[hookIndex];
    const depsChanged = !deps ||
      !hook.deps ||
      deps.some((dep, i) => !Object.is(dep, hook.deps[i]));

    if (depsChanged) {
      hook.callback = callback;
      hook.deps = deps;
    }

    return hook.callback;
  }

  useRef(initialValue) {
    const hookIndex = this.hookIndex++;

    if (!this.hooks[hookIndex]) {
      this.hooks[hookIndex] = { current: initialValue };
    }

    return this.hooks[hookIndex];
  }

  useContext(context) {
    const hookIndex = this.hookIndex++;

    if (!this.hooks[hookIndex]) {
      this.hooks[hookIndex] = signal(context._defaultValue);
    }

    const contextSignal = this.hooks[hookIndex];

    // Subscribe to context changes
    effect(() => {
      contextSignal.value = context._currentValue;
    });

    return contextSignal.value;
  }

  useReducer(reducer, initialState) {
    const state = this.useState(initialState);
    const dispatch = this.useCallback((action) => {
      state[1](prevState => reducer(prevState, action));
    }, [reducer]);

    return [state[0], dispatch];
  }

  useImperativeHandle(ref, createHandle, deps) {
    const handle = this.useMemo(() => createHandle(), deps);

    if (ref) {
      if (typeof ref === 'function') {
        ref(handle);
      } else if (ref && typeof ref === 'object') {
        ref.current = handle;
      }
    }
  }
}

// Create component function
export const createComponent = (renderFn) => {
  return (props = {}) => {
    return new ComponentInstance(renderFn, props);
  };
};

// JSX Functions
export const jsx = (tag, props, ...children) => {
  if (typeof tag === 'function') {
    // Component
    return tag({ ...props, children: children.flat() });
  }

  // DOM element
  return new JSXElement(tag, props, children);
};

export const jsxs = (tag, props) => {
  return jsx(tag, props);
};

export const Fragment = (props) => {
  return new JSXFragment(props.children || [], props);
};

// Context system
export class Context {
  constructor(defaultValue) {
    this._defaultValue = defaultValue;
    this._currentValue = defaultValue;
    this._subscribers = new Set();
    this.Provider = createProvider(this);
    this.Consumer = createConsumer(this);
  }

  provide(value) {
    const prevValue = this._currentValue;
    this._currentValue = value;

    // Notify subscribers
    this._subscribers.forEach(subscriber => subscriber(value));

    return () => {
      this._currentValue = prevValue;
    };
  }

  subscribe(subscriber) {
    this._subscribers.add(subscriber);
    return () => this._subscribers.delete(subscriber);
  }
}

const createProvider = (context) => {
  return createComponent((props) => {
    const restore = context.provide(props.value);

    // Call onMount/onUnmount if provided
    const instance = currentComponent;
    if (instance) {
      instance.useEffect(() => {
        return restore;
      }, [props.value]);
    }

    return props.children;
  });
};

const createConsumer = (context) => {
  return createComponent((props) => {
    const [value, setValue] = currentComponent.useState(context._defaultValue);

    // Subscribe to context changes
    currentComponent.useEffect(() => {
      const unsubscribe = context.subscribe(setValue);
      return unsubscribe;
    }, []);

    return props.children(value);
  });
};

// Utility functions
export const useState = (initialValue) => {
  if (!currentComponent) {
    throw new Error('useState must be called within a component');
  }
  return currentComponent.useState(initialValue);
};

export const useEffect = (fn, deps) => {
  if (!currentComponent) {
    throw new Error('useEffect must be called within a component');
  }
  return currentComponent.useEffect(fn, deps);
};

export const useMemo = (compute, deps) => {
  if (!currentComponent) {
    throw new Error('useMemo must be called within a component');
  }
  return currentComponent.useMemo(compute, deps);
};

export const useCallback = (callback, deps) => {
  if (!currentComponent) {
    throw new Error('useCallback must be called within a component');
  }
  return currentComponent.useCallback(callback, deps);
};

export const useRef = (initialValue) => {
  if (!currentComponent) {
    throw new Error('useRef must be called within a component');
  }
  return currentComponent.useRef(initialValue);
};

export const useContext = (context) => {
  if (!currentComponent) {
    throw new Error('useContext must be called within a component');
  }
  return currentComponent.useContext(context);
};

export const useReducer = (reducer, initialState) => {
  if (!currentComponent) {
    throw new Error('useReducer must be called within a component');
  }
  return currentComponent.useReducer(reducer, initialState);
};

export const useImperativeHandle = (ref, createHandle, deps) => {
  if (!currentComponent) {
    throw new Error('useImperativeHandle must be called within a component');
  }
  return currentComponent.useImperativeHandle(ref, createHandle, deps);
};

// Memoization
export const memo = (component, compareProps = (prevProps, nextProps) => {
  return JSON.stringify(prevProps) === JSON.stringify(nextProps);
}) => {
  let prevProps = null;
  let cachedInstance = null;

  return (props) => {
    if (cachedInstance && compareProps(prevProps, props)) {
      return cachedInstance.rendered.value;
    }

    prevProps = props;
    cachedInstance = new ComponentInstance(component, props);
    return cachedInstance.rendered.value;
  };
};

// Error boundary
export const createErrorBoundary = (fallbackComponent) => {
  return createComponent((props) => {
    const [error, setError] = useState(null);

    useEffect(() => {
      const handleError = (event) => {
        setError(event.error);
      };

      window.addEventListener('error', handleError);
      return () => window.removeEventListener('error', handleError);
    }, []);

    if (error) {
      return fallbackComponent({ error, resetError: () => setError(null) });
    }

    return props.children;
  });
};

// Suspense
export const Suspense = createComponent((props) => {
  const [suspenseState, setSuspenseState] = useState('pending');
  const [suspendedComponent, setSuspendedComponent] = useState(null);

  // This is a simplified implementation
  // Real implementation would handle promises and concurrent rendering

  return props.fallback || props.children;
});

// Development helpers
export const devtools = {
  getCurrentComponent: () => currentComponent,
  getComponentStack: () => [...componentStack],
  inspectComponent: (component) => {
    console.log('Component info:', {
      props: component.props.value,
      state: component.state.value,
      hooks: component.hooks.length,
      mounted: component.mounted
    });
  }
};

// Export everything
export default {
  ComponentInstance,
  createComponent,
  jsx,
  jsxs,
  Fragment,
  Context,
  useState,
  useEffect,
  useMemo,
  useCallback,
  useRef,
  useContext,
  useReducer,
  useImperativeHandle,
  memo,
  createErrorBoundary,
  Suspense,
  devtools
};
