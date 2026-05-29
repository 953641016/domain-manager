/**
 * 登录页面
 * 使用飞书OAuth扫码登录
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/api/client';

interface UserInfo {
  id: number;
  name: string;
  en_name?: string;
  role: string;
  email?: string;
  avatar_url?: string;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [oauthUrl, setOauthUrl] = useState('');

  useEffect(() => {
    // 检查是否已登录
    const token = localStorage.getItem('access_token');
    if (token) {
      navigate('/dashboard');
      return;
    }

    // 获取OAuth URL
    fetchOAuthUrl();
  }, [navigate]);

  const fetchOAuthUrl = async () => {
    try {
      const redirectUri = `${window.location.origin}/dm/api/v1/auth/callback`;
      const response = await api.get('/auth/oauth-url', {
        params: { redirect_uri: redirectUri }
      });
      setOauthUrl(response.data.oauth_url);
    } catch (err) {
      console.error('获取OAuth URL失败:', err);
      setError('获取登录链接失败，请稍后重试');
    }
  };

  const handleLogin = async () => {
    setLoading(true);
    setError('');

    try {
      // 在实际实现中，这里应该打开飞书OAuth页面
      // 由于需要弹出飞书登录窗口，这里使用模拟登录
      const code = prompt('请输入测试授权码（实际应使用飞书OAuth）:');
      if (!code) {
        setLoading(false);
        return;
      }

      const response = await api.post('/auth/login', { code });
      const { access_token, user } = response.data;

      // 存储token和用户信息
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user', JSON.stringify(user));

      // 跳转到仪表盘
      navigate('/dashboard');
    } catch (err: any) {
      console.error('登录失败:', err);
      setError(err.response?.data?.detail || '登录失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h1 className="text-center text-3xl font-bold text-gray-900">
            域名管家
          </h1>
          <p className="mt-2 text-center text-sm text-gray-600">
            企业级域名管理系统
          </p>
        </div>

        <div className="mt-8 space-y-6">
          <div className="rounded-lg shadow-lg bg-white p-8">
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <svg
                  className="h-16 w-16 text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z" />
                </svg>
              </div>

              <h2 className="text-xl font-semibold text-gray-700">
                欢迎使用域名管家
              </h2>

              <p className="text-gray-500">
                请使用飞书账号登录
              </p>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-600 text-sm">
                  {error}
                </div>
              )}

              <button
                onClick={handleLogin}
                disabled={loading}
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    登录中...
                  </span>
                ) : (
                  '飞书扫码登录'
                )}
              </button>
            </div>
          </div>

          <div className="text-center text-xs text-gray-500">
            <p>首次登录将自动创建账号</p>
            <p className="mt-1">管理员账号将自动识别</p>
          </div>
        </div>
      </div>
    </div>
  );
}
