/**
 * Store - State Management for Pyserv Client Framework
 * Provides centralized state management with reactive updates,
 * middleware support, and persistence capabilities
 */

export class Store {
  constructor(options = {}) {
    this.name = options.name || 'store';
    this.initialState = options.initialState || {};
    this.state = { ...this.initialState };
    this.listeners = new Set();
    this.middlewares = [];
    this.history = [];
    this.historyIndex = -1;
    this.maxHistorySize = options.maxHistorySize || 50;
    this.persistenceKey = options.persistenceKey;
    this.debug = options.debug || false;

    // Initialize persistence if key is provided
    if (this.persistenceKey) {
      this._loadPersistedState();
    }

    // Bind methods
    this.getState = this.getState.bind(this);
    this.setState = this.setState.bind(this);
    this.subscribe = this.subscribe.bind(this);
    this.unsubscribe = this.unsubscribe.bind(this);
    this.dispatch = this.dispatch.bind(this);
  }

  // State access
  getState() {
    return { ...this.state };
  }

  getStateSlice(path) {
    return this._getNestedValue(this.state, path);
  }

  // State updates
  setState(updater, action = 'SET_STATE') {
    const prevState = { ...this.state };

    let newState;
    if (typeof updater === 'function') {
      newState = updater(prevState);
    } else {
      newState = { ...prevState, ...updater };
    }

    // Apply middlewares
    for (const middleware of this.middlewares) {
      const result = middleware(prevState, newState, action);
      if (result === false) {
        // Middleware rejected the update
        return false;
      }
      if (result && typeof result === 'object') {
        newState = { ...newState, ...result };
      }
    }

    // Update state
    this.state = newState;

    // Add to history
    this._addToHistory(prevState, newState, action);

    // Persist if enabled
    if (this.persistenceKey) {
      this._persistState();
    }

    // Notify listeners
    this._notifyListeners(prevState, newState, action);

    if (this.debug) {
      console.log(`[${this.name}] State updated:`, { prevState, newState, action });
    }

    return true;
  }

  // Action dispatching
  dispatch(action) {
    if (typeof action === 'string') {
      action = { type: action };
    }

    if (!action.type) {
      throw new Error('Action must have a type');
    }

    const prevState = { ...this.state };

    // Handle built-in actions
    switch (action.type) {
      case 'RESET':
        this.state = { ...this.initialState };
        break;
      case 'UNDO':
        this._undo();
        break;
      case 'REDO':
        this._redo();
        break;
      default:
        // Custom action handling
        if (typeof this[action.type] === 'function') {
          this[action.type](action.payload);
        } else {
          console.warn(`Unknown action type: ${action.type}`);
        }
    }

    const newState = { ...this.state };
    this._notifyListeners(prevState, newState, action.type);
  }

