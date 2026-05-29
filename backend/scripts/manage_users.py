#!/usr/bin/env python3
"""
域名管家 - 用户管理脚本
用于管理用户的飞书身份和角色权限

使用方法：
    python manage_users.py add --userid "ou_xxx" --name "张三" --role domain_spec
    python manage_users.py import --file users.csv
    python manage_users.py list --role domain_spec
    python manage_users.py show --userid "ou_xxx"
"""

import argparse
import sys
import os
import csv

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.permission import ROLE_PERMISSIONS


class UserManagement:
    def __init__(self):
        """初始化数据库连接"""
        self.session = SessionLocal()

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
        print(f"   角色：{ROLE_PERMISSIONS[role]['name']}")
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
        """更新用户角色"""
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
        old_role_name = ROLE_PERMISSIONS.get(old_role, {}).get('name', old_role)
        new_role_name = ROLE_PERMISSIONS[new_role]['name']

        user.role = new_role
        user.permissions = list(ROLE_PERMISSIONS[new_role].keys())
        self.session.commit()

        print(f"✅ 角色更新成功")
        print(f"   用户：{user.name}")
        print(f"   原角色：{old_role_name} ({old_role})")
        print(f"   新角色：{new_role_name} ({new_role})")
        print(f"   新权限：{', '.join(user.permissions)}")

        return True

    def disable_user(self, feishu_userid: str):
        """禁用用户"""
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
        """启用用户"""
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
        """删除用户（谨慎使用）"""
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
        """列出用户"""
        query = self.session.query(User)

        if role:
            query = query.filter_by(role=role)

        if active_only:
            query = query.filter_by(is_active=True)

        users = query.all()

        print(f"\n{'='*80}")
        print(f"{'飞书ID':<25} {'姓名':<12} {'角色':<15} {'部门':<15} {'状态':<8}")
        print(f"{'='*80}")

        for user in users:
            status = "✅ 启用" if user.is_active else "❌ 禁用"
            role_name = ROLE_PERMISSIONS.get(user.role, {}).get('name', user.role)
            dept = user.department or '-'

            print(f"{user.feishu_userid:<25} {user.name:<12} {role_name:<15} {dept:<15} {status:<8}")

        print(f"{'='*80}")
        print(f"总计：{len(users)} 个用户")

    def show_user(self, feishu_userid: str):
        """显示用户详情"""
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
    try:
        cli = UserManagement()

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
    except Exception as e:
        print(f"❌ 执行失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
