/**
 * 系统配置页面
 *
 * sections 控制显示哪些 Tab：
 *   accounts  页 → ['reg-accounts', 'dns-accounts']
 *   providers 页 → ['registrar', 'dns', 'defaults']
 *
 * 账号归属规则（与后端一致）：
 *   - domain_spec：只能看/改自己的账号（owner_id = self）
 *   - super_admin：可见全部账号（含归属专员列）；新建时可指定归属专员
 */
import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import UserManagement from './config/UserManagement';
import { formatDateTime } from '@/utils/datetime';

// ==================== 当前登录用户（localStorage） ====================
function getCurrentUser(): { id: number; role: string; name: string } {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}');
  } catch {
    return { id: 0, role: '', name: '' };
  }
}

// ==================== 类型定义 ====================

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
  owner_name: string | null;   // 归属专员姓名（后端填充）
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
  owner_name: string | null;   // 归属专员姓名（后端填充）
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

/** 超管"所有专员默认配置"列表中的单行 */
interface UserDefaultsItem {
  user_id: number;
  user_name: string;
  user_role: string;
  default_registrar: string | null;
  default_dns_provider: string | null;
  default_reg_account_id: number | null;
  default_dns_account_id: number | null;
}

/** 用于"归属专员"下拉的精简用户信息 */
interface SpecialistOption {
  id: number;
  name: string;
  role: string;
}

type TabKey = 'registrar' | 'dns' | 'reg-accounts' | 'dns-accounts' | 'defaults' | 'users';

const ALL_TABS: { key: TabKey; label: string }[] = [
  { key: 'registrar',    label: '注册商' },
  { key: 'dns',          label: 'DNS服务商' },
  { key: 'reg-accounts', label: '注册账号' },
  { key: 'dns-accounts', label: 'DNS账号' },
  { key: 'defaults',     label: '默认配置' },
  { key: 'users',        label: '用户管理' },
];

interface ConfigPageProps {
  sections?: TabKey[];
  title?: string;
}

// ==================== 主组件 ====================

