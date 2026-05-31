# 飞书权限配置指南

## 文档概述

本文档详细说明域名管家系统与飞书集成的权限配置，分为三个层面：
1. **飞书应用权限** - 必须在飞书开放平台人工配置
2. **用户角色权限** - 通过数据库或脚本管理
3. **命令级权限** - 代码内置，无需配置

---

## 一、飞书应用权限配置（人工配置）

### 1.1 创建飞书应用

#### 步骤1：登录飞书开放平台

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 使用企业管理员账号登录
3. 点击「创建企业自建应用」

#### 步骤2：填写应用信息

```yaml
应用名称：域名管家
应用描述：企业级域名管理系统，支持域名注册、解析、续费等
应用图标：上传图标（建议 256x256 PNG）
```

#### 步骤3：获取应用凭证

创建应用后，在「凭证与基础信息」页面获取：

```yaml
App ID: cli_xxxxxxxxxxxxxxxx
App Secret: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

这两个凭证需要配置到系统的环境变量中：

```bash
# .env 文件
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 1.2 权限配置

在应用管理页面，点击「权限管理」→ 「开启权限」

#### 必须配置的权限

```yaml
权限列表：

# 1. 用户信息权限
- 获取用户基本信息 (contact:user.base:readonly)
  说明：识别用户身份，用于权限验证
  
- 获取用户手机号 (contact:user.phone:readonly)
  说明：用于联系方式绑定

# 2. 即时通讯权限
- 获取与发送单聊、群组消息 (im:message)
  说明：机器人发送通知和交互卡片
  
- 接收消息 (im:message:receive_v1)
  说明：接收用户发送的命令

# 3. 群组权限（可选）
- 获取群组信息 (im:chat:readonly)
  说明：如果需要在群组中使用机器人
  
- 获取群组成员 (im:chat.member:readonly)
  说明：群组命令支持
```

#### 权限配置截图指引

```
飞书开放平台 → 域名管家应用 → 权限管理
  └── 开启权限
      ├── 通讯录
      │   ├── ✅ 获取用户基本信息
      │   └── ✅ 获取用户手机号
      ├── 即时通讯
      │   ├── ✅ 发送消息
      │   └── ✅ 接收消息
      └── 群组（可选）
          ├── ✅ 获取群组信息
          └── ✅ 获取群组成员
```

---

### 1.3 配置机器人

#### 步骤1：开启机器人能力

1. 在应用管理页面，点击「添加应用能力」
2. 选择「机器人」
3. 点击「开启」

#### 步骤2：配置消息接收

1. 点击「事件订阅」
2. 配置请求地址：`https://yourcompany.com/domainmgr/api/feishu/webhook`
3. 开启「使用长连接接收事件」或配置公网回调地址

#### 步骤3：机器人配置

```yaml
机器人配置：
- 机器人名称：域名管家
- 机器人描述：企业域名管理助手
- 可处理消息类型：
  - ✅ 文本消息
  - ✅ 卡片消息
  - ✅ @机器人消息
```

---

### 1.4 配置可用范围

在「版本管理与发布」页面，配置应用可用范围

#### 方式一：指定部门和人员

```yaml
可用范围：
├── 研发部
│   ├── 张三
│   ├── 李四
│   └── 王五
├── 市场部
│   └── 赵六
└── 产品部
    └── 钱七
```

#### 方式二：全员可用

```yaml
可用范围：全体员工
说明：所有人可以使用机器人，但只有配置了角色的用户才能执行特定命令
```

#### 重要说明

```
⚠️ 注意：
1. 只有在可用范围内的用户才能与机器人交互
2. 具体功能权限由系统内部的用户角色控制
3. 建议初始阶段指定关键人员，后续再扩大范围
```

---

### 1.5 配置事件订阅

#### 需要订阅的事件

