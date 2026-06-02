/**
 * 申请详情页面
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '@/api/client';
import { formatDateTime } from '@/utils/datetime';

interface RequestDetail {
  id: string;
  type: string;
  requester_name: string;
  domain_name: string;
  status: string;
  created_at: string;
  approved_at?: string;
  reject_reason?: string;
  error_message?: string | null;
  execution_result?: any;
  approver_name?: string;
  request_data?: any;
  selected_registrar_code?: string | null;
  selected_reg_account_id?: number | null;
  selected_dns_provider_code?: string | null;
  selected_dns_account_id?: number | null;
}

interface AccountOption {
  id: number;
  name: string;
  registrar_code?: string;
  provider_code?: string;
  owner_name?: string | null;
}

export default function RequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [request, setRequest] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [regAccounts, setRegAccounts] = useState<AccountOption[]>([]);
  const [dnsAccounts, setDnsAccounts] = useState<AccountOption[]>([]);
  const [selectedRegAccountId, setSelectedRegAccountId] = useState('');
  const [selectedDnsAccountId, setSelectedDnsAccountId] = useState('');

  useEffect(() => {
    if (id) {
      fetchRequest();
      fetchAccounts();
    }
  }, [id]);

  const fetchRequest = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/requests/${id}`);
      setRequest(response.data);
      if (response.data?.selected_reg_account_id) {
        setSelectedRegAccountId(String(response.data.selected_reg_account_id));
      }
      if (response.data?.selected_dns_account_id) {
        setSelectedDnsAccountId(String(response.data.selected_dns_account_id));
      }
    } catch (err) {
      console.error('获取申请详情失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAccounts = async () => {
    try {
      const [regRes, dnsRes] = await Promise.all([
        api.get('/domains/accounts/reg/list'),
        api.get('/domains/accounts/dns/list'),
      ]);
      setRegAccounts(regRes.data?.items || []);
      setDnsAccounts(dnsRes.data?.items || []);
    } catch (err) {
      console.error('获取账号列表失败:', err);
    }
  };

  const handleApprove = async () => {
    if (!request) return;
    
    try {
      setActionLoading(true);
      const payload: Record<string, any> = {};
      if (request.type === 'domain_register' && selectedRegAccountId) {
        const account = regAccounts.find((item) => item.id === Number(selectedRegAccountId));
        payload.selected_reg_account_id = Number(selectedRegAccountId);
        payload.selected_registrar_code = account?.registrar_code;
      }
      if (request.type === 'dns_record' && selectedDnsAccountId) {
        const account = dnsAccounts.find((item) => item.id === Number(selectedDnsAccountId));
        payload.selected_dns_account_id = Number(selectedDnsAccountId);
        payload.selected_dns_provider_code = account?.provider_code;
      }
      await api.post(`/requests/${request.id}/approve`, payload);
      fetchRequest();
    } catch (err: any) {
      console.error('审批失败:', err);
      alert(err.response?.data?.detail || '审批失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!request) return;
    
    try {
      setActionLoading(true);
      await api.post(`/requests/${request.id}/reject`, { reason: rejectReason.trim() || null });
      setShowRejectModal(false);
      fetchRequest();
    } catch (err: any) {
      console.error('拒绝失败:', err);
      alert(err.response?.data?.detail || '拒绝失败');
    } finally {
      setActionLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    return formatDateTime(dateStr);
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { color: string; label: string }> = {
      pending: { color: 'bg-yellow-100 text-yellow-800', label: '待审批' },
      approved: { color: 'bg-blue-100 text-blue-800', label: '已通过' },
      rejected: { color: 'bg-red-100 text-red-800', label: '已拒绝' },
      completed: { color: 'bg-green-100 text-green-800', label: '已完成' },
      failed: { color: 'bg-gray-100 text-gray-800', label: '执行失败' },
    };
    const info = statusMap[status] || { color: 'bg-gray-100 text-gray-800', label: status };
    return (
      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${info.color}`}>
        {info.label}
      </span>
    );
  };

  const selectedRegAccount = regAccounts.find((item) => item.id === Number(selectedRegAccountId));
  const selectedDnsAccount = dnsAccounts.find((item) => item.id === Number(selectedDnsAccountId));

  const renderExecutionResult = () => {
    const result = request?.execution_result;
    if (!result) return null;

    const records = Array.isArray(result.records) ? result.records : [];
    if (records.length > 0) {
      return (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-md">
          <label className="text-sm text-gray-700 font-medium">执行明细</label>
          <div className="mt-2 space-y-2 text-sm">
            {records.map((item: any, index: number) => {
              const record = item.record || {};
              const success = item.status === 'success' || item.status === 'skipped';
              const host = record.host || record.name || record.hostname || '@';
              const value = record.value || record.content || record.target || '-';
              return (
                <div
                  key={`${host}-${record.type || record.record_type}-${index}`}
                  className={success ? 'text-green-700' : 'text-red-700'}
                >
                  <span className="font-medium">{success ? '✓' : '✗'} {record.type || record.record_type || '-'} {host}</span>
                  <span className="text-gray-600"> → {value}</span>
                  {item.message && <span>：{item.message}</span>}
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    return (
      <div className="p-4 bg-gray-50 border border-gray-200 rounded-md">
        <label className="text-sm text-gray-700 font-medium">执行结果</label>
        <pre className="mt-2 text-sm overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(result, null, 2)}
        </pre>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">申请不存在</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <button
          onClick={() => navigate('/requests')}
          className="text-gray-500 hover:text-gray-700 mr-4"
        >
          ← 返回
        </button>
        <h1 className="text-2xl font-bold text-gray-800">申请详情</h1>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">{request.domain_name}</h2>
              <p className="text-sm text-gray-500">申请编号: {request.id}</p>
            </div>
            {getStatusBadge(request.status)}
          </div>
        </div>

        <div className="px-6 py-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-500">申请类型</label>
              <p className="font-medium text-gray-900">
                {request.type === 'domain_register' ? '域名注册' : request.type}
              </p>
            </div>
            <div>
              <label className="text-sm text-gray-500">申请人</label>
              <p className="font-medium text-gray-900">{request.requester_name}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">创建时间</label>
              <p className="font-medium text-gray-900">{formatDate(request.created_at)}</p>
            </div>
            {request.approver_name && (
              <div>
                <label className="text-sm text-gray-500">审批人</label>
                <p className="font-medium text-gray-900">{request.approver_name}</p>
              </div>
            )}
            {request.approved_at && (
              <div>
                <label className="text-sm text-gray-500">审批时间</label>
                <p className="font-medium text-gray-900">{formatDate(request.approved_at)}</p>
              </div>
            )}
          </div>

          {request.reject_reason && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <label className="text-sm text-red-700 font-medium">拒绝原因</label>
              <p className="text-red-600">{request.reject_reason}</p>
            </div>
          )}

          {request.error_message && (
            <div className="p-4 bg-orange-50 border border-orange-200 rounded-md">
              <label className="text-sm text-orange-700 font-medium">失败日志</label>
              <p className="text-orange-700">{request.error_message}</p>
            </div>
          )}

          {renderExecutionResult()}

          {request.request_data && (
            <div>
              <label className="text-sm text-gray-500">申请详情</label>
              <pre className="mt-2 p-4 bg-gray-50 rounded-md text-sm overflow-x-auto">
                {typeof request.request_data === 'string' 
                  ? request.request_data 
                  : JSON.stringify(request.request_data, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {request.status === 'pending' && (
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div className="space-y-4">
              {request.type === 'domain_register' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">注册账号</label>
                  <select
                    value={selectedRegAccountId}
                    onChange={(e) => setSelectedRegAccountId(e.target.value)}
                    className="w-full md:w-96 px-3 py-2 border border-gray-300 rounded-md bg-white"
                  >
                    <option value="">不指定，后端自动判断</option>
                    {regAccounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name}（{account.registrar_code}）
                      </option>
                    ))}
                  </select>
                  {selectedRegAccount && (
                    <p className="text-xs text-gray-500 mt-1">
                      已选：{selectedRegAccount.name} / {selectedRegAccount.registrar_code}
                    </p>
                  )}
                </div>
              )}
              {request.type === 'dns_record' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">DNS账号</label>
                  <select
                    value={selectedDnsAccountId}
                    onChange={(e) => setSelectedDnsAccountId(e.target.value)}
                    className="w-full md:w-96 px-3 py-2 border border-gray-300 rounded-md bg-white"
                  >
                    <option value="">不指定，后端按域名自动匹配</option>
                    {dnsAccounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name}（{account.provider_code}）
                      </option>
                    ))}
                  </select>
                  {selectedDnsAccount && (
                    <p className="text-xs text-gray-500 mt-1">
                      已选：{selectedDnsAccount.name} / {selectedDnsAccount.provider_code}
                    </p>
                  )}
                </div>
              )}
              <div className="flex space-x-4">
              <button
                onClick={handleApprove}
                disabled={actionLoading}
                className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                通过
              </button>
              <button
                onClick={() => setShowRejectModal(true)}
                disabled={actionLoading}
                className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                拒绝
              </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">拒绝申请</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                拒绝原因
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-md"
                placeholder="请输入拒绝原因..."
              />
            </div>
            <div className="flex space-x-4">
              <button
                onClick={handleReject}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                确认拒绝
              </button>
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
