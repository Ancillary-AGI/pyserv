/**
 * Pyserv Client - TypeScript Type Definitions
 * Comprehensive type definitions for the Pyserv Client framework
 */

// Framework core types
export interface ComponentProps {
  [key: string]: any;
  children?: any;
  className?: string;
  style?: Record<string, string | number>;
  key?: string | number;
}

export interface ComponentState {
  [key: string]: any;
}

export interface ComponentContext {
  [key: string]: any;
}

// Component lifecycle
export interface ComponentLifecycle<P = ComponentProps, S = ComponentState> {
  componentWillMount?(): void;
  componentDidMount?(): void;
  componentWillUpdate?(nextProps: P, nextState: S): void;
  componentDidUpdate?(prevProps: P, prevState: S): void;
  componentWillUnmount?(): void;
  shouldComponentUpdate?(nextProps: P, nextState: S): boolean;
  componentDidCatch?(error: Error, errorInfo: ErrorInfo): void;
}

// Error handling
export interface ErrorInfo {
  componentStack: string;
}

// Event handling
export type EventHandler<T = Event> = (event: T) => void;
export type ChangeEventHandler<T = any> = (event: ChangeEvent<T>) => void;
export type FormEventHandler<T = any> = (event: FormEvent<T>) => void;

export interface ChangeEvent<T = any> extends Event {
  target: T;
}

export interface FormEvent<T = any> extends Event {
  target: T;
}

// Reactive system types
export interface ReactiveOptions {
  deep?: boolean;
  immediate?: boolean;
}

export interface Ref<T = any> {
  value: T;
  readonly current: T;
}

export interface Computed<T = any> {
  readonly value: T;
  readonly effect: Effect;
}

export interface Effect {
  run(): void;
  stop(): void;
}

export interface WatchOptions extends ReactiveOptions {
  flush?: 'pre' | 'post' | 'sync';
  onTrack?: () => void;
  onTrigger?: () => void;
}

export interface WatchCallback<T = any> {
  (value: T, oldValue: T): void;
}

// Store types
export interface StoreState {
  [key: string]: any;
}

export interface StoreOptions {
  name?: string;
  initialState?: StoreState;
  middleware?: Middleware[];
  persistence?: boolean;
  persistenceKey?: string;
}

export interface Middleware {
  (state: StoreState, action: Action): StoreState | void;
}

export interface Action {
  type: string;
  payload?: any;
  meta?: any;
}

export interface Store<S = StoreState> {
  getState(): S;
  setState(updater: Partial<S> | ((state: S) => Partial<S>), action?: string): void;
  dispatch(action: Action): void;
  subscribe(listener: (state: S, prevState: S, action: string) => void): () => void;
  replaceState(newState: S): void;
  reset(): void;
}

// Router types
export interface Route {
  path: string;
  name?: string;
  component?: ComponentClass | string;
  components?: Record<string, ComponentClass | string>;
  redirect?: string | ((route: Route, currentRoute: Route) => string);
  alias?: string | string[];
  props?: boolean | Record<string, any> | ((route: Route) => Record<string, any>);
  meta?: Record<string, any>;
  children?: Route[];
  beforeEnter?: (to: Route, from: Route, next: (path?: string) => void) => void | string | Promise<void | string>;
  beforeLeave?: (to: Route, from: Route, next: (path?: string) => void) => void | string | Promise<void | string>;
}

export interface RouteMatch {
  route: Route;
  params: Record<string, string>;
  query: Record<string, string>;
  hash: string;
  fullPath: string;
  matched: Route[];
  meta: Record<string, any>;
}

export interface RouterOptions {
  mode?: 'history' | 'hash';
  base?: string;
  scrollBehavior?: 'auto' | ((to: Route, from: Route) => void);
  linkActiveClass?: string;
  linkExactActiveClass?: string;
}

export interface Router {
  addRoute(route: Route | Route[]): Router;
  navigate(path: string, options?: { replace?: boolean; state?: any }): Promise<void>;
  go(n: number): void;
  back(): void;
  forward(): void;
  push(path: string, state?: any): void;
  replace(path: string, state?: any): void;
  getCurrentRoute(): RouteMatch | null;
  getRoutes(): Route[];
  resolve(path: string, params?: Record<string, any>): string;
  beforeEach(guard: (to: Route, from: Route, next: (path?: string) => void) => void): void;
  afterEach(hook: (to: Route, from: Route) => void): void;
  beforeResolve(hook: (to: Route, from: Route) => void): void;
  afterResolve(hook: (to: Route, from: Route) => void): void;
  init(container?: string): void;
  destroy(): void;
}

// Authentication types
export interface User {
  id: string | number;
  username?: string;
  email?: string;
  name?: string;
  avatar?: string;
  role?: string;
  permissions?: string[];
  [key: string]: any;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
  loading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  username?: string;
  email?: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  confirmPassword?: string;
  [key: string]: any;
}

export interface AuthOptions {
  apiClient?: ApiClient;
  storageKey?: string;
  refreshThreshold?: number;
  autoRefresh?: boolean;
  redirectOnAuth?: boolean;
  loginRoute?: string;
  dashboardRoute?: string;
}

export interface Auth {
  login(credentials: LoginCredentials): Promise<{ success: boolean; user?: User; error?: string }>;
  logout(): Promise<void>;
  register(userData: RegisterData): Promise<{ success: boolean; user?: User; error?: string }>;
  refresh(): Promise<{ success: boolean }>;
  updateProfile(profileData: Partial<User>): Promise<{ success: boolean; user?: User; error?: string }>;
  changePassword(passwordData: { currentPassword: string; newPassword: string }): Promise<{ success: boolean; error?: string }>;
  resetPassword(email: string): Promise<{ success: boolean; error?: string }>;
  readonly isAuthenticated: boolean;
  readonly user: User | null;
  readonly token: string | null;
  readonly refreshToken: string | null;
  readonly loading: boolean;
  readonly error: string | null;
  hasRole(role: string): boolean;
  hasPermission(permission: string): boolean;
  getUserProperty(path: string, defaultValue?: any): any;
  getTokenInfo(): TokenInfo | null;
  isTokenExpired(): boolean;
  extendSession(): void;
  invalidateSession(): void;
  on(event: string, handler: (data: any) => void): () => void;
  emit(event: string, data: any): void;
}

export interface TokenInfo {
  exp: number;
  iat: number;
  user_id: string | number;
  username: string;
  roles: string[];
  permissions: string[];
}