```yaml
事件订阅：

# 1. 接收消息事件
- im.message.receive_v1
  说明：接收用户发送给机器人的消息
  订阅方式：长连接或公网回调

# 2. 卡片点击事件（可选）
- im.message.card.action.trigger
  说明：接收交互卡片的按钮点击事件
```

#### Webhook配置

```
URL 配置：
https://yourcompany.com/domainmgr/api/feishu/webhook

加密配置：
- 开启签名校验
- 填写 Verification Token
- 填写 Encrypt Key（可选）
```

---

### 1.6 应用发布

#### 发布前检查清单

```markdown
发布前检查：
- [ ] 应用信息已填写完整
- [ ] 权限已申请并审批通过
- [ ] 机器人能力已开启
- [ ] 消息接收地址已配置
- [ ] 可用范围已设置
- [ ] 已在测试环境验证功能
```

#### 发布流程

```
1. 创建版本
   - 版本号：v1.0.0
   - 版本说明：初始版本
   
2. 提交审核
   - 审核通过后自动发布
   - 或选择手动发布
   
3. 版本管理
   - 维护多个版本
   - 支持回滚
```

---

## 二、飞书API配置

### 2.1 获取访问令牌

```python
# services/feishu_auth.py
import requests
from typing import Optional

class FeishuAuth:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn"
    
    def get_app_access_token(self) -> str:
        """
        获取应用访问令牌
        用于调用飞书开放API
        """
        url = f"{self.base_url}/open-apis/auth/v3/app_access_token/internal"
        
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取访问令牌失败: {data}")
        
        return data["app_access_token"]
    
    def get_tenant_access_token(self, code: str) -> dict:
        """
        获取tenant访问令牌
        用于用户身份验证
        """
        url = f"{self.base_url}/open-apis/authen/v1/oidc/access_token"
        
        headers = {
            "Authorization": f"Bearer {self.get_app_access_token()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "grant_type": "authorization_code",
            "code": code
        }
        
        response = requests.post(url, headers=headers, json=payload)
        return response.json()
```

### 2.2 发送消息

```python
# services/feishu_message.py
import requests
from typing import List, Union

class FeishuMessage:
    def __init__(self, app_id: str, app_secret: str):
        self.auth = FeishuAuth(app_id, app_secret)
        self.base_url = "https://open.feishu.cn"
    
    def send_text(self, receive_id_type: str, receive_id: str, content: str) -> dict:
        """
        发送文本消息
        
        Args:
            receive_id_type: 接收者类型 (open_id/user_id/union_id/email/chat_id)
            receive_id: 接收者ID
            content: 消息内容
        """
        url = f"{self.base_url}/open-apis/im/v1/messages"
        
        params = {
            "receive_id_type": receive_id_type
        }
        
        headers = {
            "Authorization": f"Bearer {self.auth.get_app_access_token()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }
        
        response = requests.post(url, headers=headers, params=params, json=payload)
        return response.json()
    
    def send_card(self, receive_id_type: str, receive_id: str, card_content: dict) -> dict:
        """
        发送交互卡片
        
        Args:
            receive_id_type: 接收者类型
            receive_id: 接收者ID
            card_content: 卡片内容 (JSON格式)
        """
        url = f"{self.base_url}/open-apis/im/v1/messages"
        
        params = {
            "receive_id_type": receive_id_type
        }
        
        headers = {
            "Authorization": f"Bearer {self.auth.get_app_access_token()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }
        
        response = requests.post(url, headers=headers, params=params, json=payload)
        return response.json()
```

---

## 三、用户角色权限配置

### 3.1 角色定义

| 角色代码 | 角色名称 | 说明 | 飞书权限 |
|---------|---------|------|----------|
| `business` | 业务同事 | 普通业务人员 | 仅可提交申请 |
| `domain_spec` | 域名专员 | 负责域名管理 | 可审批、可注册/续费 |
| `admin` | 系统管理员 | 最高权限 | 全部功能 |

### 3.2 权限矩阵

