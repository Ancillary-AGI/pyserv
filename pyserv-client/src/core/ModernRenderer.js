/**
 * Modern Renderer - Efficient DOM Updates with Signal Integration
 * Provides fine-grained DOM updates based on signal changes
 */

import { isSignal, unwrap } from './Signal.js';
import { jsxFactory } from './JSX.js';

// DOM Node Cache
export class DOMNodeCache {
  constructor() {
    this.nodes = new Map();
    this.staticNodes = new Map();
  }

  get(elementId) {
    return this.nodes.get(elementId);
  }

  set(elementId, node) {
    this.nodes.set(elementId, node);
  }

  has(elementId) {
    return this.nodes.has(elementId);
  }

  delete(elementId) {
    this.nodes.delete(elementId);
  }

  clear() {
    this.nodes.clear();
    this.staticNodes.clear();
  }
}

// Global node cache
export const domNodeCache = new DOMNodeCache();

// Renderer Configuration
export const rendererConfig = {
  enableStaticNodeCaching: true,
  enableEventDelegation: true,
  enableKeyOptimization: true,
  enableTextOptimization: true,
  enableMoveDetection: true,
  debug: false
};

// Modern Renderer
export class ModernRenderer {
  constructor(container) {
    this.container = typeof container === 'string'
      ? document.querySelector(container)
      : container;
    this.nodeCache = new DOMNodeCache();
    this.staticNodes = new Map();
    this.eventListeners = new Map();
    this.updateQueue = [];
    this.isRendering = false;
  }

  // Render JSX to DOM
  render(jsxElement) {
    if (!jsxElement) return null;

    // Clear previous content
    this.container.innerHTML = '';

    // Render new content
    const domNode = this.createDOMNode(jsxElement);
    this.container.appendChild(domNode);

    return domNode;
  }

  // Update existing DOM with new JSX
  update(jsxElement) {
    if (this.isRendering) {
      this.updateQueue.push(jsxElement);
      return;
    }

    this.isRendering = true;

    try {
      const domNode = this.createDOMNode(jsxElement);
      this.container.replaceChild(domNode, this.container.firstChild);
    } finally {
      this.isRendering = false;

      // Process queued updates
      if (this.updateQueue.length > 0) {
        const nextUpdate = this.updateQueue.shift();
        this.update(nextUpdate);
      }
    }
  }

  // Create DOM node from JSX element
  createDOMNode(jsxElement) {
    if (typeof jsxElement === 'string' || typeof jsxElement === 'number') {
      return document.createTextNode(String(jsxElement));
    }

    if (Array.isArray(jsxElement)) {
      const fragment = document.createDocumentFragment();
      jsxElement.forEach(child => {
        if (child !== null && child !== undefined) {
          fragment.appendChild(this.createDOMNode(child));
        }
      });
      return fragment;
    }

    if (jsxElement && jsxElement.$$typeof === Symbol.for('pyserv.element')) {
      return this.createElementNode(jsxElement);
    }

    if (jsxElement && jsxElement.$$typeof === Symbol.for('pyserv.fragment')) {
      return this.createFragmentNode(jsxElement);
    }

    return document.createTextNode(String(jsxElement));
  }

  createElementNode(element) {
    const { tag, props, children } = element;

    // Check cache for static elements
    if (element._isStatic && rendererConfig.enableStaticNodeCaching) {
      const cached = this.staticNodes.get(element._staticHash);
      if (cached) {
        return cached.cloneNode(true);
      }
    }

    // Create DOM element
    const domElement = document.createElement(tag);

    // Set properties
    this.setElementProps(domElement, props, element._id);

    // Create children
    if (children && children.length > 0) {
      children.forEach(child => {
        if (child !== null && child !== undefined) {
          const childNode = this.createDOMNode(child);
          domElement.appendChild(childNode);
        }
      });
    }

    // Cache static elements
    if (element._isStatic && rendererConfig.enableStaticNodeCaching) {
      this.staticNodes.set(element._staticHash, domElement.cloneNode(true));
    }

    // Cache node
    this.nodeCache.set(element._id, domElement);

    return domElement;
  }

