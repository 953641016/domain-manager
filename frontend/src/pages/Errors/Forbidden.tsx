/**
 * 403 页面
 */
import { useNavigate } from 'react-router-dom';

export default function ForbiddenPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-300">403</h1>
        <p className="mt-4 text-xl text-gray-600">无权访问</p>
        <p className="mt-2 text-gray-500">您没有权限访问此页面</p>
        <button
          onClick={() => navigate('/')}
          className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          返回首页
        </button>
      </div>
    </div>
  );
}