// API Client types
export interface ApiClientConfig {
  baseURL?: string;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  headers?: Record<string, string>;
  cache?: boolean;
  cacheTTL?: number;
}

export interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  params?: Record<string, any>;
  data?: any;
  timeout?: number;
  retries?: number;
  cache?: boolean;
}

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
  headers: Record<string, string>;
  config: RequestConfig;
  request: any;
}

export interface ApiClient {
  get<T = any>(url: string, params?: Record<string, any>, config?: RequestConfig): Promise<ApiResponse<T>>;
  post<T = any>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>>;
  put<T = any>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>>;
  patch<T = any>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>>;
  delete<T = any>(url: string, config?: RequestConfig): Promise<ApiResponse<T>>;
  request<T = any>(url: string, config: RequestConfig): Promise<ApiResponse<T>>;
  uploadFile(url: string, file: File, metadata?: Record<string, any>): Promise<ApiResponse>;
  downloadFile(url: string, filename?: string): Promise<ApiResponse>;
  batch(requests: Array<{ url: string; config: RequestConfig }>): Promise<ApiResponse[]>;
  healthCheck(): Promise<{ status: string; error?: string }>;
  getMetrics(): Promise<any>;
  setBaseURL(url: string): void;
  setAuthToken(token: string): void;
  removeAuthToken(): void;
  setHeader(key: string, value: string): void;
  removeHeader(key: string): void;
  clearCache(): void;
  addRequestInterceptor(interceptor: (url: string, config: RequestConfig) => any): void;
  addResponseInterceptor(interceptor: (response: ApiResponse) => any): void;
  addErrorInterceptor(interceptor: (error: Error, attempt: number, maxRetries: number) => boolean): void;
}

// WebSocket types
export interface WebSocketConfig {
  url?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  messageQueueSize?: number;
  debug?: boolean;
}

export interface WebSocketMessage {
  id?: string;
  type?: string;
  timestamp?: number;
  data?: any;
  inReplyTo?: string;
}

export interface WebSocketClient {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  send(data: any): string;
  sendAndWait(data: any, timeout?: number): Promise<any>;
  on(event: string, handler: (data: any) => void): () => void;
  off(event: string, handler?: (data: any) => void): void;
  emit(event: string, data: any): void;
  getConnectionState(): {
    isConnected: boolean;
    isConnecting: boolean;
    reconnectAttempts: number;
    lastHeartbeat: number | null;
    queueSize: number;
  };
  healthCheck(): Promise<{ status: string; latency?: number; error?: string }>;
}

// Notification types
export interface NotificationOptions {
  title?: string;
  duration?: number;
  persistent?: boolean;
  actions?: Array<{
    key: string;
    label: string;
    handler: (notification: Notification) => void;
  }>;
  icon?: string;
  data?: any;
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration: number;
  actions: Array<{
    key: string;
    label: string;
    handler: (notification: Notification) => void;
  }>;
  persistent: boolean;
  icon?: string;
  data?: any;
  timestamp: number;
  progress: number;
  paused: boolean;
}

export interface NotificationManager {
  show(message: string, type?: 'success' | 'error' | 'warning' | 'info', options?: NotificationOptions): string;
  success(message: string, options?: NotificationOptions): string;
  error(message: string, options?: NotificationOptions): string;
  warning(message: string, options?: NotificationOptions): string;
  info(message: string, options?: NotificationOptions): string;
  remove(id: string): void;
  removeAll(): void;
  removeByType(type: 'success' | 'error' | 'warning' | 'info'): void;
  update(id: string, updates: Partial<Notification>): void;
  getNotifications(type?: 'success' | 'error' | 'warning' | 'info'): Notification[];
  getNotification(id: string): Notification | undefined;
  on(event: string, handler: (data: any) => void): void;
  emit(event: string, data: any): void;
}

// Theme types
export interface ThemeColors {
  primary: string;
  'primary-hover': string;
  'primary-light': string;
  'primary-dark': string;
  secondary: string;
  'secondary-hover': string;
  'secondary-light': string;
  'secondary-dark': string;
  background: string;
  'background-secondary': string;
  'background-tertiary': string;
  surface: string;
  card: string;
  'text-primary': string;
  'text-secondary': string;
  'text-tertiary': string;
  'text-inverse': string;
  success: string;
  'success-light': string;
  'success-dark': string;
  error: string;
  'error-light': string;
  'error-dark': string;
  warning: string;
  'warning-light': string;
  'warning-dark': string;
  info: string;
  'info-light': string;
  'info-dark': string;
  border: string;
  'border-light': string;
  'border-dark': string;
  shadow: string;
  'shadow-light': string;
  'shadow-dark': string;
  focus: string;
  overlay: string;
  disabled: string;
  placeholder: string;
  [key: string]: string;
}

export interface ThemeSpacing {
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  '3xl': string;
  [key: string]: string;
}

export interface ThemeTypography {
  fontFamily: string;
  fontSize: {
    xs: string;
    sm: string;
    base: string;
    lg: string;
    xl: string;
    '2xl': string;
    '3xl': string;
    '4xl': string;
  };
  fontWeight: {
    normal: string;
    medium: string;
    semibold: string;
    bold: string;
  };
  lineHeight: {
    tight: string;
    normal: string;
    relaxed: string;
  };
}

export interface ThemeBorderRadius {
  none: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  full: string;
}

export interface ThemeShadows {
  none: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
}

export interface ThemeTransitions {
  fast: string;
  normal: string;
  slow: string;
}

export interface Theme {
  name: string;
  description?: string;
  colors?: Partial<ThemeColors>;
  spacing?: Partial<ThemeSpacing>;
  typography?: Partial<ThemeTypography>;
  borderRadius?: Partial<ThemeBorderRadius>;
  shadows?: Partial<ThemeShadows>;
  transitions?: Partial<ThemeTransitions>;
  [key: string]: any;
}

export interface ThemeManager {
  registerTheme(name: string, theme: Theme): void;
  unregisterTheme(name: string): void;
  getTheme(name: string): Theme | undefined;
  getCurrentTheme(): Theme | undefined;
  getThemes(): Array<{ key: string } & Theme>;
  setTheme(themeName: string): boolean;
  setCSSVariable(name: string, value: string): void;
  getCSSVariable(name: string): string | undefined;
  lightenColor(color: string, amount?: number): string;
  darkenColor(color: string, amount?: number): string;
  readonly currentTheme: string;
  readonly isDarkTheme: boolean;
  getThemeColors(): Partial<ThemeColors>;
  on(event: string, handler: (data: any) => void): () => void;
  emit(event: string, data: any): void;
}

