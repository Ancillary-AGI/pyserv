/**
 * JSX - Modern JSX Runtime with Signal Integration
 * Provides lightweight JSX support with automatic signal tracking
 */

import { isSignal, unwrap } from './Signal.js';

// JSX Runtime Configuration
export const jsxRuntimeConfig = {
  enableSignalTracking: true,
  enableStaticOptimization: true,
  enableKeyOptimization: true,
  enableFragmentSupport: true,
  enablePortalSupport: false, // Will be added later
  debug: false
};

// JSX Element Factory
export class JSXElementFactory {
  constructor() {
    this.elementId = 0;
    this.staticElements = new Map();
  }

  // Create JSX element
  createElement(tag, props = {}, ...children) {
    const elementId = `element_${this.elementId++}`;

    // Handle children in props
    if (props && props.children) {
      children = [props.children].flat();
      delete props.children;
    }

    // Flatten children
    children = children.flat();

    // Process children for signals
    const processedChildren = children.map(child => {
      if (isSignal(child)) {
        return { type: 'signal', value: child, id: elementId };
      }
      return child;
    });

    const element = {
      $$typeof: Symbol.for('pyserv.element'),
      tag,
      props: this.processProps(props, elementId),
      children: processedChildren,
      key: props?.key || null,
      ref: props?.ref || null,
      _id: elementId,
      _isStatic: this.isStaticElement(tag, props, children),
      _staticHash: this.generateStaticHash(tag, props, children)
    };

    // Cache static elements
    if (element._isStatic) {
      const existing = this.staticElements.get(element._staticHash);
      if (existing) {
        return existing;
      }
      this.staticElements.set(element._staticHash, element);
    }

    return element;
  }

  // Process props for signals and event handlers
  processProps(props, elementId) {
    if (!props) return {};

    const processed = {};

    for (const [key, value] of Object.entries(props)) {
      if (key === 'children' || key === 'key' || key === 'ref') {
        continue;
      }

      if (isSignal(value)) {
        // Signal prop - track for reactivity
        processed[key] = { type: 'signal', value, id: elementId };
      } else if (key.startsWith('on') && typeof value === 'function') {
        // Event handler - wrap for proper context
        processed[key] = this.wrapEventHandler(value, elementId);
      } else if (typeof value === 'object' && value !== null) {
        // Deep process objects
        processed[key] = this.processObject(value, elementId);
      } else {
        processed[key] = value;
      }
    }

    return processed;
  }

  processObject(obj, elementId) {
    if (isSignal(obj)) {
      return { type: 'signal', value: obj, id: elementId };
    }

    if (Array.isArray(obj)) {
      return obj.map(item => this.processObject(item, elementId));
    }

    if (typeof obj === 'object' && obj !== null) {
      const processed = {};
      for (const [key, value] of Object.entries(obj)) {
        processed[key] = this.processObject(value, elementId);
      }
      return processed;
    }

    return obj;
  }

  wrapEventHandler(handler, elementId) {
    return {
      type: 'event_handler',
      handler,
      id: elementId,
      wrapped: (event) => {
        // Create synthetic event
        const syntheticEvent = this.createSyntheticEvent(event);
        return handler(syntheticEvent);
      }
    };
  }

  createSyntheticEvent(nativeEvent) {
    return {
      type: nativeEvent.type,
      target: nativeEvent.target,
      currentTarget: nativeEvent.currentTarget,
      preventDefault: () => nativeEvent.preventDefault(),
      stopPropagation: () => nativeEvent.stopPropagation(),
      nativeEvent,
      isTrusted: nativeEvent.isTrusted,
      bubbles: nativeEvent.bubbles,
      cancelable: nativeEvent.cancelable,
      defaultPrevented: nativeEvent.defaultPrevented,
      timeStamp: nativeEvent.timeStamp,
      // Add more properties as needed
    };
  }

  // Check if element is static (no reactive dependencies)
  isStaticElement(tag, props, children) {
    if (jsxRuntimeConfig.enableStaticOptimization) {
      // Check if props contain signals
      for (const value of Object.values(props)) {
        if (isSignal(value) || (typeof value === 'object' && value?.type === 'signal')) {
          return false;
        }
      }

      // Check if children contain signals
      for (const child of children) {
        if (isSignal(child) || (typeof child === 'object' && child?.type === 'signal')) {
          return false;
        }
      }

      return true;
    }

    return false;
  }

  generateStaticHash(tag, props, children) {
    if (!jsxRuntimeConfig.enableStaticOptimization) return null;

    const content = JSON.stringify({ tag, props, children: children.length });
    let hash = 0;

    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }

    return hash.toString(36);
  }

  // Create fragment
  createFragment(props = {}, ...children) {
    return {
      $$typeof: Symbol.for('pyserv.fragment'),
      children: children.flat(),
      props,
      key: props?.key || null,
      _id: `fragment_${this.elementId++}`
    };
  }

  // Clone element
  cloneElement(element, props = {}, ...children) {
    return this.createElement(
      element.tag,
      { ...element.props, ...props },
      ...(children.length > 0 ? children : element.children)
    );
  }

  // Check if value is JSX element
  isElement(value) {
    return value && typeof value === 'object' &&
           value.$$typeof === Symbol.for('pyserv.element');
  }

  // Check if value is fragment
  isFragment(value) {
    return value && typeof value === 'object' &&
           value.$$typeof === Symbol.for('pyserv.fragment');
  }
}

// Global JSX factory instance
export const jsxFactory = new JSXElementFactory();

// JSX Functions
export const createElement = (tag, props, ...children) => {
  return jsxFactory.createElement(tag, props, ...children);
};

