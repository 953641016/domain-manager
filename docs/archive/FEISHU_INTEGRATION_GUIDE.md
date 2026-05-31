# 飞书集成完整指南

## 📋 概述

本项目提供完整的飞书集成方案，包括：
- ✅ 飞书OAuth登录
- 📱 飞书机器人消息推送
- 📄 飞书卡片消息
- 🔔 飞书事件回调
- 👥 飞书通讯录同步

---

## 🛠️ 飞书应用配置

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn)
2. 进入 **开发者后台** -> **创建应用**
3. 选择 **企业自建应用**，填写基本信息
4. 提交后获取以下关键信息：
   - App ID (`FEISHU_APP_ID`)
   - App Secret (`FEISHU_APP_SECRET`)

### 2. 权限配置

在 **权限管理** 中添加以下权限：

| 权限名称 | 权限ID | 用途 |
|---------|--------|------|
| 获取用户基本信息 | `contact:user.base:readonly` | OAuth登录 |
| 获取用户邮箱 | `contact:user.email:readonly` | 用户信息同步 |
| 获取用户手机号 | `contact:user.phone:readonly` | 用户信息同步 |
| 读取通讯录 | `contact:contact:readonly` | 用户搜索 |
| 发送消息 | `im:message` | 机器人推送 |
| 读取用户身份 | `identity:user:readonly` | 身份验证 |
| 获取群组信息 | `im:chat:readonly` | 群组管理 |

### 3. 安全配置

在 **安全设置** 中配置：

#### 重定向URL（OAuth回调）
```
https://your-domain.com/api/v1/feishu/callback
https://your-domain.com/auth/callback
```

#### 事件订阅
```
https://your-domain.com/api/v1/feishu/webhook
```

#### 验证配置
- **Verification Token** (`FEISHU_VERIFICATION_TOKEN`)
- **Encrypt Key** (`FEISHU_ENCRYPT_KEY`) - 可选

---

## 🔐 OAuth登录流程

### 1. 前端流程

```typescript
// 1. 获取OAuth URL
const response = await api.get('/api/v1/feishu/oauth-url', {
  params: {
    redirect_uri: 'https://your-domain.com/auth/callback'
  }
});

// 2. 打开扫码窗口
window.open(response.data.oauth_url, '_blank', 'width=600,height=800');

// 3. 回调页面处理Code
// 回调页面会收到 ?code=xxx&state=xxx
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');

// 4. 使用Code登录
const loginResponse = await api.post('/api/v1/auth/login', { code });

// 5. 存储token，跳转到首页
localStorage.setItem('access_token', loginResponse.data.access_token);
window.location.href = '/dashboard';
```

### 2. 后端API说明

#### 获取OAuth URL
```http
GET /api/v1/feishu/oauth-url?redirect_uri=https://...
```

#### 扫码登录
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "code": "feishu-oauth-code"
}
```

---

## 🤖 飞书机器人集成

### 1. 机器人配置

在飞书开放平台：
1. 进入 **应用功能** -> **机器人**
2. 启用机器人功能
3. 配置机器人头像、名称、描述

### 2. 发送消息API

下面是使用代码发送飞书消息的示例：

```python
import requests
from app.services.feishu_service import feishu_service

def send_text_message(receive_id: str, content: str, receive_id_type: str = "open_id"):
    """发送文本消息"""
    url = f"{feishu_service.base_url}/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {feishu_service.get_app_access_token()}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "receive_id_type": receive_id_type,
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def send_card_message(receive_id: str, card_data: dict, receive_id_type: str = "open_id"):
    """发送卡片消息"""
    url = f"{feishu_service.base_url}/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {feishu_service.get_app_access_token()}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "receive_id_type": receive_id_type,
        "receive_id": receive_id,
        "msg_type": "interactive",
        "content": json.dumps(card_data)
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()
```

### 3. 常用卡片模板

#### 域名到期提醒卡片
```python
expiry_card = {
    "header": {
        "template": "orange",
        "title": {
            "tag": "plain_text",
            "content": "⚠️ 域名到期提醒"
        }
    },
    "elements": [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**域名**: example.com\n**到期时间**: 2026-12-31\n**剩余天数**: 30天"
            }
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "查看详情"
                    },
                    "type": "primary",
                    "url": "https://your-domain.com/domains"
                }
            ]
        }
    ]
}
```

#### 审批通知卡片
```python
approval_card = {
    "header": {
        "template": "blue",
        "title": {
            "tag": "plain_text",
            "content": "📋 新的审批请求"
        }
    },
    "elements": [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**申请人**: 张三\n**申请类型**: 域名注册\n**域名**: newdomain.com\n**备注**: 新项目使用"
            }
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "审批通过"
                    },
                    "type": "primary",
                    "value": {
                        "action": "approve",
                        "request_id": "xxx"
                    }
                },
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "拒绝"
                    },
                    "type": "danger",
                    "value": {
                        "action": "reject",
                        "request_id": "xxx"
                    }
                }
            ]
        }
    ]
}
```

---

## 🔔 飞书事件回调处理

### 1. 事件回调端点

创建一个事件接收和处理的API端点：

```python
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import hashlib
import base64
import json

router = APIRouter(prefix="/feishu", tags=["飞书集成"])

@router.post("/webhook")
async def handle_feishu_webhook(request: Request, background_tasks: BackgroundTasks):
    """处理飞书事件回调"""
    body = await request.json()
    
    # 验证请求（加密验证）
    if not validate_feishu_request(await request.body()):
        raise HTTPException(status_code=403, detail="验证失败")
    
    # URL验证（首次配置时）
    if "challenge" in body:
        return {
            "challenge": body["challenge"]
        }
    
    # 异步处理事件
    event_type = body.get("header", {}).get("event_type", "")
    event_data = body.get("event", {})
    
    background_tasks.add_task(process_feishu_event, event_type, event_data)
    
    return {
        "code": 0,
        "msg": "success"
    }

