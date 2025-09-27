/**
 * WebSocketClient - Real-time Communication with Pyserv Backend
 * Provides WebSocket connectivity with automatic reconnection,
 * message queuing, and event handling
 */

export class WebSocketClient {
  constructor(config = {}) {
    this.config = {
      url: config.url || 'ws://localhost:8000/ws',
      reconnectInterval: config.reconnectInterval || 5000,
      maxReconnectAttempts: config.maxReconnectAttempts || 5,
      heartbeatInterval: config.heartbeatInterval || 30000,
      messageQueueSize: config.messageQueueSize || 100,
      debug: config.debug || false,
      ...config
    };

    this.socket = null;
    this.isConnected = false;
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.messageQueue = [];
    this.eventListeners = new Map();
    this.heartbeatTimer = null;
    this.reconnectTimer = null;
    this.lastHeartbeat = null;

    this._initializeEventHandlers();
  }

  _initializeEventHandlers() {
    this.eventHandlers = {
      open: (event) => this._handleOpen(event),
      close: (event) => this._handleClose(event),
      message: (event) => this._handleMessage(event),
      error: (error) => this._handleError(error)
    };
  }

  // Connection management
  async connect() {
    if (this.isConnected || this.isConnecting) {
      return;
    }

    this.isConnecting = true;

    try {
      this.socket = new WebSocket(this.config.url);

      // Set up event listeners
      this.socket.addEventListener('open', this.eventHandlers.open);
      this.socket.addEventListener('close', this.eventHandlers.close);
      this.socket.addEventListener('message', this.eventHandlers.message);
      this.socket.addEventListener('error', this.eventHandlers.error);

      // Wait for connection or timeout
      await this._waitForConnection();

    } catch (error) {
      this.isConnecting = false;
      this._handleError(error);
      throw error;
    }
  }

  async disconnect() {
    this.isConnecting = false;
    this._stopHeartbeat();
    this._stopReconnect();

    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }

