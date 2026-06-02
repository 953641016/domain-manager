/**
 * 域名列表页面
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/api/client';
import { formatDate as fmtDate } from '@/utils/datetime';

interface Domain {
  id: number;
  name: string;
  registrar_code: string;
  dns_provider_code?: string;
  dns_account_id?: number | null;
  dns_account_name?: string | null;
  status: string;
  expiration_date: string;
  auto_renew: boolean;
  created_at: string;
}

export default function DomainsPage() {
  const navigate = useNavigate();
  const [domains, setDomains] = useState<Domain[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    fetchDomains();
  }, [page, statusFilter]);

  const fetchDomains = async () => {
    try {
      setLoading(true);
      const response = await api.get('/domains', {
        params: {
          skip: (page - 1) * pageSize,
          limit: pageSize,
          status: statusFilter || undefined,
          search: search || undefined,
        },
      });
      setDomains(response.data.items || []);
      setTotal(response.data.total || 0);
    } catch (err) {
      console.error('获取域名列表失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
    fetchDomains();
  };

  const formatDate = (dateStr: string) => fmtDate(dateStr);

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { color: string; label: string }> = {
      active: { color: 'bg-green-100 text-green-800', label: '正常' },
      expiring: { color: 'bg-yellow-100 text-yellow-800', label: '即将到期' },
      expired: { color: 'bg-red-100 text-red-800', label: '已过期' },
      transferred: { color: 'bg-gray-100 text-gray-800', label: '已转移' },
    };
    const info = statusMap[status] || { color: 'bg-gray-100 text-gray-800', label: status };
    return (
      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${info.color}`}>
        {info.label}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* 搜索和筛选 */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-0">
            <input
              type="text"
              placeholder="搜索域名..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">全部状态</option>
            <option value="active">正常</option>
            <option value="expiring">即将到期</option>
            <option value="expired">已过期</option>
          </select>
          <button
            onClick={handleSearch}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            搜索
          </button>
        </div>
      </div>

      {/* 域名列表 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">加载中...</div>
        ) : domains.length === 0 ? (
          <div className="p-8 text-center text-gray-500">暂无域名数据</div>
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
                      DNS账号
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      状态
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      到期日期
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      自动续费
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {domains.map((domain) => (
                    <tr key={domain.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-blue-600 cursor-pointer hover:underline" onClick={() => navigate(`/domains/${domain.name}`)}>
                          {domain.name}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{domain.registrar_code || '-'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{domain.dns_account_name || '-'}</div>
                        {domain.dns_provider_code && (
                          <div className="text-xs text-gray-400">{domain.dns_provider_code}</div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(domain.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{formatDate(domain.expiration_date)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{domain.auto_renew ? '是' : '否'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          onClick={() => navigate(`/domains/${domain.name}`)}
                          className="text-blue-600 hover:text-blue-800 mr-3"
                        >
                          详情
                        </button>
                        <button
                          onClick={() => navigate(`/dns?domain_id=${domain.id}`)}
                          className="text-green-600 hover:text-green-800"
                        >
                          DNS
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 移动端卡片列表 */}
            <div className="md:hidden space-y-2 p-3">
              {domains.map((domain) => (
                <div
                  key={domain.id}
                  className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50"
                >
                  <div className="flex items-center justify-between">
                    <div
                      className="font-medium text-sm text-blue-600 cursor-pointer hover:underline"
                      onClick={() => navigate(`/domains/${domain.name}`)}
                    >
                      {domain.name}
                    </div>
                    {getStatusBadge(domain.status)}
                  </div>
                  <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                    <span>注册商: {domain.registrar_code || '-'}</span>
                    <span>到期: {formatDate(domain.expiration_date)}</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    DNS账号: {domain.dns_account_name || '-'}
                  </div>
                  <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-100">
                    <div className="text-xs text-gray-500">
                      自动续费: {domain.auto_renew ? '是' : '否'}
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => navigate(`/domains/${domain.name}`)}
                        className="px-2 py-1 text-xs text-blue-600 border border-blue-300 rounded hover:bg-blue-50"
                      >
                        详情
                      </button>
                      <button
                        onClick={() => navigate(`/dns?domain_id=${domain.id}`)}
                        className="px-2 py-1 text-xs text-green-600 border border-green-300 rounded hover:bg-green-50"
                      >
                        DNS
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 分页 */}
            <div className="bg-gray-50 px-4 md:px-6 py-3 flex items-center justify-between border-t border-gray-200">
              <div className="text-xs md:text-sm text-gray-500">
                共 {total} 条记录
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-2 md:px-3 py-1 border border-gray-300 rounded-md text-xs md:text-sm disabled:opacity-50"
                >
                  上一页
                </button>
                <span className="px-2 md:px-3 py-1 text-xs md:text-sm text-gray-700">
                  {page}
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={domains.length < pageSize}
                  className="px-2 md:px-3 py-1 border border-gray-300 rounded-md text-xs md:text-sm disabled:opacity-50"
                >
                  下一页
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
