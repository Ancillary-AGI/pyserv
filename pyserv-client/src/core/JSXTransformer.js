/**
 * JSX Transformer - Runtime JSX Syntax Support
 * Transforms JSX syntax into framework-compatible objects at runtime
 */

// JSX Runtime for handling JSX syntax
export class JSXRuntime {
  constructor() {
    this.elements = new Map();
    this.elementId = 0;
  }

  // Create JSX element from syntax
  createElement(tagName, props, ...children) {
    const element = {
      $$typeof: Symbol.for('pyserv.element'),
      tagName: tagName,
      props: props || {},
      children: children.flat(),
      key: props?.key || null,
      ref: props?.ref || null,
      _id: `element_${this.elementId++}`
    };

    // Handle children in props
    if (props && props.children) {
      element.children = [props.children].flat();
      delete props.children;
    }

    // Store element for debugging
    this.elements.set(element._id, element);

    return element;
  }

  // Create fragment
  createFragment(props, ...children) {
    return {
      $$typeof: Symbol.for('pyserv.fragment'),
      children: children.flat(),
      props: props || {},
      key: props?.key || null,
      _id: `fragment_${this.elementId++}`
    };
  }

  // Clone element
  cloneElement(element, props, ...children) {
    return {
      ...element,
      props: { ...element.props, ...props },
      children: children.length > 0 ? children.flat() : element.children,
      _id: `cloned_${this.elementId++}`
    };
  }

  // Check if value is JSX element
  isElement(value) {
    return value && typeof value === 'object' && value.$$typeof === Symbol.for('pyserv.element');
  }

  // Check if value is fragment
  isFragment(value) {
    return value && typeof value === 'object' && value.$$typeof === Symbol.for('pyserv.fragment');
  }

  // Get element by ID
  getElement(id) {
    return this.elements.get(id);
  }

  // Clear stored elements
  clear() {
    this.elements.clear();
    this.elementId = 0;
  }
}

// Global JSX runtime instance
export const jsxRuntime = new JSXRuntime();

// JSX Functions for global use
export function createElement(tagName, props, ...children) {
  return jsxRuntime.createElement(tagName, props, ...children);
}

export function createFragment(props, ...children) {
  return jsxRuntime.createFragment(props, ...children);
}

export function cloneElement(element, props, ...children) {
  return jsxRuntime.cloneElement(element, props, ...children);
}

// JSX Syntax Parser
export class JSXParser {
  constructor() {
    this.runtime = jsxRuntime;
  }

  // Parse JSX-like string into element
  parse(jsxString) {
    // This is a simplified parser for demonstration
    // In a real implementation, you'd use a proper JSX parser

    const cleanString = jsxString.trim();

    // Handle fragments
    if (cleanString.startsWith('<>') && cleanString.endsWith('</>')) {
      const content = cleanString.slice(2, -3).trim();
      return this.runtime.createFragment({}, this.parseContent(content));
    }

    // Handle regular elements
    const match = cleanString.match(/^<([a-zA-Z][a-zA-Z0-9]*)([^>]*)>(.*)<\/\1>$/);
    if (match) {
      const [, tagName, attributes, content] = match;
      const props = this.parseAttributes(attributes);
      const children = this.parseContent(content);

      return this.runtime.createElement(tagName, props, ...children);
    }

    // Return as text if no match
    return cleanString;
  }

  parseAttributes(attrString) {
    const props = {};

    if (!attrString.trim()) return props;

    // Simple attribute parsing
    const attrMatch = attrString.match(/([a-zA-Z][a-zA-Z0-9-]*)\s*=\s*["']([^"']+)["']/g);
    if (attrMatch) {
      attrMatch.forEach(match => {
        const [, key, value] = match.match(/([a-zA-Z][a-zA-Z0-9-]*)\s*=\s*["']([^"']+)["']/);
        props[key] = value;
      });
    }

    return props;
  }

  parseContent(content) {
    if (!content.trim()) return [];

    // Split by JSX elements
    const parts = content.split(/(<[^>]+>)/);
    const children = [];

    for (const part of parts) {
      if (part.trim()) {
        if (part.startsWith('<')) {
          // Nested element
          children.push(this.parse(part));
        } else {
          // Text content
          children.push(part.trim());
        }
      }
    }

    return children;
  }
}

// JSX Transformer for runtime transformation
export class JSXTransformer {
  constructor() {
    this.parser = new JSXParser();
    this.runtime = jsxRuntime;
  }

  // Transform JSX syntax to framework elements
  transform(jsxCode) {
    try {
      // If it's already a framework element, return as-is
      if (this.runtime.isElement(jsxCode) || this.runtime.isFragment(jsxCode)) {
        return jsxCode;
      }

      // If it's a string, try to parse as JSX
      if (typeof jsxCode === 'string') {
        return this.parser.parse(jsxCode);
      }

      // If it's a function returning JSX, call it
      if (typeof jsxCode === 'function') {
        return this.transform(jsxCode());
      }

      // Return as-is for other types
      return jsxCode;
    } catch (error) {
      console.error('JSX transformation error:', error);
      return jsxCode;
    }
  }

  // Transform component render output
  transformRender(renderResult) {
    return this.transform(renderResult);
  }

  // Batch transform multiple elements
  transformBatch(elements) {
    return elements.map(element => this.transform(element));
  }
}

// Global JSX transformer
export const jsxTransformer = new JSXTransformer();

// Setup global JSX functions
if (typeof window !== 'undefined') {
  // Make JSX functions globally available
  window.createElement = createElement;
  window.createFragment = createFragment;
  window.cloneElement = cloneElement;

  // Store runtime globally
  window.jsxRuntime = jsxRuntime;
  window.jsxTransformer = jsxTransformer;
}

// Export everything
export default jsxRuntime;
