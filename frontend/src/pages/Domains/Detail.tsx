/**
 * 域名详情页面
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '@/api/client';
import { formatDateTime } from '@/utils/datetime';

interface DomainInfo {
  id: number;
  name: string;
  registrar_code: string;
  dns_provider_code?: string;
  dns_account_name?: string | null;
  status: string;
  registration_date: string;
  expiration_date: string;
  auto_renew: boolean;
}

interface DnsRecord {
  id: number;
  record_type: string;
  host: string;
  value: string;
  ttl?: number;
  status?: string;
}

export default function DomainDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [domain, setDomain] = useState<DomainInfo | null>(null);
  const [dnsRecords, setDnsRecords] = useState<DnsRecord[]>([]);
  const [dnsLoading, setDnsLoading] = useState(false);
  const [showDnsRecords, setShowDnsRecords] = useState(searchParams.get('tab') === 'dns');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (name) {
      fetchDomainInfo();
    }
  }, [name]);

  useEffect(() => {
    setShowDnsRecords(searchParams.get('tab') === 'dns');
  }, [searchParams]);

  useEffect(() => {
    if (domain && showDnsRecords) {
      fetchDnsRecords(domain.id);
    }
  }, [domain, showDnsRecords]);

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

  const formatDate = (dateStr: string) => formatDateTime(dateStr);

  const fetchDnsRecords = async (domainId: number) => {
    try {
      setDnsLoading(true);
      const response = await api.get(`/dns/domain/${domainId}`);
      setDnsRecords(response.data.items || []);
    } catch (err) {
      console.error('获取DNS记录失败:', err);
      setDnsRecords([]);
    } finally {
      setDnsLoading(false);
    }
  };

  const handleViewDnsRecords = () => {
    setSearchParams({ tab: 'dns' });
    setShowDnsRecords(true);
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
              <label className="text-sm text-gray-500">DNS账号</label>
              <p className="font-medium text-gray-900">{domain.dns_account_name || '-'}</p>
              {domain.dns_provider_code && (
                <p className="text-sm text-gray-500">{domain.dns_provider_code}</p>
              )}
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
            <button
              onClick={handleViewDnsRecords}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              查看 DNS 记录
            </button>
          </div>
        </div>
      </div>

      {showDnsRecords && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">DNS 记录</h2>
            <button
              onClick={() => domain && fetchDnsRecords(domain.id)}
              disabled={dnsLoading}
              className="px-3 py-1 text-sm text-blue-600 border border-blue-300 rounded hover:bg-blue-50 disabled:opacity-50"
            >
              刷新
            </button>
          </div>
          {dnsLoading ? (
            <div className="p-6 text-center text-gray-500">加载中...</div>
          ) : dnsRecords.length === 0 ? (
            <div className="p-6 text-center text-gray-500">暂无 DNS 记录</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">主机记录</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">记录值</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">TTL</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {dnsRecords.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {record.record_type}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                        {record.host}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700 break-all">
                        {record.value}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {record.ttl ?? '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {record.status || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
