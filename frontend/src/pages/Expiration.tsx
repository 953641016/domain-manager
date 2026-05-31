/**
 * 到期管理页面
 */
import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { formatDate as fmtDate, daysUntil } from '@/utils/datetime';

interface ExpiringDomain {
  id: number;
  name: string;
  registrar_code: string;
  status: string;
  expiration_date: string;
}

export default function ExpirationPage() {
  const [domains, setDomains] = useState<ExpiringDomain[]>([]);
  const [loading, setLoading] = useState(true);
  const [daysFilter, setDaysFilter] = useState(30);

  useEffect(() => {
    fetchExpiringDomains();
  }, [daysFilter]);

  const fetchExpiringDomains = async () => {
    try {
      setLoading(true);
      const response = await api.get('/domains/expiring/list', {
        params: { days: daysFilter }
      });
      setDomains(response.data.items || []);
    } catch (err) {
      console.error('获取到期域名失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => fmtDate(dateStr);
  const getDaysRemaining = (dateStr: string) => daysUntil(dateStr);

  const getStatusColor = (days: number | null) => {
    if (days === null) return 'bg-gray-100 text-gray-800';
    if (days <= 7) return 'bg-red-100 text-red-800';
    if (days <= 30) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">到期管理</h1>
        <div className="flex items-center space-x-2">
          <select
            value={daysFilter}
            onChange={(e) => setDaysFilter(Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value={7}>7天内</option>
            <option value={30}>30天内</option>
            <option value={90}>90天内</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500">即将到期</div>
          <div className="text-2xl font-bold text-yellow-600">
            {domains.filter(d => getDaysRemaining(d.expiration_date) <= 30).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500">紧急（7天内）</div>
          <div className="text-2xl font-bold text-red-600">
            {domains.filter(d => getDaysRemaining(d.expiration_date) <= 7).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500">总计</div>
          <div className="text-2xl font-bold text-blue-600">{domains.length}</div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {domains.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            没有即将到期的域名
          </div>
        ) : (
          <>
            {/* 桌面端表格 */}
            <div className="hidden md:block">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      域名
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      注册商
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      到期日期
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      剩余天数
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      状态
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {domains.map((domain) => {
                    const daysRemaining = getDaysRemaining(domain.expiration_date);
                    return (
                      <tr key={domain.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-blue-600">
                            {domain.name}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">
                            {domain.registrar_code || '-'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">
                            {formatDate(domain.expiration_date)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(daysRemaining)}`}>
                            {daysRemaining !== null ? `${daysRemaining} 天` : '-'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{domain.status}</div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* 移动端卡片列表 */}
            <div className="md:hidden space-y-2 p-3">
              {domains.map((domain) => {
                const daysRemaining = getDaysRemaining(domain.expiration_date);
                return (
                  <div
                    key={domain.id}
                    className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-medium text-sm text-blue-600">
                        {domain.name}
                      </div>
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getStatusColor(daysRemaining)}`}>
                        {daysRemaining !== null ? `${daysRemaining} 天` : '-'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                      <span>注册商: {domain.registrar_code || '-'}</span>
                      <span>到期: {formatDate(domain.expiration_date)}</span>
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