```python
# models/permission.py

ROLE_PERMISSIONS = {
    "business": {
        "name": "业务同事",
        "description": "普通业务人员，可提交域名申请",
        
        # 申请权限
        "can_submit_register": True,      # 可提交注册申请
        "can_submit_dns": True,           # 可提交DNS解析申请
        
        # 操作权限
        "can_direct_register": False,     # ❌ 不可直接注册
        "can_renew": False,               # ❌ 不可续费
        "can_approve": False,             # ❌ 不可审批
        
        # 查询权限
        "can_query_availability": False,  # ❌ 不可查询可用性
        "can_query_info": False,          # ❌ 不可查询域名信息
        
        # 配置权限
        "can_config_accounts": False,     # ❌ 不可配置账号
        "can_manage_users": False,        # ❌ 不可管理用户
        
        # Web权限
        "web_access": False,              # ❌ 无Web访问权限
    },
    
    "domain_spec": {
        "name": "域名专员",
        "description": "负责域名管理的高级用户",
        
        # 申请权限
        "can_submit_register": True,
        "can_submit_dns": True,
        
        # 操作权限
        "can_direct_register": True,      # ✅ 可直接注册
        "can_renew": True,                # ✅ 可续费
        "can_approve": True,             # ✅ 可审批
        
        # 查询权限
        "can_query_availability": True,   # ✅ 可查询可用性
        "can_query_info": True,           # ✅ 可查询域名信息
        
        # 配置权限
        "can_config_accounts": False,
        "can_manage_users": False,
        
        # Web权限
        "web_access": True,
        "web_read_only": False,
    },
    
    "admin": {
        "name": "系统管理员",
        "description": "最高权限管理员",
        
        # 申请权限
        "can_submit_register": True,
        "can_submit_dns": True,
        
        # 操作权限
        "can_direct_register": True,
        "can_renew": True,
        "can_approve": True,
        
        # 查询权限
        "can_query_availability": True,
        "can_query_info": True,
        
        # 配置权限
        "can_config_accounts": True,      # ✅ 可配置账号
        "can_manage_users": True,         # ✅ 可管理用户
        
        # Web权限
        "web_access": True,
        "web_read_only": False,
    }
}
```

### 3.3 用户表结构

```python
# models/user.py
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="用户姓名")
    
    # 飞书身份
    feishu_userid = Column(String(100), nullable=False, unique=True, comment="飞书用户ID")
    feishu_unionid = Column(String(100), nullable=True, comment="飞书UnionID")
    feishu_openid = Column(String(100), nullable=True, comment="飞书OpenID")
    
    # 角色配置
    role = Column(String(20), nullable=False, default="business", comment="用户角色")
    permissions = Column(JSON, default=list, comment="自定义权限列表")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 备注
    email = Column(String(255), nullable=True, comment="邮箱")
    phone = Column(String(50), nullable=True, comment="手机号")
    department = Column(String(100), nullable=True, comment="部门")
    remark = Column(String(500), nullable=True, comment="备注")
```

### 3.4 用户管理脚本

#### 创建用户管理脚本

