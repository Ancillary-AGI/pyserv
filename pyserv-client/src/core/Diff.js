/**
 * Diff - Virtual DOM Diffing Algorithm
 * Provides efficient DOM updates by comparing virtual DOM trees
 * and applying minimal patches to the real DOM
 */

// Virtual DOM node structure
export class VNode {
  constructor(tagName, props = {}, children = [], key = null) {
    this.tagName = tagName;
    this.props = props;
    this.children = children;
    this.key = key;
    this.element = null;
    this.component = null;
  }

  static createElement(tagName, props, ...children) {
    return new VNode(tagName, props, children.flat());
  }
}

// Patch types
export const PATCH_TYPES = {
  CREATE: 'CREATE',
  REMOVE: 'REMOVE',
  REPLACE: 'REPLACE',
  UPDATE: 'UPDATE',
  REORDER: 'REORDER',
  MOVE: 'MOVE',
  TEXT: 'TEXT'
};

// Main diffing function
export function diff(oldVNode, newVNode) {
  if (!oldVNode && !newVNode) return [];
  if (!oldVNode) return [{ type: PATCH_TYPES.CREATE, newVNode }];
  if (!newVNode) return [{ type: PATCH_TYPES.REMOVE, oldVNode }];

  // Same VNode type
  if (oldVNode.tagName === newVNode.tagName) {
    const propsPatches = diffProps(oldVNode.props, newVNode.props);
    const childrenPatches = diffChildren(oldVNode.children, newVNode.children);

    if (propsPatches.length > 0 || childrenPatches.length > 0) {
      return [{
        type: PATCH_TYPES.UPDATE,
        oldVNode,
        newVNode,
        propsPatches,
        childrenPatches
      }];
    }

    return [];
  }

  // Different VNode types
  return [{
    type: PATCH_TYPES.REPLACE,
    oldVNode,
    newVNode
  }];
}

// Diff properties
function diffProps(oldProps, newProps) {
  const patches = [];
  const allKeys = new Set([...Object.keys(oldProps), ...Object.keys(newProps)]);

  for (const key of allKeys) {
    const oldValue = oldProps[key];
    const newValue = newProps[key];

    if (oldValue !== newValue) {
      if (newValue === undefined) {
        patches.push({ type: 'REMOVE_PROP', key });
      } else if (oldValue === undefined) {
        patches.push({ type: 'ADD_PROP', key, value: newValue });
      } else {
        patches.push({ type: 'UPDATE_PROP', key, value: newValue });
      }
    }
  }

  return patches;
}

// Diff children
function diffChildren(oldChildren, newChildren) {
  const patches = [];
  const oldChildrenMap = createKeyMap(oldChildren);
  const newChildrenMap = createKeyMap(newChildren);

  // Find removals and updates
  for (const oldChild of oldChildren) {
    const key = oldChild.key;
    const newChild = newChildrenMap.get(key);

    if (!newChild) {
      patches.push({ type: PATCH_TYPES.REMOVE, oldVNode: oldChild });
    } else {
      const childPatches = diff(oldChild, newChild);
      if (childPatches.length > 0) {
        patches.push(...childPatches);
      }
    }
  }

  // Find additions
  for (const newChild of newChildren) {
    const key = newChild.key;
    const oldChild = oldChildrenMap.get(key);

    if (!oldChild) {
      patches.push({ type: PATCH_TYPES.CREATE, newVNode: newChild });
    }
  }

  // Handle reordering
  const moves = calculateMoves(oldChildren, newChildren);
  if (moves.length > 0) {
    patches.push({ type: PATCH_TYPES.REORDER, moves });
  }

  return patches;
}

// Create key map for efficient lookup
function createKeyMap(children) {
  const map = new Map();
  for (const child of children) {
    if (child.key !== null) {
      map.set(child.key, child);
    }
  }
  return map;
}

// Calculate optimal moves for reordering
function calculateMoves(oldChildren, newChildren) {
  const moves = [];
  const oldKeys = oldChildren.map(child => child.key);
  const newKeys = newChildren.map(child => child.key);

  // Simple implementation - could be optimized with more sophisticated algorithms
  for (let i = 0; i < newChildren.length; i++) {
    const newChild = newChildren[i];
    const oldIndex = oldKeys.indexOf(newChild.key);

    if (oldIndex !== -1 && oldIndex !== i) {
      moves.push({
        from: oldIndex,
        to: i,
        vnode: newChild
      });
    }
  }

  return moves;
}

