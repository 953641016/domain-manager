/**
 * 主布局组件
 * 包含侧边栏、头部和内容区域
 */
import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { AppRoutes } from '@/config/routes';

interface UserInfo {
  id: number;
  name: string;
  en_name?: string;
  role: string;
  email?: string;
  avatar_url?: string;
}

const menuItems = [
  {
    key: 'dashboard',
    label: '仪表盘',
    path: AppRoutes.DASHBOARD,
    icon: '📊',
  },
  {
    key: 'requests',
    label: '申请记录',
    path: AppRoutes.REQUESTS,
    icon: '📋',
  },
  {
    key: 'domains',
    label: '域名管理',
    path: AppRoutes.DOMAINS,
    icon: '🌐',
    roles: ['domain_spec', 'admin', 'super_admin'],
  },
  {
    key: 'expiration',
    label: '到期管理',
    path: AppRoutes.EXPIRATION,
    icon: '⏰',
    roles: ['domain_spec', 'admin', 'super_admin'],
  },
  {
    key: 'statistics',
    label: '统计报表',
    path: AppRoutes.STATISTICS,
    icon: '📈',
    roles: ['admin', 'super_admin'],
  },
  {
    key: 'logs',
    label: '操作日志',
    path: AppRoutes.LOGS,
    icon: '📝',
    roles: ['admin', 'super_admin'],
  },
  {
    key: 'config',
    label: '系统配置',
    path: AppRoutes.CONFIG,
    icon: '⚙️',
    roles: ['admin', 'super_admin'],
  },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    // 获取用户信息
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    } else {
      navigate('/login');
    }
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const hasPermission = (roles?: string[]) => {
    if (!roles) return true;
    if (!user) return false;
    return roles.includes(user.role);
  };

  const isActive = (path: string) => {
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 侧边栏 */}
      <div
        className={`fixed inset-y-0 left-0 z-50 bg-white shadow-lg transition-all duration-300 ${
          sidebarCollapsed ? 'w-16' : 'w-64'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-center h-16 border-b border-gray-200">
          <span className="text-xl font-bold text-blue-600">
            {sidebarCollapsed ? '🌐' : '域名管家'}
          </span>
        </div>

        {/* 导航菜单 */}
        <nav className="mt-4 px-2">
          {menuItems.map((item) => {
            if (!hasPermission(item.roles)) return null;

            return (
              <button
                key={item.key}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center px-3 py-2 mt-1 text-sm rounded-md transition-colors ${
                  isActive(item.path)
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
                title={item.label}
              >
                <span className="text-lg">{item.icon}</span>
                {!sidebarCollapsed && (
                  <span className="ml-3">{item.label}</span>
                )}
              </button>
            );
          })}
        </nav>

        {/* 折叠按钮 */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute bottom-4 left-1/2 transform -translate-x-1/2 text-gray-400 hover:text-gray-600"
        >
          {sidebarCollapsed ? '→' : '←'}
        </button>
      </div>

      {/* 主内容区域 */}
      <div
        className={`transition-all duration-300 ${
          sidebarCollapsed ? 'ml-16' : 'ml-64'
        }`}
      >
        {/* 头部 */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <div className="flex items-center">
            <h1 className="text-lg font-semibold text-gray-800">
              {menuItems.find((item) => isActive(item.path))?.label || '域名管家'}
            </h1>
          </div>

          <div className="flex items-center space-x-4">
            {/* 用户信息 */}
            <div className="flex items-center space-x-2">
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.name}
                  className="h-8 w-8 rounded-full"
                />
              ) : (
                <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium">
                  {user?.name?.charAt(0) || 'U'}
                </div>
              )}
              <div className="text-sm">
                <div className="font-medium text-gray-700">{user?.name}</div>
                <div className="text-gray-500 text-xs">{user?.role}</div>
              </div>
            </div>

            {/* 退出登录 */}
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              退出
            </button>
          </div>
        </header>

        {/* 页面内容 */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
