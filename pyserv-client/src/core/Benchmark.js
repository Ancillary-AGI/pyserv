/**
 * Benchmark - Performance Testing Suite for Pyserv Client Framework
 * Comprehensive benchmarking utilities for measuring framework performance
 */

import { AdvancedDiffer, performanceMonitor, memoryManager } from './Diff.js';
import { Component } from './Component.js';
import { reactive, computed, effect } from './Reactive.js';

// Benchmark configuration
export class BenchmarkConfig {
  constructor(options = {}) {
    this.options = {
      iterations: options.iterations || 1000,
      warmupIterations: options.warmupIterations || 100,
      enablePerformanceMonitoring: options.enablePerformanceMonitoring !== false,
      enableMemoryTracking: options.enableMemoryTracking !== false,
      enableDetailedLogging: options.enableDetailedLogging || false,
      timeout: options.timeout || 30000, // 30 seconds
      ...options
    };
  }
}

// Benchmark result
export class BenchmarkResult {
  constructor(name, config) {
    this.name = name;
    this.config = config;
    this.startTime = performance.now();
    this.endTime = null;
    this.duration = 0;
    this.iterations = 0;
    this.operationsPerSecond = 0;
    this.averageTime = 0;
    this.minTime = Infinity;
    this.maxTime = 0;
    this.medianTime = 0;
    this.percentile95 = 0;
    this.percentile99 = 0;
    this.memoryUsage = 0;
    this.memoryDelta = 0;
    this.error = null;
    this.samples = [];
    this.metrics = {};
  }

  complete() {
    this.endTime = performance.now();
    this.duration = this.endTime - this.startTime;
    this.averageTime = this.duration / this.iterations;
    this.operationsPerSecond = (this.iterations / this.duration) * 1000;

    if (this.samples.length > 0) {
      this.samples.sort((a, b) => a - b);
      this.medianTime = this.samples[Math.floor(this.samples.length / 2)];
      this.percentile95 = this.samples[Math.floor(this.samples.length * 0.95)];
      this.percentile99 = this.samples[Math.floor(this.samples.length * 0.99)];
    }

    return this;
  }

  addSample(time) {
    this.samples.push(time);
    this.minTime = Math.min(this.minTime, time);
    this.maxTime = Math.max(this.maxTime, time);
  }

  setMemoryUsage(usage) {
    this.memoryUsage = usage;
  }

  setMemoryDelta(delta) {
    this.memoryDelta = delta;
  }

  setError(error) {
    this.error = error;
  }

  setMetrics(metrics) {
    this.metrics = metrics;
  }

  toJSON() {
    return {
      name: this.name,
      duration: this.duration,
      iterations: this.iterations,
      operationsPerSecond: this.operationsPerSecond,
      averageTime: this.averageTime,
      minTime: this.minTime,
      maxTime: this.maxTime,
      medianTime: this.medianTime,
      percentile95: this.percentile95,
      percentile99: this.percentile99,
      memoryUsage: this.memoryUsage,
      memoryDelta: this.memoryDelta,
      error: this.error,
      metrics: this.metrics,
      samples: this.samples.slice(0, 100) // Limit samples in JSON
    };
  }
}

// Main benchmark suite
export class BenchmarkSuite {
  constructor(config = {}) {
    this.config = new BenchmarkConfig(config);
    this.results = [];
    this.currentBenchmark = null;
    this.isRunning = false;

    if (this.config.options.enablePerformanceMonitoring) {
      performanceMonitor.enable();
    }
  }

  // Benchmark framework components
  async benchmarkComponentCreation(iterations = 1000) {
    const result = new BenchmarkResult('Component Creation', this.config);

    // Warmup
    for (let i = 0; i < this.config.options.warmupIterations; i++) {
      const component = new Component({ id: i });
    }

    const startMemory = this.getMemoryUsage();

    for (let i = 0; i < iterations; i++) {
      const start = performance.now();

      const component = new Component({
        id: i,
        name: `Component ${i}`,
        data: { value: Math.random() }
      });

      const end = performance.now();
      result.addSample(end - start);
      result.iterations++;
    }

    const endMemory = this.getMemoryUsage();
    result.setMemoryUsage(endMemory);
    result.setMemoryDelta(endMemory - startMemory);

    return result.complete();
  }

