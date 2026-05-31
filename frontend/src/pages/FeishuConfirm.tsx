/**
 * 飞书文档按钮确认页
 * 路由：/feishu/confirm?section=vercel
 *
 * 流程：
 * 1. 飞书 OAuth 登录（复用现有 auth）
 * 2. 加载 Bitable 记录（若已绑定）
 * 3. 若未绑定，引导用户粘贴 Bitable URL
 * 4. 用户填写域名 → 确认提交
 */
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

const API = '/api/v1';

interface Record {
  hostname: string;
  type: string;
  target: string;
}

interface ConfirmData {
  section: string;
  label: string;
  needs_binding: boolean;
  records: Record[];
}

export default function FeishuConfirmPage() {
  const [params] = useSearchParams();
  const section = params.get('section') || '';
  const token = localStorage.getItem('access_token');

  const [data, setData] = useState<ConfirmData | null>(null);
  const [domain, setDomain] = useState('');
  const [bitableUrl, setBitableUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [bindLoading, setBindLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // 未登录则跳登录页，登录后回到此页
  useEffect(() => {
    if (!token) {
      window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`;
    }
  }, [token]);

  // 加载 confirm-data
  useEffect(() => {
    if (!token || !section) return;
    setLoading(true);
    fetch(`${API}/feishu/confirm-data?section=${section}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => {
        if (d.detail) throw new Error(d.detail);
        setData(d);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, section]);

  // 绑定 Bitable
  const handleBind = async () => {
    setError('');
    setBindLoading(true);
    try {
      const r = await fetch(`${API}/feishu/bind-bitable`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ section, bitable_url: bitableUrl }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || '绑定失败');
      // 绑定成功，重新加载数据
      setData(null);
      setBitableUrl('');
      setLoading(true);
      const r2 = await fetch(`${API}/feishu/confirm-data?section=${section}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d2 = await r2.json();
      setData(d2);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBindLoading(false);
      setLoading(false);
    }
  };

  // 提交申请
  const handleSubmit = async () => {
    if (!domain.trim()) { setError('请填写域名'); return; }
    setError('');
    setLoading(true);
    try {
      const r = await fetch(`${API}/feishu/submit-request`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section,
          domain: domain.trim(),
          records: data?.records || [],
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || '提交失败');
      setSuccess(`申请已提交（ID: ${d.request_id}），请等待专员审批，结果将通过飞书通知您。`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) return <Layout><p className="text-gray-500">正在跳转登录...</p></Layout>;
  if (loading) return <Layout><p className="text-gray-500">加载中...</p></Layout>;
  if (success) return (
    <Layout>
      <div className="rounded-lg bg-green-50 border border-green-200 p-6 text-green-800 text-center space-y-3">
        <div className="text-2xl">✅</div>
        <p className="font-medium">{success}</p>
        <button onClick={() => window.close()} className="text-sm text-green-600 underline">关闭此页面</button>
      </div>
    </Layout>
  );

  return (
    <Layout>
      <h1 className="text-xl font-bold text-gray-800 mb-6">
        {data?.label || section}
      </h1>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 border border-red-200 p-3 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* 域名输入 */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-1">域名</label>
        <input
          type="text"
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="例：newdomain.com"
          value={domain}
          onChange={e => setDomain(e.target.value)}
        />
      </div>

      {/* Bitable 未绑定：引导绑定 */}
      {data?.needs_binding && (
        <div className="mb-6 rounded-lg bg-amber-50 border border-amber-200 p-4 space-y-3">
          <p className="text-sm text-amber-800 font-medium">首次使用，请绑定多维表格</p>
          <p className="text-xs text-amber-700">
            在飞书文档中，将对应的多维表格在新页面打开，复制地址栏完整 URL 粘贴到下方：
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              className="flex-1 border border-amber-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              placeholder="https://xxx.feishu.cn/base/bascXXX?table=tblXXX&..."
              value={bitableUrl}
              onChange={e => setBitableUrl(e.target.value)}
            />
            <button
              onClick={handleBind}
              disabled={!bitableUrl || bindLoading}
              className="px-4 py-2 bg-amber-500 text-white rounded-md text-sm font-medium hover:bg-amber-600 disabled:opacity-50"
            >
              {bindLoading ? '验证中...' : '绑定'}
            </button>
          </div>
        </div>
      )}

      {/* 待配置记录（DNS 类） */}
      {data && !data.needs_binding && data.records.length > 0 && (
        <div className="mb-6">
          <p className="text-sm font-medium text-gray-700 mb-2">
            待配置记录（共 {data.records.length} 条，读自多维表格）
          </p>
          <div className="rounded-md border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Hostname</th>
                  <th className="px-4 py-2 text-left">Type</th>
                  <th className="px-4 py-2 text-left">Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.records.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono">{r.hostname}</td>
                    <td className="px-4 py-2">
                      <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-700 text-xs font-medium">{r.type}</span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-600 truncate max-w-xs">{r.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 域名注册：无记录，仅提示 */}
      {data && !data.needs_binding && data.records.length === 0 && section === 'domain_register' && (
        <div className="mb-6 text-sm text-gray-600 bg-gray-50 rounded-md p-4">
          点击确认后，系统将为 <strong>{domain || '（请填写域名）'}</strong> 提交域名注册申请。
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex gap-3">
        <button
          onClick={handleSubmit}
          disabled={loading || !domain.trim() || data?.needs_binding}
          className="flex-1 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? '提交中...' : '确认提交'}
        </button>
        <button
          onClick={() => window.close()}
          className="px-6 py-2 border border-gray-300 text-gray-600 rounded-md hover:bg-gray-50"
        >
          取消
        </button>
      </div>
    </Layout>
  );
}

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-start justify-center pt-16 px-4">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="text-xs text-gray-400 mb-4">域名管家</div>
        {children}
      </div>
    </div>
  );
}