def validate_feishu_request(body: bytes) -> bool:
    """验证飞书请求签名"""
    timestamp = request.headers.get("x-lark-request-timestamp")
    nonce = request.headers.get("x-lark-request-nonce")
    signature = request.headers.get("x-lark-signature")
    
    if not all([timestamp, nonce, signature]):
        return False
    
    # 签名验证逻辑
    string_to_sign = f"{timestamp}{nonce}{Config.FEISHU_VERIFICATION_TOKEN}{body.decode()}"
    calculated = hashlib.sha1(string_to_sign.encode()).hexdigest()
    
    return calculated == signature

async def process_feishu_event(event_type: str, event_data: dict):
    """处理飞书事件"""
    if event_type == "im.message.receive_v1":
        await handle_new_message(event_data)
    elif event_type == "im.message.action_v1":
        await handle_card_action(event_data)
    elif event_type == "contact.user.created_v3":
        await handle_user_created(event_data)
```

### 2. 支持的事件类型

| 事件类型 | 说明 | 处理方式 |
|---------|------|---------|
| `im.message.receive_v1` | 收到消息 | 机器人对话 |
| `im.message.action_v1` | 卡片交互 | 审批操作 |
| `contact.user.created_v3` | 新用户 | 同步用户 |
| `contact.user.deleted_v3` | 用户删除 | 移除用户 |

---

## 📱 机器人命令系统

### 1. 命令格式

```
@域名管家 命令 [参数]
```

### 2. 常用命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `help` | 帮助信息 | `@域名管家 help` |
| `search` | 搜索域名 | `@域名管家 search example` |
| `check` | 检查到期 | `@域名管家 check` |
| `list` | 列表域名 | `@域名管家 list` |

### 3. 命令处理示例

```python
async def handle_new_message(event_data: dict):
    """处理新消息"""
    message = event_data.get("message", {})
    sender = event_data.get("sender", {})
    
    content = json.loads(message.get("content", "{}")).get("text", "")
    
    # 解析命令
    if content.startswith("@域名管家"):
        command = content.replace("@域名管家", "").strip()
        await process_command(sender.get("sender_id"), command)

async def process_command(user_id: str, command: str):
    """处理命令"""
    command = command.lower()
    
    if command == "help" or command == "":
        await send_help_message(user_id)
    elif command == "check":
        await send_expiry_reminder(user_id)
    elif command.startswith("search "):
        query = command.replace("search ", "")
        await search_domains(user_id, query)
    else:
        await send_text_message(user_id, "未知命令，请发送 'help' 查看帮助")
```

---

## 📊 飞书集成配置文件

### 完整的 .env 配置示例

```env
# 飞书应用配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxxxxxx
FEISHU_ENCRYPT_KEY=xxxxxxxxxxxxxx

# 超级管理员飞书用户ID（可选）
SUPER_ADMIN_FEISHU_USER_ID=ou_xxxxxxxxxxxxxx

# 管理员用户ID列表（逗号分隔）
ADMIN_USER_IDS=ou_xxxxxxxxxxxxxx,ou_yyyyyyyyyyyyyy

# 飞书通知群组ID（可选，用于群发通知）
FEISHU_NOTIFICATION_CHAT_ID=oc_xxxxxxxxxxxxxx
```

---

## 🔧 部署注意事项

### 1. 环境要求

- Python 3.8+
- FastAPI + Uvicorn
- HTTPS 支持（飞书回调必须使用HTTPS）

### 2. 网络配置

- 确保服务器可以访问 `https://open.feishu.cn`
- 确保飞书可以访问你的回调地址（需要公网IP/域名）
- 推荐使用Nginx反向代理处理SSL

### 3. HTTPS证书

飞书要求回调URL必须是HTTPS，所以你需要：
1. 申请SSL证书（Let's Encrypt免费）
2. 配置Nginx支持HTTPS
3. 域名需要备案（国内服务器）

---

## 📝 开发调试技巧

### 1. 本地调试

使用 **ngrok** 或 **frp** 进行内网穿透：

```bash
# 使用ngrok
ngrok http 8000

# 然后在飞书后台配置回调地址：
# https://xxxx-xx-xx-xx-xx.ngrok-free.app/api/v1/feishu/webhook
```

### 2. 测试OAuth登录

使用飞书开放平台提供的 **API调试台** 进行测试：
1. 访问 https://open.feishu.cn/api-explorer
2. 选择相应的API
3. 使用你的应用进行调试

### 3. 查看机器人日志

建议记录所有飞书交互：

```python
import logging
logger = logging.getLogger(__name__)

# 在关键位置添加日志
logger.info(f"发送消息给: {user_id}, 内容: {content}")
logger.debug(f"事件回调: {event_type}, 数据: {event_data}")
```

---

## 🚀 快速部署检查清单

- [ ] 飞书应用已创建
- [ ] 权限已配置
- [ ] OAuth回调地址已添加
- [ ] Webhook地址已配置
- [ ] 环境变量已设置
- [ ] 服务器已支持HTTPS
- [ ] 网络连通性已验证
- [ ] 登录流程已测试
- [ ] 机器人消息已测试
- [ ] 事件回调已测试

---

## 📚 参考资料

- [飞书开放平台文档](https://open.feishu.cn/document)
- [飞书机器人开发指南](https://open.feishu.cn/document/uAjLw4CM/uYjLw4CN)
- [飞书卡片设计规范](https://open.feishu.cn/document/uAjLw4CM/ukzMwUzL2MjL1M1)
- [飞书API调试台](https://open.feishu.cn/api-explorer)