  async benchmarkComponentRendering(iterations = 1000) {
    const result = new BenchmarkResult('Component Rendering', this.config);

    class TestComponent extends Component {
      render() {
        return `<div class="test-component">
          <h1>Test Component</h1>
          <p>Iteration: ${this.props.iteration}</p>
          <span>Value: ${this.props.value}</span>
        </div>`;
      }
    }

    // Warmup
    for (let i = 0; i < this.config.options.warmupIterations; i++) {
      const component = new TestComponent({ iteration: i, value: Math.random() });
      component.render();
    }

    const startMemory = this.getMemoryUsage();

    for (let i = 0; i < iterations; i++) {
      const start = performance.now();

      const component = new TestComponent({
        iteration: i,
        value: Math.random()
      });
      const html = component.render();

      const end = performance.now();
      result.addSample(end - start);
      result.iterations++;
    }

    const endMemory = this.getMemoryUsage();
    result.setMemoryUsage(endMemory);
    result.setMemoryDelta(endMemory - startMemory);

    return result.complete();
  }

  async benchmarkDiffing(iterations = 1000) {
    const result = new BenchmarkResult('Virtual DOM Diffing', this.config);

    const differ = new AdvancedDiffer({
      enableKeyOptimization: true,
      enableListOptimization: true,
      enableMoveDetection: true
    });

    // Create test VNodes
    const createVNode = (id, value) => ({
      tagName: 'div',
      props: { id: `item-${id}`, className: 'item' },
      children: [`Item ${id}: ${value}`],
      key: id
    });

    const oldTree = Array.from({ length: 100 }, (_, i) =>
      createVNode(i, Math.random())
    );

    // Warmup
    for (let i = 0; i < this.config.options.warmupIterations; i++) {
      const newTree = oldTree.map(node => ({
        ...node,
        children: [`Updated ${Math.random()}`]
      }));
      differ.diffAdvanced(oldTree[0], newTree[0]);
    }

    const startMemory = this.getMemoryUsage();

    for (let i = 0; i < iterations; i++) {
      const start = performance.now();

      const newTree = oldTree.map(node => ({
        ...node,
        children: [`Updated ${Math.random()}`]
      }));

      const patches = differ.diffAdvanced(oldTree[0], newTree[0]);

      const end = performance.now();
      result.addSample(end - start);
      result.iterations++;
    }

    const endMemory = this.getMemoryUsage();
    result.setMemoryUsage(endMemory);
    result.setMemoryDelta(endMemory - startMemory);

    return result.complete();
  }

  async benchmarkPatching(iterations = 1000) {
    const result = new BenchmarkResult('DOM Patching', this.config);

    const differ = new AdvancedDiffer();
    const container = document.createElement('div');

    // Create test VNodes
    const createVNode = (id, value) => ({
      tagName: 'div',
      props: { id: `item-${id}`, className: 'item' },
      children: [`Item ${id}: ${value}`],
      key: id
    });

    const oldTree = Array.from({ length: 50 }, (_, i) =>
      createVNode(i, Math.random())
    );

    // Create initial DOM
    const initialPatches = differ.diffAdvanced(null, oldTree[0]);
    this.applyPatches(container, initialPatches);

    // Warmup
    for (let i = 0; i < this.config.options.warmupIterations; i++) {
      const newTree = { ...oldTree[0], children: [`Updated ${Math.random()}`] };
      const patches = differ.diffAdvanced(oldTree[0], newTree);
      this.applyPatches(container, patches);
    }

    const startMemory = this.getMemoryUsage();

    for (let i = 0; i < iterations; i++) {
      const start = performance.now();

      const newTree = { ...oldTree[0], children: [`Updated ${Math.random()}`] };
      const patches = differ.diffAdvanced(oldTree[0], newTree);
      this.applyPatches(container, patches);

      const end = performance.now();
      result.addSample(end - start);
      result.iterations++;
    }

    const endMemory = this.getMemoryUsage();
    result.setMemoryUsage(endMemory);
    result.setMemoryDelta(endMemory - startMemory);

    return result.complete();
  }

