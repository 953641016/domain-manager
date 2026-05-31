import React, { useState, useEffect, useCallback } from 'react';
import { api } from '@/api/client';
import {
  getUsers, getRoles, createUser, updateUser, deactivateUser, deleteUser, activateUser
} from '@/api/users';
import { searchFeishuUsers } from '@/api/feishu';
import type { FeishuUserInfo } from '@/api/feishu';
import { QRCodeSVG } from 'qrcode.react';
import type { User, RoleInfo, UserCreate, UserUpdate, Specialist } from '@/types/user';

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [specialists, setSpecialists] = useState<Specialist[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  const [feishuSearchKeyword, setFeishuSearchKeyword] = useState('');
  const [feishuSearchResults, setFeishuSearchResults] = useState<FeishuUserInfo[]>([]);
  const [feishuSearching, setFeishuSearching] = useState(false);
  const [showFeishuDropdown, setShowFeishuDropdown] = useState(false);

  const [filters, setFilters] = useState({
    search: '',
    role: '',
    is_active: '',
    skip: 0,
    limit: 20,
  });

  const [formData, setFormData] = useState<Partial<UserCreate & UserUpdate>>({
    name: '',
    feishu_userid: '',
    role: 'business',
    email: '',
    phone: '',
    department: '',
    remark: '',
    assigned_specialist_id: null,
  });

  useEffect(() => {
    loadRoles();
    loadSpecialists();
  }, []);

  useEffect(() => {
    loadUsers();
  }, [filters]);

  const loadRoles = async () => {
    try {
      const data = await getRoles();
      setRoles(data);
    } catch (error) {
      console.error('加载角色失败:', error);
    }
  };

  const loadSpecialists = async () => {
    try {
      const res = await api.get('/users/specialists');
      setSpecialists(res.data);
    } catch (error) {
      console.error('加载专员列表失败:', error);
    }
  };

  const loadUsers = async () => {
    setLoading(true);
    try {
      const params = {
        ...filters,
        is_active: filters.is_active ? filters.is_active === 'true' : undefined,
      };
      const data = await getUsers(params);
      setUsers(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('加载用户失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const openModal = (user?: User) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        name: user.name,
        feishu_userid: user.feishu_userid,
        role: user.role,
        email: user.email || '',
        phone: user.phone || '',
        department: user.department || '',
        remark: user.remark || '',
        assigned_specialist_id: user.assigned_specialist_id ?? null,
      });
    } else {
      setEditingUser(null);
      setFormData({
        name: '',
        feishu_userid: '',
        role: 'business',
        email: '',
        phone: '',
        department: '',
        remark: '',
      });
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingUser(null);
  };

  const handleSave = async () => {
    if (!formData.name || !formData.feishu_userid || !formData.role) {
      alert('请填写必填字段（姓名、飞书用户ID、角色）');
      return;
    }

    try {
      let result: any;
      if (editingUser) {
        result = await updateUser(editingUser.id, formData as UserUpdate);
      } else {
        result = await createUser(formData as UserCreate);
      }
      if (result?.status === 'pending_approval') {
        alert('已提交申请，等待超级管理员飞书确认后生效。\n确认ID：' + result.confirmation_id);
      } else {
        alert(editingUser ? '更新成功' : '创建成功');
      }
      closeModal();
      loadUsers();
    } catch (error: any) {
      const msg = error.response?.data?.detail || error.message;
      alert('操作失败: ' + msg);
    }
  };

  const handleDeactivate = async (user: User) => {
    if (!confirm('确定要禁用用户 "' + user.name + '" 吗？禁用后可通过激活恢复。')) return;
    try {
      const result: any = await deactivateUser(user.id);
      if (result?.status === 'pending_approval') {
        alert('已提交申请，等待超级管理员飞书确认后生效。');
      } else {
        alert('已禁用');
        loadUsers();
      }
    } catch (error: any) {
      alert('操作失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDelete = async (user: User) => {
    if (!confirm('⚠️ 确定要删除用户 "' + user.name + '" 吗？\n\n删除后不可恢复，请谨慎操作。')) return;
    try {
      const result: any = await deleteUser(user.id);
      if (result?.status === 'pending_approval') {
        alert('已提交申请，等待超级管理员飞书确认后生效。');
      } else {
        alert('已删除');
        loadUsers();
      }
    } catch (error: any) {
      alert('操作失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleActivate = async (user: User) => {
    if (!confirm('确定要激活用户 "' + user.name + '" 吗？')) return;
    try {
      const result: any = await activateUser(user.id);
      if (result?.status === 'pending_approval') {
        alert('已提交申请，等待超级管理员飞书确认后生效。');
      } else {
        alert('已激活');
        loadUsers();
      }
    } catch (error: any) {
      alert('操作失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const getRoleLabel = (roleCode: string) => {
    const role = roles.find(r => r.code === roleCode);
    return role ? role.name : roleCode;
  };

  const searchFeishu = useCallback(async (keyword: string) => {
    if (!keyword || keyword.length < 1) {
      setFeishuSearchResults([]);
      setShowFeishuDropdown(false);
      return;
    }
    setFeishuSearching(true);
    try {
      const result = await searchFeishuUsers(keyword);
      setFeishuSearchResults(result.users || []);
      setShowFeishuDropdown(true);
    } catch (error) {
      console.error('搜索飞书用户失败:', error);
      setFeishuSearchResults([]);
    } finally {
      setFeishuSearching(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (feishuSearchKeyword && !editingUser) {
        searchFeishu(feishuSearchKeyword);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [feishuSearchKeyword, editingUser, searchFeishu]);

  const selectFeishuUser = (user: FeishuUserInfo) => {
    setFormData({
      ...formData,
      name: user.name,
      feishu_userid: user.user_id,
      email: user.email || '',
      phone: user.mobile || '',
      department: user.department_name || '',
    });
    setFeishuSearchKeyword('');
    setFeishuSearchResults([]);
    setShowFeishuDropdown(false);
  };

  const openQRModal = async () => {
    try {
      const redirectUri = `${window.location.origin}/dm/api/feishu/add-user-callback`;
      const response = await api.get('/feishu/oauth-url', {
        params: { redirect_uri: redirectUri }
      });
      setQrUrl(response.data.oauth_url);
      setShowQRModal(true);
    } catch (error) {
      alert('获取二维码失败，请稍后重试');
    }
  };

  const [showQRModal, setShowQRModal] = useState(false);
  const [qrUrl, setQrUrl] = useState('');

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'super_admin': return 'bg-purple-100 text-purple-800';
      case 'admin': return 'bg-red-100 text-red-800';
      case 'domain_spec': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-4 md:p-6">
      <div className="flex justify-between items-center mb-4 md:mb-6">
        <h1 className="text-xl md:text-2xl font-bold text-gray-900">用户管理</h1>
        <div className="flex gap-2">
          <button
            onClick={openQRModal}
            className="bg-green-600 hover:bg-green-700 text-white px-3 py-2 md:px-4 rounded-lg font-medium text-sm md:text-base"
          >
            扫码添加
          </button>
          <button
            onClick={() => openModal()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 md:px-4 rounded-lg font-medium text-sm md:text-base"
          >
            手动添加
          </button>
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-4 md:mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              placeholder="用户名、邮箱、飞书ID"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">角色</label>
            <select
              value={filters.role}
              onChange={(e) => setFilters({ ...filters, role: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">全部</option>
              {roles.map(role => (
                <option key={role.code} value={role.code}>{role.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
            <select
              value={filters.is_active}
              onChange={(e) => setFilters({ ...filters, is_active: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">全部</option>
              <option value="true">启用</option>
              <option value="false">禁用</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => setFilters({ ...filters, skip: 0 })}
              className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm"
            >
              查询
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">用户信息</th>
                <th className="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
                <th className="hidden md:table-cell px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">飞书ID</th>
                <th className="px-4 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th className="hidden lg:table-cell px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                <th className="px-4 md:px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">加载中...</td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">暂无用户数据</td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-4 md:px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{user.name}</div>
                      <div className="text-xs text-gray-500 md:hidden">{user.feishu_userid}</div>
                      {user.email && <div className="text-xs text-gray-400">{user.email}</div>}
                    </td>
                    <td className="px-4 md:px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRoleBadgeColor(user.role)}`}>
                        {getRoleLabel(user.role)}
                      </span>
                    </td>
                    <td className="hidden md:table-cell px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.feishu_userid}
                    </td>
                    <td className="px-4 md:px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {user.is_active ? '启用' : '禁用'}
                      </span>
                    </td>
                    <td className="hidden lg:table-cell px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(user.created_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}
                    </td>
                    <td className="px-4 md:px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button onClick={() => openModal(user)} className="text-blue-600 hover:text-blue-900 mr-2">编辑</button>
                      {user.is_active ? (
                        <button onClick={() => handleDeactivate(user)} className="text-orange-600 hover:text-orange-900 mr-2">禁用</button>
                      ) : (
                        <button onClick={() => handleActivate(user)} className="text-green-600 hover:text-green-900 mr-2">激活</button>
                      )}
                      <button onClick={() => handleDelete(user)} className="text-red-600 hover:text-red-900">删除</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {!loading && total > 0 && (
        <div className="flex justify-between items-center mt-4">
          <span className="text-sm text-gray-700">共 {total} 条</span>
          <div className="flex space-x-2">
            <button
              onClick={() => setFilters({ ...filters, skip: Math.max(0, filters.skip - filters.limit) })}
              disabled={filters.skip <= 0}
              className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50"
            >上一页</button>
            <button
              onClick={() => setFilters({ ...filters, skip: filters.skip + filters.limit })}
              disabled={filters.skip + filters.limit >= total}
              className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50"
            >下一页</button>
          </div>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-4 md:p-6 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                {editingUser ? '编辑用户' : '新增用户'}
              </h3>
              <button onClick={closeModal} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
            </div>
            <div className="p-4 md:p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    姓名 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="请输入姓名"
                  />
                </div>
                <div className="relative">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    飞书用户ID <span className="text-red-500">*</span>
                  </label>
                  {editingUser ? (
                    <input
                      type="text"
                      value={formData.feishu_userid}
                      disabled
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 disabled:bg-gray-100"
                    />
                  ) : (
                    <>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={formData.feishu_userid}
                          onChange={(e) => setFormData({ ...formData, feishu_userid: e.target.value })}
                          className="flex-1 border border-gray-300 rounded-lg px-3 py-2"
                          placeholder="ou_xxxxxxxxxxxxxxxx"
                        />
                      </div>
                      <div className="mt-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-400 whitespace-nowrap">或搜索：</span>
                          <div className="relative flex-1">
                            <input
                              type="text"
                              value={feishuSearchKeyword}
                              onChange={(e) => setFeishuSearchKeyword(e.target.value)}
                              onFocus={() => feishuSearchResults.length > 0 && setShowFeishuDropdown(true)}
                              className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                              placeholder="输入飞书姓名搜索，自动填充"
                            />
                            {feishuSearching && (
                              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">搜索中...</span>
                            )}
                          </div>
                        </div>
                        {showFeishuDropdown && feishuSearchResults.length > 0 && (
                          <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                            {feishuSearchResults.map((u, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => selectFeishuUser(u)}
                                className="w-full text-left px-3 py-2 hover:bg-blue-50 flex items-center gap-3 text-sm"
                              >
                                {u.avatar_url && (
                                  <img src={u.avatar_url} alt="" className="w-6 h-6 rounded-full" />
                                )}
                                <div>
                                  <div className="font-medium">{u.name}</div>
                                  <div className="text-xs text-gray-400">{u.email || u.user_id}</div>
                                </div>
                              </button>
                            ))}
                          </div>
                        )}
                        {showFeishuDropdown && feishuSearchResults.length === 0 && !feishuSearching && feishuSearchKeyword && (
                          <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm text-gray-500">
                            未找到匹配的用户
                          </div>
                        )}
                      </div>
                    </>
                  )}
                  <p className="text-xs text-gray-400 mt-1">输入姓名搜索飞书用户，点击结果自动填充</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    角色 <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                  >
                    {roles.map(role => (
                      <option key={role.code} value={role.code}>{role.name}</option>
                    ))}
                  </select>
                </div>
                {formData.role === 'business' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      归属专员
                      <span className="ml-1 text-xs text-gray-400">（业务人员必填）</span>
                    </label>
                    <select
                      value={formData.assigned_specialist_id ?? ''}
                      onChange={(e) => setFormData({ ...formData, assigned_specialist_id: e.target.value ? Number(e.target.value) : null })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    >
                      <option value="">-- 请选择归属专员 --</option>
                      {specialists.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="请输入邮箱"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">手机</label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="请输入手机号"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">部门</label>
                  <input
                    type="text"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="请输入部门"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">备注</label>
                  <textarea
                    value={formData.remark}
                    onChange={(e) => setFormData({ ...formData, remark: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    rows={3}
                    placeholder="请输入备注"
                  />
                </div>
              </div>
              <div className="flex justify-end space-x-3 pt-4 md:pt-6 border-t border-gray-200 mt-4 md:mt-6">
                <button onClick={closeModal} className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg">取消</button>
                <button onClick={handleSave} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">保存</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showQRModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">扫码添加用户</h3>
              <button onClick={() => setShowQRModal(false)} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-4">请让新用户用飞书扫描下方二维码</p>
              {qrUrl ? (
                <div className="flex justify-center mb-4">
                  <div className="border border-gray-200 rounded-lg p-3 bg-white">
                    <QRCodeSVG value={qrUrl} size={200} level="M" />
                  </div>
                </div>
              ) : (
                <div className="flex justify-center mb-4">
                  <div className="w-[200px] h-[200px] bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">加载中...</div>
                </div>
              )}
              <p className="text-xs text-gray-400">扫码后系统将自动获取用户信息并添加</p>
              <p className="text-xs text-gray-400 mt-1">新用户默认角色为「业务人员」</p>
              <button
                onClick={() => { setShowQRModal(false); loadUsers(); }}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
              >
                刷新列表
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