```python
#!/usr/bin/env python3
"""
域名管家 - 用户管理脚本
用于管理用户的飞书身份和角色权限
"""

import argparse
import sys
import csv
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.user import User
from models.permission import ROLE_PERMISSIONS

class UserManagement:
    def __init__(self, db_path: str):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def add_user(self, feishu_userid: str, name: str, role: str, **kwargs):
        """
        添加新用户
        
        Args:
            feishu_userid: 飞书用户ID (必需)
            name: 用户姓名 (必需)
            role: 角色 (必需)
            email: 邮箱 (可选)
            phone: 手机号 (可选)
            department: 部门 (可选)
        """
        # 检查用户是否已存在
        existing = self.session.query(User).filter_by(
            feishu_userid=feishu_userid
        ).first()
        
        if existing:
            print(f"❌ 用户已存在：{feishu_userid}")
            return False
        
        # 验证角色
        if role not in ROLE_PERMISSIONS:
            print(f"❌ 无效的角色：{role}")
            print(f"可用角色：{', '.join(ROLE_PERMISSIONS.keys())}")
            return False
        
        # 创建用户
        user = User(
            feishu_userid=feishu_userid,
            name=name,
            role=role,
            permissions=list(ROLE_PERMISSIONS[role].keys()),
            is_active=True,
            email=kwargs.get('email'),
            phone=kwargs.get('phone'),
            department=kwargs.get('department')
        )
        
        self.session.add(user)
        self.session.commit()
        
        print(f"✅ 用户添加成功")
        print(f"   飞书ID：{feishu_userid}")
        print(f"   姓名：{name}")
        print(f"   角色：{role}")
        print(f"   权限：{', '.join(user.permissions)}")
        
        return True
    
    def batch_import(self, csv_file: str):
        """
        从CSV文件批量导入用户
        
        CSV格式：
        feishu_userid,name,role,email,phone,department
        ou_xxx,张三,business,zs@example.com,13800138000,研发部
        """
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                success_count = 0
                fail_count = 0
                errors = []
                
                for row in reader:
                    result = self.add_user(
                        feishu_userid=row['feishu_userid'],
                        name=row['name'],
                        role=row['role'],
                        email=row.get('email'),
                        phone=row.get('phone'),
                        department=row.get('department')
                    )
                    
                    if result:
                        success_count += 1
                    else:
                        fail_count += 1
                        errors.append(f"{row['feishu_userid']} - {row['name']}")
                
                print(f"\n📊 导入完成")
                print(f"   成功：{success_count}")
                print(f"   失败：{fail_count}")
                
                if errors:
                    print(f"\n失败列表：")
                    for error in errors:
                        print(f"   - {error}")
                        
        except FileNotFoundError:
            print(f"❌ 文件不存在：{csv_file}")
        except Exception as e:
            print(f"❌ 导入失败：{e}")
    
    def update_role(self, feishu_userid: str, new_role: str):
        """
        更新用户角色
        """
        user = self.session.query(User).filter_by(
            feishu_userid=feishu_userid
        ).first()
        
        if not user:
            print(f"❌ 用户不存在：{feishu_userid}")
            return False
        
        if new_role not in ROLE_PERMISSIONS:
            print(f"❌ 无效的角色：{new_role}")
            return False
        
        old_role = user.role
        user.role = new_role
        user.permissions = list(ROLE_PERMISSIONS[new_role].keys())
        self.session.commit()
        
        print(f"✅ 角色更新成功")
        print(f"   用户：{user.name}")
        print(f"   原角色：{old_role}")
        print(f"   新角色：{new_role}")
        print(f"   新权限：{', '.join(user.permissions)}")
        
        return True
    
    def disable_user(self, feishu_userid: str):
        """
        禁用用户
        """
        user = self.session.query(User).filter_by(
            feishu_userid=feishu_userid
        ).first()
        
        if not user:
            print(f"❌ 用户不存在：{feishu_userid}")
            return False
        
        user.is_active = False
        self.session.commit()
        
        print(f"✅ 用户已禁用：{user.name} ({feishu_userid})")
        return True
    
    def enable_user(self, feishu_userid: str):
        """
        启用用户
        """
        user = self.session.query(User).filter_by(
            feishu_userid=feishu_userid
        ).first()
        
        if not user:
            print(f"❌ 用户不存在：{feishu_userid}")
            return False
        
        user.is_active = True
        self.session.commit()
        
        print(f"✅ 用户已启用：{user.name} ({feishu_userid})")
        return True
    
    def delete_user(self, feishu_userid: str):
        """
        删除用户（谨慎使用）
        """
        user = self.session.query(User).filter_by(
            feishu_userid=feishu_userid
        ).first()
        
        if not user:
            print(f"❌ 用户不存在：{feishu_userid}")
            return False
        
        user_name = user.name
        self.session.delete(user)
        self.session.commit()
        
        print(f"✅ 用户已删除：{user_name} ({feishu_userid})")
        return True
    
    def list_users(self, role: str = None, active_only: bool = False):
        """
        列出用户
        """
        query = self.session.query(User)
        
        if role:
            query = query.filter_by(role=role)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        users = query.all()
        
        print(f"\n{'='*80}")
        print(f"{'飞书ID':<25} {'姓名':<12} {'角色':<12} {'部门':<15} {'状态':<8}")
        print(f"{'='*80}")
        
        for user in users:
            status = "✅ 启用" if user.is_active else "❌ 禁用"
            role_name = ROLE_PERMISSIONS.get(user.role, {}).get('name', user.role)
            dept = user.department or '-'
            
            print(f"{user.feishu_userid:<25} {user.name:<12} {role_name:<12} {dept:<15} {status:<8}")
        
        print(f"{'='*80}")
        print(f"总计：{len(users)} 个用户")
    
    def show_user(self, feishu_userid: str):
        """
        显示用户详情
        """
        user = self.session.query(User).filter_by(
            feishu_userid=feishu_userid
        ).first()
        
        if not user:
            print(f"❌ 用户不存在：{feishu_userid}")
            return
        
        role_info = ROLE_PERMISSIONS.get(user.role, {})
        
        print(f"\n{'='*60}")
        print(f"用户详情")
        print(f"{'='*60}")
        print(f"飞书ID：{user.feishu_userid}")
        print(f"姓名：{user.name}")
        print(f"角色：{role_info.get('name', user.role)} ({user.role})")
        print(f"部门：{user.department or '-'}")
        print(f"邮箱：{user.email or '-'}")
        print(f"手机：{user.phone or '-'}")
        print(f"状态：{'启用' if user.is_active else '禁用'}")
        print(f"创建时间：{user.created_at}")
        print(f"更新时间：{user.updated_at}")
        print(f"\n权限列表：")
        for perm, has_perm in role_info.items():
            if isinstance(has_perm, bool):
                status = "✅" if has_perm else "❌"
                print(f"  {status} {perm}")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='域名管家用户管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 添加用户
  python manage_users.py add --userid "ou_xxx" --name "张三" --role domain_spec
  
  # 批量导入
  python manage_users.py import --file users.csv
  
  # 更新角色
  python manage_users.py update --userid "ou_xxx" --role admin
  
  # 禁用用户
  python manage_users.py disable --userid "ou_xxx"
  
  # 列出所有用户
  python manage_users.py list
  
  # 列出域名专员
  python manage_users.py list --role domain_spec
  
  # 显示用户详情
  python manage_users.py show --userid "ou_xxx"
        """
    )
    
    parser.add_argument('--db', default='data/domainmgr.db', help='数据库路径')
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 添加用户
    add_parser = subparsers.add_parser('add', help='添加用户')
    add_parser.add_argument('--userid', required=True, help='飞书用户ID (ou_xxx)')
    add_parser.add_argument('--name', required=True, help='用户姓名')
    add_parser.add_argument('--role', required=True, 
                            choices=['business', 'domain_spec', 'admin'],
                            help='用户角色')
    add_parser.add_argument('--email', help='邮箱')
    add_parser.add_argument('--phone', help='手机号')
    add_parser.add_argument('--department', help='部门')
    
    # 批量导入
    import_parser = subparsers.add_parser('import', help='批量导入用户')
    import_parser.add_argument('--file', required=True, help='CSV文件路径')
    
    # 更新角色
    update_parser = subparsers.add_parser('update', help='更新用户角色')
    update_parser.add_argument('--userid', required=True, help='飞书用户ID')
    update_parser.add_argument('--role', required=True,
                              choices=['business', 'domain_spec', 'admin'],
                              help='新角色')
    
    # 禁用用户
    disable_parser = subparsers.add_parser('disable', help='禁用用户')
    disable_parser.add_argument('--userid', required=True, help='飞书用户ID')
    
    # 启用用户
    enable_parser = subparsers.add_parser('enable', help='启用用户')
    enable_parser.add_argument('--userid', required=True, help='飞书用户ID')
    
    # 删除用户
    delete_parser = subparsers.add_parser('delete', help='删除用户')
    delete_parser.add_argument('--userid', required=True, help='飞书用户ID')
    
    # 列出用户
    list_parser = subparsers.add_parser('list', help='列出用户')
    list_parser.add_argument('--role', choices=['business', 'domain_spec', 'admin'],
                            help='筛选角色')
    list_parser.add_argument('--active-only', action='store_true',
                            help='仅显示启用用户')
    
    # 显示详情
    show_parser = subparsers.add_parser('show', help='显示用户详情')
    show_parser.add_argument('--userid', required=True, help='飞书用户ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    cli = UserManagement(args.db)
    
    if args.command == 'add':
        cli.add_user(
            feishu_userid=args.userid,
            name=args.name,
            role=args.role,
            email=args.email,
            phone=args.phone,
            department=args.department
        )
    elif args.command == 'import':
        cli.batch_import(args.file)
    elif args.command == 'update':
        cli.update_role(args.userid, args.role)
    elif args.command == 'disable':
        cli.disable_user(args.userid)
    elif args.command == 'enable':
        cli.enable_user(args.userid)
    elif args.command == 'delete':
        cli.delete_user(args.userid)
    elif args.command == 'list':
        cli.list_users(role=args.role, active_only=args.active_only)
    elif args.command == 'show':
        cli.show_user(args.userid)


if __name__ == '__main__':
    main()
```

