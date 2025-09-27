/**
 * Pyserv Client - API Client for Pyserv Backend Integration
 * Provides seamless integration with Pyserv backend APIs
 */

export class PyservClient {
  constructor(config = {}) {
    this.config = {
      baseURL: config.baseURL || 'http://localhost:8000',
      apiVersion: config.apiVersion || 'v1',
      timeout: config.timeout || 10000,
      retries: config.retries || 3,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...config.headers
      }
    };

    this.baseURL = `${this.config.baseURL}/api/${this.config.apiVersion}`;
    this.endpoints = new Map();
    this.interceptors = {
      request: [],
      response: [],
      error: []
    };

    this._initializeEndpoints();
  }

  _initializeEndpoints() {
    // Register common Pyserv endpoints
    this.endpoints.set('auth', {
      login: '/auth/login/',
      logout: '/auth/logout/',
      refresh: '/auth/refresh/',
      register: '/auth/register/',
      profile: '/auth/profile/',
      changePassword: '/auth/change-password/',
      resetPassword: '/auth/reset-password/'
    });

    this.endpoints.set('users', {
      list: '/users/',
      create: '/users/',
      detail: '/users/{id}/',
      update: '/users/{id}/',
      delete: '/users/{id}/',
      me: '/users/me/'
    });

    this.endpoints.set('models', {
      list: '/models/',
      create: '/models/',
      detail: '/models/{model}/',
      update: '/models/{model}/',
      delete: '/models/{model}/',
      schema: '/models/{model}/schema/'
    });

    this.endpoints.set('api', {
      docs: '/docs/',
      schema: '/schema/',
      health: '/health/',
      metrics: '/metrics/'
    });

    this.endpoints.set('files', {
      upload: '/files/upload/',
      download: '/files/{id}/download/',
      list: '/files/',
      delete: '/files/{id}/'
    });

    this.endpoints.set('notifications', {
      list: '/notifications/',
      markRead: '/notifications/{id}/read/',
      markAllRead: '/notifications/mark-all-read/',
      websocket: '/notifications/ws/'
    });
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

    let requestUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;

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
          data: null
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
          const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError;
  }

  // Authentication methods
  async login(credentials) {
    const endpoint = this.endpoints.get('auth').login;
    return await this.post(endpoint, credentials);
  }

  async logout() {
    const endpoint = this.endpoints.get('auth').logout;
    return await this.post(endpoint);
  }

  async refreshToken(refreshToken) {
    const endpoint = this.endpoints.get('auth').refresh;
    return await this.post(endpoint, { refresh: refreshToken });
  }

  async register(userData) {
    const endpoint = this.endpoints.get('auth').register;
    return await this.post(endpoint, userData);
  }

  async getProfile() {
    const endpoint = this.endpoints.get('auth').profile;
    return await this.get(endpoint);
  }

  async updateProfile(profileData) {
    const endpoint = this.endpoints.get('auth').profile;
    return await this.patch(endpoint, profileData);
  }

  async changePassword(passwordData) {
    const endpoint = this.endpoints.get('auth').changePassword;
    return await this.post(endpoint, passwordData);
  }

  async resetPassword(email) {
    const endpoint = this.endpoints.get('auth').resetPassword;
    return await this.post(endpoint, { email });
  }

  // Model operations
  async getModels() {
    const endpoint = this.endpoints.get('models').list;
    return await this.get(endpoint);
  }

  async getModelSchema(modelName) {
    const endpoint = this.endpoints.get('models').schema.replace('{model}', modelName);
    return await this.get(endpoint);
  }

  async queryModel(modelName, params = {}) {
    const endpoint = this.endpoints.get('models').detail.replace('{model}', modelName);
    return await this.get(endpoint, params);
  }

  async createModelRecord(modelName, data) {
    const endpoint = this.endpoints.get('models').detail.replace('{model}', modelName);
    return await this.post(endpoint, data);
  }

  async updateModelRecord(modelName, id, data) {
    const endpoint = this.endpoints.get('models').detail.replace('{model}', modelName);
    const url = `${endpoint}${id}/`;
    return await this.put(url, data);
  }

  async deleteModelRecord(modelName, id) {
    const endpoint = this.endpoints.get('models').detail.replace('{model}', modelName);
    const url = `${endpoint}${id}/`;
    return await this.delete(url);
  }

  // File operations
  async uploadFile(file, metadata = {}) {
    const endpoint = this.endpoints.get('files').upload;
    const formData = new FormData();
    formData.append('file', file);

    for (const [key, value] of Object.entries(metadata)) {
      formData.append(key, value);
    }

    return await this.request(endpoint, {
      method: 'POST',
      body: formData,
      headers: {} // Let browser set content-type for FormData
    });
  }

  async downloadFile(fileId) {
    const endpoint = this.endpoints.get('files').download.replace('{id}', fileId);
    const response = await this.request(endpoint, { method: 'GET' });

    // Create blob and download
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = response.headers['content-disposition']?.split('filename=')[1] || 'download';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    return response;
  }

  async getFiles(params = {}) {
    const endpoint = this.endpoints.get('files').list;
    return await this.get(endpoint, params);
  }

  async deleteFile(fileId) {
    const endpoint = this.endpoints.get('files').delete.replace('{id}', fileId);
    return await this.delete(endpoint);
  }

  // Notification methods
  async getNotifications(params = {}) {
    const endpoint = this.endpoints.get('notifications').list;
    return await this.get(endpoint, params);
  }

  async markNotificationRead(notificationId) {
    const endpoint = this.endpoints.get('notifications').markRead.replace('{id}', notificationId);
    return await this.post(endpoint);
  }

  async markAllNotificationsRead() {
    const endpoint = this.endpoints.get('notifications').markAllRead;
    return await this.post(endpoint);
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

  // Interceptor methods
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

  // Configuration methods
  setBaseURL(url) {
    this.config.baseURL = url;
    this.baseURL = `${url}/api/${this.config.apiVersion}`;
  }

  setApiVersion(version) {
    this.config.apiVersion = version;
    this.baseURL = `${this.config.baseURL}/api/${version}`;
  }

  setAuthToken(token) {
    this.config.headers['Authorization'] = `Bearer ${token}`;
  }

  removeAuthToken() {
    delete this.config.headers['Authorization'];
  }

  // Health check
  async healthCheck() {
    try {
      const endpoint = this.endpoints.get('api').health;
      const response = await this.get(endpoint);
      return { status: 'healthy', ...response };
    } catch (error) {
      return { status: 'unhealthy', error: error.message };
    }
  }

  // Metrics
  async getMetrics() {
    try {
      const endpoint = this.endpoints.get('api').metrics;
      return await this.get(endpoint);
    } catch (error) {
      console.warn('Failed to fetch metrics:', error);
      return null;
    }
  }
}
