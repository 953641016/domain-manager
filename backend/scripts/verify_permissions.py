"""权限矩阵自检脚本"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app.main  # noqa – ensure all routes loaded
from app.models.permission import ROLE_PERMISSIONS, has_permission
from app.models.user_confirmation import ConfirmationOperationType

# 期望的权限矩阵（role, permission, expected）
CASES = [
    # admin 无业务/账号权限
    ("admin", "can_manage_accounts",  False),
    ("admin", "can_view_accounts",    False),
    ("admin", "can_manage_providers", False),
    ("admin", "can_approve_request",  False),
    ("admin", "can_direct_register",  False),
    ("admin", "can_submit_request",   False),
    ("admin", "can_view_domains",     False),
    ("admin", "can_manage_users",     True),   # admin 可管人
    # domain_spec 无人员权限
    ("domain_spec", "can_manage_accounts",  True),
    ("domain_spec", "can_approve_request",  True),
    ("domain_spec", "can_manage_users",     False),
    ("domain_spec", "can_view_users",       False),
    # business 无 web 访问
    ("business", "web_access",          False),
    ("business", "can_submit_request",  True),
    ("business", "can_direct_register", False),
    # super_admin 全权
    ("super_admin", "can_manage_accounts",  True),
    ("super_admin", "can_manage_users",     True),
    ("super_admin", "can_direct_register",  True),
    ("super_admin", "web_access",           True),
]

print("=== 权限矩阵自检 ===")
all_pass = True
for role, perm, expected in CASES:
    actual = has_permission(role, perm)
    ok = actual == expected
    status = "OK  " if ok else "FAIL"
    print(f"  {status} {role}.{perm} = {actual} (expect {expected})")
    if not ok:
        all_pass = False

print()
print("=== 服务商操作类型 ===")
for op in ["add_provider", "update_provider", "delete_provider"]:
    exists = any(e.value == op for e in ConfirmationOperationType)
    print(f"  {'OK  ' if exists else 'MISS'} {op}")

print()
print("ALL PASS" if all_pass else "SOME CHECKS FAILED")
sys.exit(0 if all_pass else 1)