  applyPatches(parentElement, patches) {
    for (const patch of patches) {
      switch (patch.type) {
        case 'CREATE':
          this.createElement(parentElement, patch.newVNode);
          break;
        case 'UPDATE':
          this.updateElement(patch.oldVNode, patch.newVNode);
          break;
        case 'REPLACE':
          this.replaceElement(parentElement, patch.oldVNode, patch.newVNode);
          break;
      }
    }
  }

  createElement(parent, vnode) {
    const element = document.createElement(vnode.tagName);
    element.textContent = vnode.children[0] || '';
    parent.appendChild(element);
    vnode.element = element;
  }

  updateElement(oldVNode, newVNode) {
    const element = oldVNode.element;
    if (element) {
      element.textContent = newVNode.children[0] || '';
    }
  }

  replaceElement(parent, oldVNode, newVNode) {
    const oldElement = oldVNode.element;
    const newElement = document.createElement(newVNode.tagName);
    newElement.textContent = newVNode.children[0] || '';

    if (oldElement && oldElement.parentNode === parent) {
      parent.replaceChild(newElement, oldElement);
      newVNode.element = newElement;
    }
  }

  async benchmarkReactiveSystem(iterations = 1000) {
    const result = new BenchmarkResult('Reactive System', this.config);

    // Warmup
    for (let i = 0; i < this.config.options.warmupIterations; i++) {
      const state = reactive({ count: 0, name: 'test' });
      const double = computed(() => state.count * 2);
      effect(() => double.value);
      state.count++;
    }

    const startMemory = this.getMemoryUsage();

    for (let i = 0; i < iterations; i++) {
      const start = performance.now();

      const state = reactive({
        count: 0,
        name: `test-${i}`,
        items: Array.from({ length: 10 }, (_, j) => ({ id: j, value: Math.random() }))
      });

      const double = computed(() => state.count * 2);
      const triple = computed(() => double.value * 1.5);
      const display = computed(() => `${state.name}: ${triple.value}`);

      effect(() => {
        display.value;
      });

      state.count = Math.floor(Math.random() * 100);
      state.name = `updated-${i}`;

      const end = performance.now();
      result.addSample(end - start);
      result.iterations++;
    }

    const endMemory = this.getMemoryUsage();
    result.setMemoryUsage(endMemory);
    result.setMemoryDelta(endMemory - startMemory);

    return result.complete();
  }

  async benchmarkMemoryManagement(iterations = 1000) {
    const result = new BenchmarkResult('Memory Management', this.config);

    // Warmup
    for (let i = 0; i < this.config.options.warmupIterations; i++) {
      memoryManager.getVNode('div', { className: 'test' }, ['content'], i);
      memoryManager.releaseVNode({ tagName: 'div', key: i });
    }

    const startMemory = this.getMemoryUsage();

    for (let i = 0; i < iterations; i++) {
      const start = performance.now();

      // Allocate VNodes
      const vnodes = [];
      for (let j = 0; j < 100; j++) {
        const vnode = memoryManager.getVNode(
          'div',
          { className: 'item', id: `item-${j}` },
          [`Item ${j}`],
          j
        );
        vnodes.push(vnode);
      }

      // Release VNodes
      vnodes.forEach(vnode => memoryManager.releaseVNode(vnode));

      // Trigger cleanup
      memoryManager.cleanup();

      const end = performance.now();
      result.addSample(end - start);
      result.iterations++;
    }

    const endMemory = this.getMemoryUsage();
    result.setMemoryUsage(endMemory);
    result.setMemoryDelta(endMemory - startMemory);

    return result.complete();
  }

  // Utility methods
  getMemoryUsage() {
    if (this.config.options.enableMemoryTracking && 'memory' in performance) {
      const memory = performance.memory;
      return memory.usedJSHeapSize;
    }
    return 0;
  }

