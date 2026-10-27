# -*- coding: utf-8 -*-
"""推送前全面审查

每次 git push 之前跑一遍，不看 diff、直接扫全仓库，覆盖下面几类问题：

1. 全部 .py 能否解析、全部 case 模块能否 import
2. 重构后的函数，分支取值是否仍覆盖调用方实际传入的每一个值
   （deleteUserAccountSql 的表名 / selectUserInfoSql 的 accountType / encodeData 的 payType）
   —— 这类「分支被合并掉一个但没人发现」的问题，光看 diff 和跑局部用例都查不出来
3. 调用点的方法是否还存在（防止删方法后留下悬空调用）
4. 未使用的 import、共享层零引用定义

用法：python pre_push_audit.py
退出码：0 全部通过；1 有问题，逐条列在最后
"""
import ast
import importlib
import io
import os
import re
import sys

SELF = 'pre_push_audit.py'
CASE_PACKAGES = ['caseSlp', 'caseXsg']
# 有意保留的零引用定义：README 里记录过的公共断言 API，用例随时可能引用
ZERO_REF_ALLOWED = {'assert_in_text'}

problems = []


def fail(message):
    problems.append(message)


def source_files():
    """common / caseSlp / caseXsg 下的全部 .py，加上根目录的脚本（跳过 _ 开头的临时文件）"""
    for root in ['common'] + CASE_PACKAGES:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if os.path.isfile(path) and name.endswith('.py'):
                yield path
    for name in sorted(os.listdir('.')):
        path = os.path.join('.', name)
        if os.path.isfile(path) and name.endswith('.py') and not name.startswith('_'):
            yield path


def target(path):
    """统一成正斜杠，方便按固定字符串取用"""
    return path.replace(os.sep, '/')


files = [p for p in source_files() if os.path.basename(p) != SELF]


# Windows 下列表出来的路径是反斜杠，统一归一化后当 key，下面按固定字符串取用
sources = {target(p): io.open(p, encoding='utf-8', errors='replace').read() for p in files}
trees = {}
for path in files:
    key = target(path)
    try:
        trees[key] = ast.parse(sources[key])
    except SyntaxError as error:
        fail('{} 语法错误: {}'.format(key, error))
blob = '\n'.join(sources.values())


def const_calls(func_name):
    """收集 func_name(...) 调用点里写死的字符串实参，返回 {值: [文件...]}"""
    found = {}
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else None)
            if name != func_name:
                continue
            value = None
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                value = node.args[0].value
            for kw in node.keywords:
                if kw.arg in ('payType', 'accountType', 'tableName') and isinstance(kw.value, ast.Constant):
                    value = kw.value.value
            if value:
                found.setdefault(value, []).append(path)
    return found


def string_branches(func_names):
    """收集函数体内 if/elif 比较过的字符串常量"""
    branches = set()
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in func_names:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Compare):
                        for comp in sub.comparators:
                            if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                                branches.add(comp.value)
    return branches


def method_names(path, class_name):
    for node in ast.walk(trees[path]):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return set()


MYSQL = 'common/conSlpXsgMysql.py'
REDIS = 'common/conRedis.py'

# ---------- 1. case 模块能否 import ----------
sys.path.insert(0, os.getcwd())
imported_count = 0
for package in CASE_PACKAGES:
    if not os.path.isdir(package):
        continue
    for name in sorted(os.listdir(package)):
        if not (name.startswith('test_') and name.endswith('.py')):
            continue
        module = '{}.{}'.format(package, name[:-3])
        try:
            importlib.import_module(module)
            imported_count += 1
        except Exception as error:
            fail('{} 无法 import: {}: {}'.format(module, type(error).__name__, error))
print('[1] 解析 {} 个文件，{} 个 case 模块可 import'.format(len(trees), imported_count))

# ---------- 2. 各函数的分支覆盖 ----------
cleanup_tables = set()
for node in ast.walk(trees[MYSQL]):
    if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == '_ACCOUNT_CLEANUP_SQL':
        cleanup_tables = {k.value for k in node.value.keys}
