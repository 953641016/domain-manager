/**
 * SSL 证书监控页面
 * 展示所监控域名的证书状态、到期天数（只读）
 * 对接后端 GET /ssl/certificates
 */
import { useState, useEffect } from 'react';
import { api } from '@/api/client';

interface CertificateInfo {
  domain: string;
  issuer: string;
  valid_from: string;
  valid_to: string;
  days_remaining: number;
  is_valid: boolean;
  serial_number?: string;
  fingerprint?: string;
}

interface CertificateResponse {
  success: boolean;
  certificates: CertificateInfo[];
  total: number;
  valid_count: number;
  expiring_soon_count: number;
}

const THRESHOLD_DAYS = 30;

export default function SslPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<CertificateResponse | null>(null);

  useEffect(() => {
    loadCertificates();
  }, []);

  const loadCertificates = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get<CertificateResponse>('/ssl/certificates', {
        params: { threshold_days: THRESHOLD_DAYS },
      });
      setData(res.data);
    } catch (err: any) {
      console.error('获取证书信息失败:', err);
      setError(err.response?.data?.detail || '获取证书信息失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (s: string) => {
    if (!s) return '-';
    const d = new Date(s);
    return isNaN(d.getTime()) ? s : d.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' });
  };

  const statusBadge = (cert: CertificateInfo) => {
    if (!cert.is_valid) {
      return <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">已失效</span>;
    }
    if (cert.days_remaining <= THRESHOLD_DAYS) {
      return <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">即将到期</span>;
    }
    return <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">正常</span>;
  };

  const daysColor = (cert: CertificateInfo) => {
    if (!cert.is_valid || cert.days_remaining < 0) return 'text-red-600';
    if (cert.days_remaining <= THRESHOLD_DAYS) return 'text-yellow-600';
    return 'text-gray-700';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800">SSL 证书</h1>
        <button
          onClick={loadCertificates}
          disabled={loading}
          className="text-sm text-gray-600 border border-gray-300 px-3 py-2 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          刷新
        </button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-5">
          <div className="text-sm text-gray-500">监控证书</div>
          <div className="mt-1 text-2xl font-bold text-gray-800">{data?.total ?? '-'}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <div className="text-sm text-gray-500">有效证书</div>
          <div className="mt-1 text-2xl font-bold text-green-600">{data?.valid_count ?? '-'}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <div className="text-sm text-gray-500">即将到期（≤{THRESHOLD_DAYS}天）</div>
          <div className="mt-1 text-2xl font-bold text-yellow-600">{data?.expiring_soon_count ?? '-'}</div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">{error}</div>
      )}

      <div className="bg-white rounded-lg shadow">
        {loading ? (
          <div className="text-center py-12 text-gray-500">加载中...</div>
        ) : !data || data.certificates.length === 0 ? (
          <div className="text-center py-12 text-gray-400">暂无监控的证书</div>
        ) : (
          <>
            {/* 桌面端表格 */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">域名</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">颁发机构</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">生效日期</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">到期日期</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">剩余天数</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {data.certificates.map((cert) => (
                    <tr key={cert.domain} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{cert.domain}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{cert.issuer || '-'}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(cert.valid_from)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(cert.valid_to)}</td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${daysColor(cert)}`}>{cert.days_remaining} 天</td>
                      <td className="px-6 py-4 whitespace-nowrap">{statusBadge(cert)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 移动端卡片 */}
            <div className="md:hidden divide-y divide-gray-100">
              {data.certificates.map((cert) => (
                <div key={cert.domain} className="p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium text-gray-900">{cert.domain}</h3>
                      <p className="text-sm text-gray-500 mt-1">{cert.issuer || '-'}</p>
                    </div>
                    {statusBadge(cert)}
                  </div>
                  <div className="mt-2 text-sm text-gray-500">
                    到期：{formatDate(cert.valid_to)} · 剩余 <span className={daysColor(cert)}>{cert.days_remaining} 天</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
