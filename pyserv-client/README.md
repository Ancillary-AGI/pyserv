# 🚀 Pyserv Client Framework 3.0

**Next-Generation, Signal-Based Frontend Framework**

A modern, ultra-lightweight, reactive frontend framework built from scratch with zero dependencies. Features signal-based reactivity, function components, and a tiny runtime (~3-8KB gzipped).

## ✨ Key Features

- ⚡ **Signal-based Reactivity** - Fine-grained updates with automatic dependency tracking
- 🎯 **Function Components** - Lightweight components with hooks and lifecycle
- 🎨 **Modern JSX Runtime** - Optimized JSX with static analysis and caching
- 🚀 **Tiny Runtime** - 3-8KB gzipped core for maximum performance
- 📊 **Built-in Performance** - Automatic optimization and memory management
- 🔧 **TypeScript-First** - Full TypeScript support with advanced type inference
- 🌐 **SSR & Hydration** - Server-side rendering with progressive hydration
- 📱 **Zero Dependencies** - Completely standalone framework
- 🏗️ **Built from Scratch** - No external libraries or frameworks

## 🎯 What Makes It Special

### **Signal-Based Reactivity**
```javascript
// Create reactive signals
const count = signal(0);
const step = signal(1);

// Computed values with automatic updates
const doubleCount = computed(() => count.value * 2);
const tripleCount = computed(() => doubleCount.value * 1.5);

// Effects for side effects
effect(() => {
  console.log('Count changed:', count.value);
});

// Update triggers automatic re-computation
count.value = 5; // Updates all dependent values instantly
```

### **Function Components with Hooks**
```javascript
const Counter = createComponent(() => {
  const [count, setCount] = useState(0);
  const [step, setStep] = useState(1);

  const doubleCount = useMemo(() => count * 2, [count]);
  const tripleCount = useMemo(() => doubleCount * 1.5, [doubleCount]);

  useEffect(() => {
    console.log('Count changed:', count);
  }, [count]);

  return jsx('div', {
    className: 'counter',
    children: [
      jsx('h2', { children: 'Signal Counter' }),
      jsx('div', { children: count }),
      jsx('button', { onClick: () => setCount(c => c - 1), children: '-' }),
      jsx('button', { onClick: () => setCount(c => c + step), children: '+' })
    ]
  });
});
```

### **Modern JSX Runtime**
```javascript
// Optimized JSX with static analysis
const MyComponent = createComponent((props) => {
  return jsx('div', {
    className: 'container',
    children: [
      jsx('h1', { children: props.title }),
      jsx('p', { children: props.description }),
      // Static parts are cached and optimized
      jsx('button', {
        onClick: props.onAction,
        children: 'Click me'
      })
    ]
  });
});
```

## 🚀 Quick Start

### 1. Basic Setup

```javascript
import { signal, createComponent, jsx, render } from 'pyserv-client';

// Create a reactive component
const App = createComponent(() => {
  const count = signal(0);

  return jsx('div', {
    className: 'app',
    children: [
      jsx('h1', { children: 'Hello Signals!' }),
      jsx('p', { children: count.value }),
      jsx('button', {
        onClick: () => count.value++,
        children: 'Increment'
      })
    ]
  });
});

// Mount to DOM
const app = App();
render(app.rendered.value, '#app');
```

### 2. Advanced Example with Hooks

```javascript
const TodoApp = createComponent(() => {
  const [todos, setTodos] = useState([]);
  const [filter, setFilter] = useState('all');
  const [newTodo, setNewTodo] = useState('');

  // Computed filtered todos
  const filteredTodos = useMemo(() => {
    switch (filter) {
      case 'active': return todos.filter(t => !t.completed);
      case 'completed': return todos.filter(t => t.completed);
      default: return todos;
    }
  }, [todos, filter]);

  // Add new todo
  const addTodo = useCallback(() => {
    if (newTodo.trim()) {
      setTodos(prev => [...prev, {
        id: Date.now(),
        text: newTodo,
        completed: false
      }]);
      setNewTodo('');
    }
  }, [newTodo]);

  return jsx('div', {
    className: 'todo-app',
    children: [
      jsx('h1', { children: 'Todo App' }),
      jsx('input', {
        value: newTodo,
        onChange: (e) => setNewTodo(e.target.value),
        placeholder: 'Add todo...'
      }),
      jsx('button', { onClick: addTodo, children: 'Add' }),
      jsx('div', {
        children: filteredTodos.map(todo =>
          jsx('div', {
            key: todo.id,
            className: `todo ${todo.completed ? 'completed' : ''}`,
            children: [
              jsx('span', { children: todo.text }),
              jsx('button', {
                onClick: () => setTodos(prev =>
                  prev.map(t => t.id === todo.id
                    ? {...t, completed: !t.completed}
                    : t
                  )
                ),
                children: todo.completed ? '✓' : '○'
              })
            ]
          })
        )
      })
    ]
  });
});
```

### 3. Context and State Management

```javascript
// Create context
const ThemeContext = new Context('light');

// App with theme provider
const App = createComponent(() => {
  const [theme, setTheme] = useState('light');

  return jsx('div', {
    className: `app theme-${theme}`,
    children: [
      jsx(ThemeContext.Provider, {
        value: theme,
        children: jsx(ThemeToggle, { onToggle: () => setTheme(t => t === 'light' ? 'dark' : 'light') })
      }),
      jsx(Content, {})
    ]
  });
});

// Component consuming context
const Content = createComponent(() => {
  const theme = useContext(ThemeContext);

  return jsx('div', {
    className: `content theme-${theme}`,
    children: `Current theme: ${theme}`
  });
});
```

## 📦 Installation

### NPM
```bash
npm install pyserv-client
```

