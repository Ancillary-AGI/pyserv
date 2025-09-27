/**
 * Signal - Core Reactive Primitive
 * Provides fine-grained reactivity with automatic dependency tracking
 */

// Symbol for detecting signals
const SIGNAL = Symbol('signal');

// Global effect stack for dependency tracking
let activeEffect = null;
const effectStack = [];

// Signal class
export class Signal {
  constructor(initialValue) {
    this._value = initialValue;
    this._subscribers = new Set();
    this._version = 0;
    this[SIGNAL] = true;
  }

  get value() {
    // Track dependency when in effect context
    if (activeEffect) {
      activeEffect.dependencies.add(this);
      this._subscribers.add(activeEffect);
    }
    return this._value;
  }

  set value(newValue) {
    if (Object.is(this._value, newValue)) return;

    this._value = newValue;
    this._version++;

    // Notify all subscribers
    const subscribers = [...this._subscribers];
    this._subscribers.clear();

    for (const effect of subscribers) {
      if (effect.active) {
        effect.execute();
      }
    }
  }

  peek() {
    return this._value;
  }

  update(fn) {
    this.value = typeof fn === 'function' ? fn(this._value) : fn;
  }

  subscribe(fn) {
    const effect = new Effect(fn);
    effect.execute();
    return () => effect.stop();
  }
}

// Create signal function
export const signal = (initialValue) => new Signal(initialValue);

// Check if value is a signal
export const isSignal = (value) => value && value[SIGNAL] === true;

// Unwrap signal if needed
export const unwrap = (value) => isSignal(value) ? value.value : value;

// Computed signal
export class Computed extends Signal {
  constructor(compute) {
    super(undefined);
    this._compute = compute;
    this._dependencies = new Set();
    this._dirty = true;

    // Compute initial value
    this._update();
  }

  get value() {
    if (this._dirty) {
      this._update();
    }

    // Track dependency
    if (activeEffect) {
      activeEffect.dependencies.add(this);
      this._subscribers.add(activeEffect);
    }

    return this._value;
  }

  _update() {
    this._dirty = false;

    // Track dependencies
    const prevEffect = activeEffect;
    activeEffect = null;

    try {
      const newValue = this._compute();

      if (!Object.is(this._value, newValue)) {
        this._value = newValue;
        this._version++;

        // Notify subscribers
        const subscribers = [...this._subscribers];
        this._subscribers.clear();

        for (const effect of subscribers) {
          if (effect.active) {
            effect.execute();
          }
        }
      }
    } finally {
      activeEffect = prevEffect;
    }
  }

  peek() {
    if (this._dirty) {
      this._update();
    }
    return this._value;
  }
}

// Create computed function
export const computed = (compute) => new Computed(compute);

// Effect class for side effects
export class Effect {
  constructor(fn, options = {}) {
    this.fn = fn;
    this.options = options;
    this.active = true;
    this.dependencies = new Set();
    this.cleanup = null;
  }

  execute() {
    if (!this.active) return;

    // Clean up previous dependencies
    this.dependencies.forEach(dep => dep._subscribers.delete(this));
    this.dependencies.clear();

    // Track new dependencies
    const prevEffect = activeEffect;
    activeEffect = this;

    try {
      // Clean up previous effect
      if (this.cleanup && typeof this.cleanup === 'function') {
        this.cleanup();
      }

      // Execute effect
      this.cleanup = this.fn();
    } finally {
      activeEffect = prevEffect;
    }
  }

  stop() {
    this.active = false;
    this.dependencies.forEach(dep => dep._subscribers.delete(this));
    this.dependencies.clear();

    if (this.cleanup && typeof this.cleanup === 'function') {
      this.cleanup();
    }
  }
}

// Create effect function
export const effect = (fn, options) => {
  const eff = new Effect(fn, options);
  eff.execute();
  return () => eff.stop();
};

// Batch updates
let batchDepth = 0;
const batchedEffects = new Set();

export const batch = (fn) => {
  if (batchDepth > 0) {
    return fn();
  }

  batchDepth++;
  try {
    return fn();
  } finally {
    batchDepth--;

    if (batchDepth === 0) {
      // Execute all batched effects
      const effects = [...batchedEffects];
      batchedEffects.clear();

      for (const effect of effects) {
        if (effect.active) {
          effect.execute();
        }
      }
    }
  }
};

// Batch signal updates
export const batchUpdates = (fn) => {
  return batch(fn);
};

// Utility functions
export const untrack = (fn) => {
  const prevEffect = activeEffect;
  activeEffect = null;
  try {
    return fn();
  } finally {
    activeEffect = prevEffect;
  }
};

export const tick = () => {
  return new Promise(resolve => {
    if (batchDepth === 0) {
      resolve();
    } else {
      // Schedule after current batch
      Promise.resolve().then(resolve);
    }
  });
};

// Advanced signal operations
export const mergeSignals = (...signals) => {
  return computed(() => {
    return signals.map(s => s.value);
  });
};

export const combineSignals = (signals, combineFn) => {
  return computed(() => {
    const values = signals.map(s => s.value);
    return combineFn(...values);
  });
};

// Signal debugging
export const enableSignalDebug = () => {
  const originalSignal = Signal.prototype;
  const originalComputed = Computed.prototype;

  // Add debug logging
  Signal.prototype.set = function(newValue) {
    console.log(`Signal updated:`, this._debugName || 'unnamed', 'from', this._value, 'to', newValue);
    originalSignal.set.call(this, newValue);
  };

  Computed.prototype._update = function() {
    console.log(`Computed updated:`, this._debugName || 'unnamed');
    originalComputed._update.call(this);
  };
};

// Memory management
export const cleanupSignals = () => {
  // Clean up unused signals and effects
  // Implementation would track unused reactive objects
};

// Development helpers
export const devtools = {
  getActiveEffects: () => effectStack.length,
  getSignalSubscribers: (signal) => signal._subscribers.size,
  getComputedDependencies: (computed) => computed._dependencies.size,
  traceSignal: (signal) => {
    console.log('Signal info:', {
      value: signal.peek(),
      subscribers: signal._subscribers.size,
      version: signal._version
    });
  }
};

// Export everything
export default {
  Signal,
  signal,
  isSignal,
  unwrap,
  Computed,
  computed,
  Effect,
  effect,
  batch,
  batchUpdates,
  untrack,
  tick,
  mergeSignals,
  combineSignals,
  enableSignalDebug,
  cleanupSignals,
  devtools
};
