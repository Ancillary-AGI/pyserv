/**
 * Reactive - Reactive State Management System
 * Provides reactive primitives similar to Vue Composition API
 * with dependency tracking and automatic re-rendering
 */

export class Reactive {
  constructor(initialValue) {
    this._value = initialValue;
    this._subscribers = new Set();
    this._isReactive = true;

    // Create proxy for reactivity
    return this._createProxy();
  }

  _createProxy() {
    const self = this;

    return new Proxy(this, {
      get(target, prop) {
        // Track dependency for computed values
        if (Reactive._currentSubscriber) {
          target._subscribers.add(Reactive._currentSubscriber);
        }

        if (prop === '_isReactive') return true;
        if (prop === '_value') return target._value;
        if (prop === '_subscribers') return target._subscribers;

        const value = target._value[prop];
        if (value && typeof value === 'object' && !value._isReactive) {
          // Make nested objects reactive
          return Reactive.makeReactive(value);
        }

        return value;
      },

      set(target, prop, value) {
        if (target._value[prop] !== value) {
          target._value[prop] = value;
          target._notifySubscribers();
        }
        return true;
      }
    });
  }

  _notifySubscribers() {
    this._subscribers.forEach(subscriber => {
      if (typeof subscriber === 'function') {
        subscriber();
      }
    });
  }

  static makeReactive(obj) {
    if (obj && typeof obj === 'object' && !obj._isReactive) {
      if (Array.isArray(obj)) {
        return new ReactiveArray(obj);
      }
      return new Reactive(obj);
    }
    return obj;
  }

  static isReactive(obj) {
    return obj && obj._isReactive === true;
  }

  valueOf() {
    return this._value;
  }

  toString() {
    return String(this._value);
  }
}

export class ReactiveArray extends Reactive {
  constructor(initialArray) {
    super(initialArray);
  }

  _createProxy() {
    const self = this;

    return new Proxy(this, {
      get(target, prop) {
        if (Reactive._currentSubscriber) {
          target._subscribers.add(Reactive._currentSubscriber);
        }

        if (prop === 'push') {
          return (...items) => {
            const result = target._value.push(...items);
            target._notifySubscribers();
            return result;
          };
        }

        if (prop === 'pop') {
          return () => {
            const result = target._value.pop();
            target._notifySubscribers();
            return result;
          };
        }

        if (prop === 'splice') {
          return (start, deleteCount, ...items) => {
            const result = target._value.splice(start, deleteCount, ...items);
            target._notifySubscribers();
            return result;
          };
        }

        if (prop === 'shift') {
          return () => {
            const result = target._value.shift();
            target._notifySubscribers();
            return result;
          };
        }

        if (prop === 'unshift') {
          return (...items) => {
            const result = target._value.unshift(...items);
            target._notifySubscribers();
            return result;
          };
        }

        return target._value[prop];
      },

      set(target, prop, value) {
        target._value[prop] = value;
        target._notifySubscribers();
        return true;
      }
    });
  }
}

// Computed values
export class Computed {
  constructor(computeFn) {
    this._computeFn = computeFn;
    this._value = undefined;
    this._subscribers = new Set();
    this._dependencies = new Set();
    this._isComputed = true;

    this._updateValue();
    return this._createProxy();
  }

  _createProxy() {
    const self = this;

    return new Proxy(this, {
      get(target, prop) {
        if (prop === '_isComputed') return true;
        if (prop === '_value') return target._value;
        if (prop === '_subscribers') return target._subscribers;

        return target._value;
      }
    });
  }

  _updateValue() {
    // Track dependencies
    const prevSubscriber = Reactive._currentSubscriber;
    Reactive._currentSubscriber = this;

    try {
      this._value = this._computeFn();
    } finally {
      Reactive._currentSubscriber = prevSubscriber;
    }
  }

  _notifySubscribers() {
    this._subscribers.forEach(subscriber => {
      if (typeof subscriber === 'function') {
        subscriber();
      }
    });
  }

  static isComputed(obj) {
    return obj && obj._isComputed === true;
  }
}

// Effect system
export class Effect {
  constructor(effectFn, options = {}) {
    this._effectFn = effectFn;
    this._cleanupFn = null;
    this._isEffect = true;

    if (!options.lazy) {
      this.run();
    }
  }

