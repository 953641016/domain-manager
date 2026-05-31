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
  approver_name?: string;
  request_data?: any;
}

export default function RequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [request, setRequest] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);

  useEffect(() => {
    if (id) {
      fetchRequest();
    }
  }, [id]);

  const fetchRequest = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/requests/${id}`);
      setRequest(response.data);
    } catch (err) {
      console.error('获取申请详情失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!request) return;
    
    try {
      setActionLoading(true);
      await api.post(`/requests/${request.id}/approve`);
      fetchRequest();
    } catch (err: any) {
      console.error('审批失败:', err);
      alert(err.response?.data?.detail || '审批失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!request || !rejectReason) return;
    
    try {
      setActionLoading(true);
      await api.post(`/requests/${request.id}/reject`, { reason: rejectReason });
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
                disabled={!rejectReason || actionLoading}
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
