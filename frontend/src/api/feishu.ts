/**
 * 飞书集成 API
 */

import { api } from './client';

export interface FeishuUserInfo {
  user_id: string;
  name: string;
  en_name?: string;
  email?: string;
  mobile?: string;
  avatar_url?: string;
  union_id?: string;
  open_id?: string;
  department_name?: string;
}

export interface FeishuAppInfo {
  id: number | null;
  code: string;
  name: string;
  app_id: string;
  is_default: boolean;
  is_active: boolean;
}

export async function getFeishuApps(): Promise<FeishuAppInfo[]> {
  const response = await api.get('/feishu/apps');
  return response.data.apps || [];
}

/**
 * 获取飞书 OAuth URL
 */
export async function getFeishuOAuthUrl(redirect_uri: string, feishu_app_id?: number | null): Promise<{
  success: boolean;
  oauth_url: string;
}> {
  const response = await api.get('/feishu/oauth-url', {
    params: { redirect_uri, feishu_app_id }
  });
  return response.data;
}

/**
 * 通过 code 获取飞书用户信息
 */
export async function getFeishuUserInfo(code: string, feishu_app_id?: number | null): Promise<FeishuUserInfo> {
  const response = await api.get<FeishuUserInfo>('/feishu/user-info', {
    params: { code, feishu_app_id }
  });
  return response.data;
}

/**
 * 通过用户 ID 获取飞书用户信息
 */
export async function getFeishuUserById(user_id: string): Promise<{
  success: boolean;
  user: any;
}> {
  const response = await api.get(`/feishu/user/${user_id}`);
  return response.data;
}

/**
 * 发送飞书文本消息
 */
export async function sendFeishuMessage(
  receive_id: string,
  content: string,
  receive_id_type: string = 'open_id'
): Promise<{
  success: boolean;
  data: any;
}> {
  const response = await api.post('/feishu/send-message', {
    receive_id,
    content,
    receive_id_type
  });
  return response.data;
}

/**
 * 发送飞书交互式卡片
 */
export async function sendFeishuCard(
  receive_id: string,
  card_content: any,
  receive_id_type: string = 'open_id'
): Promise<{
  success: boolean;
  data: any;
}> {
  const response = await api.post('/feishu/send-card', {
    receive_id,
    card_content,
    receive_id_type
  });
  return response.data;
}

/**
 * 按姓名搜索飞书用户
 */
export async function searchFeishuUsers(keyword: string, feishu_app_id?: number | null): Promise<{
  success: boolean;
  users: FeishuUserInfo[];
}> {
  const response = await api.get('/feishu/search-users', {
    params: { keyword, feishu_app_id }
  });
  return response.data;
}
