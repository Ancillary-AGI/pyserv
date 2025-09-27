/**
 * Pyserv Client Framework - Clean, Simple API
 * Single component system with signal-based reactivity
 */

// Core reactive system
export {
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
  devtools as signalDevtools
} from './Signal.js';

// Component system with hooks
export {
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
  devtools as componentDevtools
} from './Component.js';

// Legacy files removed - use Component.js instead

// JSX runtime
export {
  JSXElementFactory,
  jsxFactory,
  createElement,
  createFragment,
  cloneElement,
  jsxDEV,
  JSXTemplateCompiler,
  JSXOptimizer,
  JSXDevTools,
  jsxDevTools,
  jsxRuntimeConfig
} from './JSX.js';

// Modern runtime systems
export {
  jsxRuntime,
  createElement as modernCreateElement,
  createFragment as modernCreateFragment,
  cloneElement as modernCloneElement,
  JSXParser,
  JSXTransformer,
  jsxTransformer
} from './JSXTransformer.js';

export {
  ModernRenderer,
  DOMNodeCache,
  domNodeCache,
  rendererConfig,
  getRenderer,
  render as modernRender,
  createRenderer,
  rendererDevTools
} from './ModernRenderer.js';



// Framework infrastructure
export { PyservClientFramework } from './PyservClient.js';
export { Store } from './Store.js';
export { Router } from './Router.js';
export { Auth } from './Auth.js';

// Services
export { ApiClient } from '../services/ApiClient.js';
export { WebSocketClient } from '../services/WebSocketClient.js';
export { NotificationManager } from '../services/NotificationManager.js';
export { ThemeManager } from '../services/ThemeManager.js';
export { CacheManager } from '../services/CacheManager.js';

// Components
export { App } from '../components/App.js';
export { Button } from '../components/Button.js';

// TypeScript support
export * from '../types/index.d.ts';

// Framework instance
import { PyservClientFramework } from './PyservClient.js';
import { devTools } from './DeveloperTools.js';
import { performanceMonitor } from './Diff.js';
import { memoryManager } from './Diff.js';

const framework = new PyservClientFramework({
  debug: true,
  enablePerformanceMonitoring: true,
  enableMemoryTracking: true,
  enableSignals: true
});

export const pyservClient = framework;

// Global exports for browser
if (typeof window !== 'undefined') {
  // Core
  window.signal = signal;
  window.computed = computed;
  window.effect = effect;
  window.batch = batch;

  // Components
  window.createComponent = createComponent;
  window.jsx = jsx;
  window.jsxs = jsxs;
  window.Fragment = Fragment;

  // Hooks
  window.useState = useState;
  window.useEffect = useEffect;
  window.useMemo = useMemo;
  window.useCallback = useCallback;
  window.useRef = useRef;
  window.useContext = useContext;

  // Modern components and runtime
  window.ModernRenderer = ModernRenderer;
  window.jsxTransformer = jsxTransformer;
  window.jsxRuntime = jsxRuntime;

  // Framework
  window.pyservClient = pyservClient;
  window.PyservClientFramework = PyservClientFramework;

  // Developer tools
  window.devTools = devTools;
  window.jsxDevTools = jsxDevTools;

  // Performance
  window.performanceMonitor = performanceMonitor;
  window.memoryManager = memoryManager;

  console.log('🚀 Pyserv Client Framework loaded!');
  console.log('💡 Available: signal, createComponent, jsx, useState, etc.');
  console.log('📦 Size: ~3-8KB gzipped core runtime');
}

// Framework helpers
export async function initializeFramework(config = {}) {
  const instance = new PyservClientFramework({
    ...config,
    enableSignals: true
  });
  await instance.initialize();
  return instance;
}

export async function quickStart(selector = '#app', config = {}) {
  const instance = await initializeFramework(config);
  await instance.mount(selector);
  return instance;
}

// Development helpers
export const dev = {
  tools: devTools,
  inspect: () => devTools.enable(),
  profile: () => devTools.profiler.startProfiling(),
  benchmark: () => benchmarkSuite.runAllBenchmarks(),
  signals: signalDevtools,
  jsx: jsxDevTools,
  memory: {
    snapshot: (label) => devTools.snapshot(label),
    report: () => devTools.getMemoryReport()
  }
};

// Production helpers
export const prod = {
  disableDevTools: () => devTools.disable(),
  enableOptimizations: () => {
    performanceMonitor.enable();
    memoryManager.enable();
  },
  disableOptimizations: () => {
    performanceMonitor.disable();
    memoryManager.disable();
  }
};

// Framework info
export const frameworkInfo = {
  name: 'Pyserv Client',
  version: '3.0.0',
  description: 'Signal-based frontend framework',
  runtime: '~3-8KB gzipped',
  features: [
    '⚡ Signal-based Reactivity',
    '🎯 Function Components with Hooks',
    '🎨 Modern JSX Runtime',
    '🚀 Fine-grained DOM Updates',
    '📊 Built-in Performance Monitoring',
    '💾 Automatic Memory Management',
    '🔧 TypeScript-First Design',
    '📱 Zero External Dependencies'
  ],
  author: 'Pyserv Framework Team',
  license: 'MIT',
  repository: 'https://github.com/ancillary-ai/pydance'
};

// Default export
export default framework;