#### 使用示例

```bash
# 1. 添加域名专员
python manage_users.py add \
  --db data/domainmgr.db \
  --userid "ou_xxxxx" \
  --name "张三" \
  --role domain_spec \
  --department "研发部"

# 2. 添加管理员
python manage_users.py add \
  --db data/domainmgr.db \
  --userid "ou_yyyyy" \
  --name "李四" \
  --role admin \
  --email "lisi@company.com"

# 3. 批量导入用户
python manage_users.py import \
  --db data/domainmgr.db \
  --file users.csv

# 4. 更新用户角色
python manage_users.py update \
  --db data/domainmgr.db \
  --userid "ou_xxxxx" \
  --role admin

# 5. 禁用离职员工
python manage_users.py disable \
  --db data/domainmgr.db \
  --userid "ou_xxxxx"

# 6. 列出所有域名专员
python manage_users.py list \
  --db data/domainmgr.db \
  --role domain_spec

# 7. 查看用户详情
python manage_users.py show \
  --db data/domainmgr.db \
  --userid "ou_xxxxx"
```

#### CSV导入模板

```csv
# users.csv
feishu_userid,name,role,email,phone,department
ou_1234567890,张三,domain_spec,zhangsan@company.com,13800138000,研发部
ou_0987654321,李四,admin,lisi@company.com,13800138001,IT部
ou_5555555555,王五,business,wangwu@company.com,13800138002,市场部
ou_6666666666,赵六,domain_spec,zhaoliu@company.com,13800138003,产品部
```