  run() {
    // Clean up previous effect
    if (this._cleanupFn && typeof this._cleanupFn === 'function') {
      this._cleanupFn();
    }

    // Track dependencies
    const prevSubscriber = Reactive._currentSubscriber;
    Reactive._currentSubscriber = this;

    try {
      this._cleanupFn = this._effectFn();
    } finally {
      Reactive._currentSubscriber = prevSubscriber;
    }
  }

  stop() {
    if (this._cleanupFn && typeof this._cleanupFn === 'function') {
      this._cleanupFn();
    }
  }
}

// Ref system (similar to Vue refs)
export class Ref {
  constructor(initialValue) {
    this._value = initialValue;
    this._subscribers = new Set();
    this._isRef = true;

    return this._createProxy();
  }

  _createProxy() {
    const self = this;

    return new Proxy(this, {
      get(target, prop) {
        if (prop === '_isRef') return true;
        if (prop === '_value') return target._value;
        if (prop === '_subscribers') return target._subscribers;

        if (prop === 'value') {
          // Track dependency
          if (Reactive._currentSubscriber) {
            target._subscribers.add(Reactive._currentSubscriber);
          }
          return target._value;
        }

        return target._value;
      },

      set(target, prop, value) {
        if (prop === 'value') {
          if (target._value !== value) {
            target._value = value;
            target._notifySubscribers();
          }
          return true;
        }
        return true;
      }
    });
  }

  _notifySubscribers() {
    this._subscribers.forEach(subscriber => {
      if (typeof subscriber === 'function') {
        subscriber();
      }
    });
  }

  static isRef(obj) {
    return obj && obj._isRef === true;
  }

  static create(initialValue) {
    return new Ref(initialValue);
  }
}

// Watch system
export class Watch {
  constructor(source, callback, options = {}) {
    this._source = source;
    this._callback = callback;
    this._options = options;
    this._oldValue = undefined;
    this._isWatch = true;

    this._run();
  }

  _run() {
    let newValue;

    if (typeof this._source === 'function') {
      newValue = this._source();
    } else if (Ref.isRef(this._source)) {
      newValue = this._source.value;
    } else if (Reactive.isReactive(this._source)) {
      newValue = this._source._value;
    } else {
      newValue = this._source;
    }

    if (this._options.deep) {
      newValue = JSON.parse(JSON.stringify(newValue));
      this._oldValue = JSON.parse(JSON.stringify(this._oldValue));
    }

    if (!this._options.immediate && this._oldValue === undefined) {
      this._oldValue = newValue;
      return;
    }

    if (this._oldValue !== newValue) {
      const oldValue = this._oldValue;
      this._oldValue = newValue;
      this._callback(newValue, oldValue);
    }
  }

  static watch(source, callback, options = {}) {
    return new Watch(source, callback, options);
  }
}

// Global reactive state
export const reactive = (obj) => Reactive.makeReactive(obj);
export const ref = (initialValue) => Ref.create(initialValue);
export const computed = (computeFn) => new Computed(computeFn);
export const effect = (effectFn) => new Effect(effectFn);
export const watch = (source, callback, options) => Watch.watch(source, callback, options);

// Utility functions
export const unref = (ref) => {
  return Ref.isRef(ref) ? ref.value : ref;
};

export const toRef = (object, key) => {
  return ref(object[key]);
};

export const toRefs = (object) => {
  const refs = {};
  for (const key in object) {
    refs[key] = ref(object[key]);
  }
  return refs;
};

export const isRef = (obj) => Ref.isRef(obj);
export const isReactive = (obj) => Reactive.isReactive(obj);
export const isComputed = (obj) => Computed.isComputed(obj);

// Batch updates for performance
let isBatching = false;
const batchedEffects = new Set();

export const nextTick = (fn) => {
  Promise.resolve().then(fn);
};

export const batch = (fn) => {
  if (isBatching) {
    return fn();
  }

  isBatching = true;
  try {
    return fn();
  } finally {
    isBatching = false;
    // Run batched effects
    batchedEffects.forEach(effect => effect.run());
    batchedEffects.clear();
  }
};

// Reactive utilities for components
export const useReactive = (initialValue) => {
  return reactive(initialValue);
};

export const useRef = (initialValue) => {
  return ref(initialValue);
};

export const useComputed = (computeFn) => {
  return computed(computeFn);
};

export const useWatch = (source, callback, options) => {
  return watch(source, callback, options);
};

export const useEffect = (effectFn) => {
  return effect(effectFn);
};