// Cache types
export interface CacheEntry {
  value: any;
  expires: number;
  created: number;
  ttl: number;
  compressed: boolean;
  size: number;
}

export interface CacheConfig {
  defaultTTL?: number;
  maxMemorySize?: number;
  maxLocalStorageSize?: number;
  maxSessionStorageSize?: number;
  enableCompression?: boolean;
  compressionThreshold?: number;
  enablePersistence?: boolean;
  enableMetrics?: boolean;
  debug?: boolean;
}

export interface CacheStrategy {
  memory?: boolean;
  localStorage?: boolean;
  sessionStorage?: boolean;
  indexedDB?: boolean;
}

export interface CacheOptions extends CacheStrategy {
  ttl?: number;
  compress?: boolean;
}

export interface CacheStats {
  memory: {
    size: number;
    maxSize: number;
    entries: number;
    utilization: number;
  };
  localStorage: {
    entries: number;
    maxSize: number;
  };
  sessionStorage: {
    entries: number;
    maxSize: number;
  };
  metrics: {
    hits: number;
    misses: number;
    sets: number;
    deletes: number;
    evictions: number;
  };
  config: CacheConfig;
}

export interface CacheManager {
  get(key: string, options?: CacheOptions): Promise<any>;
  set(key: string, value: any, options?: CacheOptions): Promise<void>;
  delete(key: string, options?: CacheStrategy): Promise<void>;
  clear(options?: CacheStrategy): Promise<void>;
  getOrSet(key: string, factory: () => Promise<any>, options?: CacheOptions): Promise<any>;
  invalidate(pattern: string): Promise<number>;
  batchGet(keys: string[], options?: CacheOptions): Promise<any[]>;
  batchSet(keyValuePairs: Array<[string, any]>, options?: CacheOptions): Promise<void>;
  batchDelete(keys: string[], options?: CacheStrategy): Promise<void>;
  getStats(): CacheStats;
  getHitRate(): number;
}

// Framework types
export interface FrameworkConfig {
  baseURL?: string;
  apiVersion?: string;
  enableWebSocket?: boolean;
  enableAuth?: boolean;
  enableNotifications?: boolean;
  enableTheme?: boolean;
  enableCache?: boolean;
  debug?: boolean;
  apiTimeout?: number;
  apiRetries?: number;
  authStorageKey?: string;
  authRefreshThreshold?: number;
  notificationPosition?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
  notificationDuration?: number;
  maxNotifications?: number;
  defaultTheme?: string;
  themeStorageKey?: string;
  cacheTTL?: number;
  cacheMaxSize?: number;
  wsReconnectInterval?: number;
  wsMaxReconnectAttempts?: number;
  [key: string]: any;
}

export interface FrameworkServices {
  api: ApiClient;
  websocket?: WebSocketClient;
  auth?: Auth;
  notifications?: NotificationManager;
  theme?: ThemeManager;
  cache?: CacheManager;
}

export interface FrameworkStores {
  app: Store;
  ui: Store;
  [key: string]: Store;
}

export interface PyservClientFramework {
  readonly config: FrameworkConfig;
  readonly initialized: boolean;
  readonly services: FrameworkServices;
  readonly stores: FrameworkStores;
  getService(name: keyof FrameworkServices): any;
  getStore(name: string): Store | undefined;
  registerComponent(name: string, componentFactory: () => Promise<any>): void;
  getComponent(name: string): Promise<any>;
  registerStore(name: string, store: Store): void;
  registerService(name: string, service: any): void;
  emit(event: string, data: any): void;
  on(event: string, handler: (data: any) => void): () => void;
  fetch(url: string, options?: RequestConfig): Promise<ApiResponse>;
  navigate(path: string, state?: any): void;
  showNotification(message: string, type?: 'success' | 'error' | 'warning' | 'info', options?: NotificationOptions): void;
  setTheme(theme: string): void;
  mount(selector: string): Promise<void>;
  destroy(): void;
}

// Component types
export type ComponentClass<P = ComponentProps, S = ComponentState> = new (props?: P) => Component<P, S>;

export abstract class Component<P = ComponentProps, S = ComponentState> {
  constructor(props?: P);
  readonly props: P;
  readonly state: S;
  readonly element: HTMLElement | null;
  readonly mounted: boolean;
  componentWillMount?(): void;
  componentDidMount?(): void;
  componentWillUpdate?(nextProps: P, nextState: S): void;
  componentDidUpdate?(prevProps: P, prevState: S): void;
  componentWillUnmount?(): void;
  shouldComponentUpdate?(nextProps: P, nextState: S): boolean;
  componentDidCatch?(error: Error, errorInfo: ErrorInfo): void;
  render(): string | HTMLElement;
  setState(newState: Partial<S> | ((prevState: S) => Partial<S>), callback?: () => void): void;
  setProps(newProps: Partial<P>): void;
  createElement(tagName: string, props?: any, ...children: any[]): HTMLElement;
  renderToDOM(): HTMLElement;
  mount(container: string | HTMLElement): void;
  unmount(): void;
  destroy(): void;
  addEventListener(event: string, handler: EventHandler): void;
  removeEventListener(event: string, handler: EventHandler): void;
  setRef(name: string, element: HTMLElement): void;
  getRef(name: string): HTMLElement | undefined;
  querySelector(selector: string): Element | null;
  querySelectorAll(selector: string): NodeListOf<Element>;
  addClass(className: string): void;
  removeClass(className: string): void;
  toggleClass(className: string): void;
  hasClass(className: string): boolean;
  fadeIn(duration?: number): void;
  fadeOut(duration?: number): void;
  slideDown(duration?: number): void;
  slideUp(duration?: number): void;
  focus(): void;
  blur(): void;
  setAriaLabel(label: string): void;
  setAriaDescribedBy(id: string): void;
  setRole(role: string): void;
  useState<T>(initialValue: T): [T, (value: T | ((prevValue: T) => T)) => void];
  useEffect(effect: () => void | (() => void), deps?: any[]): void;
  useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T;
  useMemo<T>(compute: () => T, deps: any[]): T;
  static create<P = ComponentProps>(props?: P): Component<P>;
  static render<P = ComponentProps>(props?: P): HTMLElement;
}

// Functional Component types
export interface FunctionalComponent<P = ComponentProps> {
  (props: P): JSX.Element | string | null;
  displayName?: string;
  defaultProps?: Partial<P>;
}