  // Subscription management
  subscribe(listener) {
    this.listeners.add(listener);

    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  unsubscribe(listener) {
    this.listeners.delete(listener);
  }

  _notifyListeners(prevState, newState, action) {
    this.listeners.forEach(listener => {
      try {
        listener(newState, prevState, action);
      } catch (error) {
        console.error('Store listener error:', error);
      }
    });
  }

  // Middleware support
  use(middleware) {
    this.middlewares.push(middleware);
  }

  removeMiddleware(middleware) {
    const index = this.middlewares.indexOf(middleware);
    if (index > -1) {
      this.middlewares.splice(index, 1);
    }
  }

  // History management
  _addToHistory(prevState, newState, action) {
    const historyEntry = {
      prevState: { ...prevState },
      newState: { ...newState },
      action,
      timestamp: Date.now()
    };

    // Remove any history after current index (for new branches)
    if (this.historyIndex < this.history.length - 1) {
      this.history = this.history.slice(0, this.historyIndex + 1);
    }

    this.history.push(historyEntry);
    this.historyIndex++;

    // Limit history size
    if (this.history.length > this.maxHistorySize) {
      this.history.shift();
      this.historyIndex--;
    }
  }

  _undo() {
    if (this.historyIndex > 0) {
      const entry = this.history[this.historyIndex];
      this.state = { ...entry.prevState };
      this.historyIndex--;
      return true;
    }
    return false;
  }

  _redo() {
    if (this.historyIndex < this.history.length - 1) {
      this.historyIndex++;
      const entry = this.history[this.historyIndex];
      this.state = { ...entry.newState };
      return true;
    }
    return false;
  }

  canUndo() {
    return this.historyIndex > 0;
  }

  canRedo() {
    return this.historyIndex < this.history.length - 1;
  }

  // Persistence
  _persistState() {
    if (!this.persistenceKey) return;

    try {
      const stateToPersist = this._serializeState(this.state);
      localStorage.setItem(this.persistenceKey, stateToPersist);
    } catch (error) {
      console.error('Failed to persist state:', error);
    }
  }

  _loadPersistedState() {
    if (!this.persistenceKey) return;

    try {
      const persisted = localStorage.getItem(this.persistenceKey);
      if (persisted) {
        const parsedState = this._deserializeState(persisted);
        this.state = { ...this.state, ...parsedState };
      }
    } catch (error) {
      console.error('Failed to load persisted state:', error);
    }
  }

  _serializeState(state) {
    // Custom serialization logic
    return JSON.stringify(state);
  }

  _deserializeState(serializedState) {
    // Custom deserialization logic
    return JSON.parse(serializedState);
  }

  // Utility methods
  _getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  _setNestedValue(obj, path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    const target = keys.reduce((current, key) => {
      if (!current[key]) current[key] = {};
      return current[key];
    }, obj);
    target[lastKey] = value;
    return obj;
  }

  // Selector support (like Redux selectors)
  select(selectorFn) {
    return selectorFn(this.state);
  }

  // Computed values
  compute(computerFn, dependencies) {
    const depsValues = dependencies.map(dep => this._getNestedValue(this.state, dep));

    return {
      value: computerFn(...depsValues),
      dependencies: depsValues
    };
  }

  // Batch updates
  batch(updates) {
    const prevState = { ...this.state };
    let newState = { ...prevState };

    updates.forEach(update => {
      if (typeof update === 'function') {
        newState = update(newState);
      } else {
        newState = { ...newState, ...update };
      }
    });

    this.state = newState;
    this._notifyListeners(prevState, newState, 'BATCH_UPDATE');
  }

  // Reset functionality
  reset() {
    this.setState({ ...this.initialState }, 'RESET');
  }

  // State validation
  validate(validatorFn) {
    try {
      const errors = validatorFn(this.state);
      return { isValid: !errors || Object.keys(errors).length === 0, errors };
    } catch (error) {
      return { isValid: false, errors: { validation: error.message } };
    }
  }

  // Export/Import state
  exportState() {
    return {
      name: this.name,
      state: { ...this.state },
      history: [...this.history],
      historyIndex: this.historyIndex,
      timestamp: Date.now()
    };
  }

  importState(stateData) {
    if (stateData.name !== this.name) {
      throw new Error('State data name does not match store name');
    }

    this.state = { ...stateData.state };
    this.history = [...stateData.history];
    this.historyIndex = stateData.historyIndex;

    this._notifyListeners({}, this.state, 'IMPORT_STATE');
  }

  // Debug utilities
  getDebugInfo() {
    return {
      name: this.name,
      stateSize: JSON.stringify(this.state).length,
      listenerCount: this.listeners.size,
      middlewareCount: this.middlewares.length,
      historySize: this.history.length,
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      persistenceEnabled: !!this.persistenceKey
    };
  }

  // Event emission (for integration with framework)
  emit(event, data) {
    if (this.debug) {
      console.log(`[${this.name}] Event: ${event}`, data);
    }

    // Notify listeners about the event
    this.listeners.forEach(listener => {
      try {
        if (typeof listener === 'function') {
          listener(this.state, this.state, event, data);
        }
      } catch (error) {
        console.error('Store listener error:', error);
      }
    });
  }

  on(event, handler) {
    const listener = (state, prevState, action, data) => {
      if (action === event) {
        handler(state, prevState, data);
      }
    };

    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  // Cleanup
  destroy() {
    this.listeners.clear();
    this.middlewares = [];
    this.history = [];
    this.state = { ...this.initialState };

    if (this.persistenceKey) {
      localStorage.removeItem(this.persistenceKey);
    }

    if (this.debug) {
      console.log(`Store ${this.name} destroyed`);
    }
  }
}

// Built-in middlewares
export const loggerMiddleware = (prevState, newState, action) => {
  console.log('Store action:', action);
  console.log('Previous state:', prevState);
  console.log('New state:', newState);
};

export const persistenceMiddleware = (store) => {
  return (prevState, newState, action) => {
    // Only persist certain actions
    const persistActions = ['SET_STATE', 'UPDATE_USER', 'UPDATE_SETTINGS'];
    if (persistActions.includes(action)) {
      // Trigger persistence
      store._persistState();
    }
  };
};

export const validationMiddleware = (validator) => {
  return (prevState, newState, action) => {
    try {
      const errors = validator(newState);
      if (errors && Object.keys(errors).length > 0) {
        console.error('State validation failed:', errors);
        // Could emit an error event or revert the state
        return false; // Reject the update
      }
    } catch (error) {
      console.error('State validation error:', error);
      return false;
    }
  };
};

export const throttleMiddleware = (delay = 100) => {
  let lastUpdate = 0;

  return (prevState, newState, action) => {
    const now = Date.now();
    if (now - lastUpdate < delay) {
      return false; // Throttle the update
    }
    lastUpdate = now;
  };
};

// Store factory
export function createStore(options = {}) {
  return new Store(options);
}

// Global store registry
const storeRegistry = new Map();

export function registerStore(name, store) {
  storeRegistry.set(name, store);
}

export function getStore(name) {
  return storeRegistry.get(name);
}

export function unregisterStore(name) {
  const store = storeRegistry.get(name);
  if (store) {
    store.destroy();
    storeRegistry.delete(name);
  }
}

// Store enhancers (like Redux enhancers)
export function applyMiddleware(...middlewares) {
  return (store) => {
    middlewares.forEach(middleware => store.use(middleware));
    return store;
  };
}

export function withPersistence(store, key) {
  store.persistenceKey = key;
  store._loadPersistedState();
  return store;
}

export function withHistory(store, maxSize = 50) {
  store.maxHistorySize = maxSize;
  return store;
}

export function withValidation(store, validator) {
  store.use(validationMiddleware(validator));
  return store;
}

export function withLogging(store) {
  store.use(loggerMiddleware);
  store.debug = true;
  return store;
}

// Store composition
export function combineStores(stores) {
  const combinedStore = new Store({
    name: 'combined',
    initialState: {}
  });

  // Combine initial states
  stores.forEach(store => {
    combinedStore.initialState[store.name] = store.initialState;
  });

  // Subscribe to all stores
  stores.forEach(store => {
    store.subscribe((state, prevState, action) => {
      combinedStore.setState({
        [store.name]: state
      }, `UPDATE_${store.name.toUpperCase()}`);
    });
  });

  return combinedStore;
}

// Store selectors
export function createSelector(...selectors) {
  return (state) => {
    return selectors.map(selector => selector(state));
  };
}

export function createStructuredSelector(selectors) {
  return (state) => {
    const result = {};
    Object.entries(selectors).forEach(([key, selector]) => {
      result[key] = selector(state);
    });
    return result;
  };
}

// Store utilities
export function shallowEqual(obj1, obj2) {
  if (obj1 === obj2) return true;

  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);

  if (keys1.length !== keys2.length) return false;

  for (const key of keys1) {
    if (obj1[key] !== obj2[key]) return false;
  }

  return true;
}

export function deepEqual(obj1, obj2) {
  if (obj1 === obj2) return true;

  if (obj1 == null || obj2 == null) return obj1 === obj2;

  if (typeof obj1 !== typeof obj2) return false;

  if (typeof obj1 !== 'object') return obj1 === obj2;

  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);

  if (keys1.length !== keys2.length) return false;

  for (const key of keys1) {
    if (!deepEqual(obj1[key], obj2[key])) return false;
  }

  return true;
}
