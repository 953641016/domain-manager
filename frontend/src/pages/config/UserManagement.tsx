/**
 * 用户管理页面
 */

import React, { useState, useEffect } from 'react';
import {
  getUsers, getRoles, createUser, updateUser, deleteUser, activateUser
} from '@/api/users';
import {
  getFeishuOAuthUrl, getFeishuUserInfo, type FeishuUserInfo
} from '@/api/feishu';
import type { User, RoleInfo, UserCreate, UserUpdate } from '@/types/user';

const UserManagement: React.FC = () => {
  // 状态
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  
  // 飞书扫码相关
  const [showQRModal, setShowQRModal] = useState(false);
  const [qrUrl, setQrUrl] = useState('');
  const [qrLoading, setQrLoading] = useState(false);
  const [qrPolling, setQrPolling] = useState(false);
  
  // 搜索过滤条件
  const [filters, setFilters] = useState({
    search: '',
    role: '',
    is_active: '',
    skip: 0,
    limit: 20,
  });
  
  // 表单数据
  const [formData, setFormData] = useState<Partial<UserCreate>>({
    name: '',
    feishu_userid: '',
    role: 'business',
    email: '',
    phone: '',
    department: '',
    remark: '',
  });

  // 加载角色列表
  useEffect(() => {
    loadRoles();
  }, []);

  // 加载用户列表
  useEffect(() => {
    loadUsers();
  }, [filters]);

  // 加载角色
  const loadRoles = async () => {
    try {
      const data = await getRoles();
      setRoles(data);
    } catch (error) {
      console.error('加载角色失败:', error);
    }
  };

  // 加载用户
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

  // 打开新建/编辑弹窗
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

  // 关闭弹窗
  const closeModal = () => {
    setShowModal(false);
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
  };

  // 保存用户
  const handleSave = async () => {
    if (!formData.name || !formData.feishu_userid || !formData.role) {
      alert('请填写必填字段');
      return;
    }

    try {
      if (editingUser) {
        await updateUser(editingUser.id, formData as UserUpdate);
        alert('更新成功');
      } else {
        await createUser(formData as UserCreate);
        alert('创建成功');
      }
      closeModal();
      loadUsers();
    } catch (error: any) {
      console.error('保存失败:', error);
      alert(`保存失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  // 删除用户
  const handleDelete = async (user: User) => {
    if (!confirm(`确定要删除用户 "${user.name}" 吗？')) {
      return;
    }

    try {
      await deleteUser(user.id);
      alert('删除成功');
      loadUsers();
    } catch (error: any) {
      console.error('删除失败:', error);
      alert(`删除失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  // 激活用户
  const handleActivate = async (user: User) => {
    if (!confirm(`确定要激活用户 "${user.name}" 吗？`)) {
      return;
    }

    try {
      await activateUser(user.id);
      alert('激活成功');
      loadUsers();
    } catch (error: any) {
      console.error('激活失败:', error);
      alert(`激活失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  // 打开飞书扫码
  const openFeishuQR = async () => {
    try {
      setQrLoading(true);
      setShowQRModal(true);
      
      // 获取当前页面URL作为回调地址
      const redirectUri = window.location.origin + window.location.pathname;
      const result = await getFeishuOAuthUrl(redirectUri);
      setQrUrl(result.oauth_url);
      
      // 监听URL变化，检测是否有code返回
      const checkCodeInterval = setInterval(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        
        if (code) {
          clearInterval(checkCodeInterval);
          handleFeishuCode(code);
          // 清除URL中的code参数
          const newUrl = window.location.pathname;
          window.history.replaceState({}, '', newUrl);
        }
      }, 500);
      
      setQrPolling(true);
      
      // 清理函数
      return () => {
        clearInterval(checkCodeInterval);
        setQrPolling(false);
      };
    } catch (error: any) {
      console.error('获取OAuth URL失败:', error);
      alert(`获取飞书授权URL失败: ${error.response?.data?.detail || error.message}`);
      setShowQRModal(false);
    } finally {
      setQrLoading(false);
    }
  };

  // 处理飞书返回的code
  const handleFeishuCode = async (code: string) => {
    try {
      setQrLoading(true);
      const feishuUser = await getFeishuUserInfo(code);
      
      // 自动填充表单
      setFormData({
        name: feishuUser.name,
        feishu_user_id: feishuUser.user_id,
        role: 'business',
        email: feishuUser.email || '',
        phone: feishuUser.mobile || '',
        department: feishuUser.department_name || '',
        remark: ''
      });
      
      setShowQRModal(false);
      alert('用户信息获取成功，请确认信息后保存！');
    } catch (error: any) {
      console.error('获取用户信息失败:', error);
      alert(`获取飞书用户信息失败: ${error.response?.data?.detail || error.message}`);
    } finally {
      setQrLoading(false);
    }
  };

  // 填充飞书用户信息到表单
  const fillFeishuUserInfo = (feishuUser: FeishuUserInfo) => {
    setFormData({
      name: feishuUser.name,
      feishu_user_id: feishuUser.user_id,
      role: 'business',
      email: feishuUser.email || '',
      phone: feishuUser.mobile || '',
      department: feishuUser.department_name || '',
      remark: ''
    });
  };

  // 渲染角色标签
  const getRoleLabel = (roleCode: string) => {
    const role = roles.find(r => r.code === roleCode);
    return role ? role.name : roleCode;
  };

  return (
    <div className="p-6">
      {/* 头部 */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">用户管理</h1>
        <button
          onClick={() => openModal()}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium"
        >
          新增用户
        </button>
      </div>

      {/* 搜索筛选 */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              placeholder="搜索用户名、邮箱、飞书ID"
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">角色</label>
            <select
              value={filters.role}
              onChange={(e) => setFilters({ ...filters, role: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
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
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="">全部</option>
              <option value="true">启用</option>
              <option value="false">禁用</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => setFilters({ ...filters, skip: 0 })}
              className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg"
            >
              查询
            </button>
          </div>
        </div>
      </div>

      {/* 用户列表 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  用户信息
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  角色
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  飞书ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  状态
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  创建时间
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    加载中...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                  暂无用户
                </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="ml-2">
                          <div className="text-sm font-medium text-gray-900">{user.name}</div>
                          <div className="text-sm text-gray-500">{user.email || '-'}</div>
                          <div className="text-sm text-gray-400">{user.department || '-'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      user.role === 'admin' ? 'bg-red-100 text-red-800' :
                      user.role === 'domain_spec' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                      }`}
                      >
                        {getRoleLabel(user.role)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.feishu_userid}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        user.is_active ? 'bg-green-100 text-green-800' :
                        'bg-red-100 text-red-800'
                      }`}
                      >
                        {user.is_active ? '启用' : '禁用'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(user.created_at).toLocaleString('zh-CN')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => openModal(user)}
                        className="text-blue-600 hover:text-blue-900 mr-3"
                      >
                        编辑
                      </button>
                      {user.is_active ? (
                        <button
                          onClick={() => handleDelete(user)}
                          className="text-red-600 hover:text-red-900 mr-3"
                        >
                          禁用
                        </button>
                      ) : (
                        <button
                          onClick={() => handleActivate(user)}
                          className="text-green-600 hover:text-green-900 mr-3"
                        >
                          激活
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 分页 */}
      {!loading && total > 0 && (
        <div className="flex justify-between items-center mt-4">
          <span className="text-sm text-gray-700">
            显示 {users.length} 条，共 {total} 条
          </span>
          <div className="flex space-x-2">
            <button
              onClick={() => setFilters({ ...filters, skip: Math.max(0, filters.skip - filters.limit) })}
              disabled={filters.skip <= 0}
              className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50"
            >
              上一页
            </button>
            <button
              onClick={() => setFilters({ ...filters, skip: filters.skip + filters.limit })}
              disabled={filters.skip + filters.limit >= total}
              className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50"
            >
              下一页
            </button>
          </div>
        </div>
      </div>

      {/* 用户编辑/新建弹窗 */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center p-6 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                {editingUser ? '编辑用户' : '新增用户'}
              </h3>
              <button
                onClick={closeModal}
                className="text-gray-400 hover:text-gray-600"
              >
                关闭
              </button>
            </div>
            <div className="p-6">
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
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                  飞书用户ID <span className="text-red-500">*</span>
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={formData.feishu_userid}
                      onChange={(e) => setFormData({ ...formData, feishu_userid: e.target.value })}
                      disabled={editingUser !== null}
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-2"
                      placeholder="请输入飞书用户ID"
                    />
                    {!editingUser && (
                      <button
                        type="button"
                        onClick={() => {
                          closeModal();
                          openFeishuQR();
                        }}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 whitespace-nowrap"
                      >
                        扫码获取
                      </button>
                    )}
                  </div>
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
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    邮箱
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="请输入邮箱"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                  手机
                  </label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="请输入手机号"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                  部门
                  </label>
                  <input
                    type="text"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    placeholder="请输入部门"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    备注
                  </label>
                  <textarea
                    value={formData.remark}
                    onChange={(e) => setFormData({ ...formData, remark: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    rows={3}
                    placeholder="请输入备注"
                  />
                </div>
              </div>
              <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200 mt-6">
                <button
                  onClick={closeModal}
                  className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg"
                >
                  取消
                </button>
                <button
                  onClick={handleSave}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  保存
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 飞书扫码弹窗 */}
      {showQRModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg w-full max-w-md mx-4">
            <div className="flex justify-between items-center p-6 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                飞书扫码获取用户信息
              </h3>
              <button
                onClick={() => setShowQRModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                关闭
              </button>
            </div>
            <div className="p-6">
              {qrLoading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p className="text-gray-600">正在生成二维码...</p>
                </div>
              ) : qrUrl ? (
                <div className="text-center">
                  <p className="text-gray-600 mb-4">请使用飞书扫描下方二维码</p>
                  <div className="flex justify-center mb-4">
                    {/* 这里可以使用 qrCode.react 等库生成二维码，为简化示例直接显示链接 */}
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 bg-gray-50">
                      <p className="text-sm text-gray-500 mb-2">二维码区域</p>
                      <a 
                        href={qrUrl} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-sm break-all"
                      >
                        点击这里打开授权页面
                      </a>
                    </div>
                  </div>
                  <p className="text-sm text-gray-500">
                    扫码后会自动填充用户信息
                  </p>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  加载失败，请重试
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