export interface FunctionalComponentInstance<P = ComponentProps, S = ComponentState> {
  props: P;
  state: S;
  hooks: Map<number, any>;
  hookIndex: number;
  element: HTMLElement | null;
  mounted: boolean;
  useState<T>(initialValue: T): [T, (value: T | ((prevValue: T) => T)) => void];
  useEffect(effect: () => void | (() => void), deps?: any[]): void;
  useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T;
  useMemo<T>(compute: () => T, deps: any[]): T;
  useRef<T>(initialValue: T): { current: T };
  useContext<T>(context: Context<T>): T;
  useReducer<R extends (state: S, action: any) => S, I>(
    reducer: R,
    initialState: I
  ): [S, (action: any) => void];
  useImperativeHandle<T, R extends T>(
    ref: Ref<T | null>,
    createHandle: () => R,
    deps?: any[]
  ): void;
  render(): JSX.Element | string | null;
  mount(container: string | HTMLElement): void;
  unmount(): void;
  destroy(): void;
}

export type FC<P = ComponentProps> = FunctionalComponent<P>;

export interface FunctionComponentFactory {
  create<P = ComponentProps>(renderFunction: (props: P) => JSX.Element | string | null): FunctionalComponent<P>;
  render<P = ComponentProps>(component: FunctionalComponent<P>, props: P): JSX.Element | string | null;
}

// Hook types
export interface HookContext {
  currentComponent: FunctionalComponentInstance | null;
  hookIndex: number;
  hooks: Map<string, any>;
}

export interface UseStateHook<T> {
  value: T;
  setValue: (value: T | ((prevValue: T) => T)) => void;
  subscribers: Set<() => void>;
}

export interface UseEffectHook {
  effect: () => void | (() => void);
  deps?: any[];
  cleanup?: () => void;
  prevDeps?: any[];
}

export interface UseCallbackHook<T extends (...args: any[]) => any> {
  callback: T;
  deps: any[];
  memoizedCallback: T;
}

export interface UseMemoHook<T> {
  compute: () => T;
  deps: any[];
  value: T;
  prevDeps?: any[];
}

export interface UseRefHook<T> {
  current: T;
}

export interface UseContextHook<T> {
  context: Context<T>;
  value: T;
  subscribers: Set<() => void>;
}

export interface UseReducerHook<R extends (state: any, action: any) => any, I> {
  reducer: R;
  state: I;
  dispatch: (action: any) => void;
}

export interface UseImperativeHandleHook<T, R extends T> {
  ref: Ref<T | null>;
  createHandle: () => R;
  deps?: any[];
}

// Context types
export interface Context<T> {
  Provider: FunctionalComponent<{ value: T; children: any }>;
  Consumer: FunctionalComponent<{ children: (value: T) => any }>;
  displayName?: string;
  _currentValue: T;
  _defaultValue: T;
  _subscribers: Set<() => void>;
}

export interface ContextFactory {
  create<T>(defaultValue: T): Context<T>;
}

// JSX types
export namespace JSX {
  interface Element {
    $$typeof: Symbol;
    tagName: string;
    props: Record<string, any>;
    children: Array<Element | string>;
    key: string | number | null;
    ref: any;
    _id: string;
  }

  interface Fragment {
    $$typeof: Symbol;
    children: Array<Element | string>;
    props: Record<string, any>;
    key: string | number | null;
    _id: string;
  }

  interface IntrinsicElements {
    [elemName: string]: any;
    div: HTMLAttributes & { children?: any };
    span: HTMLAttributes & { children?: any };
    button: HTMLAttributes & { children?: any };
    input: InputHTMLAttributes & { children?: any };
    form: FormHTMLAttributes & { children?: any };
    h1: HTMLAttributes & { children?: any };
    h2: HTMLAttributes & { children?: any };
    h3: HTMLAttributes & { children?: any };
    h4: HTMLAttributes & { children?: any };
    h5: HTMLAttributes & { children?: any };
    h6: HTMLAttributes & { children?: any };
    p: HTMLAttributes & { children?: any };
    ul: HTMLAttributes & { children?: any };
    li: HTMLAttributes & { children?: any };
    a: AnchorHTMLAttributes & { children?: any };
    img: ImgHTMLAttributes;
    select: SelectHTMLAttributes & { children?: any };
    option: OptionHTMLAttributes & { children?: any };
    textarea: TextareaHTMLAttributes & { children?: any };
    label: LabelHTMLAttributes & { children?: any };
  }

  interface HTMLAttributes {
    className?: string;
    id?: string;
    style?: CSSProperties;
    children?: any;
    key?: string | number;
    ref?: any;
    onClick?: (event: MouseEvent) => void;
    onChange?: (event: Event) => void;
    onInput?: (event: Event) => void;
    onSubmit?: (event: Event) => void;
    onKeyDown?: (event: KeyboardEvent) => void;
    onKeyUp?: (event: KeyboardEvent) => void;
    onKeyPress?: (event: KeyboardEvent) => void;
    onFocus?: (event: Event) => void;
    onBlur?: (event: Event) => void;
    onMouseEnter?: (event: MouseEvent) => void;
    onMouseLeave?: (event: MouseEvent) => void;
    onMouseOver?: (event: MouseEvent) => void;
    onMouseOut?: (event: MouseEvent) => void;
    [key: string]: any;
  }

  interface InputHTMLAttributes extends HTMLAttributes {
    type?: string;
    value?: string | number;
    placeholder?: string;
    disabled?: boolean;
    readOnly?: boolean;
    required?: boolean;
    min?: string | number;
    max?: string | number;
    step?: string | number;
    pattern?: string;
    accept?: string;
    multiple?: boolean;
    checked?: boolean;
    name?: string;
  }

  interface FormHTMLAttributes extends HTMLAttributes {
    action?: string;
    method?: string;
    encType?: string;
    noValidate?: boolean;
    target?: string;
  }

  interface AnchorHTMLAttributes extends HTMLAttributes {
    href?: string;
    target?: string;
    rel?: string;
    download?: string;
  }

  interface ImgHTMLAttributes extends HTMLAttributes {
    src?: string;
    alt?: string;
    width?: string | number;
    height?: string | number;
    loading?: 'lazy' | 'eager';
    decoding?: 'async' | 'sync' | 'auto';
  }

  interface SelectHTMLAttributes extends HTMLAttributes {
    value?: string | number;
    disabled?: boolean;
    multiple?: boolean;
    name?: string;
    required?: boolean;
  }