    this.isConnected = false;
    this.emit('disconnected', { reason: 'client_disconnect' });
  }

  async _waitForConnection() {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, 10000);

      const checkConnection = () => {
        if (this.isConnected) {
          clearTimeout(timeout);
          resolve();
        } else if (!this.isConnecting) {
          clearTimeout(timeout);
          reject(new Error('Connection failed'));
        } else {
          setTimeout(checkConnection, 100);
        }
      };

      checkConnection();
    });
  }

  // Message handling
  send(data) {
    if (!this.isConnected) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      id: this._generateMessageId(),
      timestamp: Date.now(),
      data: data
    };

    try {
      this.socket.send(JSON.stringify(message));
      this.emit('message:sent', message);
      return message.id;
    } catch (error) {
      this._handleError(error);
      throw error;
    }
  }

  async sendAndWait(data, timeout = 5000) {
    const messageId = this.send(data);

    return new Promise((resolve, reject) => {
      const responseTimeout = setTimeout(() => {
        this.off('message:response', responseHandler);
        reject(new Error('Response timeout'));
      }, timeout);

      const responseHandler = (response) => {
        if (response.inReplyTo === messageId) {
          clearTimeout(responseTimeout);
          this.off('message:response', responseHandler);
          resolve(response);
        }
      };

      this.on('message:response', responseHandler);
    });
  }

  // Event system
  on(event, handler) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event).add(handler);

    return () => this.off(event, handler);
  }

  off(event, handler) {
    if (this.eventListeners.has(event)) {
      if (handler) {
        this.eventListeners.get(event).delete(handler);
      } else {
        this.eventListeners.delete(event);
      }
    }
  }

  emit(event, data) {
    if (this.config.debug) {
      console.log(`[WebSocket] Event: ${event}`, data);
    }

    if (this.eventListeners.has(event)) {
      this.eventListeners.get(event).forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error('WebSocket event handler error:', error);
        }
      });
    }

    // Also emit to global event system
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(`pyserv:ws:${event}`, { detail: data }));
    }
  }

  // Internal event handlers
  _handleOpen(event) {
    this.isConnected = true;
    this.isConnecting = false;
    this.reconnectAttempts = 0;

    // Start heartbeat
    this._startHeartbeat();

    // Flush message queue
    this._flushMessageQueue();

    this.emit('connected', { event });
    console.log('✅ WebSocket connected');
  }

  _handleClose(event) {
    this.isConnected = false;
    this.isConnecting = false;

    this._stopHeartbeat();

    const reason = this._getCloseReason(event.code);
    this.emit('disconnected', { event, reason });

    // Attempt reconnection if not intentional
    if (event.code !== 1000 && this.reconnectAttempts < this.config.maxReconnectAttempts) {
      this._scheduleReconnect();
    } else {
      console.log('❌ WebSocket disconnected permanently');
    }
  }

  _handleMessage(event) {
    try {
      const message = JSON.parse(event.data);

      // Handle different message types
      if (message.type === 'heartbeat') {
        this._handleHeartbeat(message);
      } else if (message.type === 'response') {
        this.emit('message:response', message);
      } else {
        this.emit('message', message);
        this.emit(`message:${message.type}`, message);
      }

    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      this.emit('message:error', { error, data: event.data });
    }
  }

  _handleError(error) {
    console.error('WebSocket error:', error);
    this.emit('error', { error });
  }

  _handleHeartbeat(message) {
    this.lastHeartbeat = Date.now();

    // Send heartbeat response
    this.send({
      type: 'heartbeat',
      timestamp: this.lastHeartbeat
    });
  }

  // Heartbeat management
  _startHeartbeat() {
    this._stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send({
          type: 'heartbeat',
          timestamp: Date.now()
        });
      }
    }, this.config.heartbeatInterval);
  }

  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  // Reconnection logic
  _scheduleReconnect() {
    this.reconnectAttempts++;

    const delay = this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`🔄 Attempting WebSocket reconnection ${this.reconnectAttempts}/${this.config.maxReconnectAttempts} in ${delay}ms`);

    this.reconnectTimer = setTimeout(async () => {
      try {
        await this.connect();
      } catch (error) {
        console.error('Reconnection failed:', error);
        if (this.reconnectAttempts < this.config.maxReconnectAttempts) {
          this._scheduleReconnect();
        } else {
          this.emit('reconnect:failed', { attempts: this.reconnectAttempts });
        }
      }
    }, delay);
  }

  _stopReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  // Message queuing
  _flushMessageQueue() {
    while (this.messageQueue.length > 0 && this.isConnected) {
      const message = this.messageQueue.shift();
      try {
        this.send(message);
      } catch (error) {
        // Put back in queue if send fails
        this.messageQueue.unshift(message);
        break;
      }
    }
  }

  // Utility methods
  _generateMessageId() {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  _getCloseReason(code) {
    const reasons = {
      1000: 'normal_closure',
      1001: 'going_away',
      1002: 'protocol_error',
      1003: 'unsupported_data',
      1004: 'reserved',
      1005: 'no_status_received',
      1006: 'abnormal_closure',
      1007: 'invalid_frame_payload_data',
      1008: 'policy_violation',
      1009: 'message_too_big',
      1010: 'mandatory_extension',
      1011: 'internal_server_error',
      1012: 'service_restart',
      1013: 'try_again_later',
      1014: 'bad_gateway',
      1015: 'tls_handshake'
    };

    return reasons[code] || 'unknown';
  }

  // Connection state
  getConnectionState() {
    return {
      isConnected: this.isConnected,
      isConnecting: this.isConnecting,
      reconnectAttempts: this.reconnectAttempts,
      lastHeartbeat: this.lastHeartbeat,
      queueSize: this.messageQueue.length
    };
  }

  // Health check
  async healthCheck() {
    if (!this.isConnected) {
      return { status: 'disconnected' };
    }

    const startTime = Date.now();
    try {
      await this.sendAndWait({ type: 'ping' }, 5000);
      const latency = Date.now() - startTime;
      return {
        status: 'healthy',
        latency,
        lastHeartbeat: this.lastHeartbeat
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error.message,
        lastHeartbeat: this.lastHeartbeat
      };
    }
  }

  // Debug utilities
  getDebugInfo() {
    return {
      url: this.config.url,
      isConnected: this.isConnected,
      isConnecting: this.isConnecting,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.config.maxReconnectAttempts,
      heartbeatInterval: this.config.heartbeatInterval,
      lastHeartbeat: this.lastHeartbeat,
      queueSize: this.messageQueue.length,
      eventListenerCount: this.eventListeners.size
    };
  }

  // Cleanup
  destroy() {
    this.disconnect();
    this.eventListeners.clear();
    this.messageQueue = [];

    if (typeof window !== 'undefined') {
      // Remove global event listeners
      const events = ['connected', 'disconnected', 'message', 'error'];
      events.forEach(event => {
        window.removeEventListener(`pyserv:ws:${event}`, () => {});
      });
    }
  }
}

// WebSocket message types
export const WS_MESSAGE_TYPES = {
  // System messages
  HEARTBEAT: 'heartbeat',
  PING: 'ping',
  PONG: 'pong',

  // User messages
  CHAT: 'chat',
  NOTIFICATION: 'notification',
  TYPING: 'typing',
  PRESENCE: 'presence',

  // Data updates
  MODEL_UPDATE: 'model_update',
  RECORD_UPDATE: 'record_update',
  BULK_UPDATE: 'bulk_update',

  // Custom events
  CUSTOM: 'custom'
};

// WebSocket utilities
export function createWebSocketClient(config) {
  return new WebSocketClient(config);
}

export function useWebSocket() {
  return window.__PYSERV_WS__;
}

// Global WebSocket instance
let globalWebSocket = null;

export function setGlobalWebSocket(ws) {
  globalWebSocket = ws;
  window.__PYSERV_WS__ = ws;
}

export function getGlobalWebSocket() {
  return globalWebSocket;
}
