/**
 * 日期时间工具函数 — 统一以北京时间（CST / UTC+8）显示
 *
 * 根本原因：
 *   后端数据库存储 UTC 时间，序列化返回时不带时区标识符（无 Z 或 +00:00）。
 *   ECMAScript 规范规定：含时间分量的无时区字符串（如 "2026-05-31T00:48:25"）
 *   按"本地时间"解析；在 UTC+8 环境下会被误读为 UTC+8，导致
 *   toLocaleString({ timeZone: 'Asia/Shanghai' }) 仍然显示错误的 UTC 值。
 *
 * 解决方案：
 *   - 含 T（datetime 字符串）且不带时区时，追加 Z 强制为 UTC 解析。
 *   - 纯日期字符串（如 "2027-06-15"）按 ECMAScript 规范已视为 UTC 午夜，无需处理。
 */

/** 补全时区标识：datetime 字符串追加 Z，date-only 字符串保持原样 */
function ensureUTC(dateStr: string): string {
  if (!dateStr) return dateStr;
  // 已有时区标识 (Z / +08:00 等)
  if (dateStr.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(dateStr)) return dateStr;
  // datetime 字符串（含 T）→ 追加 Z 强制 UTC
  if (dateStr.includes('T')) return dateStr + 'Z';
  // date-only 字符串 → ECMAScript 已视为 UTC 午夜，无需处理
  return dateStr;
}

/**
 * 格式化为完整日期时间（yyyy/M/d HH:mm:ss，北京时间）
 * 适用于所有含时间分量的字段：created_at、updated_at、approved_at 等
 */
export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  try {
    return new Date(ensureUTC(dateStr)).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
  } catch {
    return dateStr;
  }
}

/**
 * 格式化为日期（yyyy/M/d，北京时间）
 * 适用于 date-only 字段：expire_date、expiration_date 等
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  try {
    return new Date(ensureUTC(dateStr)).toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' });
  } catch {
    return dateStr;
  }
}

/**
 * 计算距今剩余天数（正数=未来，负数=已过期）
 * 适用于域名/证书到期提醒场景
 */
export function daysUntil(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  try {
    const expiration = new Date(ensureUTC(dateStr));
    const now = new Date();
    const diff = expiration.getTime() - now.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}
