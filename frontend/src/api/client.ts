/**
 * 域名管家 - Axios API 客户端配置
 *
 * 支持二级目录部署
 * API 请求自动使用二级目录作为前缀
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';
import { API_BASE_PATH, APP_BASE_PATH } from '@/config/routes';

// 创建 Axios 实例
const apiClient: AxiosInstance = axios.create({
  // API 基础路径
  baseURL: API_BASE_PATH,

  // 请求超时时间
  timeout: 30000,

  // 请求头
  headers: {
    'Content-Type': 'application/json',
  },

  // 允许携带 cookies
  withCredentials: true,
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem('access_token');

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 添加请求日志（在开发环境）
    if (import.meta.env.DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    // 响应成功处理
    if (import.meta.env.DEV) {
      console.log(`[API Response] ${response.status} ${response.config.url}`);
    }

    return response;
  },
  async (error: AxiosError) => {
    // 错误处理
    if (error.response) {
      const status = error.response.status;

      switch (status) {
        case 401:
          // 未授权，清除 token 并跳转登录（使用 basename 保证子目录部署正确）
          localStorage.removeItem('access_token');
          window.location.href = `${APP_BASE_PATH}/login`;
          break;

        case 403:
          // 无权限：交由调用方处理（如展示错误提示）。
          // 不在此处强制跳转——页面级权限由 PermissionRoute 守卫，
          // 而操作级 403（如"超管不能被禁用"）只需提示，不应离开当前页。
          console.error('无权限操作:', error.response.data);
          break;

        case 404:
          // 资源不存在
          console.error('API 资源不存在:', error.config?.url);
          break;

        case 500:
          // 服务器错误
          console.error('服务器错误:', error.response.data);
          break;

        default:
          break;
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('网络错误，请检查网络连接');
    } else {
      // 请求配置出错
      console.error('请求配置错误:', error.message);
    }

    return Promise.reject(error);
  }
);

// API 方法封装
export const api = {
  // GET 请求
  get: <T = any>(url: string, config?: AxiosRequestConfig) =>
    apiClient.get<T>(url, config),

  // POST 请求
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    apiClient.post<T>(url, data, config),

  // PUT 请求
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    apiClient.put<T>(url, data, config),

  // PATCH 请求
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    apiClient.patch<T>(url, data, config),

  // DELETE 请求
  delete: <T = any>(url: string, config?: AxiosRequestConfig) =>
    apiClient.delete<T>(url, config),
};

// 导出实例和便捷方法
export default apiClient;
export { apiClient as axios };