  interface OptionHTMLAttributes extends HTMLAttributes {
    value?: string | number;
    disabled?: boolean;
    selected?: boolean;
  }

  interface TextareaHTMLAttributes extends HTMLAttributes {
    value?: string;
    placeholder?: string;
    disabled?: boolean;
    readOnly?: boolean;
    required?: boolean;
    rows?: number;
    cols?: number;
    name?: string;
  }

  interface LabelHTMLAttributes extends HTMLAttributes {
    htmlFor?: string;
  }

  interface CSSProperties {
    [key: string]: string | number | undefined;
    color?: string;
    backgroundColor?: string;
    fontSize?: string | number;
    fontWeight?: string | number;
    margin?: string | number;
    padding?: string | number;
    border?: string;
    borderRadius?: string | number;
    width?: string | number;
    height?: string | number;
    display?: string;
    flexDirection?: string;
    justifyContent?: string;
    alignItems?: string;
    position?: string;
    top?: string | number;
    left?: string | number;
    right?: string | number;
    bottom?: string | number;
    zIndex?: number;
    opacity?: number;
    transform?: string;
    transition?: string;
    cursor?: string;
    overflow?: string;
    textAlign?: string;
    lineHeight?: string | number;
    letterSpacing?: string | number;
    textDecoration?: string;
    fontFamily?: string;
    boxShadow?: string;
    outline?: string;
  }
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type Prettify<T> = {
  [K in keyof T]: T[K];
} & {};

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

export type RequiredKeys<T, K extends keyof T> = T & Required<Pick<T, K>>;

// Hook types
export type StateUpdater<S> = S | ((prevState: S) => S);
export type EffectCallback = () => void | (() => void);
export type DependencyList = any[];

// Event types
export interface SyntheticEvent<T = Element, E = Event> {
  currentTarget: T;
  target: Element;
  bubbles: boolean;
  cancelable: boolean;
  defaultPrevented: boolean;
  eventPhase: number;
  isTrusted: boolean;
  nativeEvent: E;
  preventDefault(): void;
  stopPropagation(): void;
  type: string;
}

export interface MouseEvent<T = Element> extends SyntheticEvent<T, globalThis.MouseEvent> {
  altKey: boolean;
  button: number;
  buttons: number;
  clientX: number;
  clientY: number;
  ctrlKey: boolean;
  metaKey: boolean;
  movementX: number;
  movementY: number;
  pageX: number;
  pageY: number;
  relatedTarget: Element | null;
  screenX: number;
  screenY: number;
  shiftKey: boolean;
}

export interface KeyboardEvent<T = Element> extends SyntheticEvent<T, globalThis.KeyboardEvent> {
  altKey: boolean;
  charCode: number;
  ctrlKey: boolean;
  key: string;
  keyCode: number;
  locale: string;
  location: number;
  metaKey: boolean;
  repeat: boolean;
  shiftKey: boolean;
  which: number;
}

// Diffing and patching types
export interface VNode {
  tagName: string;
  props: Record<string, any>;
  children: Array<VNode | string>;
  key: string | number | null;
  element: HTMLElement | null;
  component: any | null;
}

export interface Patch {
  type: string;
  oldVNode?: VNode;
  newVNode?: VNode;
  propsPatches?: PropPatch[];
  childrenPatches?: Patch[];
  moves?: Move[];
  from?: number;
  to?: number;
  vnode?: VNode;
}

export interface PropPatch {
  type: 'ADD_PROP' | 'REMOVE_PROP' | 'UPDATE_PROP';
  key: string;
  value?: any;
}

export interface Move {
  from: number;
  to: number;
  vnode: VNode;
}

export type PatchType =
  | 'CREATE'
  | 'REMOVE'
  | 'REPLACE'
  | 'UPDATE'
  | 'REORDER'
  | 'MOVE'
  | 'TEXT';

export interface DiffOptions {
  enableKeyOptimization?: boolean;
  enableListOptimization?: boolean;
  enableTextOptimization?: boolean;
  enableMoveDetection?: boolean;
}

export interface DiffResult {
  patches: Patch[];
  time: number;
  optimized: boolean;
}

// Performance monitoring types
export interface PerformanceMetrics {
  diffTime: number;
  patchTime: number;
  renderTime: number;
  totalTime: number;
  diffCount: number;
  patchCount: number;
  renderCount: number;
  memoryUsage?: number;
  domNodes?: number;
}

export interface PerformanceConfig {
  enabled: boolean;
  sampleRate: number;
  maxSamples: number;
  enableMemoryTracking: boolean;
  enableDOMTracking: boolean;
}

export interface BenchmarkResult {
  operation: string;
  duration: number;
  iterations: number;
  averageTime: number;
  minTime: number;
  maxTime: number;
  memoryUsage: number;
  timestamp: number;
}

// Memory management types
export interface MemoryPool {
  size: number;
  used: number;
  available: number;
  utilization: number;
}

export interface MemoryStats {
  vNodePool: MemoryPool;
  elementPool: MemoryPool;
  totalAllocated: number;
  totalReleased: number;
  cleanupTasks: number;
}

export interface MemoryConfig {
  maxVNodePoolSize: number;
  maxElementPoolSize: number;
  enablePooling: boolean;
  enableCleanup: boolean;
  cleanupInterval: number;
}

// Advanced component types
export interface ComponentLifecycleHooks {
  onBeforeMount?: () => void;
  onMounted?: () => void;
  onBeforeUpdate?: () => void;
  onUpdated?: () => void;
  onBeforeUnmount?: () => void;
  onUnmounted?: () => void;
  onError?: (error: Error) => void;
}

export interface ComponentOptions {
  name?: string;
  props?: Record<string, any>;
  state?: Record<string, any>;
  hooks?: ComponentLifecycleHooks;
  render?: () => string | HTMLElement;
  template?: string;
  style?: string;
  computed?: Record<string, () => any>;
  watch?: Record<string, (newVal: any, oldVal: any) => void>;
  methods?: Record<string, Function>;
  inject?: string[];
  provide?: Record<string, any>;
}

export interface ComponentInstance {
  readonly props: Record<string, any>;
  readonly state: Record<string, any>;
  readonly element: HTMLElement | null;
  readonly mounted: boolean;
  readonly name: string;
  setState(updater: any): void;
  setProps(props: Record<string, any>): void;
  forceUpdate(): void;
  mount(container: string | HTMLElement): void;
  unmount(): void;
  destroy(): void;
  $refs: Record<string, HTMLElement>;
  $parent?: ComponentInstance;
  $children: ComponentInstance[];
  $root: ComponentInstance;
  emit(event: string, ...args: any[]): void;
  on(event: string, handler: Function): void;
  off(event: string, handler?: Function): void;
}

// Reactive system advanced types
export interface ReactiveEffect {
  id: string;
  fn: () => void;
  deps: Set<ReactiveDependency>;
  cleanup?: () => void;
  active: boolean;
  scheduler?: (fn: () => void) => void;
}

export interface ReactiveDependency {
  target: object;
  key: string | symbol;
  type: 'get' | 'set' | 'add' | 'delete';
}

export interface ReactiveConfig {
  deep: boolean;
  immediate: boolean;
  lazy: boolean;
  scheduler?: (fn: () => void) => void;
  onTrack?: (event: ReactiveDependency) => void;
  onTrigger?: (event: ReactiveDependency) => void;
}

export interface ComputedConfig extends ReactiveConfig {
  getter: () => any;
  setter?: (value: any) => void;
}

export interface WatchConfig extends ReactiveConfig {
  source: any;
  callback: (newValue: any, oldValue: any) => void;
  flush?: 'pre' | 'post' | 'sync';
  once?: boolean;
  deep?: boolean;
  immediate?: boolean;
}

// Advanced store types
export interface StoreConfig {
  name: string;
  initialState: Record<string, any>;
  middleware?: Middleware[];
  persistence?: boolean;
  persistenceKey?: string;
  enableDevtools?: boolean;
  enableLogger?: boolean;
  enableTimeTravel?: boolean;
  maxHistorySize?: number;
  enableOptimisticUpdates?: boolean;
  enableBatching?: boolean;
}

export interface StoreState {
  data: Record<string, any>;
  status: 'idle' | 'loading' | 'success' | 'error';
  error: Error | null;
  lastUpdated: number;
  version: number;
  history: StoreSnapshot[];
  optimisticUpdates: Map<string, any>;
}

export interface StoreSnapshot {
  state: Record<string, any>;
  timestamp: number;
  action: string;
  metadata: Record<string, any>;
}

export interface StoreAction {
  type: string;
  payload?: any;
  meta?: Record<string, any>;
  timestamp: number;
  id: string;
  optimistic?: boolean;
  rollback?: () => void;
}

export interface StoreMiddleware {
  (store: EnhancedStore) => (next: Function) => (action: StoreAction) => any;
}

export interface EnhancedStore {
  name: string;
  state: StoreState;
  actions: Record<string, Function>;
  getters: Record<string, Function>;
  mutations: Record<string, Function>;
  dispatch(action: string | StoreAction, payload?: any): Promise<any>;
  commit(mutation: string, payload?: any): void;
  subscribe(listener: (state: StoreState, prevState: StoreState) => void): () => void;
  replaceState(newState: Record<string, any>): void;
  reset(): void;
  undo(): boolean;
  redo(): boolean;
  canUndo(): boolean;
  canRedo(): boolean;
  getHistory(): StoreSnapshot[];
  clearHistory(): void;
  enableTimeTravel(): void;
  disableTimeTravel(): void;
  getStateAt(timestamp: number): StoreSnapshot | null;
}

// Advanced router types
export interface RouteConfig {
  path: string;
  name?: string;
  component?: string | Function;
  components?: Record<string, string | Function>;
  redirect?: string | Function;
  alias?: string | string[];
  props?: boolean | Record<string, any> | Function;
  meta?: Record<string, any>;
  children?: RouteConfig[];
  beforeEnter?: Function;
  beforeLeave?: Function;
  beforeResolve?: Function;
  afterEnter?: Function;
  afterLeave?: Function;
  scrollBehavior?: Function;
  lazy?: boolean;
  chunkName?: string;
}

export interface RouterConfig {
  mode: 'history' | 'hash' | 'memory';
  base?: string;
  routes: RouteConfig[];
  scrollBehavior?: Function;
  linkActiveClass?: string;
  linkExactActiveClass?: string;
  parseQuery?: Function;
  stringifyQuery?: Function;
  fallback?: boolean;
  sensitive?: boolean;
  strict?: boolean;
  end?: boolean;
  meta?: Record<string, any>;
}

export interface RouterMatch {
  path: string;
  params: Record<string, string>;
  query: Record<string, string>;
  hash: string;
  fullPath: string;
  matched: RouteConfig[];
  meta: Record<string, any>;
  redirectedFrom?: RouterMatch;
  depth: number;
}

export interface RouterHistory {
  current: RouterMatch;
  previous?: RouterMatch;
  stack: RouterMatch[];
  index: number;
  length: number;
  go(delta: number): void;
  back(): void;
  forward(): void;
  push(location: string | RouterLocation): void;
  replace(location: string | RouterLocation): void;
  canGo(delta: number): boolean;
}

export interface RouterLocation {
  path: string;
  query?: Record<string, string>;
  hash?: string;
  params?: Record<string, string>;
  state?: any;
  replace?: boolean;
  force?: boolean;
}

// Advanced API client types
export interface ApiClientConfig {
  baseURL: string;
  timeout: number;
  retries: number;
  retryDelay: number;
  headers: Record<string, string>;
  cache: boolean;
  cacheTTL: number;
  enableInterceptors: boolean;
  enableTransformers: boolean;
  enableMetrics: boolean;
  enableLogging: boolean;
  requestInterceptors: Array<(config: RequestConfig) => RequestConfig>;
  responseInterceptors: Array<(response: ApiResponse) => ApiResponse>;
  errorInterceptors: Array<(error: ApiError) => boolean>;
  transformers: {
    request?: (data: any, headers: Record<string, string>) => any;
    response?: (data: any, headers: Record<string, string>) => any;
  };
}

export interface RequestConfig {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';
  url: string;
  params?: Record<string, any>;
  data?: any;
  headers?: Record<string, string>;
  timeout?: number;
  retries?: number;
  cache?: boolean;
  cacheKey?: string;
  cacheTTL?: number;
  withCredentials?: boolean;
  responseType?: 'json' | 'text' | 'blob' | 'arraybuffer';
  signal?: AbortSignal;
  onUploadProgress?: (progress: number) => void;
  onDownloadProgress?: (progress: number) => void;
  validateStatus?: (status: number) => boolean;
  transformRequest?: (data: any) => any;
  transformResponse?: (data: any) => any;
}

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
  headers: Record<string, string>;
  config: RequestConfig;
  request: XMLHttpRequest | null;
  duration: number;
  cached: boolean;
  size: number;
}