---

## 四、命令级权限配置

### 4.1 飞书命令权限表

```python
# bot/command_permissions.py

"""
飞书机器人命令权限映射
定义每个命令需要的权限
"""

COMMAND_PERMISSIONS = {
    # ===== 查询命令 =====
    "帮助": {
        "permissions": [],
        "description": "显示帮助信息",
        "all_roles": True  # 所有角色可用
    },
    
    "状态": {
        "permissions": [],
        "description": "查看系统状态",
        "all_roles": True
    },
    
    "我的申请": {
        "permissions": [],
        "description": "查看我的申请记录",
        "all_roles": True
    },
    
    "查询": {
        "permissions": ["can_query_availability"],
        "description": "查询域名可注册性",
        "roles": ["domain_spec", "admin"]
    },
    
    "域名信息": {
        "permissions": ["can_query_info"],
        "description": "查询域名详细信息",
        "roles": ["domain_spec", "admin"]
    },
    
    # ===== 注册命令 =====
    "注册": {
        "permissions": ["can_direct_register"],
        "description": "直接注册域名",
        "roles": ["domain_spec", "admin"]
    },
    
    "立即注册": {
        "permissions": ["can_direct_register"],
        "description": "直接注册域名（别名）",
        "roles": ["domain_spec", "admin"]
    },
    
    # ===== 续费命令 =====
    "续费": {
        "permissions": ["can_renew"],
        "description": "为域名续费",
        "roles": ["domain_spec", "admin"]
    },
    
    "域名续费": {
        "permissions": ["can_renew"],
        "description": "为域名续费（别名）",
        "roles": ["domain_spec", "admin"]
    },
    
    # ===== 审批命令 =====
    "审批": {
        "permissions": ["can_approve"],
        "description": "审批申请",
        "roles": ["domain_spec", "admin"]
    },
    
    "通过": {
        "permissions": ["can_approve"],
        "description": "通过申请",
        "roles": ["domain_spec", "admin"]
    },
    
    "拒绝": {
        "permissions": ["can_approve"],
        "description": "拒绝申请",
        "roles": ["domain_spec", "admin"]
    },
    
    # ===== 配置命令（仅管理员）=====
    "配置账号": {
        "permissions": ["can_config_accounts"],
        "description": "配置注册/解析账号",
        "roles": ["admin"]
    },
    
    "添加注册商": {
        "permissions": ["can_config_accounts"],
        "description": "添加注册商",
        "roles": ["admin"]
    },
    
    "系统设置": {
        "permissions": ["can_config_accounts"],
        "description": "系统设置",
        "roles": ["admin"]
    },
    
    # ===== 用户管理命令（仅管理员）=====
    "添加用户": {
        "permissions": ["can_manage_users"],
        "description": "添加系统用户",
        "roles": ["admin"]
    },
    
    "用户列表": {
        "permissions": ["can_manage_users"],
        "description": "查看用户列表",
        "roles": ["admin"]
    }
}
```

