/**
 * 仪表盘页面
 * 显示系统概览、统计信息和快捷操作
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/api/client';

interface DashboardStats {
  totalDomains: number;
  expiringDomains: number;
  pendingRequests: number;
  completedRequests: number;
}

interface ExpiringDomain {
  id: number;
  name: string;
  expiration_date: string;
  registrar_code: string;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats>({
    totalDomains: 0,
    expiringDomains: 0,
    pendingRequests: 0,
    completedRequests: 0,
  });
  const [expiringDomains, setExpiringDomains] = useState<ExpiringDomain[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      // 并行请求数据
      const [domainsRes, requestsRes, expiringRes] = await Promise.all([
        api.get('/domains', { params: { limit: 1 } }),
        api.get('/requests/stats'),
        api.get('/domains/expiring/list', { params: { days: 30 } }),
      ]);

      setStats({
        totalDomains: domainsRes.data.total || 0,
        expiringDomains: expiringRes.data.total || 0,
        pendingRequests: requestsRes.data.pending || 0,
        completedRequests: requestsRes.data.completed || 0,
      });

      setExpiringDomains(expiringRes.data.items?.slice(0, 5) || []);
    } catch (err) {
      console.error('获取仪表盘数据失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' });
  };

  const getDaysUntilExpiration = (dateStr: string) => {
    if (!dateStr) return null;
    const expiration = new Date(dateStr);
    const now = new Date();
    const diff = expiration.getTime() - now.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4 md:space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6">
        <div className="bg-white rounded-lg shadow p-4 md:p-6">
          <div className="flex items-center">
            <div className="p-2 md:p-3 rounded-full bg-blue-100 text-blue-600">
              <span className="text-xl md:text-2xl">🌐</span>
            </div>
            <div className="ml-3 md:ml-4">
              <p className="text-xs md:text-sm text-gray-500">域名总数</p>
              <p className="text-xl md:text-2xl font-semibold text-gray-900">{stats.totalDomains}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4 md:p-6">
          <div className="flex items-center">
            <div className="p-2 md:p-3 rounded-full bg-yellow-100 text-yellow-600">
              <span className="text-xl md:text-2xl">⏰</span>
            </div>
            <div className="ml-3 md:ml-4">
              <p className="text-xs md:text-sm text-gray-500">即将到期</p>
              <p className="text-xl md:text-2xl font-semibold text-gray-900">{stats.expiringDomains}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4 md:p-6">
          <div className="flex items-center">
            <div className="p-2 md:p-3 rounded-full bg-orange-100 text-orange-600">
              <span className="text-xl md:text-2xl">📋</span>
            </div>
            <div className="ml-3 md:ml-4">
              <p className="text-xs md:text-sm text-gray-500">待处理</p>
              <p className="text-xl md:text-2xl font-semibold text-gray-900">{stats.pendingRequests}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4 md:p-6">
          <div className="flex items-center">
            <div className="p-2 md:p-3 rounded-full bg-green-100 text-green-600">
              <span className="text-xl md:text-2xl">✅</span>
            </div>
            <div className="ml-3 md:ml-4">
              <p className="text-xs md:text-sm text-gray-500">已完成</p>
              <p className="text-xl md:text-2xl font-semibold text-gray-900">{stats.completedRequests}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 快捷操作 */}
      <div className="bg-white rounded-lg shadow p-4 md:p-6">
        <h2 className="text-base md:text-lg font-semibold text-gray-800 mb-3 md:mb-4">快捷操作</h2>
        <div className="grid grid-cols-2 gap-3 md:gap-4">
          <button
            onClick={() => navigate('/domains')}
            className="flex items-center justify-center p-3 md:p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="text-center">
              <span className="text-2xl md:text-3xl">🔍</span>
              <p className="mt-1 md:mt-2 text-xs md:text-sm text-gray-600">查询域名</p>
            </div>
          </button>

          <button
            onClick={() => navigate('/requests')}
            className="flex items-center justify-center p-3 md:p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="text-center">
              <span className="text-2xl md:text-3xl">📋</span>
              <p className="mt-1 md:mt-2 text-xs md:text-sm text-gray-600">查看申请</p>
            </div>
          </button>
        </div>
      </div>

      {/* 即将到期的域名 */}
      <div className="bg-white rounded-lg shadow p-4 md:p-6">
        <div className="flex items-center justify-between mb-3 md:mb-4">
          <h2 className="text-base md:text-lg font-semibold text-gray-800">即将到期的域名</h2>
          <button
            onClick={() => navigate('/expiration')}
            className="text-xs md:text-sm text-blue-600 hover:text-blue-800"
          >
            查看全部 →
          </button>
        </div>

        {expiringDomains.length === 0 ? (
          <div className="text-center py-6 md:py-8 text-gray-500 text-sm">
            暂无即将到期的域名
          </div>
        ) : (
          <>
            {/* 桌面端表格 */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">域名</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">注册商</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">到期日期</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">剩余天数</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {expiringDomains.map((domain) => {
                    const daysLeft = getDaysUntilExpiration(domain.expiration_date);
                    return (
                      <tr
                        key={domain.id}
                        className="hover:bg-gray-50 cursor-pointer"
                        onClick={() => navigate(`/domains/${domain.name}`)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{domain.name}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{domain.registrar_code}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{formatDate(domain.expiration_date)}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                              daysLeft !== null && daysLeft <= 7
                                ? 'bg-red-100 text-red-800'
                                : daysLeft !== null && daysLeft <= 30
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-green-100 text-green-800'
                            }`}
                          >
                            {daysLeft !== null ? `${daysLeft}天` : '-'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* 移动端卡片列表 */}
            <div className="md:hidden space-y-2">
              {expiringDomains.map((domain) => {
                const daysLeft = getDaysUntilExpiration(domain.expiration_date);
                return (
                  <div
                    key={domain.id}
                    className="border border-gray-200 rounded-lg p-3 cursor-pointer hover:bg-gray-50"
                    onClick={() => navigate(`/domains/${domain.name}`)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-medium text-sm text-gray-900">{domain.name}</div>
                      <span
                        className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                          daysLeft !== null && daysLeft <= 7
                            ? 'bg-red-100 text-red-800'
                            : daysLeft !== null && daysLeft <= 30
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-green-100 text-green-800'
                        }`}
                      >
                        {daysLeft !== null ? `${daysLeft}天` : '-'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
                      <span>{domain.registrar_code}</span>
                      <span>{formatDate(domain.expiration_date)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
