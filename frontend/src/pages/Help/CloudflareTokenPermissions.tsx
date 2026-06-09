import { Link } from 'react-router-dom';

const requiredPermissions = [
  {
    name: 'DNS',
    level: 'Edit',
    description: '创建、修改和读取普通 DNS 解析记录，是 Clerk、Vercel、后端域名解析必须权限。',
  },
  {
    name: 'Zone',
    level: 'Read',
    description: '读取域名所在 Zone，用于系统找到 Cloudflare Zone ID。',
  },
];

const optionalPermissions = [
  {
    name: 'Single Redirect / Dynamic URL Redirects / Rulesets',
    level: 'Edit',
    description: '仅在需要自动创建 Cloudflare 301/302 重定向规则时配置。',
  },
  {
    name: 'Registrar Domains',
    level: 'Admin',
    description: '仅注册账号需要，用于 Cloudflare Registrar 域名购买、续费和查询。',
  },
];

const wrongPermissions = [
  'Account DNS Settings',
  'Zone DNS Settings',
  'DNS Firewall',
  'DNS View',
];

const setupSteps = [
  '打开 Cloudflare Dashboard → 管理账户 → 账户 API 令牌。',
  '编辑当前 Token，或创建新的 Account API Token / Custom Token。',
  '资源范围选择“所有域名”，或只包含要解析的 Zone，例如 joyai-echo.net。',
  '在 DNS & Zones 权限组中勾选 DNS 的 Edit（建议 Read 也勾选）。',
  '在 DNS & Zones 权限组中勾选 Zone 的 Read。',
  '如需 CF 重定向规则，在 Rules & Configuration 中补充 Redirect / Rulesets 的 Edit 权限。',
  '保存 Token 后，回到域名管家 DNS 账号列表点击“自检”。',
];

export default function CloudflareTokenPermissionsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm text-blue-600 font-medium">Cloudflare 配置指南</p>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">Token 权限配置说明</h1>
          <p className="text-sm text-gray-500 mt-2 max-w-3xl">
            用于解决 DNS 解析失败、后台自检失败、Cloudflare 返回
            <span className="mx-1 font-mono text-red-600">Authentication error</span>
            等权限问题。
          </p>
        </div>
        <Link
          to="/system/accounts"
          className="inline-flex items-center justify-center rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          返回账号管理
        </Link>
      </div>

      <div className="rounded-2xl border border-blue-100 bg-blue-50 p-5">
        <div className="flex items-start gap-3">
          <div className="text-2xl">💡</div>
          <div>
            <h2 className="font-semibold text-blue-900">一句话结论</h2>
            <p className="text-sm text-blue-800 mt-1">
              普通 DNS 解析需要的是 <strong>Zone 级别</strong> 的
              <strong> DNS / Edit</strong> 和 <strong>Zone / Read</strong>。
              账号级的 DNS Settings、DNS Firewall、DNS View 不能替代 DNS Records 权限。
            </p>
          </div>
        </div>
      </div>

      <section className="rounded-2xl bg-white border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">DNS 解析账号必需权限</h2>
          <p className="text-sm text-gray-500 mt-1">用于 Clerk、Vercel、后端域名、GSC TXT 等 DNS 记录写入。</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">权限项</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">级别</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">作用</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {requiredPermissions.map((item) => (
                <tr key={item.name}>
                  <td className="px-6 py-4 text-sm font-semibold text-gray-900">{item.name}</td>
                  <td className="px-6 py-4">
                    <span className="inline-flex rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-700">
                      {item.level}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{item.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-white border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900">后台操作步骤</h2>
          <ol className="mt-4 space-y-3">
            {setupSteps.map((step, index) => (
              <li key={step} className="flex gap-3 text-sm text-gray-700">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
                  {index + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl bg-white border border-gray-200 shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900">自检通过标准</h2>
            <div className="mt-4 space-y-3 text-sm">
              <div className="rounded-lg bg-green-50 border border-green-100 p-3 text-green-800">
                ✓ Zone 读取权限：可读取 Zone 列表
              </div>
              <div className="rounded-lg bg-green-50 border border-green-100 p-3 text-green-800">
                ✓ DNS 记录读取权限：可读取 DNS 记录
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-4">
              如果 Zone 可读但 DNS 记录不可读，通常就是缺少 DNS / Edit，或资源范围没有包含当前域名。
            </p>
          </div>

          <div className="rounded-2xl bg-red-50 border border-red-100 p-6">
            <h2 className="text-lg font-semibold text-red-900">常见误区</h2>
            <p className="text-sm text-red-700 mt-1">下面这些权限看起来像 DNS，但不能替代普通 DNS 记录权限：</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {wrongPermissions.map((item) => (
                <span key={item} className="rounded-full bg-white border border-red-200 px-3 py-1 text-xs font-medium text-red-700">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-2xl bg-white border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">可选权限</h2>
          <p className="text-sm text-gray-500 mt-1">只有对应功能启用时才需要配置。</p>
        </div>
        <div className="divide-y divide-gray-100">
          {optionalPermissions.map((item) => (
            <div key={item.name} className="px-6 py-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{item.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{item.description}</p>
                </div>
                <span className="inline-flex w-fit rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700">
                  {item.level}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl bg-gray-900 p-6 text-white">
        <h2 className="text-lg font-semibold">错误信息怎么判断？</h2>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <div className="rounded-xl bg-white/10 p-4">
            <p className="font-mono text-sm text-red-200">Authentication error</p>
            <p className="text-sm text-gray-200 mt-2">优先检查 DNS / Edit 和 Zone 资源范围。</p>
          </div>
          <div className="rounded-xl bg-white/10 p-4">
            <p className="font-mono text-sm text-yellow-200">Unauthorized to access requested resource</p>
            <p className="text-sm text-gray-200 mt-2">通常表示缺少 Redirect / Rulesets 等功能权限。</p>
          </div>
        </div>
      </section>
    </div>
  );
}
