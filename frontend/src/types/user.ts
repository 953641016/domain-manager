/**
 * 用户类型定义
 */

export enum UserRole {
  SUPER_ADMIN = 'super_admin',
  ADMIN = 'admin',
  DOMAIN_SPEC = 'domain_spec',
  BUSINESS = 'business',
}

export interface User {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  department: string | null;
  feishu_user_id: string;
  feishu_union_id: string | null;
  feishu_open_id: string | null;
  role: string;
  permissions: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  remark: string | null;
  assigned_specialist_id: number | null;
}

export interface RoleInfo {
  code: string;
  name: string;
  description: string;
  web_access: boolean;
  permissions: string[];
}

export interface UserListResponse {
  total: number;
  items: User[];
}

export interface UserCreate {
  name: string;
  feishu_user_id: string;
  feishu_union_id?: string;
  feishu_open_id?: string;
  email?: string;
  phone?: string;
  department?: string;
  role: string;
  remark?: string;
}

export interface UserUpdate {
  name?: string;
  email?: string;
  phone?: string;
  department?: string;
  role?: string;
  is_active?: boolean;
  remark?: string;
  assigned_specialist_id?: number | null;
}

export interface Specialist {
  id: number;
  name: string;
}
