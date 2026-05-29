/**
 * 系统配置页面
 */
import { useState, useEffect } from 'react';
import { api } from '@/api/client';

interface RegistrarInfo {
  code: string;
  name: string;
  description: string;
}

interface DnsProviderInfo {
  code: string;
  name: string;
  description: string;
}

export default function ConfigPage() {
  const [registrars, setRegistrars] = useState<RegistrarInfo[]>([]);
  const [dnsProviders, setDnsProviders] = useState<DnsProviderInfo[]>([]);
  const [activeTab, setActiveTab] = useState('registrar');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchConfigInfo();
  }, []);

  const fetchConfigInfo = async () => {
    try {
      setLoading(true);
      const [registrarsRes, dnsRes] = await Promise.all([
        api.get('/registrar/list'),
        api.get('/registrar/dns-providers')
      ]);

      setRegistrars(registrarsRes.data.registrars || []);
      setDnsProviders(dnsRes.data.dns_providers || []);
    } catch (err) {
      console.error('获取配置信息失败:', err);
    } finally {
      setLoading(false);
    }
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
      <h1 className="text-2xl font-bold text-gray-800">系统配置</h1>

      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            <button
              onClick={() => setActiveTab('registrar')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'registrar'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              注册商配置
            </button>
            <button
              onClick={() => setActiveTab('dns')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'dns'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              DNS配置
            </button>
            <button
              onClick={() => setActiveTab('general')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'general'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              通用设置
            </button>
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'registrar' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold">支持的注册商</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {registrars.map((reg) => (
                  <div
                    key={reg.code}
                    className="border border-gray-200 rounded-lg p-4 hover:border-blue-300"
                  >
                    <h3 className="font-medium text-gray-800">{reg.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">{reg.description}</p>
                    <div className="mt-2 text-xs text-gray-400">Code: {reg.code}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'dns' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold">支持的DNS服务商</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {dnsProviders.map((provider) => (
                  <div
                    key={provider.code}
                    className="border border-gray-200 rounded-lg p-4 hover:border-blue-300"
                  >
                    <h3 className="font-medium text-gray-800">{provider.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">{provider.description}</p>
                    <div className="mt-2 text-xs text-gray-400">Code: {provider.code}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'general' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold">通用设置</h2>
              <div className="bg-gray-50 rounded-lg p-4 text-gray-500">
                通用设置功能待开发
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
