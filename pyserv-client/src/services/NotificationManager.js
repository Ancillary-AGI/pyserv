/**
 * NotificationManager - Toast and In-App Notifications
 * Provides a comprehensive notification system with different types,
 * positions, animations, and persistence
 */

export class NotificationManager {
  constructor(config = {}) {
    this.config = {
      position: config.position || 'top-right',
      duration: config.duration || 5000,
      maxNotifications: config.maxNotifications || 5,
      showProgress: config.showProgress !== false,
      pauseOnHover: config.pauseOnHover !== false,
      clickToClose: config.clickToClose !== false,
      newestOnTop: config.newestOnTop !== false,
      debug: config.debug || false,
      ...config
    };

    this.notifications = new Map();
    this.container = null;
    this.zIndex = 10000;

    this._initializeContainer();
    this._initializeStyles();
  }

  _initializeContainer() {
    if (typeof document === 'undefined') return;

    this.container = document.createElement('div');
    this.container.className = `pyserv-notifications pyserv-notifications--${this.config.position}`;
    this.container.setAttribute('role', 'log');
    this.container.setAttribute('aria-live', 'polite');
    this.container.setAttribute('aria-label', 'Notifications');

    document.body.appendChild(this.container);
  }

  _initializeStyles() {
    if (typeof document === 'undefined') return;

    const styleId = 'pyserv-notification-styles';
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      .pyserv-notifications {
        position: fixed;
        z-index: ${this.zIndex};
        pointer-events: none;
        display: flex;
        flex-direction: column;
        max-width: 400px;
        min-width: 300px;
      }

      .pyserv-notifications--top-right {
        top: 20px;
        right: 20px;
      }

      .pyserv-notifications--top-left {
        top: 20px;
        left: 20px;
      }

      .pyserv-notifications--bottom-right {
        bottom: 20px;
        right: 20px;
        flex-direction: column-reverse;
      }

      .pyserv-notifications--bottom-left {
        bottom: 20px;
        left: 20px;
        flex-direction: column-reverse;
      }

      .pyserv-notifications--top-center {
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
      }

      .pyserv-notifications--bottom-center {
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        flex-direction: column-reverse;
      }

      .pyserv-notification {
        pointer-events: auto;
        margin-bottom: 10px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        overflow: hidden;
        transform: translateX(100%);
        opacity: 0;
        transition: all 0.3s ease;
        position: relative;
      }

      .pyserv-notification--show {
        transform: translateX(0);
        opacity: 1;
      }

      .pyserv-notification--success {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
      }

      .pyserv-notification--error {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
      }

      .pyserv-notification--warning {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
      }

      .pyserv-notification--info {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: white;
      }

      .pyserv-notification__content {
        padding: 16px;
        display: flex;
        align-items: flex-start;
        gap: 12px;
      }

      .pyserv-notification__icon {
        flex-shrink: 0;
        width: 20px;
        height: 20px;
        margin-top: 2px;
      }

      .pyserv-notification__text {
        flex: 1;
        font-size: 14px;
        line-height: 1.4;
      }

      .pyserv-notification__title {
        font-weight: 600;
        margin-bottom: 4px;
      }

      .pyserv-notification__message {
        font-weight: 400;
        opacity: 0.9;
      }

      .pyserv-notification__close {
        background: none;
        border: none;
        color: currentColor;
        cursor: pointer;
        padding: 4px;
        margin: -4px -4px -4px 8px;
        border-radius: 4px;
        opacity: 0.7;
        transition: opacity 0.2s ease;
      }

      .pyserv-notification__close:hover {
        opacity: 1;
      }

      .pyserv-notification__progress {
        position: absolute;
        bottom: 0;
        left: 0;
        height: 3px;
        background: rgba(255, 255, 255, 0.3);
        transition: width linear;
      }

      .pyserv-notification__actions {
        padding: 12px 16px;
        background: rgba(0, 0, 0, 0.1);
        display: flex;
        gap: 8px;
        justify-content: flex-end;
      }

      .pyserv-notification__action {
        background: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: white;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s ease;
      }

      .pyserv-notification__action:hover {
        background: rgba(255, 255, 255, 0.3);
      }

      @keyframes pyserv-notification-shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
      }

