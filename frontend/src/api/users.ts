/**
 * 用户管理 API
 */

import { api } from './client';
import type {
  User,
  RoleInfo,
  UserListResponse,
  UserCreate,
  UserUpdate,
} from '@/types/user';

/**
 * 获取用户列表
 */
export async function getUsers(params?: {
  skip?: number;
  limit?: number;
  role?: string;
  is_active?: boolean;
  search?: string;
}): Promise<UserListResponse> {
  const response = await api.get<UserListResponse>('/users', { params });
  return response.data;
}

/**
 * 获取用户详情
 */
export async function getUser(id: number): Promise<User> {
  const response = await api.get<User>(`/users/${id}`);
  return response.data;
}

/**
 * 获取角色列表
 */
export async function getRoles(): Promise<RoleInfo[]> {
  const response = await api.get<RoleInfo[]>('/users/roles');
  return response.data;
}

/**
 * 创建用户
 */
export async function createUser(data: UserCreate): Promise<User> {
  const response = await api.post<User>('/users', data);
  return response.data;
}

/**
 * 更新用户
 */
export async function updateUser(id: number, data: UserUpdate): Promise<User> {
  const response = await api.put<User>(`/users/${id}`, data);
  return response.data;
}

/**
 * 删除用户
 */
export async function deleteUser(id: number): Promise<void> {
  await api.delete(`/users/${id}`);
}

/**
 * 激活用户
 */
export async function activateUser(id: number): Promise<User> {
  const response = await api.post<User>(`/users/${id}/activate`);
  return response.data;
}