### 4.2 权限检查实现

```python
# bot/permission_checker.py

from functools import wraps
from typing import List, Optional

class PermissionChecker:
    def __init__(self, user_service):
        self.user_service = user_service
    
    def check_permission(self, user, permission: str) -> bool:
        """
        检查用户是否有指定权限
        """
        if not user or not user.is_active:
            return False
        
        # 如果用户有自定义权限列表
        if user.permissions:
            return permission in user.permissions
        
        # 否则从角色权限中获取
        from models.permission import ROLE_PERMISSIONS
        role_perms = ROLE_PERMISSIONS.get(user.role, {})
        return role_perms.get(permission, False)
    
    def check_command_permission(self, user, command: str) -> tuple:
        """
        检查用户是否有执行命令的权限
        
        Returns:
            (has_permission: bool, error_message: str)
        """
        if not user or not user.is_active:
            return False, "用户状态异常，请联系管理员"
        
        # 获取命令权限配置
        cmd_config = COMMAND_PERMISSIONS.get(command)
        
        if not cmd_config:
            return False, f"未知命令：{command}"
        
        # 检查是否所有角色可用
        if cmd_config.get('all_roles'):
            return True, ""
        
        # 检查角色是否允许
        allowed_roles = cmd_config.get('roles', [])
        if user.role not in allowed_roles:
            return False, f"您的角色（{user.role}）无权执行此命令"
        
        # 检查具体权限
        required_perms = cmd_config.get('permissions', [])
        for perm in required_perms:
            if not self.check_permission(user, perm):
                return False, f"您没有执行此操作的权限"
        
        return True, ""
    
    def require_command_permission(self, command: str):
        """
        命令权限装饰器
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(message, user, *args, **kwargs):
                # 检查权限
                has_perm, error_msg = self.check_command_permission(user, command)
                
                if not has_perm:
                    await message.reply(error_msg)
                    return False
                
                # 权限检查通过，执行命令
                return await func(message, user, *args, **kwargs)
            
            return wrapper
        return decorator


# 使用示例
permission_checker = PermissionChecker(user_service)

@permission_checker.require_command_permission("注册")
async def cmd_register(message, user, *args):
    """注册域名命令"""
    # 命令实现
    pass
```