// Apply patches to the DOM
export function patch(parentElement, patches) {
  const timer = performanceMonitor.startTimer('patch');

  for (const patch of patches) {
    switch (patch.type) {
      case PATCH_TYPES.CREATE:
        applyCreatePatch(parentElement, patch.newVNode);
        break;
      case PATCH_TYPES.REMOVE:
        applyRemovePatch(parentElement, patch.oldVNode);
        break;
      case PATCH_TYPES.REPLACE:
        applyReplacePatch(parentElement, patch.oldVNode, patch.newVNode);
        break;
      case PATCH_TYPES.UPDATE:
        applyUpdatePatch(patch.oldVNode, patch.newVNode, patch.propsPatches, patch.childrenPatches);
        break;
      case PATCH_TYPES.REORDER:
        applyReorderPatch(parentElement, patch.moves);
        break;
      case PATCH_TYPES.MOVE:
        applyMovePatch(parentElement, patch.vnode, patch.from, patch.to);
        break;
      case PATCH_TYPES.TEXT:
        applyTextPatch(patch.oldVNode, patch.newVNode);
        break;
    }
  }

  timer();
}

// Patch application functions
function applyCreatePatch(parentElement, vnode) {
  const element = createElementFromVNode(vnode);
  parentElement.appendChild(element);
  vnode.element = element;
}

function applyRemovePatch(parentElement, vnode) {
  const element = vnode.element;
  if (element && element.parentNode === parentElement) {
    parentElement.removeChild(element);
  }
}

function applyReplacePatch(parentElement, oldVNode, newVNode) {
  const oldElement = oldVNode.element;
  const newElement = createElementFromVNode(newVNode);

  if (oldElement && oldElement.parentNode === parentElement) {
    parentElement.replaceChild(newElement, oldElement);
    newVNode.element = newElement;
  }
}

function applyUpdatePatch(oldVNode, newVNode, propsPatches, childrenPatches) {
  const element = oldVNode.element;

  // Apply property patches
  for (const patch of propsPatches) {
    switch (patch.type) {
      case 'ADD_PROP':
      case 'UPDATE_PROP':
        updateElementProp(element, patch.key, patch.value);
        break;
      case 'REMOVE_PROP':
        removeElementProp(element, patch.key);
        break;
    }
  }

  // Apply children patches
  if (childrenPatches.length > 0) {
    patch(element, childrenPatches);
  }
}

function applyReorderPatch(parentElement, moves) {
  const elements = Array.from(parentElement.children);

  // Simple reordering - could be optimized
  for (const move of moves) {
    const element = elements[move.from];
    if (element) {
      parentElement.removeChild(element);
      parentElement.insertBefore(element, elements[move.to] || null);
    }
  }
}

function applyMovePatch(parentElement, vnode, from, to) {
  const element = vnode.element;
  if (element && element.parentNode === parentElement) {
    parentElement.removeChild(element);
    const referenceElement = parentElement.children[to];
    parentElement.insertBefore(element, referenceElement || null);
  }
}

function applyTextPatch(oldVNode, newVNode) {
  const element = oldVNode.element;
  if (element && element.nodeType === Node.TEXT_NODE) {
    element.textContent = newVNode;
  }
}

// Helper functions
function createElementFromVNode(vnode) {
  const element = document.createElement(vnode.tagName);

  // Set properties
  for (const [key, value] of Object.entries(vnode.props)) {
    updateElementProp(element, key, value);
  }

  // Create children
  for (const child of vnode.children) {
    if (typeof child === 'string') {
      element.appendChild(document.createTextNode(child));
    } else {
      const childElement = createElementFromVNode(child);
      element.appendChild(childElement);
      child.element = childElement;
    }
  }

  return element;
}

function updateElementProp(element, key, value) {
  if (key === 'className') {
    element.className = value;
  } else if (key === 'style' && typeof value === 'object') {
    Object.assign(element.style, value);
  } else if (key.startsWith('on') && typeof value === 'function') {
    const eventName = key.slice(2).toLowerCase();
    element.addEventListener(eventName, value);
  } else {
    element.setAttribute(key, value);
  }
}

function removeElementProp(element, key) {
  if (key === 'className') {
    element.className = '';
  } else if (key === 'style') {
    element.style.cssText = '';
  } else if (key.startsWith('on')) {
    const eventName = key.slice(2).toLowerCase();
    element.removeEventListener(eventName, element[`_${key}`]);
    delete element[`_${key}`];
  } else {
    element.removeAttribute(key);
  }
}

// Utility functions for components
export function renderToVNode(component) {
  const html = component.render();
  return parseHTMLToVNode(html);
}