export interface ApiError {
  message: string;
  code: string | number;
  status: number;
  response?: ApiResponse;
  request?: RequestConfig;
  isRetryable: boolean;
  retryCount: number;
  maxRetries: number;
}

export interface ApiMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  cacheHitRate: number;
  requestsPerSecond: number;
  errorRate: number;
  statusCodes: Record<number, number>;
  endpointMetrics: Record<string, {
    count: number;
    averageTime: number;
    errorCount: number;
  }>;
}

// Advanced WebSocket types
export interface WebSocketConfig {
  url: string;
  protocols?: string | string[];
  reconnectInterval: number;
  maxReconnectAttempts: number;
  heartbeatInterval: number;
  messageQueueSize: number;
  enableCompression: boolean;
  enableHeartbeat: boolean;
  enableReconnect: boolean;
  enableQueue: boolean;
  debug: boolean;
  timeout: number;
  pingTimeout: number;
  pongTimeout: number;
  binaryType: 'blob' | 'arraybuffer';
}

export interface WebSocketMessage {
  id: string;
  type: string;
  timestamp: number;
  data: any;
  inReplyTo?: string;
  correlationId?: string;
  priority?: 'low' | 'normal' | 'high';
  persistent?: boolean;
  ttl?: number;
  metadata?: Record<string, any>;
}

