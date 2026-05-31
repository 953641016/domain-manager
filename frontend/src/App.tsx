/**
 * 域名管家 - React Router 配置
 *
 * 支持二级目录部署
 * 使用 React Router v6 的 basename 配置
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { APP_BASE_PATH } from './config/routes';

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
import SslPage from '@/pages/Ssl';
import StatisticsPage from '@/pages/Statistics';
import LogsPage from '@/pages/Logs';
import ConfigPage from '@/pages/Config';
import UserManagement from '@/pages/config/UserManagement';
import ForbiddenPage from '@/pages/Errors/Forbidden';
import NotFoundPage from '@/pages/Errors/NotFound';
import FeishuConfirmPage from '@/pages/FeishuConfirm';

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
        {/* 飞书文档按钮确认页（无需主布局，独立页面） */}
        <Route path="/feishu/confirm" element={<FeishuConfirmPage />} />

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

          {/* 域名管理 - 超级管理员、管理员和域名专员可见 */}
          <Route
            path="domains"
            element={
              <PermissionRoute allowedRoles={[UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DOMAIN_SPEC]}>
                <DomainsPage />
              </PermissionRoute>
            }
          />
          <Route
            path="domains/:name"
            element={
              <PermissionRoute allowedRoles={[UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DOMAIN_SPEC]}>
                <DomainDetailPage />
              </PermissionRoute>
            }
          />

          {/* 到期管理 - 超级管理员、管理员和域名专员可见 */}
          <Route
            path="expiration"
            element={
              <PermissionRoute allowedRoles={[UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DOMAIN_SPEC]}>
                <ExpirationPage />
              </PermissionRoute>
            }
          />

          {/* SSL 证书 - 超级管理员、管理员和域名专员可见 */}
          <Route
            path="ssl"
            element={
              <PermissionRoute allowedRoles={[UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DOMAIN_SPEC]}>
                <SslPage />
              </PermissionRoute>
            }
          />

          {/* 统计报表 - 超级管理员和管理员可见 */}
          <Route
            path="statistics"
            element={
              <PermissionRoute allowedRoles={[UserRole.SUPER_ADMIN, UserRole.ADMIN]}>
                <StatisticsPage />
              </PermissionRoute>
            }
          />

          {/* 操作日志 - 超级管理员和管理员可见 */}
          <Route
            path="logs"
            element={
              <PermissionRoute allowedRoles={[UserRole.SUPER_ADMIN, UserRole.ADMIN]}>
                <LogsPage />
              </PermissionRoute>
            }
          />

          {/* ==================== 系统管理 - 超级管理员和管理员可见 ==================== */}
          {/* 用户管理 */}
          <Route
            path="system/users"
            element={
              <PermissionRoute allowedRoles={[UserRole.SUPER_ADMIN, UserRole.ADMIN]}>
                <UserManagement />
              </PermissionRoute>
            }
          />
          {/* 账号管理（注册账号 + DNS账号）
              权限：domain_spec/super_admin 可发起；写操作后端要求超管飞书确认
              admin 无 can_manage_accounts 权限，不列入此路由 */}
          <Route
            path="system/accounts"
            element={
              <PermissionRoute allowedRoles={[UserRole.SUPER_ADMIN, UserRole.DOMAIN_SPEC]}>
                {/* key 防止 React 复用同一 ConfigPage 实例导致 activeTab state 残留 */}
                <ConfigPage key="accounts" sections={['reg-accounts', 'dns-accounts']} title="域名账号管理" />
              </PermissionRoute>
            }
          />
          {/* 服务商与默认（注册商目录 + DNS服务商目录 + 默认配置）
              权限：domain_spec/super_admin 可发起；写操作后端要求超管飞书确认
              admin 无 can_manage_providers 权限，不列入此路由 */}
          <Route
            path="system/providers"
            element={
              <PermissionRoute allowedRoles={[UserRole.SUPER_ADMIN, UserRole.DOMAIN_SPEC]}>
                <ConfigPage key="providers" sections={['registrar', 'dns', 'defaults']} title="服务商与默认" />
              </PermissionRoute>
            }
          />

          {/* 旧版系统配置入口，重定向到用户管理 */}
          <Route path="config" element={<Navigate to="/system/users" replace />} />
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