function parseHTMLToVNode(html) {
  const template = document.createElement('template');
  template.innerHTML = html;
  return elementToVNode(template.content.firstChild);
}

function elementToVNode(element) {
  if (!element) return null;

  if (element.nodeType === Node.TEXT_NODE) {
    return element.textContent;
  }

  const tagName = element.tagName.toLowerCase();
  const props = {};

  // Copy attributes
  for (const attr of element.attributes) {
    props[attr.name] = attr.value;
  }

  // Copy children
  const children = [];
  for (const child of element.childNodes) {
    children.push(elementToVNode(child));
  }

  return new VNode(tagName, props, children);
}

// Performance optimizations
export class VNodeCache {
  constructor() {
    this.cache = new Map();
  }

  get(key) {
    return this.cache.get(key);
  }

  set(key, vnode) {
    this.cache.set(key, vnode);
  }

  clear() {
    this.cache.clear();
  }

  has(key) {
    return this.cache.has(key);
  }
}

// Advanced diffing algorithms
export class AdvancedDiffer {
  constructor(options = {}) {
    this.options = {
      enableKeyOptimization: options.enableKeyOptimization !== false,
      enableListOptimization: options.enableListOptimization !== false,
      enableTextOptimization: options.enableTextOptimization !== false,
      enableMoveDetection: options.enableMoveDetection !== false,
      ...options
    };
  }

  // Advanced diffing with optimizations
  diffAdvanced(oldVNode, newVNode) {
    if (!oldVNode && !newVNode) return [];
    if (!oldVNode) return [{ type: PATCH_TYPES.CREATE, newVNode }];
    if (!newVNode) return [{ type: PATCH_TYPES.REMOVE, oldVNode }];

    // Same VNode type - use advanced comparison
    if (oldVNode.tagName === newVNode.tagName) {
      return this.diffSameType(oldVNode, newVNode);
    }

    // Different VNode types
    return [{
      type: PATCH_TYPES.REPLACE,
      oldVNode,
      newVNode
    }];
  }

  diffSameType(oldVNode, newVNode) {
    const patches = [];

    // Check if nodes are identical (fast path)
    if (this.isIdenticalVNode(oldVNode, newVNode)) {
      return patches;
    }

    // Diff properties
    const propsPatches = this.diffPropsAdvanced(oldVNode.props, newVNode.props);
    if (propsPatches.length > 0) {
      patches.push(...propsPatches);
    }

    // Diff children with optimizations
    const childrenPatches = this.diffChildrenAdvanced(oldVNode.children, newVNode.children);
    if (childrenPatches.length > 0) {
      patches.push(...childrenPatches);
    }

    return patches.length > 0 ? [{
      type: PATCH_TYPES.UPDATE,
      oldVNode,
      newVNode,
      patches
    }] : [];
  }

  isIdenticalVNode(vnode1, vnode2) {
    return vnode1.tagName === vnode2.tagName &&
           JSON.stringify(vnode1.props) === JSON.stringify(vnode2.props) &&
           this.childrenAreIdentical(vnode1.children, vnode2.children);
  }

  childrenAreIdentical(children1, children2) {
    if (children1.length !== children2.length) return false;

    for (let i = 0; i < children1.length; i++) {
      const child1 = children1[i];
      const child2 = children2[i];

      if (typeof child1 === 'string' && typeof child2 === 'string') {
        if (child1 !== child2) return false;
      } else if (typeof child1 === 'object' && typeof child2 === 'object') {
        if (!this.isIdenticalVNode(child1, child2)) return false;
      } else {
        return false;
      }
    }

    return true;
  }

  diffPropsAdvanced(oldProps, newProps) {
    const patches = [];
    const allKeys = new Set([...Object.keys(oldProps), ...Object.keys(newProps)]);

    for (const key of allKeys) {
      const oldValue = oldProps[key];
      const newValue = newProps[key];

      if (oldValue !== newValue) {
        if (newValue === undefined) {
          patches.push({ type: 'REMOVE_PROP', key });
        } else if (oldValue === undefined) {
          patches.push({ type: 'ADD_PROP', key, value: newValue });
        } else {
          patches.push({ type: 'UPDATE_PROP', key, value: newValue });
        }
      }
    }

    return patches;
  }

