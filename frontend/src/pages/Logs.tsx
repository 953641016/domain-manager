/**
 * 审计日志页面
 */
import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { formatDateTime } from '@/utils/datetime';

interface AuditLog {
  id: number;
  user_id: number;
  user_name: string;
  action: string;
  resource_type: string;
  resource_name: string;
  status: string;
  created_at: string;
}

export default function LogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [actorTypeFilter, setActorTypeFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [resourceTypeFilter, setResourceTypeFilter] = useState('');
  const [keyword, setKeyword] = useState('');
  const [userKeyword, setUserKeyword] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const pageSize = 20;

  useEffect(() => {
    fetchLogs();
  }, [page, actorTypeFilter, actionFilter, resourceTypeFilter, keyword, userKeyword, startDate, endDate]);

  const resetPage = (setter: (value: string) => void, value: string) => {
    setter(value);
    setPage(1);
  };

  const startTime = startDate ? `${startDate}T00:00:00` : undefined;
  const endTime = endDate ? `${endDate}T23:59:59` : undefined;

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await api.get('/audit/logs', {
        params: {
          skip: (page - 1) * pageSize,
          limit: pageSize,
          actor_type: actorTypeFilter || undefined,
          action: actionFilter || undefined,
          resource_type: resourceTypeFilter || undefined,
          keyword: keyword || undefined,
          user_keyword: userKeyword || undefined,
          start_time: startTime,
          end_time: endTime
        }
      });
      setLogs(response.data.items || []);
      setTotal(response.data.total || 0);
    } catch (err) {
      console.error('获取审计日志失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => formatDateTime(dateStr);

  const clearFilters = () => {
    setActorTypeFilter('');
    setActionFilter('');
    setResourceTypeFilter('');
    setKeyword('');
    setUserKeyword('');
    setStartDate('');
    setEndDate('');
    setPage(1);
  };

  const getStatusBadge = (status: string) => {
    return status === 'success' ? (
      <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
        成功
      </span>
    ) : (
      <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
        失败
      </span>
    );
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
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <h1 className="text-2xl font-bold text-gray-800">审计日志</h1>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-7 gap-2">
          <select
            value={actorTypeFilter}
            onChange={(e) => resetPage(setActorTypeFilter, e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="">全部类型</option>
            <option value="user">用户操作</option>
            <option value="system">系统任务</option>
          </select>
          <select
            value={actionFilter}
            onChange={(e) => resetPage(setActionFilter, e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="">全部操作</option>
            <option value="create">创建</option>
            <option value="update">更新</option>
            <option value="delete">删除</option>
            <option value="approve">审批</option>
          </select>
          <select
            value={resourceTypeFilter}
            onChange={(e) => resetPage(setResourceTypeFilter, e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="">全部资源</option>
            <option value="domain">域名</option>
            <option value="dns_record">DNS记录</option>
            <option value="request">申请</option>
            <option value="user">用户</option>
          </select>
          <input
            type="date"
            value={startDate}
            onChange={(e) => resetPage(setStartDate, e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
            title="开始日期"
          />
          <input
            type="date"
            value={endDate}
            onChange={(e) => resetPage(setEndDate, e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
            title="结束日期"
          />
          <input
            type="text"
            value={keyword}
            onChange={(e) => resetPage(setKeyword, e.target.value)}
            placeholder="关键词"
            className="px-3 py-2 border border-gray-300 rounded-md"
          />
          <input
            type="text"
            value={userKeyword}
            onChange={(e) => resetPage(setUserKeyword, e.target.value)}
            placeholder="用户"
            className="px-3 py-2 border border-gray-300 rounded-md"
          />
          <button
            onClick={clearFilters}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50"
          >
            清空
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            暂无审计日志
          </div>
        ) : (
          <>
            {/* 桌面端表格 */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      时间
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      用户
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      资源
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      状态
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{formatDate(log.created_at)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{log.user_name || '-'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{log.action}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">
                          {log.resource_type}: {log.resource_name || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(log.status)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 移动端卡片列表 */}
            <div className="md:hidden space-y-2">
              {logs.map((log) => (
                <div key={log.id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900">{log.action}</span>
                    {getStatusBadge(log.status)}
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {log.resource_type}: {log.resource_name || '-'}
                  </div>
                  <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
                    <span>{log.user_name || '-'}</span>
                    <span>{formatDate(log.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-gray-50 px-4 md:px-6 py-3 flex items-center justify-between">
              <div className="text-xs md:text-sm text-gray-500">
                共 {total} 条记录
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 border border-gray-300 rounded-md text-xs md:text-sm disabled:opacity-50"
                >
                  上一页
                </button>
                <span className="px-3 py-1 text-xs md:text-sm text-gray-700">
                  第 {page} 页
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={logs.length < pageSize}
                  className="px-3 py-1 border border-gray-300 rounded-md text-xs md:text-sm disabled:opacity-50"
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