---

## 五、完整配置检查清单

### 5.1 飞书开放平台配置

```markdown
## 飞书开放平台配置检查清单

### 1. 应用基础信息
- [ ] 已创建应用
- [ ] 应用名称：域名管家
- [ ] 应用描述已填写
- [ ] 应用图标已上传

### 2. 应用凭证
- [ ] App ID 已获取
- [ ] App Secret 已获取
- [ ] 凭证已配置到环境变量

### 3. 权限配置
- [ ] 获取用户基本信息 ✅
- [ ] 获取用户手机号 ✅
- [ ] 发送消息 ✅
- [ ] 接收消息 ✅
- [ ] 权限已审批通过

### 4. 机器人配置
- [ ] 机器人能力已开启
- [ ] 消息接收地址已配置
- [ ] 事件订阅已配置

### 5. 可用范围
- [ ] 已设置可用人员/部门
- [ ] 或设置为全员可用

### 6. 应用发布
- [ ] 已创建版本
- [ ] 版本已发布
```

### 5.2 用户权限配置

```markdown
## 用户权限配置检查清单

### 1. 初始化用户
- [ ] 已添加系统管理员
- [ ] 已添加域名专员
- [ ] 已配置业务同事（如需要）

### 2. 角色验证
- [ ] 管理员可执行所有管理命令
- [ ] 域名专员可执行注册/续费命令
- [ ] 业务同事只能提交申请

### 3. 功能测试
- [ ] 管理员登录测试
- [ ] 域名专员注册测试
- [ ] 域名专员续费测试
- [ ] 权限拒绝测试
```

### 5.3 环境变量配置

```bash
# .env 文件配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_ENCRYPT_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 六、故障排查

### 6.1 常见问题

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 机器人无响应 | 用户不在可用范围内 | 在飞书管理后台添加用户到可用范围 |
| 权限不足 | 用户角色不正确 | 使用脚本更新用户角色 |
| 消息发送失败 | 应用权限未审批 | 在飞书开放平台审批权限 |
| 消息接收失败 | Webhook地址错误 | 检查回调地址配置 |
| 用户不存在 | 未添加到数据库 | 使用脚本添加用户 |

### 6.2 诊断命令

```bash
# 1. 检查用户是否在数据库中
python manage_users.py show --userid "ou_xxx"

# 2. 检查用户权限
python manage_users.py list --role domain_spec

# 3. 测试飞书连接
curl -X POST "https://yourcompany.com/domainmgr/api/feishu/webhook" \
  -H "Content-Type: application/json" \
  -d '{"type": "url_verification", "token": "xxx", "challenge": "xxx"}'
```

---

## 七、安全建议

### 7.1 权限最小化原则

```
建议：
1. 仅给需要的人员开通域名管家
2. 域名专员数量不宜过多
3. 管理员账号专人专用
4. 定期审查用户权限
```

### 7.2 操作审计

```markdown
审计日志包含：
- 操作人（姓名、飞书ID）
- 操作时间
- 操作类型（注册/续费/审批）
- 操作域名
- 操作结果
- IP地址
- User Agent
```

### 7.3 敏感操作通知

```markdown
建议配置通知：
- 新用户添加 → 通知管理员
- 角色变更 → 通知当事人和管理员
- 大额操作（注册/续费）→ 通知管理员
```

---

## 八、联系方式

如有问题，请联系：
- 飞书群：域名管家技术支持
- 邮箱：domain-support@company.com