  diffChildrenAdvanced(oldChildren, newChildren) {
    const patches = [];

    // Fast path for identical children
    if (this.childrenAreIdentical(oldChildren, newChildren)) {
      return patches;
    }

    // Use key-based optimization if enabled
    if (this.options.enableKeyOptimization) {
      return this.diffChildrenWithKeys(oldChildren, newChildren);
    }

    // Use list optimization if enabled
    if (this.options.enableListOptimization) {
      return this.diffChildrenAsList(oldChildren, newChildren);
    }

    // Fallback to simple diffing
    return this.diffChildrenSimple(oldChildren, newChildren);
  }

  diffChildrenWithKeys(oldChildren, newChildren) {
    const patches = [];
    const oldMap = new Map();
    const newMap = new Map();

    // Create key maps
    oldChildren.forEach((child, index) => {
      if (child.key !== null && child.key !== undefined) {
        oldMap.set(child.key, { child, index });
      }
    });

    newChildren.forEach((child, index) => {
      if (child.key !== null && child.key !== undefined) {
        newMap.set(child.key, { child, index });
      }
    });

    // Find removals
    oldMap.forEach((oldItem, key) => {
      if (!newMap.has(key)) {
        patches.push({ type: PATCH_TYPES.REMOVE, oldVNode: oldItem.child });
      }
    });

    // Find additions and updates
    newMap.forEach((newItem, key) => {
      const oldItem = oldMap.get(key);

      if (!oldItem) {
        patches.push({ type: PATCH_TYPES.CREATE, newVNode: newItem.child });
      } else {
        const childPatches = this.diffAdvanced(oldItem.child, newItem.child);
        if (childPatches.length > 0) {
          patches.push(...childPatches);
        }

        // Check for moves
        if (this.options.enableMoveDetection && oldItem.index !== newItem.index) {
          patches.push({
            type: PATCH_TYPES.MOVE,
            vnode: newItem.child,
            from: oldItem.index,
            to: newItem.index
          });
        }
      }
    });

    return patches;
  }

  diffChildrenAsList(oldChildren, newChildren) {
    const patches = [];

    // Use longest common subsequence algorithm for list diffing
    const lcs = this.longestCommonSubsequence(oldChildren, newChildren);

    let oldIndex = 0;
    let newIndex = 0;

    for (const item of lcs) {
      // Remove items that are not in LCS
      while (oldIndex < oldChildren.length && oldChildren[oldIndex] !== item) {
        patches.push({ type: PATCH_TYPES.REMOVE, oldVNode: oldChildren[oldIndex] });
        oldIndex++;
      }

      // Add items that are not in LCS
      while (newIndex < newChildren.length && newChildren[newIndex] !== item) {
        patches.push({ type: PATCH_TYPES.CREATE, newVNode: newChildren[newIndex] });
        newIndex++;
      }

      // Move to next item in LCS
      oldIndex++;
      newIndex++;
    }

    // Remove remaining old items
    while (oldIndex < oldChildren.length) {
      patches.push({ type: PATCH_TYPES.REMOVE, oldVNode: oldChildren[oldIndex] });
      oldIndex++;
    }

    // Add remaining new items
    while (newIndex < newChildren.length) {
      patches.push({ type: PATCH_TYPES.CREATE, newVNode: newChildren[newIndex] });
      newIndex++;
    }

    return patches;
  }

  diffChildrenSimple(oldChildren, newChildren) {
    const patches = [];
    const maxLength = Math.max(oldChildren.length, newChildren.length);

    for (let i = 0; i < maxLength; i++) {
      const oldChild = oldChildren[i];
      const newChild = newChildren[i];

      if (!oldChild && newChild) {
        patches.push({ type: PATCH_TYPES.CREATE, newVNode: newChild });
      } else if (oldChild && !newChild) {
        patches.push({ type: PATCH_TYPES.REMOVE, oldVNode: oldChild });
      } else if (oldChild && newChild) {
        const childPatches = this.diffAdvanced(oldChild, newChild);
        patches.push(...childPatches);
      }
    }

    return patches;
  }

  longestCommonSubsequence(oldChildren, newChildren) {
    const oldLength = oldChildren.length;
    const newLength = newChildren.length;
    const matrix = Array(oldLength + 1).fill().map(() => Array(newLength + 1).fill(0));

    for (let i = 1; i <= oldLength; i++) {
      for (let j = 1; j <= newLength; j++) {
        if (this.isIdenticalVNode(oldChildren[i - 1], newChildren[j - 1])) {
          matrix[i][j] = matrix[i - 1][j - 1] + 1;
        } else {
          matrix[i][j] = Math.max(matrix[i - 1][j], matrix[i][j - 1]);
        }
      }
    }

    // Backtrack to find LCS
    const lcs = [];
    let i = oldLength;
    let j = newLength;

    while (i > 0 && j > 0) {
      if (this.isIdenticalVNode(oldChildren[i - 1], newChildren[j - 1])) {
        lcs.unshift(oldChildren[i - 1]);
        i--;
        j--;
      } else if (matrix[i - 1][j] > matrix[i][j - 1]) {
        i--;
      } else {
        j--;
      }
    }

    return lcs;
  }
}