coverage = [
    ('deleteUserAccountSql 的表名', cleanup_tables, const_calls('deleteUserAccountSql')),
    ('selectUserInfoSql 的 accountType',
     string_branches({'selectUserInfoSql', '_query_user_info'}), const_calls('selectUserInfoSql')),
    ('encodeData 的 payType', string_branches({'encodeData'}), const_calls('encodeData')),
]
print('\n[2] 分支覆盖')
for label, branches, used in coverage:
    missing = {value: paths for value, paths in used.items() if value not in branches}
    print('    {:<32} 分支 {:>2}  在用 {:>2}  缺分支 {}'.format(
        label, len(branches), len(used), sorted(missing) or '无'))
    if missing:
        fail('{} 缺少分支: {}（调用方: {}）'.format(
            label, sorted(missing), sorted({p for ps in missing.values() for p in ps})))
    unused = sorted(branches - set(used))
    if unused:
        print('    {:<32} 未被调用（保留兼容）: {}'.format('', unused))

# ---------- 3. 调用点的方法是否存在 ----------
mysql_methods = method_names(MYSQL, 'conMysql')
redis_methods = method_names(REDIS, 'conRedis')
# 只认实例变量名：redis 本身是模块名，redis.ConnectionPool 不是 conRedis 的方法
alias = {'mysql': mysql_methods, 'conMysql': mysql_methods, 'conRedis': redis_methods}
dangling = set()
for path, tree in trees.items():
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if not isinstance(owner, ast.Name) or owner.id not in alias:
            continue
        if node.func.attr not in alias[owner.id]:
            dangling.add('{}: {}.{}'.format(path, owner.id, node.func.attr))
print('\n[3] 调用点存在性  conMysql {} 个方法 / conRedis {} 个方法  悬空调用: {}'.format(
    len(mysql_methods), len(redis_methods), sorted(dangling) or '无'))
if dangling:
    fail('调用了不存在的方法: {}'.format(sorted(dangling)))

# ---------- 4. 未使用的 import ----------
print('\n[4] 未使用的 import')
count = 0
for path, tree in trees.items():
    lines = sources[path].splitlines()
    imported = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        # 转发模块（caseSlp/tools.py 等）故意 re-export 给用例用，同一行带 noqa 标记
        if 'noqa' in lines[node.lineno - 1].lower():
            continue
        if isinstance(node, ast.Import):
            imported += [(a.asname or a.name.split('.')[0], node.lineno) for a in node.names]
        else:
            imported += [(a.asname or a.name, node.lineno) for a in node.names if a.name != '*']
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            value = node.value
            while isinstance(value, ast.Attribute):
                value = value.value
            if isinstance(value, ast.Name):
                used.add(value.id)
    for name, lineno in imported:
        if name not in used:
            count += 1
            fail('{}:{} 未使用的 import: {}'.format(target(path), lineno, name))
print('    共 {} 处'.format(count))

# ---------- 5. 共享层的零引用定义 ----------
print('\n[5] 共享层零引用定义')
zero = 0
for path, tree in trees.items():
    if not (target(path).startswith('common/') or target(path).count('/') == 0):
        continue
    definitions = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definitions.append((node.name, node.lineno))
        elif isinstance(node, ast.Assign):
            for item in node.targets:
                if isinstance(item, ast.Name) and item.id.isupper():
                    definitions.append((item.id, node.lineno))
    for name, lineno in definitions:
        if name in ZERO_REF_ALLOWED:
            continue
        if len(re.findall(r'\b{}\b'.format(re.escape(name)), blob)) <= 1:
            zero += 1
            fail('{}:{} 零引用: {}'.format(target(path), lineno, name))
print('    共 {} 处（白名单: {}）'.format(zero, ', '.join(sorted(ZERO_REF_ALLOWED))))

# ---------- 结论 ----------
print('\n' + '=' * 60)
if problems:
    print('审查未通过，{} 个问题：'.format(len(problems)))
    for item in problems:
        print('  -', item)
    sys.exit(1)
print('审查通过：可以提交并推送')
sys.exit(0)
