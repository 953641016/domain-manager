/**
 * 域名管家 - React Router 配置
 *
 * 支持二级目录部署
 * 使用 React Router v6 的 basename 配置
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { APP_BASE_PATH } from './routes';

// 布局组件
import MainLayout from '@/layouts/MainLayout';

// 页面组件
import LoginPage from '@/pages/Login';
import DashboardPage from '@/pages/Dashboard';
import RequestsPage from '@/pages/Requests';
import RequestDetailPage from '@/pages/Requests/Detail';
import DomainsPage from '@/pages/Domains';
import DomainDetailPage from '@/pages/Domains/Detail';
import ExpirationPage from '@/pages/Expiration';
import StatisticsPage from '@/pages/Statistics';
import LogsPage from '@/pages/Logs';
import ConfigPages from '@/pages/Config';
import ForbiddenPage from '@/pages/Errors/Forbidden';
import NotFoundPage from '@/pages/Errors/NotFound';

// 路由守卫组件
import ProtectedRoute from '@/components/ProtectedRoute';
import PermissionRoute from '@/components/PermissionRoute';

// 用户角色
import { UserRole } from '@/types/user';

function AppRouter() {
  return (
    // BrowserRouter 使用 basename 支持二级目录部署
    <BrowserRouter basename={APP_BASE_PATH}>
      <Routes>
        {/* 公开路由 */}
        <Route path="/login" element={<LoginPage />} />

        {/* 受保护的路由 */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          {/* 首页重定向到仪表盘 */}
          <Route index element={<Navigate to="/dashboard" replace />} />

          {/* 仪表盘 - 所有登录用户可见 */}
          <Route path="dashboard" element={<DashboardPage />} />

          {/* 申请记录 - 所有登录用户可见 */}
          <Route path="requests" element={<RequestsPage />} />
          <Route path="requests/:id" element={<RequestDetailPage />} />

          {/* 域名管理 - 域名专员和管理员可见 */}
          <Route
            path="domains"
            element={
              <PermissionRoute allowedRoles={[UserRole.DOMAIN_SPEC, UserRole.ADMIN]}>
                <DomainsPage />
              </PermissionRoute>
            }
          />
          <Route
            path="domains/:name"
            element={
              <PermissionRoute allowedRoles={[UserRole.DOMAIN_SPEC, UserRole.ADMIN]}>
                <DomainDetailPage />
              </PermissionRoute>
            }
          />

          {/* 到期管理 - 域名专员和管理员可见 */}
          <Route
            path="expiration"
            element={
              <PermissionRoute allowedRoles={[UserRole.DOMAIN_SPEC, UserRole.ADMIN]}>
                <ExpirationPage />
              </PermissionRoute>
            }
          />

          {/* 统计报表 - 仅管理员可见 */}
          <Route
            path="statistics"
            element={
              <PermissionRoute allowedRoles={[UserRole.ADMIN]}>
                <StatisticsPage />
              </PermissionRoute>
            }
          />

          {/* 操作日志 - 仅管理员可见 */}
          <Route
            path="logs"
            element={
              <PermissionRoute allowedRoles={[UserRole.ADMIN]}>
                <LogsPage />
              </PermissionRoute>
            }
          />

          {/* 系统配置 - 仅管理员可见 */}
          <Route
            path="config/*"
            element={
              <PermissionRoute allowedRoles={[UserRole.ADMIN]}>
                <ConfigPages />
              </PermissionRoute>
            }
          />
        </Route>

        {/* 错误页面 */}
        <Route path="/403" element={<ForbiddenPage />} />
        <Route path="/404" element={<NotFoundPage />} />

        {/* 未匹配的路由重定向到 404 */}
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default AppRouter;
