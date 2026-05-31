/**
 * 系统配置页面
 */
import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import UserManagement from './config/UserManagement';
import { formatDateTime } from '@/utils/datetime';

interface RegistrarInfo {
  id: number;
  code: string;
  name: string;
  description: string | null;
  api_endpoint: string | null;
  is_enabled: boolean;
}

interface DnsProviderInfo {
  id: number;
  code: string;
  name: string;
  description: string | null;
  api_endpoint: string | null;
  is_enabled: boolean;
}

interface RegAccount {
  id: number;
  name: string;
  registrar_code: string;
  owner_id: number | null;
  is_active: boolean;
  remark: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface DnsAccount {
  id: number;
  name: string;
  provider_code: string;
  owner_id: number | null;
  is_active: boolean;
  remark: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface DefaultConfig {
  default_registrar: string;
  default_dns_provider: string;
  default_reg_account_id: number | null;
  default_dns_account_id: number | null;
}

type TabKey = 'registrar' | 'dns' | 'reg-accounts' | 'dns-accounts' | 'defaults' | 'users';

const ALL_TABS: { key: TabKey; label: string }[] = [
  { key: 'registrar', label: '注册商' },
  { key: 'dns', label: 'DNS服务商' },
  { key: 'reg-accounts', label: '注册账号' },
  { key: 'dns-accounts', label: 'DNS账号' },
  { key: 'defaults', label: '默认配置' },
  { key: 'users', label: '用户管理' },
];

interface ConfigPageProps {
  /** 仅渲染指定分区的 Tab，缺省渲染全部 */
  sections?: TabKey[];
  /** 页面标题 */
  title?: string;
}

export default function ConfigPage({ sections, title = '系统配置' }: ConfigPageProps) {
  const TABS = sections
    ? ALL_TABS.filter((t) => sections.includes(t.key))
    : ALL_TABS;
  const [activeTab, setActiveTab] = useState<TabKey>(TABS[0]?.key ?? 'registrar');
  const [loading, setLoading] = useState(true);

  // ========== 注册商 & DNS 服务商 ==========
  const [registrars, setRegistrars] = useState<RegistrarInfo[]>([]);
  const [dnsProviders, setDnsProviders] = useState<DnsProviderInfo[]>([]);

  // ========== 注册账号 ==========
  const [regAccounts, setRegAccounts] = useState<RegAccount[]>([]);
  const [regAccountsLoading, setRegAccountsLoading] = useState(false);
  const [showRegModal, setShowRegModal] = useState(false);
  const [editingRegAccount, setEditingRegAccount] = useState<RegAccount | null>(null);
  const [regForm, setRegForm] = useState({ name: '', registrar_code: '', api_key: '', api_secret: '', remark: '' });

  // ========== DNS 账号 ==========
  const [dnsAccounts, setDnsAccounts] = useState<DnsAccount[]>([]);
  const [dnsAccountsLoading, setDnsAccountsLoading] = useState(false);
  const [showDnsModal, setShowDnsModal] = useState(false);
  const [editingDnsAccount, setEditingDnsAccount] = useState<DnsAccount | null>(null);
  const [dnsForm, setDnsForm] = useState({ name: '', provider_code: '', api_key: '', api_secret: '', remark: '' });

  // ========== 默认配置 ==========
  const [defaultConfig, setDefaultConfig] = useState<DefaultConfig>({
    default_registrar: '',
    default_dns_provider: '',
    default_reg_account_id: null,
    default_dns_account_id: null,
  });
  const [defaultsLoading, setDefaultsLoading] = useState(false);

  // ========== 注册商 CRUD 模态框 ==========
  const [showRegistrarModal, setShowRegistrarModal] = useState(false);
  const [editingRegistrar, setEditingRegistrar] = useState<RegistrarInfo | null>(null);
  const [registrarForm, setRegistrarForm] = useState({ name: '', code: '', description: '', api_endpoint: '', is_enabled: true });

  // ========== DNS 服务商 CRUD 模态框 ==========
  const [showDnsProviderModal, setShowDnsProviderModal] = useState(false);
  const [editingDnsProvider, setEditingDnsProvider] = useState<DnsProviderInfo | null>(null);
  const [dnsProviderForm, setDnsProviderForm] = useState({ name: '', code: '', description: '', api_endpoint: '', is_enabled: true });

  useEffect(() => {
    fetchConfigInfo();
  }, []);

  useEffect(() => {
    if (activeTab === 'reg-accounts') loadRegAccounts();
    if (activeTab === 'dns-accounts') loadDnsAccounts();
    if (activeTab === 'defaults') loadDefaults();
  }, [activeTab]);

  const fetchConfigInfo = async () => {
    try {
      setLoading(true);
      const [registrarsRes, dnsRes] = await Promise.all([
        api.get('/providers/registrars?enabled_only=false'),
        api.get('/providers/dns-providers?enabled_only=false'),
      ]);
      setRegistrars(Array.isArray(registrarsRes.data) ? registrarsRes.data : []);
      setDnsProviders(Array.isArray(dnsRes.data) ? dnsRes.data : []);
    } catch (err) {
      console.error('获取配置信息失败:', err);
    } finally {
      setLoading(false);
    }
  };

  // ==================== 注册账号 CRUD ====================

  const loadRegAccounts = async () => {
    setRegAccountsLoading(true);
    try {
      const res = await api.get('/domains/accounts/reg/list');
      setRegAccounts(res.data.items || []);
    } catch (err) {
      console.error('获取注册账号失败:', err);
    } finally {
      setRegAccountsLoading(false);
    }
  };

  const openRegModal = (account?: RegAccount) => {
    if (account) {
      setEditingRegAccount(account);
      setRegForm({
        name: account.name,
        registrar_code: account.registrar_code,
        api_key: '',
        api_secret: '',
        remark: account.remark || '',
      });
    } else {
      setEditingRegAccount(null);
      setRegForm({ name: '', registrar_code: '', api_key: '', api_secret: '', remark: '' });
    }
    setShowRegModal(true);
  };

  const closeRegModal = () => {
    setShowRegModal(false);
    setEditingRegAccount(null);
    setRegForm({ name: '', registrar_code: '', api_key: '', api_secret: '', remark: '' });
  };

  const handleRegSave = async () => {
    if (!regForm.name || !regForm.registrar_code) {
      alert('请填写账号名称和注册商');
      return;
    }
    try {
      if (editingRegAccount) {
        await api.put(`/domains/accounts/reg/${editingRegAccount.id}`, {
          name: regForm.name,
          api_key: regForm.api_key || undefined,
          api_secret: regForm.api_secret || undefined,
          remark: regForm.remark || undefined,
        });
        alert('更新成功');
      } else {
        await api.post('/domains/accounts/reg', {
          name: regForm.name,
          registrar_code: regForm.registrar_code,
          api_key: regForm.api_key || undefined,
          api_secret: regForm.api_secret || undefined,
          remark: regForm.remark || undefined,
        });
        alert('创建成功');
      }
      closeRegModal();
      loadRegAccounts();
    } catch (err: any) {
      console.error('保存注册账号失败:', err);
      alert('保存失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleRegDelete = async (account: RegAccount) => {
    if (!confirm(`确定要删除注册账号 "${account.name}" 吗？`)) return;
    try {
      await api.delete(`/domains/accounts/reg/${account.id}`);
      alert('删除成功');
      loadRegAccounts();
    } catch (err: any) {
      console.error('删除注册账号失败:', err);
      alert('删除失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  // ==================== DNS 账号 CRUD ====================

  const loadDnsAccounts = async () => {
    setDnsAccountsLoading(true);
    try {
      const res = await api.get('/domains/accounts/dns/list');
      setDnsAccounts(res.data.items || []);
    } catch (err) {
      console.error('获取DNS账号失败:', err);
    } finally {
      setDnsAccountsLoading(false);
    }
  };

  const openDnsModal = (account?: DnsAccount) => {
    if (account) {
      setEditingDnsAccount(account);
      setDnsForm({
        name: account.name,
        provider_code: account.provider_code,
        api_key: '',
        api_secret: '',
        remark: account.remark || '',
      });
    } else {
      setEditingDnsAccount(null);
      setDnsForm({ name: '', provider_code: '', api_key: '', api_secret: '', remark: '' });
    }
    setShowDnsModal(true);
  };

  const closeDnsModal = () => {
    setShowDnsModal(false);
    setEditingDnsAccount(null);
    setDnsForm({ name: '', provider_code: '', api_key: '', api_secret: '', remark: '' });
  };

  const handleDnsSave = async () => {
    if (!dnsForm.name || !dnsForm.provider_code) {
      alert('请填写账号名称和DNS服务商');
      return;
    }
    try {
      if (editingDnsAccount) {
        await api.put(`/domains/accounts/dns/${editingDnsAccount.id}`, {
          name: dnsForm.name,
          api_key: dnsForm.api_key || undefined,
          api_secret: dnsForm.api_secret || undefined,
          remark: dnsForm.remark || undefined,
        });
        alert('更新成功');
      } else {
        await api.post('/domains/accounts/dns', {
          name: dnsForm.name,
          provider_code: dnsForm.provider_code,
          api_key: dnsForm.api_key || undefined,
          api_secret: dnsForm.api_secret || undefined,
          remark: dnsForm.remark || undefined,
        });
        alert('创建成功');
      }
      closeDnsModal();
      loadDnsAccounts();
    } catch (err: any) {
      console.error('保存DNS账号失败:', err);
      alert('保存失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDnsDelete = async (account: DnsAccount) => {
    if (!confirm(`确定要删除DNS账号 "${account.name}" 吗？`)) return;
    try {
      await api.delete(`/domains/accounts/dns/${account.id}`);
      alert('删除成功');
      loadDnsAccounts();
    } catch (err: any) {
      console.error('删除DNS账号失败:', err);
      alert('删除失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  // ==================== 默认配置 ====================

  const loadDefaults = async () => {
    setDefaultsLoading(true);
    try {
      const res = await api.get('/config/defaults');
      setDefaultConfig(res.data);
    } catch (err) {
      console.error('获取默认配置失败:', err);
    } finally {
      setDefaultsLoading(false);
    }
  };

  const handleSaveDefaults = async () => {
    try {
      await api.put('/config/defaults', defaultConfig);
      alert('保存成功');
    } catch (err: any) {
      console.error('保存默认配置失败:', err);
      alert('保存失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  // ==================== 注册商 CRUD ====================

  const openRegistrarModal = (reg?: RegistrarInfo) => {
    if (reg) {
      setEditingRegistrar(reg);
      setRegistrarForm({ name: reg.name, code: reg.code, description: reg.description || '', api_endpoint: reg.api_endpoint || '', is_enabled: reg.is_enabled });
    } else {
      setEditingRegistrar(null);
      setRegistrarForm({ name: '', code: '', description: '', api_endpoint: '', is_enabled: true });
    }
    setShowRegistrarModal(true);
  };

  const closeRegistrarModal = () => { setShowRegistrarModal(false); setEditingRegistrar(null); };

  const handleRegistrarSave = async () => {
    if (!registrarForm.name || (!editingRegistrar && !registrarForm.code)) {
      alert('请填写名称' + (editingRegistrar ? '' : '和唯一代码'));
      return;
    }
    try {
      let res;
      if (editingRegistrar) {
        res = await api.put(`/providers/registrars/${editingRegistrar.id}`, {
          name: registrarForm.name,
          description: registrarForm.description || undefined,
          api_endpoint: registrarForm.api_endpoint || undefined,
          is_enabled: registrarForm.is_enabled,
        });
      } else {
        res = await api.post('/providers/registrars', {
          name: registrarForm.name,
          code: registrarForm.code.toLowerCase(),
          description: registrarForm.description || undefined,
          api_endpoint: registrarForm.api_endpoint || undefined,
          is_enabled: registrarForm.is_enabled,
        });
      }
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
      closeRegistrarModal();
      fetchConfigInfo();
    } catch (err: any) {
      alert('操作失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleRegistrarDelete = async (reg: RegistrarInfo) => {
    if (!confirm(`确定要删除注册商「${reg.name}」吗？此操作需超管飞书确认。`)) return;
    try {
      const res = await api.delete(`/providers/registrars/${reg.id}`);
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
      fetchConfigInfo();
    } catch (err: any) {
      alert('操作失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  // ==================== DNS 服务商 CRUD ====================

  const openDnsProviderModal = (prov?: DnsProviderInfo) => {
    if (prov) {
      setEditingDnsProvider(prov);
      setDnsProviderForm({ name: prov.name, code: prov.code, description: prov.description || '', api_endpoint: prov.api_endpoint || '', is_enabled: prov.is_enabled });
    } else {
      setEditingDnsProvider(null);
      setDnsProviderForm({ name: '', code: '', description: '', api_endpoint: '', is_enabled: true });
    }
    setShowDnsProviderModal(true);
  };

  const closeDnsProviderModal = () => { setShowDnsProviderModal(false); setEditingDnsProvider(null); };

  const handleDnsProviderSave = async () => {
    if (!dnsProviderForm.name || (!editingDnsProvider && !dnsProviderForm.code)) {
      alert('请填写名称' + (editingDnsProvider ? '' : '和唯一代码'));
      return;
    }
    try {
      let res;
      if (editingDnsProvider) {
        res = await api.put(`/providers/dns-providers/${editingDnsProvider.id}`, {
          name: dnsProviderForm.name,
          description: dnsProviderForm.description || undefined,
          api_endpoint: dnsProviderForm.api_endpoint || undefined,
          is_enabled: dnsProviderForm.is_enabled,
        });
      } else {
        res = await api.post('/providers/dns-providers', {
          name: dnsProviderForm.name,
          code: dnsProviderForm.code.toLowerCase(),
          description: dnsProviderForm.description || undefined,
          api_endpoint: dnsProviderForm.api_endpoint || undefined,
          is_enabled: dnsProviderForm.is_enabled,
        });
      }
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
      closeDnsProviderModal();
      fetchConfigInfo();
    } catch (err: any) {
      alert('操作失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDnsProviderDelete = async (prov: DnsProviderInfo) => {
    if (!confirm(`确定要删除 DNS 服务商「${prov.name}」吗？此操作需超管飞书确认。`)) return;
    try {
      const res = await api.delete(`/providers/dns-providers/${prov.id}`);
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
      fetchConfigInfo();
    } catch (err: any) {
      alert('操作失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  // ==================== 渲染工具 ====================

  const findRegistrarName = (code: string) => {
    const reg = registrars.find((r) => r.code === code);
    return reg ? reg.name : code;
  };

  const findDnsProviderName = (code: string) => {
    const p = dnsProviders.find((d) => d.code === code);
    return p ? p.name : code;
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
      <h1 className="text-2xl font-bold text-gray-800">{title}</h1>

      <div className="bg-white rounded-lg shadow">
        {/* Tab 导航（仅在有多个分区时显示） */}
        {TABS.length > 1 && (
        <div className="border-b border-gray-200">
          <nav className="flex overflow-x-auto px-6 scrollbar-none">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`py-4 px-3 border-b-2 font-medium text-sm whitespace-nowrap flex-shrink-0 ${
                  activeTab === tab.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
        )}

        <div className="p-6">
          {/* ==================== 注册商配置 ==================== */}
          {activeTab === 'registrar' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-semibold">注册商管理</h2>
                <button
                  onClick={() => openRegistrarModal()}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                >
                  新增注册商
                </button>
              </div>
              <p className="text-sm text-gray-500">新增/修改/删除操作需超级管理员飞书确认后生效。</p>
              {registrars.length === 0 ? (
                <div className="text-center py-12 text-gray-400">暂无注册商，请新增</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {registrars.map((reg) => (
                    <div key={reg.code} className="border border-gray-200 rounded-lg p-4 hover:border-blue-300">
                      <div className="flex justify-between items-start">
                        <div className="flex-1 min-w-0 pr-2">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium text-gray-800">{reg.name}</h3>
                            <span className={`inline-flex px-1.5 py-0.5 text-xs rounded-full ${reg.is_enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                              {reg.is_enabled ? '启用' : '禁用'}
                            </span>
                          </div>
                          {reg.description && <p className="text-sm text-gray-500 mt-1">{reg.description}</p>}
                          <div className="mt-1 text-xs text-gray-400">code: {reg.code}</div>
                        </div>
                        <div className="flex gap-2 flex-shrink-0">
                          <button onClick={() => openRegistrarModal(reg)} className="text-blue-600 hover:text-blue-800 text-sm">编辑</button>
                          <button onClick={() => handleRegistrarDelete(reg)} className="text-red-600 hover:text-red-800 text-sm">删除</button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* 注册商弹窗 */}
              {showRegistrarModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg w-full max-w-lg">
                    <div className="flex justify-between items-center p-6 border-b border-gray-200">
                      <h3 className="text-lg font-medium text-gray-900">{editingRegistrar ? '编辑注册商' : '新增注册商'}</h3>
                      <button onClick={closeRegistrarModal} className="text-gray-400 hover:text-gray-600">关闭</button>
                    </div>
                    <div className="p-6 space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">名称 <span className="text-red-500">*</span></label>
                        <input type="text" value={registrarForm.name} onChange={(e) => setRegistrarForm({ ...registrarForm, name: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2" placeholder="如：Cloudflare" />
                      </div>
                      {!editingRegistrar && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">唯一代码 <span className="text-red-500">*</span></label>
                          <input type="text" value={registrarForm.code} onChange={(e) => setRegistrarForm({ ...registrarForm, code: e.target.value })}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2" placeholder="如：cloudflare（创建后不可修改）" />
                        </div>
                      )}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                        <input type="text" value={registrarForm.description} onChange={(e) => setRegistrarForm({ ...registrarForm, description: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2" placeholder="可选说明" />
                      </div>
                      <div className="flex items-center gap-3">
                        <input type="checkbox" id="reg-enabled" checked={registrarForm.is_enabled}
                          onChange={(e) => setRegistrarForm({ ...registrarForm, is_enabled: e.target.checked })} className="w-4 h-4" />
                        <label htmlFor="reg-enabled" className="text-sm text-gray-700">启用</label>
                      </div>
                      <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-700">
                        提交后将发送飞书确认给超级管理员，审批通过后生效。
                      </div>
                    </div>
                    <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
                      <button onClick={closeRegistrarModal} className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg">取消</button>
                      <button onClick={handleRegistrarSave} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">提交申请</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ==================== DNS配置 ==================== */}
          {activeTab === 'dns' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-semibold">DNS 服务商管理</h2>
                <button
                  onClick={() => openDnsProviderModal()}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                >
                  新增 DNS 服务商
                </button>
              </div>
              <p className="text-sm text-gray-500">新增/修改/删除操作需超级管理员飞书确认后生效。</p>
              {dnsProviders.length === 0 ? (
                <div className="text-center py-12 text-gray-400">暂无 DNS 服务商，请新增</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {dnsProviders.map((prov) => (
                    <div key={prov.code} className="border border-gray-200 rounded-lg p-4 hover:border-blue-300">
                      <div className="flex justify-between items-start">
                        <div className="flex-1 min-w-0 pr-2">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium text-gray-800">{prov.name}</h3>
                            <span className={`inline-flex px-1.5 py-0.5 text-xs rounded-full ${prov.is_enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                              {prov.is_enabled ? '启用' : '禁用'}
                            </span>
                          </div>
                          {prov.description && <p className="text-sm text-gray-500 mt-1">{prov.description}</p>}
                          <div className="mt-1 text-xs text-gray-400">code: {prov.code}</div>
                        </div>
                        <div className="flex gap-2 flex-shrink-0">
                          <button onClick={() => openDnsProviderModal(prov)} className="text-blue-600 hover:text-blue-800 text-sm">编辑</button>
                          <button onClick={() => handleDnsProviderDelete(prov)} className="text-red-600 hover:text-red-800 text-sm">删除</button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* DNS 服务商弹窗 */}
              {showDnsProviderModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg w-full max-w-lg">
                    <div className="flex justify-between items-center p-6 border-b border-gray-200">
                      <h3 className="text-lg font-medium text-gray-900">{editingDnsProvider ? '编辑 DNS 服务商' : '新增 DNS 服务商'}</h3>
                      <button onClick={closeDnsProviderModal} className="text-gray-400 hover:text-gray-600">关闭</button>
                    </div>
                    <div className="p-6 space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">名称 <span className="text-red-500">*</span></label>
                        <input type="text" value={dnsProviderForm.name} onChange={(e) => setDnsProviderForm({ ...dnsProviderForm, name: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2" placeholder="如：Cloudflare DNS" />
                      </div>
                      {!editingDnsProvider && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">唯一代码 <span className="text-red-500">*</span></label>
                          <input type="text" value={dnsProviderForm.code} onChange={(e) => setDnsProviderForm({ ...dnsProviderForm, code: e.target.value })}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2" placeholder="如：cloudflare（创建后不可修改）" />
                        </div>
                      )}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                        <input type="text" value={dnsProviderForm.description} onChange={(e) => setDnsProviderForm({ ...dnsProviderForm, description: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2" placeholder="可选说明" />
                      </div>
                      <div className="flex items-center gap-3">
                        <input type="checkbox" id="dns-enabled" checked={dnsProviderForm.is_enabled}
                          onChange={(e) => setDnsProviderForm({ ...dnsProviderForm, is_enabled: e.target.checked })} className="w-4 h-4" />
                        <label htmlFor="dns-enabled" className="text-sm text-gray-700">启用</label>
                      </div>
                      <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-700">
                        提交后将发送飞书确认给超级管理员，审批通过后生效。
                      </div>
                    </div>
                    <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
                      <button onClick={closeDnsProviderModal} className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg">取消</button>
                      <button onClick={handleDnsProviderSave} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">提交申请</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ==================== 注册账号管理 ==================== */}
          {activeTab === 'reg-accounts' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-semibold">注册账号管理</h2>
                <button
                  onClick={() => openRegModal()}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                >
                  新增账号
                </button>
              </div>

              {regAccountsLoading ? (
                <div className="text-center py-12 text-gray-500">加载中...</div>
              ) : regAccounts.length === 0 ? (
                <div className="text-center py-12 text-gray-400">暂无注册账号</div>
              ) : (
                <>
                  {/* 桌面端表格 */}
                  <div className="hidden md:block overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">账号名称</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">注册商</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">备注</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">创建时间</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {regAccounts.map((account) => (
                          <tr key={account.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{account.name}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{findRegistrarName(account.registrar_code)}</td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${account.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                {account.is_active ? '启用' : '禁用'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{account.remark || '-'}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDateTime(account.created_at)}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <button onClick={() => openRegModal(account)} className="text-blue-600 hover:text-blue-900 mr-3">编辑</button>
                              <button onClick={() => handleRegDelete(account)} className="text-red-600 hover:text-red-900">删除</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* 移动端卡片 */}
                  <div className="md:hidden space-y-3">
                    {regAccounts.map((account) => (
                      <div key={account.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <h3 className="font-medium text-gray-900">{account.name}</h3>
                            <p className="text-sm text-gray-500 mt-1">{findRegistrarName(account.registrar_code)}</p>
                          </div>
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${account.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {account.is_active ? '启用' : '禁用'}
                          </span>
                        </div>
                        {account.remark && <p className="text-sm text-gray-400 mt-2">{account.remark}</p>}
                        <div className="flex justify-end space-x-3 mt-3 pt-3 border-t border-gray-100">
                          <button onClick={() => openRegModal(account)} className="text-blue-600 text-sm">编辑</button>
                          <button onClick={() => handleRegDelete(account)} className="text-red-600 text-sm">删除</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* 注册账号弹窗 */}
              {showRegModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto">
                    <div className="flex justify-between items-center p-6 border-b border-gray-200">
                      <h3 className="text-lg font-medium text-gray-900">
                        {editingRegAccount ? '编辑注册账号' : '新增注册账号'}
                      </h3>
                      <button onClick={closeRegModal} className="text-gray-400 hover:text-gray-600">关闭</button>
                    </div>
                    <div className="p-6 space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">账号名称 <span className="text-red-500">*</span></label>
                        <input
                          type="text"
                          value={regForm.name}
                          onChange={(e) => setRegForm({ ...regForm, name: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder="请输入账号名称"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">注册商 <span className="text-red-500">*</span></label>
                        <select
                          value={regForm.registrar_code}
                          onChange={(e) => setRegForm({ ...regForm, registrar_code: e.target.value })}
                          disabled={!!editingRegAccount}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 disabled:bg-gray-100"
                        >
                          <option value="">请选择注册商</option>
                          {registrars.map((r) => (
                            <option key={r.code} value={r.code}>{r.name}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                        <input
                          type="password"
                          value={regForm.api_key}
                          onChange={(e) => setRegForm({ ...regForm, api_key: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder={editingRegAccount ? '留空表示不修改' : '请输入API Key'}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Secret</label>
                        <input
                          type="password"
                          value={regForm.api_secret}
                          onChange={(e) => setRegForm({ ...regForm, api_secret: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder={editingRegAccount ? '留空表示不修改' : '请输入API Secret'}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">备注</label>
                        <textarea
                          value={regForm.remark}
                          onChange={(e) => setRegForm({ ...regForm, remark: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          rows={2}
                          placeholder="请输入备注"
                        />
                      </div>
                    </div>
                    <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
                      <button onClick={closeRegModal} className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg">取消</button>
                      <button onClick={handleRegSave} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">保存</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ==================== DNS账号管理 ==================== */}
          {activeTab === 'dns-accounts' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-semibold">DNS账号管理</h2>
                <button
                  onClick={() => openDnsModal()}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                >
                  新增账号
                </button>
              </div>

              {dnsAccountsLoading ? (
                <div className="text-center py-12 text-gray-500">加载中...</div>
              ) : dnsAccounts.length === 0 ? (
                <div className="text-center py-12 text-gray-400">暂无DNS账号</div>
              ) : (
                <>
                  {/* 桌面端表格 */}
                  <div className="hidden md:block overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">账号名称</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">DNS服务商</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">备注</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">创建时间</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {dnsAccounts.map((account) => (
                          <tr key={account.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{account.name}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{findDnsProviderName(account.provider_code)}</td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${account.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                {account.is_active ? '启用' : '禁用'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{account.remark || '-'}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDateTime(account.created_at)}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <button onClick={() => openDnsModal(account)} className="text-blue-600 hover:text-blue-900 mr-3">编辑</button>
                              <button onClick={() => handleDnsDelete(account)} className="text-red-600 hover:text-red-900">删除</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* 移动端卡片 */}
                  <div className="md:hidden space-y-3">
                    {dnsAccounts.map((account) => (
                      <div key={account.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <h3 className="font-medium text-gray-900">{account.name}</h3>
                            <p className="text-sm text-gray-500 mt-1">{findDnsProviderName(account.provider_code)}</p>
                          </div>
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${account.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {account.is_active ? '启用' : '禁用'}
                          </span>
                        </div>
                        {account.remark && <p className="text-sm text-gray-400 mt-2">{account.remark}</p>}
                        <div className="flex justify-end space-x-3 mt-3 pt-3 border-t border-gray-100">
                          <button onClick={() => openDnsModal(account)} className="text-blue-600 text-sm">编辑</button>
                          <button onClick={() => handleDnsDelete(account)} className="text-red-600 text-sm">删除</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* DNS账号弹窗 */}
              {showDnsModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto">
                    <div className="flex justify-between items-center p-6 border-b border-gray-200">
                      <h3 className="text-lg font-medium text-gray-900">
                        {editingDnsAccount ? '编辑DNS账号' : '新增DNS账号'}
                      </h3>
                      <button onClick={closeDnsModal} className="text-gray-400 hover:text-gray-600">关闭</button>
                    </div>
                    <div className="p-6 space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">账号名称 <span className="text-red-500">*</span></label>
                        <input
                          type="text"
                          value={dnsForm.name}
                          onChange={(e) => setDnsForm({ ...dnsForm, name: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder="请输入账号名称"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">DNS服务商 <span className="text-red-500">*</span></label>
                        <select
                          value={dnsForm.provider_code}
                          onChange={(e) => setDnsForm({ ...dnsForm, provider_code: e.target.value })}
                          disabled={!!editingDnsAccount}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 disabled:bg-gray-100"
                        >
                          <option value="">请选择DNS服务商</option>
                          {dnsProviders.map((p) => (
                            <option key={p.code} value={p.code}>{p.name}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                        <input
                          type="password"
                          value={dnsForm.api_key}
                          onChange={(e) => setDnsForm({ ...dnsForm, api_key: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder={editingDnsAccount ? '留空表示不修改' : '请输入API Key'}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Secret</label>
                        <input
                          type="password"
                          value={dnsForm.api_secret}
                          onChange={(e) => setDnsForm({ ...dnsForm, api_secret: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder={editingDnsAccount ? '留空表示不修改' : '请输入API Secret'}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">备注</label>
                        <textarea
                          value={dnsForm.remark}
                          onChange={(e) => setDnsForm({ ...dnsForm, remark: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          rows={2}
                          placeholder="请输入备注"
                        />
                      </div>
                    </div>
                    <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
                      <button onClick={closeDnsModal} className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg">取消</button>
                      <button onClick={handleDnsSave} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">保存</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ==================== 默认配置 ==================== */}
          {activeTab === 'defaults' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold">默认配置</h2>
              {defaultsLoading ? (
                <div className="text-center py-12 text-gray-500">加载中...</div>
              ) : (
                <div className="max-w-xl space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">默认注册商</label>
                    <select
                      value={defaultConfig.default_registrar}
                      onChange={(e) => setDefaultConfig({ ...defaultConfig, default_registrar: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    >
                      <option value="">请选择</option>
                      {registrars.map((r) => (
                        <option key={r.code} value={r.code}>{r.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">默认DNS服务商</label>
                    <select
                      value={defaultConfig.default_dns_provider}
                      onChange={(e) => setDefaultConfig({ ...defaultConfig, default_dns_provider: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    >
                      <option value="">请选择</option>
                      {dnsProviders.map((p) => (
                        <option key={p.code} value={p.code}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">默认注册账号ID</label>
                    <input
                      type="number"
                      value={defaultConfig.default_reg_account_id ?? ''}
                      onChange={(e) => setDefaultConfig({ ...defaultConfig, default_reg_account_id: e.target.value ? Number(e.target.value) : null })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                      placeholder="请输入注册账号ID（可选）"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">默认DNS账号ID</label>
                    <input
                      type="number"
                      value={defaultConfig.default_dns_account_id ?? ''}
                      onChange={(e) => setDefaultConfig({ ...defaultConfig, default_dns_account_id: e.target.value ? Number(e.target.value) : null })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                      placeholder="请输入DNS账号ID（可选）"
                    />
                  </div>
                  <div className="pt-4">
                    <button
                      onClick={handleSaveDefaults}
                      className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      保存配置
                    </button>
                  </div>
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-700">
                    提示：如果后端尚未提供 <code className="bg-yellow-100 px-1 rounded">/config/defaults</code> 接口，此功能将无法使用。请联系后端开发人员。
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ==================== 用户管理 ==================== */}
          {activeTab === 'users' && <UserManagement />}
        </div>
      </div>
    </div>
  );
}