  async runAllBenchmarks() {
    this.isRunning = true;
    const results = [];

    try {
      console.log('🚀 Starting Pyserv Client Benchmark Suite...');

      // Run individual benchmarks
      const benchmarks = [
        () => this.benchmarkComponentCreation(),
        () => this.benchmarkComponentRendering(),
        () => this.benchmarkDiffing(),
        () => this.benchmarkPatching(),
        () => this.benchmarkReactiveSystem(),
        () => this.benchmarkMemoryManagement()
      ];

      for (const benchmark of benchmarks) {
        const result = await benchmark();
        results.push(result);

        if (this.config.options.enableDetailedLogging) {
          console.log(`✅ ${result.name}: ${(result.averageTime * 1000).toFixed(2)}μs avg, ${result.operationsPerSecond.toFixed(0)} ops/sec`);
        }
      }

      // Generate summary
      this.generateSummary(results);

    } catch (error) {
      console.error('❌ Benchmark suite failed:', error);
    } finally {
      this.isRunning = false;
    }

    return results;
  }

  generateSummary(results) {
    console.log('\n📊 Benchmark Summary');
    console.log('==================');

    let totalOps = 0;
    let totalTime = 0;

    results.forEach(result => {
      console.log(`${result.name}:`);
      console.log(`  Average Time: ${(result.averageTime * 1000).toFixed(2)}μs`);
      console.log(`  Operations/sec: ${result.operationsPerSecond.toFixed(0)}`);
      console.log(`  Memory Usage: ${(result.memoryUsage / 1024 / 1024).toFixed(2)}MB`);
      console.log(`  Memory Delta: ${(result.memoryDelta / 1024 / 1024).toFixed(2)}MB`);
      console.log('');

      totalOps += result.operationsPerSecond;
      totalTime += result.duration;
    });

    console.log(`Total Operations/sec: ${totalOps.toFixed(0)}`);
    console.log(`Total Execution Time: ${(totalTime / 1000).toFixed(2)}s`);
    console.log(`Average Memory Usage: ${(results.reduce((sum, r) => sum + r.memoryUsage, 0) / results.length / 1024 / 1024).toFixed(2)}MB`);
  }

  // Export results
  exportResults(results, format = 'json') {
    if (format === 'json') {
      return JSON.stringify(results.map(r => r.toJSON()), null, 2);
    }

    if (format === 'csv') {
      const headers = 'Name,Duration,Iterations,OpsPerSec,AvgTime,MinTime,MaxTime,MedianTime,P95,P99,MemoryUsage,MemoryDelta\n';
      const data = results.map(r => [
        r.name,
        r.duration,
        r.iterations,
        r.operationsPerSecond,
        r.averageTime,
        r.minTime,
        r.maxTime,
        r.medianTime,
        r.percentile95,
        r.percentile99,
        r.memoryUsage,
        r.memoryDelta
      ].join(',')).join('\n');

      return headers + data;
    }

    throw new Error(`Unsupported export format: ${format}`);
  }
}

// Performance comparison utilities
export class PerformanceComparator {
  constructor() {
    this.baselines = new Map();
  }

  async loadBaseline(name, results) {
    this.baselines.set(name, results);
  }

  compareResults(currentResults, baselineName) {
    const baseline = this.baselines.get(baselineName);
    if (!baseline) {
      throw new Error(`Baseline '${baselineName}' not found`);
    }

    const comparisons = [];

    for (const current of currentResults) {
      const baselineResult = baseline.find(b => b.name === current.name);
      if (baselineResult) {
        const improvement = ((baselineResult.averageTime - current.averageTime) / baselineResult.averageTime) * 100;
        const perfRatio = baselineResult.operationsPerSecond / current.operationsPerSecond;

        comparisons.push({
          name: current.name,
          improvement: improvement,
          performanceRatio: perfRatio,
          current: current.averageTime,
          baseline: baselineResult.averageTime,
          memoryImprovement: baselineResult.memoryUsage - current.memoryUsage
        });
      }
    }

    return comparisons;
  }

