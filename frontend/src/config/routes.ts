/**
 * 域名管家 - 前端路由配置文件
 *
 * 支持二级目录部署
 * 部署路径通过 VITE_BASE_PATH 环境变量配置
 */

// 获取基础路径配置
const getBasePath = (): string => {
  return import.meta.env.VITE_BASE_PATH || '/dm';
};

// API 基础路径
export const API_BASE_PATH = `${getBasePath()}/api`;

// WebSocket 路径
export const WS_BASE_PATH = `${getBasePath()}/ws`;

// 应用基础路径
export const APP_BASE_PATH = getBasePath();

// 应用路由配置
export const AppRoutes = {
  // 首页
  HOME: '/',

  // 登录
  LOGIN: '/login',

  // 仪表盘
  DASHBOARD: '/dashboard',

  // 申请记录
  REQUESTS: '/requests',
  REQUEST_DETAIL: '/requests/:id',

  // 域名管理
  DOMAINS: '/domains',
  DOMAIN_DETAIL: '/domains/:name',
  DOMAIN_RENEW: '/domains/:name/renew',

  // 到期管理
  EXPIRATION: '/expiration',

  // 系统配置
  CONFIG: '/config',
  CONFIG_REGISTRARS: '/config/registrars',
  CONFIG_DNS_PROVIDERS: '/config/dns-providers',
  CONFIG_REG_ACCOUNTS: '/config/reg-accounts',
  CONFIG_DNS_ACCOUNTS: '/config/dns-accounts',
  CONFIG_DEFAULTS: '/config/defaults',
  CONFIG_USERS: '/config/users',

  // 统计报表
  STATISTICS: '/statistics',

  // 操作日志
  LOGS: '/logs',

  // 403 无权限页面
  FORBIDDEN: '/403',

  // 404 未找到页面
  NOT_FOUND: '/404',
};

// 路由路径生成函数
export const getRoutePath = (route: string, params?: Record<string, string>): string => {
  let path = `${getBasePath()}${route}`;

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      path = path.replace(`:${key}`, value);
    });
  }

  return path;
};

// API 路径生成函数
export const getApiPath = (endpoint: string): string => {
  return `${API_BASE_PATH}${endpoint}`;
};

// 完整 URL 生成函数
export const getFullUrl = (path: string): string => {
  const baseUrl = window.location.origin;
  return `${baseUrl}${getBasePath()}${path}`;
};