export const createFragment = (props, ...children) => {
  return jsxFactory.createFragment(props, ...children);
};

export const cloneElement = (element, props, ...children) => {
  return jsxFactory.cloneElement(element, props, ...children);
};

// JSX Runtime for Babel/TypeScript
export const jsx = (tag, props, ...children) => {
  return jsxFactory.createElement(tag, props, ...children);
};

export const jsxs = (tag, props, ...children) => {
  return jsxFactory.createElement(tag, props, ...children);
};

export const jsxDEV = (tag, props, ...children) => {
  if (jsxRuntimeConfig.debug) {
    console.log('JSX DEV:', { tag, props, children });
  }
  return jsxFactory.createElement(tag, props, ...children);
};

// Fragment component
export const Fragment = (props) => {
  return jsxFactory.createFragment(props, props.children);
};

// JSX Template Compiler
export class JSXTemplateCompiler {
  constructor() {
    this.templates = new Map();
    this.compiledTemplates = new Map();
  }

  // Compile JSX template to optimized function
  compileTemplate(templateFn) {
    const templateString = templateFn.toString();
    const cacheKey = this.hashString(templateString);

    if (this.compiledTemplates.has(cacheKey)) {
      return this.compiledTemplates.get(cacheKey);
    }

    // Analyze template for static optimization
    const analysis = this.analyzeTemplate(templateString);

    // Generate optimized template function
    const compiled = this.generateOptimizedTemplate(templateFn, analysis);

    this.compiledTemplates.set(cacheKey, compiled);
    return compiled;
  }

  analyzeTemplate(templateString) {
    const analysis = {
      staticNodes: [],
      dynamicNodes: [],
      signalDependencies: [],
      eventHandlers: [],
      hasStaticContent: false
    };

    // Simple analysis - in real implementation would use AST parsing
    const signalMatches = templateString.match(/signal\([^)]+\)/g) || [];
    const eventMatches = templateString.match(/on[A-Z][a-zA-Z]+=\{[^}]+\}/g) || [];

    analysis.signalDependencies = signalMatches;
    analysis.eventHandlers = eventMatches;
    analysis.hasStaticContent = signalMatches.length === 0;

    return analysis;
  }

  generateOptimizedTemplate(originalFn, analysis) {
    // Generate optimized version
    return (props) => {
      // For now, just call original - real implementation would optimize
      return originalFn(props);
    };
  }

  hashString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return hash.toString(36);
  }
}

// JSX Optimizer
export class JSXOptimizer {
  constructor() {
    this.compiler = new JSXTemplateCompiler();
  }

  // Optimize JSX element
  optimize(element) {
    if (!element || typeof element !== 'object') {
      return element;
    }

    if (element.$$typeof === Symbol.for('pyserv.element')) {
      return this.optimizeElement(element);
    }

    if (element.$$typeof === Symbol.for('pyserv.fragment')) {
      return this.optimizeFragment(element);
    }

    if (Array.isArray(element)) {
      return element.map(child => this.optimize(child));
    }

    return element;
  }

  optimizeElement(element) {
    const optimized = { ...element };

    // Optimize props
    optimized.props = this.optimizeProps(element.props);

    // Optimize children
    optimized.children = element.children.map(child => this.optimize(child));

    // Mark as optimized
    optimized._optimized = true;

    return optimized;
  }

  optimizeFragment(fragment) {
    return {
      ...fragment,
      children: fragment.children.map(child => this.optimize(child)),
      _optimized: true
    };
  }

  optimizeProps(props) {
    const optimized = {};

    for (const [key, value] of Object.entries(props)) {
      if (value && typeof value === 'object' && value.type === 'signal') {
        // Keep signal references
        optimized[key] = value;
      } else if (value && typeof value === 'object' && value.type === 'event_handler') {
        // Keep event handler references
        optimized[key] = value;
      } else {
        // Static values can be optimized
        optimized[key] = value;
      }
    }

    return optimized;
  }
}

// JSX Development Tools
export class JSXDevTools {
  constructor() {
    this.elements = new Map();
    this.renderCount = 0;
    this.updateCount = 0;
  }

  // Track element creation
  trackElement(element) {
    this.elements.set(element._id, {
      element,
      created: Date.now(),
      renderCount: 0
    });
  }

  // Track element updates
  trackUpdate(elementId) {
    const tracked = this.elements.get(elementId);
    if (tracked) {
      tracked.renderCount++;
      this.updateCount++;
    }
  }

  // Get element stats
  getElementStats(elementId) {
    return this.elements.get(elementId);
  }

  // Get overall stats
  getStats() {
    return {
      totalElements: this.elements.size,
      renderCount: this.renderCount,
      updateCount: this.updateCount,
      averageUpdates: this.elements.size > 0 ? this.updateCount / this.elements.size : 0
    };
  }

  // Clear tracking
  clear() {
    this.elements.clear();
    this.renderCount = 0;
    this.updateCount = 0;
  }
}

// Global JSX dev tools instance
export const jsxDevTools = new JSXDevTools();

// Setup global JSX functions for browser
if (typeof window !== 'undefined') {
  window.jsx = jsx;
  window.jsxs = jsxs;
  window.Fragment = Fragment;
  window.createElement = createElement;
  window.createFragment = createFragment;
  window.cloneElement = cloneElement;
  window.jsxDevTools = jsxDevTools;
}

// Export everything
export default {
  JSXElementFactory,
  jsxFactory,
  createElement,
  createFragment,
  cloneElement,
  jsx,
  jsxs,
  jsxDEV,
  Fragment,
  JSXTemplateCompiler,
  JSXOptimizer,
  JSXDevTools,
  jsxDevTools,
  jsxRuntimeConfig
};