export interface WebSocketEvent {
  type: 'open' | 'close' | 'error' | 'message' | 'reconnect' | 'heartbeat';
  timestamp: number;
  data?: any;
  error?: Error;
  retryCount?: number;
  connectionId?: string;
}

export interface WebSocketState {
  readyState: number;
  isConnected: boolean;
  isConnecting: boolean;
  isReconnecting: boolean;
  reconnectAttempts: number;
  lastHeartbeat: number | null;
  lastPong: number | null;
  queueSize: number;
  connectionId: string;
  latency: number;
  uptime: number;
  messagesSent: number;
  messagesReceived: number;
  errors: number;
}

// Advanced notification types
export interface NotificationConfig {
  position: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
  duration: number;
  maxNotifications: number;
  enableQueue: boolean;
  enablePersistence: boolean;
  enableGrouping: boolean;
  enableActions: boolean;
  enableProgress: boolean;
  enableSound: boolean;
  defaultDuration: Record<string, number>;
  animations: Record<string, string>;
  zIndex: number;
  gap: number;
  width: number;
}

export interface NotificationItem {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info' | 'loading';
  title: string;
  message: string;
  description?: string;
  icon?: string;
  image?: string;
  duration: number;
  persistent: boolean;
  dismissible: boolean;
  actions: NotificationAction[];
  progress: number;
  paused: boolean;
  timestamp: number;
  expiresAt: number;
  priority: 'low' | 'normal' | 'high';
  category: string;
  tags: string[];
  data: Record<string, any>;
  group?: string;
  position?: number;
}

export interface NotificationAction {
  key: string;
  label: string;
  icon?: string;
  variant?: 'primary' | 'secondary' | 'destructive';
  handler: (notification: NotificationItem) => void;
  disabled?: boolean;
  hidden?: boolean;
}

export interface NotificationGroup {
  id: string;
  title: string;
  count: number;
  notifications: NotificationItem[];
  collapsed: boolean;
  lastUpdated: number;
}

// Advanced theme types
export interface ThemeConfig {
  name: string;
  version: string;
  description?: string;
  author?: string;
  license?: string;
  colors: ThemeColors;
  spacing: ThemeSpacing;
  typography: ThemeTypography;
  borderRadius: ThemeBorderRadius;
  shadows: ThemeShadows;
  transitions: ThemeTransitions;
  breakpoints: Record<string, string>;
  zIndex: Record<string, number>;
  components: Record<string, Record<string, any>>;
  variants: Record<string, Record<string, any>>;
  darkMode: 'class' | 'media' | 'system' | false;
  enableCSSVariables: boolean;
  enableRuntimeGeneration: boolean;
  enablePrefersReducedMotion: boolean;
  enableHighContrast: boolean;
}

export interface ThemeColors {
  primary: ColorPalette;
  secondary: ColorPalette;
  success: ColorPalette;
  warning: ColorPalette;
  error: ColorPalette;
  info: ColorPalette;
  neutral: ColorPalette;
  background: Record<string, string>;
  foreground: Record<string, string>;
  border: Record<string, string>;
  text: Record<string, string>;
  [key: string]: any;
}

export interface ColorPalette {
  50: string;
  100: string;
  200: string;
  300: string;
  400: string;
  500: string;
  600: string;
  700: string;
  800: string;
  900: string;
  DEFAULT: string;
}

export interface ThemeSpacing {
  0: string;
  1: string;
  2: string;
  3: string;
  4: string;
  5: string;
  6: string;
  8: string;
  10: string;
  12: string;
  16: string;
  20: string;
  24: string;
  32: string;
  40: string;
  48: string;
  56: string;
  64: string;
  px: string;
  auto: string;
}

export interface ThemeTypography {
  fontFamily: {
    sans: string[];
    serif: string[];
    mono: string[];
  };
  fontSize: Record<string, string>;
  fontWeight: Record<string, string>;
  lineHeight: Record<string, string>;
  letterSpacing: Record<string, string>;
  textColor: Record<string, string>;
  textDecoration: Record<string, string>;
  textTransform: Record<string, string>;
}

export interface ThemeBorderRadius {
  none: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  '3xl': string;
  full: string;
}

export interface ThemeShadows {
  none: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  inner: string;
  outline: string;
  drop: string;
}

export interface ThemeTransitions {
  none: string;
  fast: string;
  normal: string;
  slow: string;
  'very-slow': string;
  all: string;
  colors: string;
  opacity: string;
  shadow: string;
  transform: string;
}

// Advanced cache types
export interface CacheConfig {
  defaultTTL: number;
  maxMemorySize: number;
  maxLocalStorageSize: number;
  maxSessionStorageSize: number;
  maxIndexedDBSize: number;
  enableCompression: boolean;
  compressionThreshold: number;
  enablePersistence: boolean;
  enableMetrics: boolean;
  enableAutoCleanup: boolean;
  cleanupInterval: number;
  debug: boolean;
  strategies: {
    memory: boolean;
    localStorage: boolean;
    sessionStorage: boolean;
    indexedDB: boolean;
  };
  serializers: {
    json: boolean;
    msgpack: boolean;
    cbor: boolean;
  };
  compressors: {
    lz4: boolean;
    lz77: boolean;
    deflate: boolean;
  };
}