  generateComparisonReport(comparisons) {
    console.log('\n📈 Performance Comparison Report');
    console.log('==============================');

    comparisons.forEach(comp => {
      const status = comp.improvement > 0 ? '✅ Improved' : comp.improvement < 0 ? '⚠️  Regressed' : '➖ No Change';
      console.log(`${comp.name}: ${status}`);
      console.log(`  Improvement: ${comp.improvement > 0 ? '+' : ''}${comp.improvement.toFixed(2)}%`);
      console.log(`  Performance Ratio: ${comp.performanceRatio.toFixed(2)}x`);
      console.log(`  Memory Improvement: ${(comp.memoryImprovement / 1024 / 1024).toFixed(2)}MB`);
      console.log('');
    });
  }
}

// Automated performance testing
export class AutomatedTester {
  constructor(suite, config = {}) {
    this.suite = suite;
    this.config = {
      testInterval: config.testInterval || 3600000, // 1 hour
      maxRetries: config.maxRetries || 3,
      enableAlerts: config.enableAlerts !== false,
      alertThreshold: config.alertThreshold || 0.1, // 10% degradation
      ...config
    };

    this.history = [];
    this.alerts = [];
  }

  async runAutomatedTest() {
    const timestamp = new Date().toISOString();
    const results = await this.suite.runAllBenchmarks();

    const testResult = {
      timestamp,
      results,
      summary: this.generateTestSummary(results)
    };

    this.history.push(testResult);
    this.analyzePerformance(testResult);

    return testResult;
  }

  generateTestSummary(results) {
    return {
      totalBenchmarks: results.length,
      averageOpsPerSec: results.reduce((sum, r) => sum + r.operationsPerSecond, 0) / results.length,
      totalMemoryUsage: results.reduce((sum, r) => sum + r.memoryUsage, 0),
      fastestBenchmark: results.reduce((fastest, current) =>
        current.operationsPerSecond > fastest.operationsPerSecond ? current : fastest
      ),
      slowestBenchmark: results.reduce((slowest, current) =>
        current.operationsPerSecond < slowest.operationsPerSecond ? current : slowest
      )
    };
  }

  analyzePerformance(currentTest) {
    if (this.history.length < 2) return;

    const previousTest = this.history[this.history.length - 2];
    const comparisons = [];

    currentTest.results.forEach(current => {
      const previous = previousTest.results.find(p => p.name === current.name);
      if (previous) {
        const degradation = (current.averageTime - previous.averageTime) / previous.averageTime;

        if (degradation > this.config.alertThreshold) {
          this.alerts.push({
            timestamp: new Date().toISOString(),
            benchmark: current.name,
            degradation: degradation,
            previousTime: previous.averageTime,
            currentTime: current.averageTime,
            type: 'performance_degradation'
          });
        }

        comparisons.push({
          name: current.name,
          degradation,
          significant: Math.abs(degradation) > this.config.alertThreshold
        });
      }
    });

    if (this.config.enableAlerts && this.alerts.length > 0) {
      this.sendAlerts(this.alerts);
    }

    return comparisons;
  }

  sendAlerts(alerts) {
    console.warn('🚨 Performance Alerts Detected:');
    alerts.forEach(alert => {
      console.warn(`  ${alert.benchmark}: ${(alert.degradation * 100).toFixed(2)}% degradation`);
    });
  }

  getPerformanceHistory() {
    return this.history;
  }

  getAlerts() {
    return this.alerts;
  }
}

// Export benchmark utilities
export const benchmarkSuite = new BenchmarkSuite();
export const performanceComparator = new PerformanceComparator();
export const automatedTester = new AutomatedTester(benchmarkSuite);

// Convenience functions
export async function runQuickBenchmark() {
  console.log('🔥 Running Quick Benchmark...');
  const results = await benchmarkSuite.runAllBenchmarks();
  return results;
}

export async function runDetailedBenchmark(iterations = 5000) {
  console.log(`🔥 Running Detailed Benchmark (${iterations} iterations)...`);
  const suite = new BenchmarkSuite({ iterations });
  const results = await suite.runAllBenchmarks();
  return results;
}

export async function compareWithBaseline(baselineName, currentResults) {
  return performanceComparator.compareResults(currentResults, baselineName);
}
