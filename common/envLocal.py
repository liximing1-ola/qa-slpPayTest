# coding=utf-8
"""本机环境配置读取：内网地址、账号、节点标识一律不进仓库

取值顺序：环境变量（同名）> common/env_local.py > None
env_local.py 在 .gitignore 里，首次部署时按 env_local.example.py 复制并填值。

这里刻意不抛异常：连不上库应该在 preflight 里报成「环境不通」，而不是让 import
阶段直接崩掉——那样连一句可读的原因都拿不到，只剩一屏 traceback。
"""

import os

try:
    from common import env_local as _local
except ImportError:  # 还没建 env_local.py，走占位值 + preflight 提示
    _local = None

# preflight 用这几项判断「配置齐不齐」，缺了就直说缺什么，不必一条条去试连接
REQUIRED = ('DB_HOST', 'DB_USER', 'DB_PASS', 'REDIS_HOST', 'APP_HOST')


def get(name):
    """先环境变量（同名），再 env_local.py 里的同名常量，都没有返回 None"""
    value = os.environ.get(name)
    if value:
        return value
    return getattr(_local, name, None) if _local else None


def missing():
    """哪几项没配置：返回名称列表，全齐则返回空列表"""
    return [name for name in REQUIRED if not get(name)]
