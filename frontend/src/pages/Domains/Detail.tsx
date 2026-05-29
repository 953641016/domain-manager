/**
 * 域名详情页面
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '@/api/client';

interface DomainInfo {
  id: number;
  name: string;
  registrar_code: string;
  status: string;
  registration_date: string;
  expiration_date: string;
  auto_renew: boolean;
}

export default function DomainDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [domain, setDomain] = useState<DomainInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (name) {
      fetchDomainInfo();
    }
  }, [name]);

  const fetchDomainInfo = async () => {
    try {
      setLoading(true);
      // 由于API没有单个域名查询接口，这里使用列表搜索模拟
      const response = await api.get('/domains', {
        params: { search: name }
      });
      const domainList = response.data.items || [];
      const found = domainList.find((d: DomainInfo) => d.name === name);
      setDomain(found || null);
    } catch (err) {
      console.error('获取域名信息失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (!domain) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">域名不存在</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <button
          onClick={() => navigate('/domains')}
          className="text-gray-500 hover:text-gray-700 mr-4"
        >
          ← 返回
        </button>
        <h1 className="text-2xl font-bold text-gray-800">{domain.name}</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">基本信息</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-gray-500">域名状态</label>
              <p className="font-medium text-gray-900">{domain.status}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">注册商</label>
              <p className="font-medium text-gray-900">{domain.registrar_code || '-'}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">注册日期</label>
              <p className="font-medium text-gray-900">{formatDate(domain.registration_date)}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">到期日期</label>
              <p className="font-medium text-gray-900">{formatDate(domain.expiration_date)}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">自动续费</label>
              <p className="font-medium text-gray-900">{domain.auto_renew ? '是' : '否'}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">操作</h2>
          <div className="space-y-3">
            <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
              查看 DNS 记录
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