export default function ConfigPage({ sections, title = '系统配置' }: ConfigPageProps) {
  const TABS = sections ? ALL_TABS.filter((t) => sections.includes(t.key)) : ALL_TABS;
  const [activeTab, setActiveTab] = useState<TabKey>(TABS[0]?.key ?? 'registrar');
  const [loading, setLoading] = useState(true);

  const currentUser = getCurrentUser();
  const isSuperAdmin = currentUser.role === 'super_admin';

  // ========== 注册商 & DNS 服务商 ==========
  const [registrars, setRegistrars] = useState<RegistrarInfo[]>([]);
  const [dnsProviders, setDnsProviders] = useState<DnsProviderInfo[]>([]);

  // ========== 注册账号 ==========
  const [regAccounts, setRegAccounts] = useState<RegAccount[]>([]);
  const [regAccountsLoading, setRegAccountsLoading] = useState(false);
  const [showRegModal, setShowRegModal] = useState(false);
  const [editingRegAccount, setEditingRegAccount] = useState<RegAccount | null>(null);
  const [regForm, setRegForm] = useState({
    name: '', registrar_code: '', api_key: '', api_secret: '', remark: '',
    target_owner_id: '' as string | number,  // super_admin 新建时指定归属
  });

  // ========== DNS 账号 ==========
  const [dnsAccounts, setDnsAccounts] = useState<DnsAccount[]>([]);
  const [dnsAccountsLoading, setDnsAccountsLoading] = useState(false);
  const [showDnsModal, setShowDnsModal] = useState(false);
  const [editingDnsAccount, setEditingDnsAccount] = useState<DnsAccount | null>(null);
  const [dnsForm, setDnsForm] = useState({
    name: '', provider_code: '', api_key: '', api_secret: '', remark: '',
    target_owner_id: '' as string | number,
  });

  // ========== 归属专员候选列表（super_admin 新建时用） ==========
  const [specialists, setSpecialists] = useState<SpecialistOption[]>([]);

  // ========== 默认配置 ==========
  // domain_spec：只看/改自己的默认配置
  const [defaultConfig, setDefaultConfig] = useState<DefaultConfig>({
    default_registrar: '',
    default_dns_provider: '',
    default_reg_account_id: null,
    default_dns_account_id: null,
  });
  // super_admin：所有专员的默认配置列表
  const [allDefaults, setAllDefaults] = useState<UserDefaultsItem[]>([]);
  const [defaultsLoading, setDefaultsLoading] = useState(false);
  // super_admin 编辑某专员的默认配置弹窗
  const [editingDefaultsFor, setEditingDefaultsFor] = useState<UserDefaultsItem | null>(null);
  const [defaultsEditForm, setDefaultsEditForm] = useState<DefaultConfig>({
    default_registrar: '',
    default_dns_provider: '',
    default_reg_account_id: null,
    default_dns_account_id: null,
  });

  // ========== 注册商 CRUD 模态框 ==========
  const [showRegistrarModal, setShowRegistrarModal] = useState(false);
  const [editingRegistrar, setEditingRegistrar] = useState<RegistrarInfo | null>(null);
  const [registrarForm, setRegistrarForm] = useState({
    name: '', code: '', description: '', api_endpoint: '', is_enabled: true,
  });

  // ========== DNS 服务商 CRUD 模态框 ==========
  const [showDnsProviderModal, setShowDnsProviderModal] = useState(false);
  const [editingDnsProvider, setEditingDnsProvider] = useState<DnsProviderInfo | null>(null);
  const [dnsProviderForm, setDnsProviderForm] = useState({
    name: '', code: '', description: '', api_endpoint: '', is_enabled: true,
  });

  // ==================== 初始化 ====================

  useEffect(() => { fetchConfigInfo(); }, []);

  useEffect(() => {
    if (activeTab === 'reg-accounts') loadRegAccounts();
    if (activeTab === 'dns-accounts') loadDnsAccounts();
    if (activeTab === 'defaults') {
      loadDefaults();
      loadRegAccounts();
      loadDnsAccounts();
    }
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

  /** 加载 domain_spec + super_admin 用户列表，供"归属专员"下拉使用 */
  const loadSpecialists = async () => {
    if (!isSuperAdmin || specialists.length > 0) return;
    try {
      const [specRes, superRes] = await Promise.all([
        api.get('/users?role=domain_spec&limit=200'),
        api.get('/users?role=super_admin&limit=20'),
      ]);
      const items = [
        ...(specRes.data?.items || []),
        ...(superRes.data?.items || []),
      ];
      setSpecialists(items.map((u: any) => ({ id: u.id, name: u.name, role: u.role })));
    } catch (err) {
      console.error('获取专员列表失败:', err);
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

  const openRegModal = async (account?: RegAccount) => {
    if (isSuperAdmin) await loadSpecialists();
    if (account) {
      setEditingRegAccount(account);
      setRegForm({
        name: account.name,
        registrar_code: account.registrar_code,
        api_key: '',
        api_secret: '',
        remark: account.remark || '',
        target_owner_id: account.owner_id ?? '',
      });
    } else {
      setEditingRegAccount(null);
      setRegForm({
        name: '', registrar_code: '', api_key: '', api_secret: '', remark: '',
        target_owner_id: isSuperAdmin ? currentUser.id : '',
      });
    }
    setShowRegModal(true);
  };

  const closeRegModal = () => {
    setShowRegModal(false);
    setEditingRegAccount(null);
    setRegForm({ name: '', registrar_code: '', api_key: '', api_secret: '', remark: '', target_owner_id: '' });
  };

  const handleRegSave = async () => {
    if (!regForm.name || !regForm.registrar_code) {
      alert('请填写账号名称和注册商');
      return;
    }
    try {
      let res;
      if (editingRegAccount) {
        res = await api.put(`/domains/accounts/reg/${editingRegAccount.id}`, {
          name: regForm.name,
          api_key: regForm.api_key || undefined,
          api_secret: regForm.api_secret || undefined,
          remark: regForm.remark || undefined,
        });
      } else {
        const body: Record<string, any> = {
          name: regForm.name,
          registrar_code: regForm.registrar_code,
          api_key: regForm.api_key || undefined,
          api_secret: regForm.api_secret || undefined,
          remark: regForm.remark || undefined,
        };
        if (isSuperAdmin && regForm.target_owner_id) {
          body.target_owner_id = Number(regForm.target_owner_id);
        }
        res = await api.post('/domains/accounts/reg', body);
      }
      // 后端始终返回 pending_approval
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
      closeRegModal();
      loadRegAccounts();
    } catch (err: any) {
      alert('操作失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleRegDelete = async (account: RegAccount) => {
    if (!confirm(`确定要删除注册账号「${account.name}」吗？此操作需超管飞书确认。`)) return;
    try {
      const res = await api.delete(`/domains/accounts/reg/${account.id}`);
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
      loadRegAccounts();
    } catch (err: any) {
      alert('操作失败: ' + (err.response?.data?.detail || err.message));
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

  const openDnsModal = async (account?: DnsAccount) => {
    if (isSuperAdmin) await loadSpecialists();
    if (account) {
      setEditingDnsAccount(account);
      setDnsForm({
        name: account.name,
        provider_code: account.provider_code,
        api_key: '',
        api_secret: '',
        remark: account.remark || '',
        target_owner_id: account.owner_id ?? '',
      });
    } else {
      setEditingDnsAccount(null);
      setDnsForm({
        name: '', provider_code: '', api_key: '', api_secret: '', remark: '',
        target_owner_id: isSuperAdmin ? currentUser.id : '',
      });
    }
    setShowDnsModal(true);
  };

  const closeDnsModal = () => {
    setShowDnsModal(false);
    setEditingDnsAccount(null);
    setDnsForm({ name: '', provider_code: '', api_key: '', api_secret: '', remark: '', target_owner_id: '' });
  };

  const handleDnsSave = async () => {
    if (!dnsForm.name || !dnsForm.provider_code) {
      alert('请填写账号名称和DNS服务商');
      return;
    }
    try {
      let res;
      if (editingDnsAccount) {
        res = await api.put(`/domains/accounts/dns/${editingDnsAccount.id}`, {
          name: dnsForm.name,
          api_key: dnsForm.api_key || undefined,
          api_secret: dnsForm.api_secret || undefined,
          remark: dnsForm.remark || undefined,
        });
      } else {
        const body: Record<string, any> = {
          name: dnsForm.name,
          provider_code: dnsForm.provider_code,
          api_key: dnsForm.api_key || undefined,
          api_secret: dnsForm.api_secret || undefined,
          remark: dnsForm.remark || undefined,
        };
        if (isSuperAdmin && dnsForm.target_owner_id) {
          body.target_owner_id = Number(dnsForm.target_owner_id);
        }
        res = await api.post('/domains/accounts/dns', body);
      }
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
      closeDnsModal();
      loadDnsAccounts();
    } catch (err: any) {
      alert('操作失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDnsDelete = async (account: DnsAccount) => {
    if (!confirm(`确定要删除DNS账号「${account.name}」吗？此操作需超管飞书确认。`)) return;
    try {
      const res = await api.delete(`/domains/accounts/dns/${account.id}`);
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
      loadDnsAccounts();
    } catch (err: any) {
      alert('操作失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  // ==================== 默认配置 ====================

  const loadDefaults = async () => {
    setDefaultsLoading(true);
    try {
      if (isSuperAdmin) {
        // 超管：加载所有专员的默认配置列表 + 自己的（表单用）
        const [allRes, myRes] = await Promise.all([
          api.get('/config/defaults/all'),
          api.get('/config/defaults'),
        ]);
        setAllDefaults(Array.isArray(allRes.data) ? allRes.data : []);
        setDefaultConfig({
          default_registrar: myRes.data?.default_registrar || '',
          default_dns_provider: myRes.data?.default_dns_provider || '',
          default_reg_account_id: myRes.data?.default_reg_account_id ?? null,
          default_dns_account_id: myRes.data?.default_dns_account_id ?? null,
        });
      } else {
        // domain_spec：只加载自己的
        const res = await api.get('/config/defaults');
        setDefaultConfig({
          default_registrar: res.data?.default_registrar || '',
          default_dns_provider: res.data?.default_dns_provider || '',
          default_reg_account_id: res.data?.default_reg_account_id ?? null,
          default_dns_account_id: res.data?.default_dns_account_id ?? null,
        });
      }
    } catch (err) {
      console.error('获取默认配置失败:', err);
    } finally {
      setDefaultsLoading(false);
    }
  };

  /** domain_spec / super_admin 自己的默认配置提交 */
  const handleSaveDefaults = async () => {
    try {
      const res = await api.put('/config/defaults', defaultConfig);
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
    } catch (err: any) {
      alert('保存失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  /** 超管打开"替某专员设置默认配置"弹窗 */
  const openEditDefaultsModal = (item: UserDefaultsItem) => {
    setEditingDefaultsFor(item);
    setDefaultsEditForm({
      default_registrar: item.default_registrar || '',
      default_dns_provider: item.default_dns_provider || '',
      default_reg_account_id: item.default_reg_account_id,
      default_dns_account_id: item.default_dns_account_id,
    });
  };

  const closeEditDefaultsModal = () => {
    setEditingDefaultsFor(null);
    setDefaultsEditForm({ default_registrar: '', default_dns_provider: '', default_reg_account_id: null, default_dns_account_id: null });
  };

  /** 超管替某专员保存默认配置 */
  const handleSaveUserDefaults = async () => {
    if (!editingDefaultsFor) return;
    try {
      const isSelf = editingDefaultsFor.user_id === currentUser.id;
      const res = isSelf
        ? await api.put('/config/defaults', defaultsEditForm)
        : await api.put(`/config/defaults/${editingDefaultsFor.user_id}`, defaultsEditForm);
      alert(res.data?.message || '已提交超管确认申请，审批通过后生效');
      closeEditDefaultsModal();
      loadDefaults();
    } catch (err: any) {
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

  const findRegistrarName = (code: string) => registrars.find((r) => r.code === code)?.name ?? code;
  const findDnsProviderName = (code: string) => dnsProviders.find((d) => d.code === code)?.name ?? code;

  /** 判断当前用户是否可对某账号执行写操作（编辑/删除） */
  const canEditAccount = (ownerId: number | null) =>
    isSuperAdmin || ownerId === currentUser.id;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  // ==================== "归属专员"下拉（super_admin 新建账号时用） ====================
  const OwnerSelect = ({
    value,
    onChange,
  }: {
    value: string | number;
    onChange: (v: string | number) => void;
  }) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        归属专员 <span className="text-red-500">*</span>
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border border-gray-300 rounded-lg px-3 py-2"
      >
        <option value="">请选择归属专员</option>
        {specialists.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}（{s.role === 'super_admin' ? '超管' : '域名专员'}）
            {s.id === currentUser.id ? ' ← 自己' : ''}
          </option>
        ))}
      </select>
    </div>
  );

  // ==================== 渲染 ====================

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">{title}</h1>

      <div className="bg-white rounded-lg shadow">
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
                <button onClick={() => openRegistrarModal()} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
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

          {/* ==================== DNS 服务商配置 ==================== */}
          {activeTab === 'dns' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-semibold">DNS 服务商管理</h2>
                <button onClick={() => openDnsProviderModal()} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
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
                <button onClick={() => openRegModal()} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
                  新增账号
                </button>
              </div>
              <p className="text-sm text-gray-500">
                {isSuperAdmin
                  ? '超管可查看并管理所有专员的账号，新建时需指定归属专员。'
                  : '仅显示归属于您的账号，新增/编辑/删除均需超管飞书确认。'}
              </p>

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
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">账号名称</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">注册商</th>
                          {isSuperAdmin && (
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">归属专员</th>
                          )}
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">备注</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {regAccounts.map((account) => (
                          <tr key={account.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{account.name}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{findRegistrarName(account.registrar_code)}</td>
                            {isSuperAdmin && (
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {account.owner_name ?? <span className="text-gray-400 italic">未指定</span>}
                              </td>
                            )}
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${account.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                {account.is_active ? '启用' : '禁用'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{account.remark || '-'}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDateTime(account.created_at)}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              {canEditAccount(account.owner_id) ? (
                                <>
                                  <button onClick={() => openRegModal(account)} className="text-blue-600 hover:text-blue-900 mr-3">编辑</button>
                                  <button onClick={() => handleRegDelete(account)} className="text-red-600 hover:text-red-900">删除</button>
                                </>
                              ) : (
                                <span className="text-gray-300 text-xs">无权操作</span>
                              )}
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
                            {isSuperAdmin && account.owner_name && (
                              <p className="text-xs text-gray-400 mt-1">归属：{account.owner_name}</p>
                            )}
                          </div>
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${account.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {account.is_active ? '启用' : '禁用'}
                          </span>
                        </div>
                        {account.remark && <p className="text-sm text-gray-400 mt-2">{account.remark}</p>}
                        {canEditAccount(account.owner_id) && (
                          <div className="flex justify-end space-x-3 mt-3 pt-3 border-t border-gray-100">
                            <button onClick={() => openRegModal(account)} className="text-blue-600 text-sm">编辑</button>
                            <button onClick={() => handleRegDelete(account)} className="text-red-600 text-sm">删除</button>
                          </div>
                        )}
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
                      {/* super_admin 新建时选择归属专员 */}
                      {isSuperAdmin && !editingRegAccount && (
                        <OwnerSelect
                          value={regForm.target_owner_id}
                          onChange={(v) => setRegForm({ ...regForm, target_owner_id: v })}
                        />
                      )}
                      {/* super_admin 编辑时只读展示归属专员 */}
                      {isSuperAdmin && editingRegAccount && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">归属专员</label>
                          <p className="text-sm text-gray-600 px-3 py-2 bg-gray-50 rounded-lg">
                            {editingRegAccount.owner_name ?? '未指定'}
                          </p>
                        </div>
                      )}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">账号名称 <span className="text-red-500">*</span></label>
                        <input type="text" value={regForm.name}
                          onChange={(e) => setRegForm({ ...regForm, name: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2" placeholder="请输入账号名称" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">注册商 <span className="text-red-500">*</span></label>
                        <select value={regForm.registrar_code}
                          onChange={(e) => setRegForm({ ...regForm, registrar_code: e.target.value })}
                          disabled={!!editingRegAccount}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 disabled:bg-gray-100">
                          <option value="">请选择注册商</option>
                          {registrars.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                        <input type="password" value={regForm.api_key}
                          onChange={(e) => setRegForm({ ...regForm, api_key: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder={editingRegAccount ? '留空表示不修改' : '请输入 API Key'} />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Secret</label>
                        <input type="password" value={regForm.api_secret}
                          onChange={(e) => setRegForm({ ...regForm, api_secret: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder={editingRegAccount ? '留空表示不修改' : '请输入 API Secret'} />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">备注</label>
                        <textarea value={regForm.remark}
                          onChange={(e) => setRegForm({ ...regForm, remark: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2" rows={2} />
                      </div>
                      <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-700">
                        提交后将发送飞书确认给超级管理员，审批通过后生效。
                      </div>
                    </div>
                    <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
                      <button onClick={closeRegModal} className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg">取消</button>
                      <button onClick={handleRegSave} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">提交申请</button>
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
                <button onClick={() => openDnsModal()} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
                  新增账号
                </button>
              </div>
              <p className="text-sm text-gray-500">
                {isSuperAdmin
                  ? '超管可查看并管理所有专员的账号，新建时需指定归属专员。'
                  : '仅显示归属于您的账号，新增/编辑/删除均需超管飞书确认。'}
              </p>

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
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">账号名称</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">DNS服务商</th>
                          {isSuperAdmin && (
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">归属专员</th>
                          )}
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">备注</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {dnsAccounts.map((account) => (
                          <tr key={account.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{account.name}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{findDnsProviderName(account.provider_code)}</td>
                            {isSuperAdmin && (
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {account.owner_name ?? <span className="text-gray-400 italic">未指定</span>}
                              </td>
                            )}
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${account.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                {account.is_active ? '启用' : '禁用'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{account.remark || '-'}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDateTime(account.created_at)}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              {canEditAccount(account.owner_id) ? (
                                <>
                                  <button onClick={() => openDnsModal(account)} className="text-blue-600 hover:text-blue-900 mr-3">编辑</button>
                                  <button onClick={() => handleDnsDelete(account)} className="text-red-600 hover:text-red-900">删除</button>
                                </>
                              ) : (
                                <span className="text-gray-300 text-xs">无权操作</span>
                              )}
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
                            {isSuperAdmin && account.owner_name && (
                              <p className="text-xs text-gray-400 mt-1">归属：{account.owner_name}</p>
                            )}
                          </div>
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${account.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {account.is_active ? '启用' : '禁用'}
                          </span>
                        </div>
                        {account.remark && <p className="text-sm text-gray-400 mt-2">{account.remark}</p>}
                        {canEditAccount(account.owner_id) && (
                          <div className="flex justify-end space-x-3 mt-3 pt-3 border-t border-gray-100">
                            <button onClick={() => openDnsModal(account)} className="text-blue-600 text-sm">编辑</button>
                            <button onClick={() => handleDnsDelete(account)} className="text-red-600 text-sm">删除</button>
                          </div>
                        )}
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
                      {isSuperAdmin && !editingDnsAccount && (
                        <OwnerSelect
                          value={dnsForm.target_owner_id}
                          onChange={(v) => setDnsForm({ ...dnsForm, target_owner_id: v })}
                        />
                      )}
                      {isSuperAdmin && editingDnsAccount && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">归属专员</label>
                          <p className="text-sm text-gray-600 px-3 py-2 bg-gray-50 rounded-lg">
                            {editingDnsAccount.owner_name ?? '未指定'}
                          </p>
                        </div>
                      )}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">账号名称 <span className="text-red-500">*</span></label>
                        <input type="text" value={dnsForm.name}
                          onChange={(e) => setDnsForm({ ...dnsForm, name: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2" placeholder="请输入账号名称" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">DNS服务商 <span className="text-red-500">*</span></label>
                        <select value={dnsForm.provider_code}
                          onChange={(e) => setDnsForm({ ...dnsForm, provider_code: e.target.value })}
                          disabled={!!editingDnsAccount}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 disabled:bg-gray-100">
                          <option value="">请选择DNS服务商</option>
                          {dnsProviders.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                        <input type="password" value={dnsForm.api_key}
                          onChange={(e) => setDnsForm({ ...dnsForm, api_key: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder={editingDnsAccount ? '留空表示不修改' : '请输入 API Key'} />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">API Secret</label>
                        <input type="password" value={dnsForm.api_secret}
                          onChange={(e) => setDnsForm({ ...dnsForm, api_secret: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          placeholder={editingDnsAccount ? '留空表示不修改' : '请输入 API Secret'} />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">备注</label>
                        <textarea value={dnsForm.remark}
                          onChange={(e) => setDnsForm({ ...dnsForm, remark: e.target.value })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2" rows={2} />
                      </div>
                      <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-700">
                        提交后将发送飞书确认给超级管理员，审批通过后生效。
                      </div>
                    </div>
                    <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
                      <button onClick={closeDnsModal} className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg">取消</button>
                      <button onClick={handleDnsSave} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">提交申请</button>
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
              <p className="text-sm text-gray-500">
                默认配置仅作为新建域名时的初始建议值，申请人可在提交时手动选择覆盖。修改需超管飞书确认。
              </p>

              {defaultsLoading ? (
                <div className="text-center py-12 text-gray-500">加载中...</div>
              ) : isSuperAdmin ? (
                /* ── 超管视图：所有专员的默认配置表格 ── */
                <div className="space-y-4">
                  <p className="text-sm text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-4 py-2">
                    点击各专员右侧的「编辑」按钮，可替该专员设置其新建域名时的默认注册商/账号偏好。
                  </p>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">专员</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">默认注册商</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">默认DNS服务商</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">默认注册账号</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">默认DNS账号</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {allDefaults.map((item) => {
                          const ownRegAcc = regAccounts.find((a) => a.id === item.default_reg_account_id);
                          const ownDnsAcc = dnsAccounts.find((a) => a.id === item.default_dns_account_id);
                          return (
                            <tr key={item.user_id} className={`hover:bg-gray-50 ${item.user_id === currentUser.id ? 'bg-blue-50/40' : ''}`}>
                              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                {item.user_name}
                                {item.user_id === currentUser.id && (
                                  <span className="ml-1 text-xs text-blue-500">（自己）</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-xs text-gray-500">
                                {item.user_role === 'super_admin' ? '超管' : '域名专员'}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600">
                                {item.default_registrar ? findRegistrarName(item.default_registrar) : <span className="text-gray-300">—</span>}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600">
                                {item.default_dns_provider ? findDnsProviderName(item.default_dns_provider) : <span className="text-gray-300">—</span>}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600">
                                {ownRegAcc ? ownRegAcc.name : <span className="text-gray-300">—</span>}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600">
                                {ownDnsAcc ? ownDnsAcc.name : <span className="text-gray-300">—</span>}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <button
                                  onClick={() => openEditDefaultsModal(item)}
                                  className="text-blue-600 hover:text-blue-800 text-sm"
                                >
                                  编辑
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                        {allDefaults.length === 0 && (
                          <tr>
                            <td colSpan={7} className="px-4 py-8 text-center text-gray-400 text-sm">
                              暂无专员数据
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* 超管编辑某专员默认配置的弹窗 */}
                  {editingDefaultsFor && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                      <div className="bg-white rounded-lg w-full max-w-lg">
                        <div className="flex justify-between items-center p-6 border-b border-gray-200">
                          <div>
                            <h3 className="text-lg font-medium text-gray-900">
                              编辑默认配置
                            </h3>
                            <p className="text-sm text-gray-500 mt-0.5">
                              专员：{editingDefaultsFor.user_name}
                              （{editingDefaultsFor.user_role === 'super_admin' ? '超管' : '域名专员'}）
                            </p>
                          </div>
                          <button onClick={closeEditDefaultsModal} className="text-gray-400 hover:text-gray-600">关闭</button>
                        </div>
                        <div className="p-6 space-y-4">
                          {/* 注册商 */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">默认注册商</label>
                            <select
                              value={defaultsEditForm.default_registrar}
                              onChange={(e) => setDefaultsEditForm({ ...defaultsEditForm, default_registrar: e.target.value })}
                              className="w-full border border-gray-300 rounded-lg px-3 py-2"
                            >
                              <option value="">不指定</option>
                              {registrars.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
                            </select>
                          </div>
                          {/* DNS 服务商 */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">默认 DNS 服务商</label>
                            <select
                              value={defaultsEditForm.default_dns_provider}
                              onChange={(e) => setDefaultsEditForm({ ...defaultsEditForm, default_dns_provider: e.target.value })}
                              className="w-full border border-gray-300 rounded-lg px-3 py-2"
                            >
                              <option value="">不指定</option>
                              {dnsProviders.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
                            </select>
                          </div>
                          {/* 注册账号：仅显示该专员名下的账号 */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">默认注册账号</label>
                            <select
                              value={defaultsEditForm.default_reg_account_id ?? ''}
                              onChange={(e) => setDefaultsEditForm({ ...defaultsEditForm, default_reg_account_id: e.target.value ? Number(e.target.value) : null })}
                              className="w-full border border-gray-300 rounded-lg px-3 py-2"
                            >
                              <option value="">不指定（可选）</option>
                              {regAccounts
                                .filter((a) => a.owner_id === editingDefaultsFor.user_id)
                                .map((a) => (
                                  <option key={a.id} value={a.id}>
                                    {a.name}（{findRegistrarName(a.registrar_code)}）
                                  </option>
                                ))}
                            </select>
                            {regAccounts.filter((a) => a.owner_id === editingDefaultsFor.user_id).length === 0 && (
                              <p className="text-xs text-gray-400 mt-1">该专员名下暂无注册账号</p>
                            )}
                          </div>
                          {/* DNS 账号：仅显示该专员名下的账号 */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">默认 DNS 账号</label>
                            <select
                              value={defaultsEditForm.default_dns_account_id ?? ''}
                              onChange={(e) => setDefaultsEditForm({ ...defaultsEditForm, default_dns_account_id: e.target.value ? Number(e.target.value) : null })}
                              className="w-full border border-gray-300 rounded-lg px-3 py-2"
                            >
                              <option value="">不指定（可选）</option>
                              {dnsAccounts
                                .filter((a) => a.owner_id === editingDefaultsFor.user_id)
                                .map((a) => (
                                  <option key={a.id} value={a.id}>
                                    {a.name}（{findDnsProviderName(a.provider_code)}）
                                  </option>
                                ))}
                            </select>
                            {dnsAccounts.filter((a) => a.owner_id === editingDefaultsFor.user_id).length === 0 && (
                              <p className="text-xs text-gray-400 mt-1">该专员名下暂无 DNS 账号</p>
                            )}
                          </div>
                          <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-700">
                            提交后将发送飞书确认给超级管理员，审批通过后生效。
                          </div>
                        </div>
                        <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
                          <button onClick={closeEditDefaultsModal} className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg">取消</button>
                          <button onClick={handleSaveUserDefaults} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                            提交申请
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* ── domain_spec 视图：仅自己的默认配置表单 ── */
                <div className="max-w-xl space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">默认注册商</label>
                    <select
                      value={defaultConfig.default_registrar}
                      onChange={(e) => setDefaultConfig({ ...defaultConfig, default_registrar: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    >
                      <option value="">不指定</option>
                      {registrars.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">默认 DNS 服务商</label>
                    <select
                      value={defaultConfig.default_dns_provider}
                      onChange={(e) => setDefaultConfig({ ...defaultConfig, default_dns_provider: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    >
                      <option value="">不指定</option>
                      {dnsProviders.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">默认注册账号</label>
                    <select
                      value={defaultConfig.default_reg_account_id ?? ''}
                      onChange={(e) => setDefaultConfig({ ...defaultConfig, default_reg_account_id: e.target.value ? Number(e.target.value) : null })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    >
                      <option value="">不指定（可选）</option>
                      {regAccounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}（{findRegistrarName(a.registrar_code)}）
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">默认 DNS 账号</label>
                    <select
                      value={defaultConfig.default_dns_account_id ?? ''}
                      onChange={(e) => setDefaultConfig({ ...defaultConfig, default_dns_account_id: e.target.value ? Number(e.target.value) : null })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    >
                      <option value="">不指定（可选）</option>
                      {dnsAccounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}（{findDnsProviderName(a.provider_code)}）
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="pt-4">
                    <button onClick={handleSaveDefaults} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                      提交申请
                    </button>
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