export interface CacheEntry {
  key: string;
  value: any;
  type: 'memory' | 'localStorage' | 'sessionStorage' | 'indexedDB';
  size: number;
  compressed: boolean;
  compressedSize: number;
  created: number;
  accessed: number;
  expires: number;
  ttl: number;
  accessCount: number;
  hitCount: number;
  missCount: number;
  lastHit: number;
  lastMiss: number;
  metadata: Record<string, any>;
  tags: string[];
  dependencies: string[];
  version: number;
  checksum: string;
}

export interface CacheStats {
  memory: {
    size: number;
    maxSize: number;
    entries: number;
    utilization: number;
    evictions: number;
    hits: number;
    misses: number;
    hitRate: number;
  };
  localStorage: {
    size: number;
    maxSize: number;
    entries: number;
    utilization: number;
    evictions: number;
    hits: number;
    misses: number;
    hitRate: number;
  };
  sessionStorage: {
    size: number;
    maxSize: number;
    entries: number;
    utilization: number;
    evictions: number;
    hits: number;
    misses: number;
    hitRate: number;
  };
  indexedDB: {
    size: number;
    maxSize: number;
    entries: number;
    utilization: number;
    evictions: number;
    hits: number;
    misses: number;
    hitRate: number;
  };
  total: {
    size: number;
    maxSize: number;
    entries: number;
    utilization: number;
    evictions: number;
    hits: number;
    misses: number;
    hitRate: number;
    compressionRatio: number;
  };
  performance: {
    averageGetTime: number;
    averageSetTime: number;
    averageDeleteTime: number;
    averageHitTime: number;
    averageMissTime: number;
  };
}

// Framework configuration types
export interface FrameworkConfig {
  name: string;
  version: string;
  debug: boolean;
  production: boolean;
  baseURL: string;
  apiVersion: string;
  enableWebSocket: boolean;
  enableAuth: boolean;
  enableNotifications: boolean;
  enableTheme: boolean;
  enableCache: boolean;
  enableRouter: boolean;
  enableStore: boolean;
  enableI18n: boolean;
  enablePWA: boolean;
  enableSSR: boolean;
  enableTesting: boolean;
  apiTimeout: number;
  apiRetries: number;
  authStorageKey: string;
  authRefreshThreshold: number;
  notificationPosition: string;
  notificationDuration: number;
  maxNotifications: number;
  defaultTheme: string;
  themeStorageKey: string;
  cacheTTL: number;
  cacheMaxSize: number;
  wsReconnectInterval: number;
  wsMaxReconnectAttempts: number;
  routerMode: 'history' | 'hash' | 'memory';
  routerBase: string;
  storePersistence: boolean;
  storePersistenceKey: string;
  i18nLocale: string;
  i18nFallbackLocale: string;
  i18nMessages: Record<string, any>;
  pwaManifest: Record<string, any>;
  ssrTimeout: number;
  ssrMaxAge: number;
  testingEnvironment: 'development' | 'staging' | 'production';
  testingCoverage: boolean;
  testingHeadless: boolean;
  plugins: PluginConfig[];
  middleware: MiddlewareConfig[];
  interceptors: InterceptorConfig[];
  transformers: TransformerConfig[];
  [key: string]: any;
}

export interface PluginConfig {
  name: string;
  version: string;
  enabled: boolean;
  config: Record<string, any>;
  dependencies: string[];
  hooks: Record<string, Function>;
}

export interface MiddlewareConfig {
  name: string;
  type: 'request' | 'response' | 'error' | 'route' | 'auth' | 'cache';
  enabled: boolean;
  priority: number;
  config: Record<string, any>;
  handler: Function;
}

export interface InterceptorConfig {
  name: string;
  type: 'request' | 'response' | 'error';
  enabled: boolean;
  priority: number;
  config: Record<string, any>;
  handler: Function;
}

export interface TransformerConfig {
  name: string;
  type: 'request' | 'response' | 'data' | 'template';
  enabled: boolean;
  priority: number;
  config: Record<string, any>;
  handler: Function;
}

// Global type declarations
declare global {
  interface Window {
    PyservClient: PyservClientFramework;
    __PYSERV_ROUTER__: Router;
    __PYSERV_AUTH__: Auth;
    __PYSERV_NOTIFICATIONS__: NotificationManager;
    __PYSERV_THEME__: ThemeManager;
    __PYSERV_CACHE__: CacheManager;
    __PYSERV_WS__: WebSocketClient;
    __PYSERV_PERFORMANCE__: PerformanceMonitor;
    __PYSERV_MEMORY__: MemoryManager;
    __PYSERV_ADVANCED_DIFFER__: AdvancedDiffer;
  }

  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}

// Export all types
export type {
  ComponentProps,
  ComponentState,
  ComponentContext,
  ComponentLifecycle,
  ErrorInfo,
  EventHandler,
  ChangeEventHandler,
  FormEventHandler,
  ChangeEvent,
  FormEvent,
  ReactiveOptions,
  Ref,
  Computed,
  Effect,
  WatchOptions,
  WatchCallback,
  StoreState,
  StoreOptions,
  Middleware,
  Action,
  Store,
  Route,
  RouteMatch,
  RouterOptions,
  Router,
  User,
  AuthState,
  LoginCredentials,
  RegisterData,
  AuthOptions,
  Auth,
  TokenInfo,
  ApiClientConfig,
  RequestConfig,
  ApiResponse,
  ApiClient,
  WebSocketConfig,
  WebSocketMessage,
  WebSocketClient,
  NotificationOptions,
  Notification,
  NotificationManager,
  ThemeColors,
  ThemeSpacing,
  ThemeTypography,
  ThemeBorderRadius,
  ThemeShadows,
  ThemeTransitions,
  Theme,
  ThemeManager,
  CacheEntry,
  CacheConfig,
  CacheStrategy,
  CacheOptions,
  CacheStats,
  CacheManager,
  FrameworkConfig,
  FrameworkServices,
  FrameworkStores,
  PyservClientFramework,
  ComponentClass,
  Component,
  DeepPartial,
  Prettify,
  Optional,
  RequiredKeys,
  StateUpdater,
  EffectCallback,
  DependencyList,
  SyntheticEvent,
  MouseEvent,
  KeyboardEvent
};
