/**
 * 主布局组件
 * 包含侧边栏（分组二级菜单）、头部和内容区域
 * 支持移动端响应式
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

interface MenuLeaf {
  key: string;
  label: string;
  path: string;
  icon: string;
  roles?: string[];
}

interface MenuGroup {
  key: string;
  label: string;
  icon: string;
  roles?: string[];
  children: MenuLeaf[];
}

type MenuEntry = MenuLeaf | MenuGroup;

const isGroup = (entry: MenuEntry): entry is MenuGroup =>
  (entry as MenuGroup).children !== undefined;

const DOMAIN_ROLES = ['domain_spec', 'admin', 'super_admin'];
const ADMIN_ROLES = ['admin', 'super_admin'];

const MENU: MenuEntry[] = [
  // 概览
  { key: 'dashboard', label: '仪表盘', path: AppRoutes.DASHBOARD, icon: '📊' },
  // 申请审批
  { key: 'requests', label: '申请记录', path: AppRoutes.REQUESTS, icon: '📋' },
  // 域名资产
  {
    key: 'domains',
    label: '域名资产',
    icon: '🌐',
    roles: DOMAIN_ROLES,
    children: [
      { key: 'domains-list', label: '域名列表', path: AppRoutes.DOMAINS, icon: '🌐' },
      { key: 'expiration', label: '到期管理', path: AppRoutes.EXPIRATION, icon: '⏰' },
      { key: 'ssl', label: 'SSL 证书', path: AppRoutes.SSL, icon: '🔒' },
    ],
  },
  // 系统管理
  {
    key: 'system',
    label: '系统管理',
    icon: '⚙️',
    roles: ADMIN_ROLES,
    children: [
      { key: 'users', label: '用户管理', path: AppRoutes.SYSTEM_USERS, icon: '👥' },
      { key: 'accounts', label: '域名账号管理', path: AppRoutes.SYSTEM_ACCOUNTS, icon: '🔑' },
      { key: 'providers', label: '服务商与默认', path: AppRoutes.SYSTEM_PROVIDERS, icon: '🏷️' },
      { key: 'statistics', label: '统计报表', path: AppRoutes.STATISTICS, icon: '📈' },
      { key: 'logs', label: '操作日志', path: AppRoutes.LOGS, icon: '📝' },
    ],
  },
];

const ALL_LEAVES: MenuLeaf[] = MENU.flatMap((e) => (isGroup(e) ? e.children : [e]));

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    domains: true,
    system: true,
  });

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) {
        setMobileMenuOpen(false);
      }
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    } else {
      navigate('/login');
    }
  }, [navigate]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

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

  const roleLabels: Record<string, string> = {
    super_admin: '超级管理员',
    admin: '管理员',
    domain_spec: '域名专员',
    business: '业务人员',
  };

  const isActive = (path: string) => location.pathname.startsWith(path);

  const handleNavigate = (path: string) => {
    navigate(path);
    setMobileMenuOpen(false);
  };

  const toggleGroup = (key: string) => {
    setExpandedGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // 桌面端折叠为图标栏时，扁平展示所有叶子项（图标）
  const iconOnly = !isMobile && sidebarCollapsed;
  const sidebarWidth = sidebarCollapsed ? 'w-16' : 'w-64';

  // 当前激活的叶子项（用于头部标题）
  const activeLeaf = ALL_LEAVES.find((l) => isActive(l.path));

  const renderLeaf = (item: MenuLeaf, indented: boolean) => (
    <button
      key={item.key}
      onClick={() => handleNavigate(item.path)}
      className={`w-full flex items-center px-3 py-2 mt-0.5 text-sm rounded-md transition-colors ${
        isActive(item.path)
          ? 'bg-blue-50 text-blue-600 font-medium'
          : 'text-gray-600 hover:bg-gray-50'
      } ${indented && !iconOnly ? 'pl-9' : ''}`}
      title={item.label}
    >
      <span className="text-base">{item.icon}</span>
      {!iconOnly && <span className="ml-3">{item.label}</span>}
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 移动端遮罩层 */}
      {isMobile && mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* 侧边栏 */}
      <div
        className={`fixed inset-y-0 left-0 z-50 bg-white shadow-lg transition-all duration-300 ${
          isMobile
            ? `w-64 ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`
            : sidebarWidth
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 border-b border-gray-200 px-4">
          <span className="text-xl font-bold text-blue-600">
            {iconOnly ? '🌐' : '域名管家'}
          </span>
          {isMobile && (
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* 导航菜单 */}
        <nav className="mt-4 px-2 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 8rem)' }}>
          {MENU.map((entry) => {
            if (!hasPermission(entry.roles)) return null;

            // 叶子项（顶级）
            if (!isGroup(entry)) {
              return renderLeaf(entry, false);
            }

            // 分组
            const visibleChildren = entry.children.filter((c) => hasPermission(c.roles));
            if (visibleChildren.length === 0) return null;

            // 折叠为图标栏时，扁平展示子项图标，不显示分组标题
            if (iconOnly) {
              return (
                <div key={entry.key} className="mt-2 pt-2 border-t border-gray-100">
                  {visibleChildren.map((child) => renderLeaf(child, false))}
                </div>
              );
            }

            const expanded = expandedGroups[entry.key] ?? true;
            const groupActive = visibleChildren.some((c) => isActive(c.path));

            return (
              <div key={entry.key} className="mt-3">
                <button
                  onClick={() => toggleGroup(entry.key)}
                  className={`w-full flex items-center px-3 py-2 text-xs font-semibold uppercase tracking-wider rounded-md transition-colors ${
                    groupActive ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'
                  }`}
                >
                  <span className="text-base">{entry.icon}</span>
                  <span className="ml-3 flex-1 text-left">{entry.label}</span>
                  <svg
                    className={`w-4 h-4 transition-transform ${expanded ? 'rotate-90' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                {expanded && (
                  <div className="mt-1">
                    {visibleChildren.map((child) => renderLeaf(child, true))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* 折叠按钮 - 仅桌面端显示 */}
        {!isMobile && (
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="absolute bottom-4 left-1/2 transform -translate-x-1/2 text-gray-400 hover:text-gray-600 p-2"
          >
            <svg
              className={`w-5 h-5 transition-transform ${sidebarCollapsed ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        )}
      </div>

      {/* 主内容区域 */}
      <div
        className={`transition-all duration-300 ${
          isMobile ? 'ml-0' : (sidebarCollapsed ? 'ml-16' : 'ml-64')
        }`}
      >
        {/* 头部 */}
        <header className="sticky top-0 z-30 h-14 md:h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 md:px-6">
          <div className="flex items-center space-x-3">
            {/* 移动端汉堡菜单 */}
            {isMobile && (
              <button
                onClick={() => setMobileMenuOpen(true)}
                className="text-gray-500 hover:text-gray-700 p-1"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
            <h1 className="text-base md:text-lg font-semibold text-gray-800 truncate">
              {activeLeaf?.label || '域名管家'}
            </h1>
          </div>

          <div className="flex items-center space-x-2 md:space-x-4">
            {/* 用户信息 */}
            <div className="flex items-center space-x-2">
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.name}
                  className="h-7 w-7 md:h-8 md:w-8 rounded-full"
                />
              ) : (
                <div className="h-7 w-7 md:h-8 md:w-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs md:text-sm font-medium">
                  {user?.name?.charAt(0) || 'U'}
                </div>
              )}
              <div className="text-sm hidden sm:block">
                <div className="font-medium text-gray-700 text-xs md:text-sm">{user?.name}</div>
                <div className="text-gray-500 text-xs">{roleLabels[user?.role || ''] || user?.role}</div>
              </div>
            </div>

            {/* 退出登录 */}
            <button
              onClick={handleLogout}
              className="text-xs md:text-sm text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100"
            >
              退出
            </button>
          </div>
        </header>

        {/* 页面内容 */}
        <main className="p-3 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