  createFragmentNode(fragment) {
    const fragmentNode = document.createDocumentFragment();

    if (fragment.children && fragment.children.length > 0) {
      fragment.children.forEach(child => {
        if (child !== null && child !== undefined) {
          fragmentNode.appendChild(this.createDOMNode(child));
        }
      });
    }

    return fragmentNode;
  }

  // Set element properties
  setElementProps(element, props, elementId) {
    if (!props) return;

    for (const [key, value] of Object.entries(props)) {
      this.setElementProp(element, key, value, elementId);
    }
  }

  setElementProp(element, key, value, elementId) {
    if (key === 'children' || key === 'key' || key === 'ref') {
      return;
    }

    if (value && typeof value === 'object' && value.type === 'signal') {
      // Signal value - set up reactive binding
      this.setReactiveProp(element, key, value.value, elementId);
    } else if (value && typeof value === 'object' && value.type === 'event_handler') {
      // Event handler
      this.setEventHandler(element, key, value, elementId);
    } else {
      // Static value
      this.setStaticProp(element, key, value);
    }
  }

  setReactiveProp(element, key, signal, elementId) {
    // Set initial value
    const initialValue = unwrap(signal);
    this.setStaticProp(element, key, initialValue);

    // Subscribe to signal changes
    const unsubscribe = signal.subscribe(() => {
      const newValue = unwrap(signal);
      this.setStaticProp(element, key, newValue);
    });

    // Store cleanup function
    if (!this.eventListeners.has(elementId)) {
      this.eventListeners.set(elementId, new Set());
    }
    this.eventListeners.get(elementId).add(unsubscribe);
  }

  setEventHandler(element, key, eventHandler, elementId) {
    const eventName = key.slice(2).toLowerCase(); // Remove 'on' prefix
    const handler = eventHandler.wrapped;

    element.addEventListener(eventName, handler);

    // Store cleanup function
    if (!this.eventListeners.has(elementId)) {
      this.eventListeners.set(elementId, new Set());
    }
    this.eventListeners.get(elementId).add(() => {
      element.removeEventListener(eventName, handler);
    });
  }

  setStaticProp(element, key, value) {
    if (key === 'className') {
      element.className = value || '';
    } else if (key === 'style' && typeof value === 'object') {
      Object.assign(element.style, value);
    } else if (key === 'value' && ['input', 'textarea', 'select'].includes(element.tagName.toLowerCase())) {
      element.value = value || '';
    } else if (key === 'checked' && ['input'].includes(element.tagName.toLowerCase())) {
      element.checked = value || false;
    } else if (key === 'selected' && ['option'].includes(element.tagName.toLowerCase())) {
      element.selected = value || false;
    } else if (key === 'disabled') {
      element.disabled = value || false;
    } else if (key === 'innerHTML') {
      element.innerHTML = value || '';
    } else if (key === 'textContent') {
      element.textContent = value || '';
    } else {
      element.setAttribute(key, value || '');
    }
  }

  // Cleanup
  cleanup() {
    // Clean up all event listeners
    this.eventListeners.forEach(listeners => {
      listeners.forEach(cleanup => cleanup());
    });

    this.eventListeners.clear();
    this.nodeCache.clear();
    this.staticNodes.clear();
  }
}

// Global renderer instance
let globalRenderer = null;

export const getRenderer = (container) => {
  if (!globalRenderer) {
    globalRenderer = new ModernRenderer(container);
  }
  return globalRenderer;
};

// Utility functions
export const render = (jsxElement, container) => {
  const renderer = new ModernRenderer(container);
  return renderer.render(jsxElement);
};

export const createRenderer = (container) => {
  return new ModernRenderer(container);
};

// Development helpers
export const rendererDevTools = {
  getNodeCache: () => domNodeCache,
  getStaticNodes: () => globalRenderer?.staticNodes || new Map(),
  getEventListeners: () => globalRenderer?.eventListeners || new Map(),
  inspectElement: (elementId) => {
    const node = domNodeCache.get(elementId);
    const listeners = globalRenderer?.eventListeners.get(elementId);

    console.log('Element info:', {
      id: elementId,
      node,
      listeners: listeners?.size || 0
    });
  }
};

// Export everything
export default {
  ModernRenderer,
  DOMNodeCache,
  domNodeCache,
  rendererConfig,
  getRenderer,
  render,
  createRenderer,
  rendererDevTools
};
