# coding=utf-8
"""本机环境配置模板：复制成 common/env_local.py 后填真实值

    cp common/env_local.example.py common/env_local.py

env_local.py 已在 .gitignore 里，不会被提交，也不会出现在 git 历史中。
文件名必须是 env_local.py（带下划线）：带点的 env.local.py 在 Python 里根本 import 不了。

不改文件也行：直接用同名环境变量覆盖，优先级高于本文件。
比如 crontab 里 export DB_HOST=... 就够了，机器上什么都不用建。
"""

DB_HOST = '<测试库地址>'
DB_USER = '<数据库账号>'
DB_PASS = '<数据库密码>'

REDIS_HOST = '<Redis 地址>'
REDIS_PORT = 6379

# 末尾的 / 可以省略，代码会补齐
APP_HOST = 'https://<测试环境域名>'

# 测试机标识（hostname 或云主机实例 ID），用于判断「是否同机房」以决定断言前要不要等
NODE_ALI = '<主测试机标识>'
NODE_ALI_SLP = '<SLP 测试机标识>'
NODE_ALI_XSG = '<XSG 测试机标识>'
