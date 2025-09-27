/**
 * Button - Reusable Button Component
 * Provides a flexible button component with different variants,
 * sizes, states, and loading indicators
 */

import { Component } from '../core/Component.js';

export class Button extends Component {
  constructor(props = {}) {
    super(props);

    this.state = {
      loading: props.loading || false,
      disabled: props.disabled || false
    };
  }

  static getDefaultProps() {
    return {
      variant: 'primary', // primary, secondary, outline, ghost, link
      size: 'md', // xs, sm, md, lg, xl
      type: 'button', // button, submit, reset
      disabled: false,
      loading: false,
      fullWidth: false,
      rounded: false,
      icon: null,
      iconPosition: 'left', // left, right
      children: null
    };
  }

  componentWillUpdate(nextProps, nextState) {
    // Update loading state when props change
    if (nextProps.loading !== this.props.loading) {
      this.setState({ loading: nextProps.loading });
    }

    if (nextProps.disabled !== this.props.disabled) {
      this.setState({ disabled: nextProps.disabled });
    }
  }

  render() {
    const {
      variant = 'primary',
      size = 'md',
      type = 'button',
      disabled = false,
      loading = false,
      fullWidth = false,
      rounded = false,
      icon = null,
      iconPosition = 'left',
      children,
      className = '',
      onClick,
      ...otherProps
    } = this.props;

    const isDisabled = disabled || loading || this.state.disabled;
    const isLoading = loading || this.state.loading;

    const baseClasses = [
      'pyserv-button',
      `pyserv-button--${variant}`,
      `pyserv-button--${size}`,
      {
        'pyserv-button--disabled': isDisabled,
        'pyserv-button--loading': isLoading,
        'pyserv-button--full-width': fullWidth,
        'pyserv-button--rounded': rounded,
        'pyserv-button--icon-only': !children && icon
      },
      className
    ].filter(Boolean).join(' ');

    return this.createElement('button', {
      type,
      className: baseClasses,
      disabled: isDisabled,
      onClick: this._handleClick.bind(this),
      'aria-disabled': isDisabled,
      ...otherProps
    },
      // Loading spinner
      isLoading && this.createElement('span', { className: 'pyserv-button__spinner' }),

      // Icon (left)
      icon && iconPosition === 'left' && !isLoading && this.createElement('span', {
        className: 'pyserv-button__icon pyserv-button__icon--left'
      }, icon),

      // Content
      this.createElement('span', {
        className: 'pyserv-button__content',
        style: isLoading ? { opacity: 0 } : {}
      },
        children
      ),

      // Icon (right)
      icon && iconPosition === 'right' && !isLoading && this.createElement('span', {
        className: 'pyserv-button__icon pyserv-button__icon--right'
      }, icon)
    );
  }

  _handleClick(event) {
    if (this.state.disabled || this.state.loading) {
      event.preventDefault();
      return;
    }

    if (this.props.onClick) {
      this.props.onClick(event);
    }
  }

  // Public methods
  setLoading(loading) {
    this.setState({ loading });
  }

  setDisabled(disabled) {
    this.setState({ disabled });
  }

  focus() {
    if (this.element) {
      this.element.focus();
    }
  }

  blur() {
    if (this.element) {
      this.element.blur();
    }
  }
}

// Button group component
export class ButtonGroup extends Component {
  constructor(props = {}) {
    super(props);

    this.state = {
      selectedIndex: props.selectedIndex || 0,
      size: props.size || 'md',
      variant: props.variant || 'outline'
    };
  }

  render() {
    const { children, className = '', ...otherProps } = this.props;
    const { size, variant } = this.state;

    return this.createElement('div', {
      className: `pyserv-button-group pyserv-button-group--${size} pyserv-button-group--${variant} ${className}`,
      role: 'group',
      ...otherProps
    },
      children.map((child, index) => {
        if (!child) return null;

        return this.createElement(child.type, {
          ...child.props,
          key: index,
          size: size,
          variant: variant,
          className: `${child.props.className || ''} pyserv-button-group__item`,
          onClick: (event) => {
            this.setState({ selectedIndex: index });
            if (child.props.onClick) {
              child.props.onClick(event);
            }
          }
        }, child.props.children);
      })
    );
  }
}