### CDN
```html
<script type="module">
  import { signal, createComponent, jsx } from 'https://cdn.jsdelivr.net/npm/pyserv-client@latest/dist/index.js';
</script>
```

### From Source
```bash
git clone https://github.com/ancillary-ai/pydance.git
cd pydance/pyserv-client
npm install
npm run build
```

## 🎨 Framework Architecture

### **Core Runtime (~3-8KB)**
| Module | Size | Purpose |
|--------|------|---------|
| **Signal.js** | ~1.5KB | Reactive primitives with dependency tracking |
| **ModernComponent.js** | ~1.5KB | Function components and hooks system |
| **ModernJSX.js** | ~1KB | JSX runtime with static optimization |
| **ModernRenderer.js** | ~1.5KB | Efficient DOM updates with caching |

### **Advanced Features**
- **🔍 Compile-time Optimization**: Static analysis and tree-shaking
- **⚡ Fine-grained Updates**: Only re-renders what changed
- **💾 Memory Management**: Automatic cleanup and pooling
- **📊 Performance Monitoring**: Built-in benchmarking tools
- **🎯 TypeScript Support**: Full type definitions and inference

## 🛠️ API Reference

### **Reactive Primitives**
```javascript
// Signals
const count = signal(0);
count.value = 5; // Update value
count.subscribe(fn); // Subscribe to changes

// Computed values
const double = computed(() => count.value * 2);

// Effects
effect(() => {
  console.log('Count changed:', count.value);
});

// Batching
batch(() => {
  count.value = 1;
  otherSignal.value = 2; // Batched update
});
```

### **Components & Hooks**
```javascript
// Function component
const MyComponent = createComponent((props) => {
  const [state, setState] = useState(initial);
  const memoized = useMemo(() => compute(), [deps]);
  const callback = useCallback(() => action(), [deps]);
  const ref = useRef(null);

  useEffect(() => {
    // Side effect
    return () => cleanup();
  }, [deps]);

  return jsx('div', { children: content });
});

// Context
const MyContext = new Context(defaultValue);
const value = useContext(MyContext);
```

### **JSX Runtime**
```javascript
// JSX elements
jsx('div', { className: 'container', children: content });
jsxs('div', { className: 'container' }); // Same as jsx

// Fragments
jsx(Fragment, { children: [child1, child2] });

// Components
jsx(MyComponent, { prop: value, children: content });
```

## 🎯 Performance Comparison

| Framework | Runtime Size | Update Granularity | Learning Curve |
|-----------|--------------|-------------------|----------------|
| **Pyserv Client 3.0** | ~5KB | Fine-grained | Low |
| React | ~40KB | Component-level | Medium |
| Vue | ~30KB | Component-level | Medium |
| Svelte | ~10KB | Component-level | Medium |
| SolidJS | ~8KB | Fine-grained | Medium |

## 🧪 Examples

### **Counter Example**
```javascript
const Counter = createComponent(() => {
  const count = signal(0);

  return jsx('div', {
    children: [
      jsx('span', { children: count.value }),
      jsx('button', { onClick: () => count.value--, children: '-' }),
      jsx('button', { onClick: () => count.value++, children: '+' })
    ]
  });
});
```

### **Todo List Example**
```javascript
const TodoList = createComponent(() => {
  const [todos, setTodos] = useState([]);
  const [filter, setFilter] = useState('all');

  const addTodo = (text) => {
    setTodos(prev => [...prev, { id: Date.now(), text, completed: false }]);
  };

  const filteredTodos = useMemo(() => {
    return todos.filter(todo => {
      if (filter === 'active') return !todo.completed;
      if (filter === 'completed') return todo.completed;
      return true;
    });
  }, [todos, filter]);

  return jsx('div', {
    children: [
      jsx('input', {
        onKeyPress: (e) => e.key === 'Enter' && addTodo(e.target.value)
      }),
      jsx('select', {
        value: filter,
        onChange: (e) => setFilter(e.target.value),
        children: ['all', 'active', 'completed'].map(f =>
          jsx('option', { value: f, children: f })
        )
      }),
      jsx('div', {
        children: filteredTodos.map(todo =>
          jsx('div', { key: todo.id, children: todo.text })
        )
      })
    ]
  });
});
```

## 🔧 Development

### **Build & Test**
```bash
# Install dependencies
npm install

# Build framework
npm run build

# Run tests
npm test

# Development server
npm run dev
```

### **Framework Configuration**
```javascript
import { initializeFramework } from 'pyserv-client';

const app = await initializeFramework({
  debug: true,
  enablePerformanceMonitoring: true,
  enableMemoryTracking: true,
  enableSignals: true,
  enableModernComponents: true
});

await app.mount('#app');
```

## 📚 Advanced Features

### **SSR & Hydration**
```javascript
// Server-side rendering
const html = await renderToString(App);

// Client-side hydration
const app = await hydrate('#app', App);
```

### **Routing**
```javascript
const router = createRouter([
  { path: '/', component: Home },
  { path: '/users/:id', component: UserProfile }
]);

router.navigate('/users/123');
```

### **State Management**
```javascript
const store = createStore({
  users: [],
  loading: false
});

const users = computed(() => store.get().users);
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- Documentation: [docs.pyserv-client.com](https://docs.pyserv-client.com)
- Issues: [GitHub Issues](https://github.com/ancillary-ai/pydance/issues)
- Discussions: [GitHub Discussions](https://github.com/ancillary-ai/pydance/discussions)

## 🙏 Acknowledgments

Built with modern web technologies and inspired by SolidJS, Svelte, and Vue.js. Special thanks to the reactive programming community for advancing the state of frontend development.

---

**🚀 Ready to build something amazing? Get started with Pyserv Client 3.0 today!**
