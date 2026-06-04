/**
 * 审计日志页面
 */
import { useState, useEffect, type KeyboardEvent } from 'react';
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
  const [draftActionFilter, setDraftActionFilter] = useState('');
  const [draftResourceTypeFilter, setDraftResourceTypeFilter] = useState('');
  const [draftKeyword, setDraftKeyword] = useState('');
  const [draftUserKeyword, setDraftUserKeyword] = useState('');
  const [draftStartDate, setDraftStartDate] = useState('');
  const [draftEndDate, setDraftEndDate] = useState('');
  const [dateRangeOpen, setDateRangeOpen] = useState(false);
  const pageSize = 20;

  useEffect(() => {
    fetchLogs();
  }, [page, actorTypeFilter, actionFilter, resourceTypeFilter, keyword, userKeyword, startDate, endDate]);

  const switchActorType = (value: string) => {
    setActorTypeFilter(value);
    setPage(1);
  };

  const applyFilters = () => {
    setActionFilter(draftActionFilter);
    setResourceTypeFilter(draftResourceTypeFilter);
    setKeyword(draftKeyword.trim());
    setUserKeyword(draftUserKeyword.trim());
    setStartDate(draftStartDate);
    setEndDate(draftEndDate);
    setDateRangeOpen(false);
    setPage(1);
  };

  const handleFilterKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      applyFilters();
    }
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
    setDraftActionFilter('');
    setDraftResourceTypeFilter('');
    setDraftKeyword('');
    setDraftUserKeyword('');
    setDraftStartDate('');
    setDraftEndDate('');
    setDateRangeOpen(false);
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

  const actorTabs = [
    { value: '', label: '全部日志' },
    { value: 'user', label: '用户操作' },
    { value: 'system', label: '系统任务' },
  ];
  const dateRangeLabel = draftStartDate || draftEndDate
    ? `${draftStartDate || '开始日期'} 至 ${draftEndDate || '结束日期'}`
    : '日期范围';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">审计日志</h1>
        <p className="mt-1 text-sm text-gray-500">按操作来源、日期、关键词和用户快速定位日志。</p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-100">
        <div className="border-b border-gray-100 px-4 md:px-5">
          <div className="flex gap-1 overflow-x-auto">
            {actorTabs.map((tab) => (
              <button
                key={tab.value || 'all'}
                onClick={() => switchActorType(tab.value)}
                className={`relative px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                  actorTypeFilter === tab.value
                    ? 'text-blue-600'
                    : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                {tab.label}
                {actorTypeFilter === tab.value && (
                  <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-blue-600" />
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 md:p-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6 gap-3">
            <select
              value={draftActionFilter}
              onChange={(e) => setDraftActionFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">全部操作</option>
              <option value="create">创建</option>
              <option value="update">更新</option>
              <option value="delete">删除</option>
              <option value="approve">审批</option>
            </select>
            <select
              value={draftResourceTypeFilter}
              onChange={(e) => setDraftResourceTypeFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">全部资源</option>
              <option value="domain">域名</option>
              <option value="dns_record">DNS记录</option>
              <option value="request">申请</option>
              <option value="user">用户</option>
            </select>
            <button
              type="button"
              onClick={() => setDateRangeOpen(true)}
              className="flex items-center justify-between gap-2 px-3 py-2 border border-gray-300 rounded-md text-left text-sm text-gray-700 hover:bg-gray-50"
              title="日期范围"
            >
              <span className="truncate">{dateRangeLabel}</span>
              <span className="text-gray-400">📅</span>
            </button>
            <input
              type="text"
              value={draftKeyword}
              onChange={(e) => setDraftKeyword(e.target.value)}
              onKeyDown={handleFilterKeyDown}
              placeholder="关键词"
              className="px-3 py-2 border border-gray-300 rounded-md"
            />
            <input
              type="text"
              value={draftUserKeyword}
              onChange={(e) => setDraftUserKeyword(e.target.value)}
              onKeyDown={handleFilterKeyDown}
              placeholder="用户"
              className="px-3 py-2 border border-gray-300 rounded-md"
            />
            <button
              onClick={applyFilters}
              className="px-3 py-2 rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              搜索
            </button>
            <button
              onClick={clearFilters}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50"
            >
              清空
            </button>
          </div>
        </div>
      </div>

      {dateRangeOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4"
          onClick={() => setDateRangeOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">选择日期范围</h2>
              <button
                type="button"
                onClick={() => setDateRangeOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <div className="space-y-4">
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-gray-700">开始时间</span>
                <input
                  type="date"
                  value={draftStartDate}
                  onChange={(e) => setDraftStartDate(e.target.value)}
                  onKeyDown={handleFilterKeyDown}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-gray-700">结束时间</span>
                <input
                  type="date"
                  value={draftEndDate}
                  onChange={(e) => setDraftEndDate(e.target.value)}
                  onKeyDown={handleFilterKeyDown}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </label>
            </div>
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setDraftStartDate('');
                  setDraftEndDate('');
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50"
              >
                清空日期
              </button>
              <button
                type="button"
                onClick={() => setDateRangeOpen(false)}
                className="px-4 py-2 rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                确定
              </button>
            </div>
          </div>
        </div>
      )}

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
