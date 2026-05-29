/**
 * 权限路由守卫组件
 * 检查用户是否具有所需角色
 */
import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';

interface PermissionRouteProps {
  children: ReactNode;
  allowedRoles: string[];
}

export default function PermissionRoute({ children, allowedRoles }: PermissionRouteProps) {
  const userStr = localStorage.getItem('user');
  if (!userStr) {
    return <Navigate to="/login" replace />;
  }

  try {
    const user = JSON.parse(userStr);
    if (!allowedRoles.includes(user.role)) {
      return <Navigate to="/403" replace />;
    }
  } catch {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