// Performance monitoring
export class PerformanceMonitor {
  constructor() {
    this.metrics = {
      diffTime: 0,
      patchTime: 0,
      renderTime: 0,
      totalTime: 0,
      diffCount: 0,
      patchCount: 0,
      renderCount: 0
    };
    this.enabled = false;
  }

  startTimer(name) {
    if (!this.enabled) return () => {};
    this.metrics[`${name}Start`] = performance.now();
    return () => {
      const end = performance.now();
      const duration = end - this.metrics[`${name}Start`];
      this.metrics[`${name}Time`] += duration;
      this.metrics[`${name}Count`]++;
    };
  }

  enable() {
    this.enabled = true;
  }

  disable() {
    this.enabled = false;
  }

  reset() {
    this.metrics = {
      diffTime: 0,
      patchTime: 0,
      renderTime: 0,
      totalTime: 0,
      diffCount: 0,
      patchCount: 0,
      renderCount: 0
    };
  }

  getMetrics() {
    return { ...this.metrics };
  }

  getAverageTime(operation) {
    const time = this.metrics[`${operation}Time`];
    const count = this.metrics[`${operation}Count`];
    return count > 0 ? time / count : 0;
  }
}

export const performanceMonitor = new PerformanceMonitor();

// Memory management
export class MemoryManager {
  constructor() {
    this.cleanupTasks = new Set();
    this.vNodePool = new Map();
    this.elementPool = new Set();
  }

  // Pool VNodes for reuse
  getVNode(tagName, props, children, key) {
    const poolKey = `${tagName}_${key || 'default'}`;
    const pool = this.vNodePool.get(poolKey) || [];

    if (pool.length > 0) {
      const vnode = pool.pop();
      vnode.props = props;
      vnode.children = children;
      vnode.key = key;
      return vnode;
    }

    return new VNode(tagName, props, children, key);
  }

  releaseVNode(vnode) {
    if (vnode) {
      vnode.props = {};
      vnode.children = [];
      vnode.element = null;
      vnode.component = null;

      const poolKey = `${vnode.tagName}_${vnode.key || 'default'}`;
      const pool = this.vNodePool.get(poolKey) || [];
      pool.push(vnode);
      this.vNodePool.set(poolKey, pool);
    }
  }

  // Clean up unused resources
  cleanup() {
    // Clear VNode pools
    this.vNodePool.clear();

    // Clear element pool
    this.elementPool.clear();

    // Run cleanup tasks
    this.cleanupTasks.forEach(task => {
      if (typeof task === 'function') {
        task();
      }
    });

    this.cleanupTasks.clear();
  }

  addCleanupTask(task) {
    this.cleanupTasks.add(task);
  }

  removeCleanupTask(task) {
    this.cleanupTasks.delete(task);
  }
}

export const memoryManager = new MemoryManager();

// Memoization for expensive computations
export function memoize(fn) {
  const cache = new Map();

  return function(...args) {
    const key = JSON.stringify(args);
    if (cache.has(key)) {
      return cache.get(key);
    }

    const result = fn.apply(this, args);
    cache.set(key, result);
    return result;
  };
}

// Batch DOM updates for performance
export class DOMBatcher {
  constructor() {
    this.pendingUpdates = [];
    this.isScheduled = false;
  }

  schedule(update) {
    this.pendingUpdates.push(update);

    if (!this.isScheduled) {
      this.isScheduled = true;
      requestAnimationFrame(() => this.flush());
    }
  }

  flush() {
    const updates = this.pendingUpdates.splice(0);
    updates.forEach(update => update());
    this.isScheduled = false;
  }
}

export const domBatcher = new DOMBatcher();

// Hook for debugging
export function enableDiffingDebug() {
  const originalDiff = diff;
  const originalPatch = patch;

  diff = function(oldVNode, newVNode) {
    console.log('Diffing:', oldVNode, newVNode);
    const patches = originalDiff(oldVNode, newVNode);
    console.log('Patches:', patches);
    return patches;
  };

  patch = function(parentElement, patches) {
    console.log('Applying patches:', patches);
    return originalPatch(parentElement, patches);
  };
}
