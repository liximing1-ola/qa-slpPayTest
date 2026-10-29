# coding=utf-8
"""把改造前硬编码在源码里的环境配置搬回本机：生成 common/env_local.py

凭据与环境信息现在一律走 common/envLocal.get()，源码里只剩占位。这个脚本从改造前
的历史提交里把当时的字面量取出来，写成 common/env_local.py——用于「本机连不到内网、
又没法从别处拷文件」的场景（开发机不在测试内网，scp 到测试机会超时）。

**这不是推荐做法**：正常情况下这份配置该由知情人提供。之所以从历史里取，是因为
这些值本来就硬编码在旧版本里、历史删不掉，取出来只是搬个家，没有新增暴露面。

生成的文件在 .gitignore 内，不会被提交。已存在时默认不覆盖，要覆盖加 --force。
"""
import argparse
import ast
import os
import subprocess
import sys

DEFAULT_REV = '5e4786d'
REQUIRED = ('DB_HOST', 'DB_USER', 'DB_PASS', 'REDIS_HOST', 'APP_HOST')
TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'common', 'env_local.py')

TEMPLATE = '''# coding=utf-8
"""本机环境配置：.gitignore 内，不进仓库

字段与 common/env_local.example.py 对应，值由 bootstrap_env.py 从历史提交 {} 取出。
换机器时把这几行照抄过去、按实际环境改即可，不必再翻历史。
"""

DB_HOST = {DB_HOST!r}
DB_USER = {DB_USER!r}
DB_PASS = {DB_PASS!r}

REDIS_HOST = {REDIS_HOST!r}
REDIS_PORT = {REDIS_PORT}

# 末尾的 / 已去掉，代码会自己补
APP_HOST = {APP_HOST!r}

# 与 platform.node() 比对（即 hostname），命中则断言前免等待；留空只是慢，不影响正确性
NODE_ALI = {NODE_ALI!r}
NODE_ALI_SLP = {NODE_ALI_SLP!r}
NODE_ALI_XSG = {NODE_ALI_XSG!r}
'''


def git_show(rev, path):
    try:
        return subprocess.check_output(['git', 'show', '{}:{}'.format(rev, path)],
                                       text=True, encoding='utf-8', errors='replace')
    except (subprocess.CalledProcessError, FileNotFoundError):
        # 浅克隆或提交被重写时这里会失败，说清楚原因比抛 traceback 有用
        raise SystemExit('取不到 {} 在提交 {} 里的内容：'\
                         '确认当前目录是 git 仓库、且该提交存在（深克隆才行）'.format(path, rev))


def fold(node):
    """把以下写法都折成字面量，只取兜底那一支

        'x'
        X or 'x'
        os.environ.get('K', 'x')
        int(X or 6379)

    历史配置是「环境变量优先、常量兜底」，兜底值就是当时真正在用的那个。
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BoolOp):
        return fold(node.values[-1])
    if isinstance(node, ast.Call):
        # int() / str() 这类包装：折里面那个
        if isinstance(node.func, ast.Name) and node.func.id in ('int', 'str', 'float'):
            return fold(node.args[0])
        # os.environ.get('K', '默认')：取默认值；只传一个实参说明没兜底
        return fold(node.args[1]) if len(node.args) > 1 else None
    return None


def assignments(tree):
    """模块级与类内一级的赋值：db_config / redis_config 在 class 里面"""
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            found[node.targets[0].id] = node.value
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.Assign) and isinstance(item.targets[0], ast.Name):
                    found[item.targets[0].id] = item.value
    return found


def mapping(node):
    return {fold(key): fold(value) for key, value in zip(node.keys, node.values)}


def collect(rev):
    config = assignments(ast.parse(git_show(rev, 'common/Config.py')))
    database = mapping(assignments(ast.parse(git_show(rev, 'common/conSlpXsgMysql.py')))['db_config'])
    cache = mapping(assignments(ast.parse(git_show(rev, 'common/conRedis.py')))['redis_config'])
    nodes = mapping(config['linux_node'])
    app = mapping(config['appInfo'])['slp'].rstrip('/')
    return {
        'DB_HOST': database.get('ali_db'),
        'DB_USER': database.get('ali_user'),
        'DB_PASS': database.get('ali_pas'),
        'REDIS_HOST': cache.get('host_slp'),
        'REDIS_PORT': int(cache.get('port') or 6379),
        'APP_HOST': app,
        'NODE_ALI': nodes.get('ali') or '',
        'NODE_ALI_SLP': nodes.get('ali-slp') or '',
        'NODE_ALI_XSG': nodes.get('ali-xsg') or '',
    }


def main():
    parser = argparse.ArgumentParser(description='生成 common/env_local.py')
    parser.add_argument('--rev', default=DEFAULT_REV, help='从哪个提交取，默认 %(default)s')
    parser.add_argument('--force', action='store_true', help='目标文件已存在时覆盖')
    args = parser.parse_args()

    if os.path.exists(TARGET) and not args.force:
        print('{} 已存在，未覆盖（要覆盖加 --force）'.format(os.path.relpath(TARGET)))
        return 1

    values = collect(args.rev)
    # NODE_* 不拦：它只决定断言前要不要等，缺失只是慢，不影响正确性
    absent = [name for name in REQUIRED if not values.get(name)]
    if absent:
        print('历史提交 {} 里找不到这些项：{}'.format(args.rev, '、'.join(absent)))
        print('换个 --rev 再试，或手工填写 common/env_local.py')
        return 2

    with open(TARGET, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(TEMPLATE.format(args.rev, **values))

    # 只报字段，不报值：值不该出现在终端、日志或聊天记录里
    print('已写入 {}（来源 {}）'.format(os.path.relpath(TARGET), args.rev))
    for name in values:
        print('  {:<14} 已填'.format(name))
    print('下一步：python3 -m common.preflight slp')
    return 0


if __name__ == '__main__':
    sys.exit(main())
