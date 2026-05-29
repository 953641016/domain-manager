/**
 * 统计报表页面
 */
import { useState, useEffect } from 'react';
import { api } from '@/api/client';

interface StatsData {
  domains: {
    total: number;
    active: number;
    expiring: number;
    expired: number;
  };
  requests: {
    total: number;
    pending: number;
    approved: number;
    rejected: number;
  };
}

export default function StatisticsPage() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      // 同时获取多个统计数据
      const [domainsRes, requestsRes, auditRes] = await Promise.all([
        api.get('/domains', { params: { limit: 1 } }),
        api.get('/requests/stats'),
        api.get('/audit/stats')
      ]);

      setStats({
        domains: {
          total: domainsRes.data.total || 0,
          active: 0,
          expiring: 0,
          expired: 0
        },
        requests: {
          total: requestsRes.data.total || 0,
          pending: requestsRes.data.pending || 0,
          approved: requestsRes.data.approved || 0,
          rejected: requestsRes.data.rejected || 0
        }
      });
    } catch (err) {
      console.error('获取统计数据失败:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">统计报表</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">域名总数</h3>
          <div className="text-3xl font-bold text-blue-600 mt-2">
            {stats?.domains.total || 0}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">待审批申请</h3>
          <div className="text-3xl font-bold text-yellow-600 mt-2">
            {stats?.requests.pending || 0}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">已通过申请</h3>
          <div className="text-3xl font-bold text-green-600 mt-2">
            {stats?.requests.approved || 0}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">申请总数</h3>
          <div className="text-3xl font-bold text-purple-600 mt-2">
            {stats?.requests.total || 0}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">域名分布</h2>
          <div className="h-64 flex items-center justify-center text-gray-400">
            图表占位
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">申请趋势</h2>
          <div className="h-64 flex items-center justify-center text-gray-400">
            图表占位
          </div>
        </div>
      </div>
    </div>
  );
}