      .pyserv-notification--shake {
        animation: pyserv-notification-shake 0.5s ease-in-out;
      }
    `;

    document.head.appendChild(style);
  }

  // Notification methods
  show(message, type = 'info', options = {}) {
    const notification = this._createNotification(message, type, options);
    const id = notification.id;

    this.notifications.set(id, notification);
    this._renderNotification(notification);

    // Auto-remove after duration
    if (notification.duration > 0) {
      this._scheduleRemoval(id, notification.duration);
    }

    // Limit number of notifications
    this._enforceMaxNotifications();

    this.emit('notification:shown', { notification, id });

    return id;
  }

  success(message, options = {}) {
    return this.show(message, 'success', options);
  }

  error(message, options = {}) {
    return this.show(message, 'error', { ...options, duration: 0 });
  }

  warning(message, options = {}) {
    return this.show(message, 'warning', options);
  }

  info(message, options = {}) {
    return this.show(message, 'info', options);
  }

  _createNotification(message, type, options) {
    const id = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    let title = options.title;
    let duration = options.duration !== undefined ? options.duration : this.config.duration;

    // Auto-generate title based on type
    if (!title) {
      switch (type) {
        case 'success':
          title = 'Success';
          break;
        case 'error':
          title = 'Error';
          break;
        case 'warning':
          title = 'Warning';
          break;
        case 'info':
        default:
          title = 'Info';
          break;
      }
    }

    return {
      id,
      type,
      title,
      message,
      duration,
      actions: options.actions || [],
      persistent: options.persistent || false,
      icon: options.icon,
      data: options.data,
      timestamp: Date.now(),
      progress: 100,
      paused: false
    };
  }

  _renderNotification(notification) {
    if (!this.container) return;

    const element = document.createElement('div');
    element.className = `pyserv-notification pyserv-notification--${notification.type}`;
    element.setAttribute('role', 'alert');
    element.setAttribute('aria-live', 'assertive');

    const icon = this._getIcon(notification.type);

    element.innerHTML = `
      <div class="pyserv-notification__content">
        ${icon ? `<div class="pyserv-notification__icon">${icon}</div>` : ''}
        <div class="pyserv-notification__text">
          <div class="pyserv-notification__title">${this._escapeHtml(notification.title)}</div>
          <div class="pyserv-notification__message">${this._escapeHtml(notification.message)}</div>
        </div>
        <button class="pyserv-notification__close" aria-label="Close notification">×</button>
      </div>
      ${notification.actions.length > 0 ? `
        <div class="pyserv-notification__actions">
          ${notification.actions.map(action => `
            <button class="pyserv-notification__action" data-action="${action.key}">
              ${this._escapeHtml(action.label)}
            </button>
          `).join('')}
        </div>
      ` : ''}
      ${this.config.showProgress && notification.duration > 0 ? `
        <div class="pyserv-notification__progress" style="width: 100%"></div>
      ` : ''}
    `;

    // Add event listeners
    const closeBtn = element.querySelector('.pyserv-notification__close');
    closeBtn.addEventListener('click', () => this.remove(notification.id));

    // Add action listeners
    const actionBtns = element.querySelectorAll('.pyserv-notification__action');
    actionBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const actionKey = e.target.dataset.action;
        const action = notification.actions.find(a => a.key === actionKey);
        if (action && action.handler) {
          action.handler(notification);
        }
        if (!notification.persistent) {
          this.remove(notification.id);
        }
      });
    });

    // Pause on hover
    if (this.config.pauseOnHover) {
      element.addEventListener('mouseenter', () => {
        notification.paused = true;
        this._updateProgress(notification.id);
      });

      element.addEventListener('mouseleave', () => {
        notification.paused = false;
        this._updateProgress(notification.id);
      });
    }

    // Click to close
    if (this.config.clickToClose) {
      element.addEventListener('click', (e) => {
        if (e.target === element) {
          this.remove(notification.id);
        }
      });
    }

    this.container.appendChild(element);

    // Trigger animation
    requestAnimationFrame(() => {
      element.classList.add('pyserv-notification--show');
    });
  }

  _getIcon(type) {
    const icons = {
      success: '✓',
      error: '⚠',
      warning: '⚠',
      info: 'ℹ'
    };

    return icons[type] || icons.info;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  _scheduleRemoval(id, duration) {
    if (duration <= 0) return;

    const startTime = Date.now();
    const updateInterval = 50;

    const updateProgress = () => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, duration - elapsed);
      const progress = (remaining / duration) * 100;

      const notification = this.notifications.get(id);
      if (notification && !notification.paused) {
        notification.progress = progress;

        if (remaining <= 0) {
          this.remove(id);
        } else {
          this._updateProgress(id);
          setTimeout(updateProgress, updateInterval);
        }
      }
    };

    setTimeout(updateProgress, updateInterval);
  }

  _updateProgress(id) {
    const notification = this.notifications.get(id);
    if (!notification) return;

    const element = this.container?.querySelector(`[data-notification-id="${id}"] .pyserv-notification__progress`);
    if (element) {
      element.style.width = `${notification.progress}%`;
    }
  }

  _enforceMaxNotifications() {
    if (this.notifications.size <= this.config.maxNotifications) return;

    const toRemove = this.notifications.size - this.config.maxNotifications;
    const notificationsArray = Array.from(this.notifications.entries());

    // Remove oldest non-persistent notifications first
    const removable = notificationsArray
      .filter(([_, notification]) => !notification.persistent)
      .slice(0, toRemove);

    removable.forEach(([id]) => this.remove(id));
  }

  // Notification management
  remove(id) {
    const notification = this.notifications.get(id);
    if (!notification) return;

    const element = this.container?.querySelector(`[data-notification-id="${id}"]`);
    if (element) {
      element.classList.remove('pyserv-notification--show');
      setTimeout(() => {
        if (element.parentNode) {
          element.parentNode.removeChild(element);
        }
      }, 300);
    }

    this.notifications.delete(id);
    this.emit('notification:removed', { notification, id });
  }

  removeAll() {
    const ids = Array.from(this.notifications.keys());
    ids.forEach(id => this.remove(id));
  }

  removeByType(type) {
    const ids = Array.from(this.notifications.entries())
      .filter(([_, notification]) => notification.type === type)
      .map(([id]) => id);

    ids.forEach(id => this.remove(id));
  }

  // Update notification
  update(id, updates) {
    const notification = this.notifications.get(id);
    if (!notification) return;

    Object.assign(notification, updates);
    this._updateNotificationElement(id);
    this.emit('notification:updated', { notification, id, updates });
  }

  _updateNotificationElement(id) {
    const element = this.container?.querySelector(`[data-notification-id="${id}"]`);
    if (!element) return;

    const notification = this.notifications.get(id);

    // Update content
    const titleEl = element.querySelector('.pyserv-notification__title');
    const messageEl = element.querySelector('.pyserv-notification__message');

    if (titleEl) titleEl.textContent = notification.title;
    if (messageEl) messageEl.textContent = notification.message;

    // Update type class
    element.className = element.className.replace(/pyserv-notification--\w+/, `pyserv-notification--${notification.type}`);
  }

  // Event system
  emit(event, data) {
    if (this.config.debug) {
      console.log(`[NotificationManager] Event: ${event}`, data);
    }

    // Emit to global event system
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(`pyserv:notification:${event}`, { detail: data }));
    }
  }

  on(event, handler) {
    if (typeof window !== 'undefined') {
      window.addEventListener(`pyserv:notification:${event}`, (e) => handler(e.detail));
    }
  }

  // Utility methods
  getNotifications(type) {
    const notifications = Array.from(this.notifications.values());

    if (type) {
      return notifications.filter(n => n.type === type);
    }

    return notifications;
  }

  getNotification(id) {
    return this.notifications.get(id);
  }

  // Debug utilities
  getDebugInfo() {
    return {
      notificationCount: this.notifications.size,
      maxNotifications: this.config.maxNotifications,
      position: this.config.position,
      containerExists: !!this.container,
      notifications: Array.from(this.notifications.entries()).map(([id, notification]) => ({
        id,
        type: notification.type,
        title: notification.title,
        persistent: notification.persistent,
        progress: notification.progress
      }))
    };
  }

  // Cleanup
  destroy() {
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }

    this.notifications.clear();

    // Remove styles
    const style = document.getElementById('pyserv-notification-styles');
    if (style) {
      style.remove();
    }
  }
}

// Notification types
export const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info'
};

// Notification utilities
export function useNotifications() {
  return window.__PYSERV_NOTIFICATIONS__;
}

// Global notification instance
let globalNotifications = null;

export function setGlobalNotifications(notifications) {
  globalNotifications = notifications;
  window.__PYSERV_NOTIFICATIONS__ = notifications;
}

export function getGlobalNotifications() {
  return globalNotifications;
}

// Convenience functions
export function showNotification(message, type = 'info', options = {}) {
  const notifications = getGlobalNotifications();
  if (notifications) {
    return notifications.show(message, type, options);
  }
}

export function showSuccess(message, options = {}) {
  return showNotification(message, 'success', options);
}

export function showError(message, options = {}) {
  return showNotification(message, 'error', { ...options, duration: 0 });
}

export function showWarning(message, options = {}) {
  return showNotification(message, 'warning', options);
}

export function showInfo(message, options = {}) {
  return showNotification(message, 'info', options);
}
