/**
 * ApiClient - Enhanced HTTP Client for Pyserv Integration
 * Provides robust HTTP client with interceptors, caching, retry logic,
 * and seamless integration with Pyserv backend
 */

export class ApiClient {
  constructor(config = {}) {
    this.config = {
      baseURL: config.baseURL || 'http://localhost:8000/api/v1',
      timeout: config.timeout || 10000,
      retries: config.retries || 3,
      retryDelay: config.retryDelay || 1000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...config.headers
      },
      cache: config.cache !== false,
      cacheTTL: config.cacheTTL || 300000, // 5 minutes
      ...config
    };

    this.cache = new Map();
    this.interceptors = {
      request: [],
      response: [],
      error: []
    };

    this._initializeInterceptors();
  }

  _initializeInterceptors() {
    // Add default interceptors
    this.addRequestInterceptor(this._authInterceptor.bind(this));
    this.addRequestInterceptor(this._cacheInterceptor.bind(this));
    this.addResponseInterceptor(this._cacheResponseInterceptor.bind(this));
    this.addErrorInterceptor(this._retryInterceptor.bind(this));
  }

  // HTTP Methods
  async get(url, params = {}, config = {}) {
    const queryString = this._buildQueryString(params);
    const fullUrl = queryString ? `${url}?${queryString}` : url;
    return await this.request(fullUrl, { ...config, method: 'GET' });
  }

  async post(url, data = {}, config = {}) {
    return await this.request(url, {
      ...config,
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async put(url, data = {}, config = {}) {
    return await this.request(url, {
      ...config,
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async patch(url, data = {}, config = {}) {
    return await this.request(url, {
      ...config,
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }

  async delete(url, config = {}) {
    return await this.request(url, { ...config, method: 'DELETE' });
  }

  async request(url, config = {}) {
    const fullConfig = {
      ...this.config,
      ...config,
      headers: { ...this.config.headers, ...config.headers }
    };

    let requestUrl = url.startsWith('http') ? url : `${this.config.baseURL}${url}`;

    // Apply request interceptors
    for (const interceptor of this.interceptors.request) {
      const result = await interceptor(requestUrl, fullConfig);
      if (result) {
        requestUrl = result.url || requestUrl;
        Object.assign(fullConfig, result.config || {});
      }
    }

    const requestOptions = {
      method: fullConfig.method || 'GET',
      headers: fullConfig.headers,
      signal: fullConfig.signal
    };

    if (fullConfig.body && typeof fullConfig.body === 'string') {
      requestOptions.body = fullConfig.body;
    }

    let lastError;
    for (let attempt = 0; attempt <= fullConfig.retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), fullConfig.timeout);

        const response = await fetch(requestUrl, {
          ...requestOptions,
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        // Apply response interceptors
        let responseData = {
          status: response.status,
          statusText: response.statusText,
          headers: Object.fromEntries(response.headers.entries()),
          data: null,
          config: fullConfig,
          request: { url: requestUrl, options: requestOptions }
        };

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          responseData.data = await response.json();
        } else {
          responseData.data = await response.text();
        }

        for (const interceptor of this.interceptors.response) {
          const result = await interceptor(responseData);
          if (result !== undefined) {
            responseData = result;
          }
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return responseData;

      } catch (error) {
        lastError = error;

        // Apply error interceptors
        for (const interceptor of this.interceptors.error) {
          const result = await interceptor(error, attempt, fullConfig.retries);
          if (result === false) {
            // Interceptor handled the error, don't retry
            throw error;
          }
        }

        if (attempt < fullConfig.retries) {
          // Exponential backoff
          const delay = fullConfig.retryDelay * Math.pow(2, attempt);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError;
  }

  // Interceptors
  addRequestInterceptor(interceptor) {
    this.interceptors.request.push(interceptor);
  }

  addResponseInterceptor(interceptor) {
    this.interceptors.response.push(interceptor);
  }

  addErrorInterceptor(interceptor) {
    this.interceptors.error.push(interceptor);
  }

  removeRequestInterceptor(interceptor) {
    const index = this.interceptors.request.indexOf(interceptor);
    if (index > -1) {
      this.interceptors.request.splice(index, 1);
    }
  }

  removeResponseInterceptor(interceptor) {
    const index = this.interceptors.response.indexOf(interceptor);
    if (index > -1) {
      this.interceptors.response.splice(index, 1);
    }
  }

  removeErrorInterceptor(interceptor) {
    const index = this.interceptors.error.indexOf(interceptor);
    if (index > -1) {
      this.interceptors.error.splice(index, 1);
    }
  }

  // Built-in interceptors
  async _authInterceptor(url, config) {
    const token = localStorage.getItem('pyserv_auth_token');
    if (token) {
      config.headers = {
        ...config.headers,
        'Authorization': `Bearer ${token}`
      };
    }
  }

  async _cacheInterceptor(url, config) {
    if (config.method === 'GET' && this.config.cache) {
      const cacheKey = this._getCacheKey(url, config);
      const cached = this._getFromCache(cacheKey);

      if (cached) {
        return {
          ...config,
          cached: true,
          data: cached
        };
      }
    }
  }

  async _cacheResponseInterceptor(response) {
    if (response.config.method === 'GET' && this.config.cache && !response.config.cached) {
      const cacheKey = this._getCacheKey(response.request.url, response.config);
      this._setCache(cacheKey, response.data, this.config.cacheTTL);
    }
  }

  async _retryInterceptor(error, attempt, maxRetries) {
    if (attempt < maxRetries) {
      console.warn(`Request failed (attempt ${attempt + 1}/${maxRetries + 1}):`, error.message);
      return true; // Retry
    }
    return false; // Don't retry
  }

  // Caching
  _getCacheKey(url, config) {
    return `${config.method || 'GET'}:${url}`;
  }

  _getFromCache(key) {
    const cached = this.cache.get(key);
    if (cached && cached.expires > Date.now()) {
      return cached.data;
    }

    if (cached) {
      this.cache.delete(key); // Remove expired cache
    }

    return null;
  }

  _setCache(key, data, ttl) {
    this.cache.set(key, {
      data,
      expires: Date.now() + ttl
    });

    // Limit cache size
    if (this.cache.size > 100) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
  }

  clearCache() {
    this.cache.clear();
  }

  // Utility methods
  _buildQueryString(params) {
    const searchParams = new URLSearchParams();

    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined) {
        if (Array.isArray(value)) {
          value.forEach(v => searchParams.append(key, v));
        } else {
          searchParams.append(key, value);
        }
      }
    }

    return searchParams.toString();
  }

  // Configuration
  setBaseURL(url) {
    this.config.baseURL = url;
  }

  setAuthToken(token) {
    this.config.headers['Authorization'] = `Bearer ${token}`;
    localStorage.setItem('pyserv_auth_token', token);
  }

  removeAuthToken() {
    delete this.config.headers['Authorization'];
    localStorage.removeItem('pyserv_auth_token');
  }

  setHeader(key, value) {
    this.config.headers[key] = value;
  }

  removeHeader(key) {
    delete this.config.headers[key];
  }

  // File upload
  async uploadFile(url, file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);

    for (const [key, value] of Object.entries(metadata)) {
      formData.append(key, value);
    }

    return await this.request(url, {
      method: 'POST',
      body: formData,
      headers: {} // Let browser set content-type for FormData
    });
  }

  // Download file
  async downloadFile(url, filename) {
    const response = await this.request(url, { method: 'GET' });

    // Create blob and download
    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename || 'download';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);

    return response;
  }

  // Batch requests
  async batch(requests) {
    const promises = requests.map(req => this.request(req.url, req.config));
    return await Promise.all(promises);
  }

  // Health check
  async healthCheck() {
    try {
      const response = await this.get('/health/');
      return { status: 'healthy', ...response };
    } catch (error) {
      return { status: 'unhealthy', error: error.message };
    }
  }

  // Metrics
  async getMetrics() {
    try {
      return await this.get('/metrics/');
    } catch (error) {
      console.warn('Failed to fetch metrics:', error);
      return null;
    }
  }

  // Debug utilities
  getDebugInfo() {
    return {
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      retries: this.config.retries,
      cacheSize: this.cache.size,
      interceptorCounts: {
        request: this.interceptors.request.length,
        response: this.interceptors.response.length,
        error: this.interceptors.error.length
      }
    };
  }

  // Cleanup
  destroy() {
    this.cache.clear();
    this.interceptors = {
      request: [],
      response: [],
      error: []
    };
  }
}