// Icon button component
export class IconButton extends Component {
  constructor(props = {}) {
    super(props);

    this.state = {
      loading: props.loading || false
    };
  }

  render() {
    const { icon, children, className = '', ...otherProps } = this.props;
    const { loading } = this.state;

    return this.createElement(Button, {
      className: `pyserv-icon-button ${className}`,
      icon: loading ? null : icon,
      ...otherProps
    },
      loading && this.createElement('span', { className: 'pyserv-icon-button__spinner' }),
      children
    );
  }
}

// Floating action button
export class FloatingActionButton extends Component {
  constructor(props = {}) {
    super(props);

    this.state = {
      extended: props.extended || false,
      position: props.position || 'bottom-right'
    };
  }

  render() {
    const { icon, children, className = '', ...otherProps } = this.props;
    const { extended, position } = this.state;

    return this.createElement('button', {
      className: `pyserv-fab pyserv-fab--${position} ${extended ? 'pyserv-fab--extended' : ''} ${className}`,
      ...otherProps
    },
      this.createElement('span', { className: 'pyserv-fab__icon' }, icon),
      extended && this.createElement('span', { className: 'pyserv-fab__label' }, children)
    );
  }
}

// CSS Styles
const styles = `
  .pyserv-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border: 1px solid transparent;
    border-radius: var(--pyserv-radius-md);
    font-family: var(--pyserv-font-family);
    font-size: var(--pyserv-font-size-sm);
    font-weight: var(--pyserv-font-weight-medium);
    line-height: 1.5;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
    user-select: none;
    white-space: nowrap;
  }

  .pyserv-button:focus {
    outline: 2px solid var(--pyserv-focus);
    outline-offset: 2px;
  }

  .pyserv-button:disabled,
  .pyserv-button--disabled {
    opacity: 0.6;
    cursor: not-allowed;
    pointer-events: none;
  }

  .pyserv-button--loading {
    color: transparent;
    pointer-events: none;
  }

  .pyserv-button__spinner {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 1rem;
    height: 1rem;
    border: 2px solid transparent;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: pyserv-button-spin 1s linear infinite;
  }

  .pyserv-button__content {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .pyserv-button__icon {
    display: flex;
    align-items: center;
    font-size: 1rem;
  }

  /* Variants */
  .pyserv-button--primary {
    background: var(--pyserv-primary);
    color: white;
    border-color: var(--pyserv-primary);
  }

  .pyserv-button--primary:hover:not(.pyserv-button--disabled) {
    background: var(--pyserv-primary-hover);
    border-color: var(--pyserv-primary-hover);
  }

  .pyserv-button--secondary {
    background: var(--pyserv-secondary);
    color: white;
    border-color: var(--pyserv-secondary);
  }

  .pyserv-button--secondary:hover:not(.pyserv-button--disabled) {
    background: var(--pyserv-secondary-hover);
    border-color: var(--pyserv-secondary-hover);
  }

  .pyserv-button--outline {
    background: transparent;
    color: var(--pyserv-primary);
    border-color: var(--pyserv-primary);
  }

  .pyserv-button--outline:hover:not(.pyserv-button--disabled) {
    background: var(--pyserv-primary-light);
    color: var(--pyserv-primary-dark);
  }

  .pyserv-button--ghost {
    background: transparent;
    color: var(--pyserv-primary);
    border-color: transparent;
  }

  .pyserv-button--ghost:hover:not(.pyserv-button--disabled) {
    background: var(--pyserv-primary-light);
  }

  .pyserv-button--link {
    background: transparent;
    color: var(--pyserv-primary);
    border-color: transparent;
    text-decoration: underline;
    padding: 0.25rem 0;
  }

  .pyserv-button--link:hover:not(.pyserv-button--disabled) {
    color: var(--pyserv-primary-hover);
  }

  /* Sizes */
  .pyserv-button--xs {
    padding: 0.25rem 0.5rem;
    font-size: var(--pyserv-font-size-xs);
  }

  .pyserv-button--sm {
    padding: 0.375rem 0.75rem;
    font-size: var(--pyserv-font-size-xs);
  }

  .pyserv-button--md {
    padding: 0.5rem 1rem;
    font-size: var(--pyserv-font-size-sm);
  }

  .pyserv-button--lg {
    padding: 0.75rem 1.5rem;
    font-size: var(--pyserv-font-size-base);
  }

  .pyserv-button--xl {
    padding: 1rem 2rem;
    font-size: var(--pyserv-font-size-lg);
  }

  /* Full width */
  .pyserv-button--full-width {
    width: 100%;
  }

  /* Rounded */
  .pyserv-button--rounded {
    border-radius: var(--pyserv-radius-full);
  }

  /* Icon only */
  .pyserv-button--icon-only {
    padding: 0.5rem;
    width: auto;
    aspect-ratio: 1;
  }

  /* Button group */
  .pyserv-button-group {
    display: inline-flex;
    border-radius: var(--pyserv-radius-md);
    overflow: hidden;
    box-shadow: var(--pyserv-shadow-sm);
  }

  .pyserv-button-group__item {
    border-radius: 0;
    border-right-width: 0;
  }

  .pyserv-button-group__item:first-child {
    border-top-left-radius: var(--pyserv-radius-md);
    border-bottom-left-radius: var(--pyserv-radius-md);
  }

  .pyserv-button-group__item:last-child {
    border-top-right-radius: var(--pyserv-radius-md);
    border-bottom-right-radius: var(--pyserv-radius-md);
    border-right-width: 1px;
  }

  .pyserv-button-group__item:only-child {
    border-radius: var(--pyserv-radius-md);
  }

  /* Floating action button */
  .pyserv-fab {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--pyserv-primary);
    color: white;
    border: none;
    cursor: pointer;
    box-shadow: var(--pyserv-shadow-lg);
    transition: all 0.3s ease;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .pyserv-fab:hover {
    background: var(--pyserv-primary-hover);
    transform: scale(1.1);
    box-shadow: var(--pyserv-shadow-xl);
  }

  .pyserv-fab--extended {
    width: auto;
    height: auto;
    border-radius: var(--pyserv-radius-full);
    padding: 0 1.5rem;
    gap: 0.5rem;
  }

  .pyserv-fab__icon {
    font-size: 1.5rem;
  }

  .pyserv-fab__label {
    font-size: var(--pyserv-font-size-sm);
    font-weight: var(--pyserv-font-weight-medium);
  }

  .pyserv-fab--bottom-right {
    bottom: 2rem;
    right: 2rem;
  }

  .pyserv-fab--bottom-left {
    bottom: 2rem;
    left: 2rem;
  }

  .pyserv-fab--top-right {
    top: 2rem;
    right: 2rem;
  }

  .pyserv-fab--top-left {
    top: 2rem;
    left: 2rem;
  }

  /* Icon button */
  .pyserv-icon-button {
    padding: 0.5rem;
    border-radius: var(--pyserv-radius-md);
  }

  .pyserv-icon-button__spinner {
    width: 1rem;
    height: 1rem;
  }

  /* Animations */
  @keyframes pyserv-button-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  /* Responsive */
  @media (max-width: 768px) {
    .pyserv-button {
      font-size: var(--pyserv-font-size-base);
      padding: 0.75rem 1rem;
    }

    .pyserv-button--xs,
    .pyserv-button--sm {
      font-size: var(--pyserv-font-size-sm);
      padding: 0.5rem 0.75rem;
    }

    .pyserv-fab {
      bottom: 1rem;
      right: 1rem;
      width: 48px;
      height: 48px;
    }

    .pyserv-fab--extended {
      padding: 0 1rem;
    }
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = styles;
  document.head.appendChild(style);
}
