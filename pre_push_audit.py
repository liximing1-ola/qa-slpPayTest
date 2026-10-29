# -*- coding: utf-8 -*-
"""推送前全面审查

每次 git push 之前跑一遍，不看 diff、直接扫全仓库，覆盖下面几类问题：

1. 全部 .py 能否解析、全部 case 模块能否 import
2. 重构后的函数，分支取值是否仍覆盖调用方实际传入的每一个值
   （deleteUserAccountSql 的表名 / selectUserInfoSql 的 accountType / encodeData 的 payType）
   —— 这类「分支被合并掉一个但没人发现」的问题，光看 diff 和跑局部用例都查不出来
3. 调用点的方法是否还存在（防止删方法后留下悬空调用）
4. 未使用的 import
5. 共享层的零引用定义
6. 读账户表的断言是否写了轮询版，且轮询版的第一个参数确实是 lambda
   （写成同步读值，实测会让 36% 的用例靠重试才有结果）
7. 验证强度：断言是否被 if 包住（条件不成立就整段不校验）、被 except 吞掉、
   被注释掉、或容差放宽到个位以上
   —— 这些 case 的目的是发现服务端支付逻辑的问题，任何「让用例更容易过」的写法
   都要拦住：为了 pass 而放松校验，等于把这个 case 废掉
8. 密钥泄露：.py / .md 里不许出现 GitHub token、企微 webhook key、私钥、
   URL 内嵌账号密码、第三方 app_secret
   —— 凭据一提交就永久留在 git 历史里，删文件也回收不了，只能重新生成
9. 场景族登记：新增的用例模块必须在 common/case_groups.py 里登记
   —— 漏登记不会报错，只会让这一类悄悄归到「未分组」、从分类统计里消失，
   比没有统计更糟：看的人会以为「这类没问题」
10. 未定义名字：用到但当前作用域里找不到绑定的名字
   —— compileall 只查语法，`time.sleep(...)` 在删掉 import time 后依然编译通过，
   要等服务器真跑到那一行才 NameError；那一行如果刚好在 skip 或异常分支里，
   可能几轮都碰不到
11. 调用点实参与签名：实参个数、关键字名是否还对得上函数定义
   —— 第 3 类只管「方法还在不在」，改了参数名却漏改调用点，方法还在、编译也过，
   要等跑到才 TypeError（重构公共助手时最常见）

用法：python pre_push_audit.py
退出码：0 全部通过；1 有问题，逐条列在最后
"""
import ast
import builtins
import importlib
import inspect
import io
import os
import re
import string
import sys

SELF = 'pre_push_audit.py'
# 三个用例包都要审：caseStress 是并发与幂等用例，走独立入口运行，但不能因此成为审计盲区
CASE_PACKAGES = ['caseSlp', 'caseXsg', 'caseStress']
# 有意保留的零引用定义：README 里记录过的公共断言 API，用例随时可能引用
ZERO_REF_ALLOWED = {'assert_in_text'}

problems = []
# 提醒级问题：不影响退出码，但要人看一眼（如 skip 数量突增，可能是用 skip 躲失败）
warnings = []


def warn(message):
    warnings.append(message)


def fail(message):
    problems.append(message)


def source_files():
    """common / caseSlp / caseXsg / caseStress 下的全部 .py，加上根目录的脚本（跳过 _ 开头的临时文件）"""
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

# ---------- 6. 读账户表的断言写法 ----------
# 服务端分账是异步的：请求返回时收礼方分成还没落库，同步读一次必然读到 0。
# 2026-10-27 那轮实测：50/137 条用例是重试一轮才过的，失败明细全是「实际结果: 0」。
# 所以「读账户表 + 断言」必须用 assert_equal_eventually + lambda；反过来说，
# 把读值提前求好再传进去等于白等一轮超时，也必须拦住。
print('\n[6] 账户读值的断言写法')
bad_plain = []
bad_eager = []
for path, tree in trees.items():
    if not (target(path).startswith('caseSlp/') or target(path).startswith('caseXsg/')
            or target(path).startswith('caseStress/')):
        continue
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or not node.args:
            continue
        if node.func.id not in ('assert_equal', 'assert_equal_eventually'):
            continue
        first = node.args[0]
        is_read = (isinstance(first, ast.Call) and isinstance(first.func, ast.Attribute)
                   and first.func.attr == 'selectUserInfoSql')
        if node.func.id == 'assert_equal' and is_read:
            bad_plain.append('{}:{}'.format(target(path), node.lineno))
        elif node.func.id == 'assert_equal_eventually' and is_read:
            bad_eager.append('{}:{}'.format(target(path), node.lineno))
print('    直接读值用 assert_equal: {} 处  轮询版传了已读好的值: {} 处'.format(
    len(bad_plain), len(bad_eager)))
if bad_plain:
    fail('读账户表必须用 assert_equal_eventually + lambda（异步落库）: {}'.format(bad_plain))
if bad_eager:
    fail('轮询版的第一个参数必须是 lambda，不能是提前读好的值: {}'.format(bad_eager))

# ---------- 7. 验证强度：防止为了通过而弱化校验 ----------
# 这个仓库的 case 是用来发现服务端支付逻辑问题的，不是用来交绿报告的。验证口径一旦放松，
# 报告变绿但问题就消失了。下面四类「让用例更容易过」的写法在这里拦住：
#   a. 条件断言：assert 被 if 包住，条件不成立时整段校验静默跳过
#   b. 断言被 try 吞掉：except 分支没有 raise，失败变成了继续往下跑
#   c. 被注释掉的断言：历史上就有人用这招「修好」用例
#   d. 容差放宽到个位以上：金额、次数都是整数，容忍 2 以上等于不校验
print('\n[7] 验证强度（防止弱化校验）')
# 按数值/多值分支是必要写法，不是弱化；白名单只此一个文件
COND_ASSERT_ALLOWED = {'common/Assert.py'}
# 轮询助手本来就要捕获断言失败后重试（中间态不算失败），超时那一轮仍会 raise
SWALLOW_ALLOWED = {'common/Assert.py'}
conditional = []
swallowed = []
commented = []
loose = []
for path, tree in trees.items():
    rel = target(path)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            if isinstance(parents.get(node), (ast.If, ast.IfExp, ast.While)) and rel not in COND_ASSERT_ALLOWED:
                conditional.append('{}:{}'.format(rel, node.lineno))
        elif isinstance(node, ast.Try):
            # 只看 try 体里真的有断言的那种，避免把普通容错（如现场读取失败不影响主流程）误报
            body_has_assert = False
            for stmt in node.body:
                for inner in ast.walk(stmt):
                    if isinstance(inner, ast.Assert) or (
                            isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                            and inner.func.id.startswith('assert')):
                        body_has_assert = True
            if not body_has_assert:
                continue
            for handler in node.handlers:
                if not any(isinstance(inner, ast.Raise) for inner in ast.walk(handler)) \
                        and rel not in SWALLOW_ALLOWED:
                    swallowed.append('{}:{}'.format(rel, handler.lineno))
        elif isinstance(node, ast.Compare) and isinstance(node.left, ast.Call) \
                and isinstance(node.left.func, ast.Name) and node.left.func.id == 'abs':
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Lt, ast.LtE)) and isinstance(comparator, ast.Constant) \
                        and isinstance(comparator.value, (int, float)) and comparator.value > 1:
                    loose.append('{}:{}'.format(rel, node.lineno))
for path, text in sources.items():
    for lineno, line in enumerate(text.splitlines(), 1):
        # 必须整行就是一句断言才算（行首 # 后直接跟断言）；写得宽松会把注释里提到
        # 「assert_x(...)」这种说明文字也当成被注释掉的断言。两种写法都要覆盖：
        # 裸语句 `# assert a == b` 和函数调用 `# assert_equal(a, b)`
        if re.match(r'^#\s*(self\.|Assert\.)?assert(_[a-z_]*\(|\s)', line.strip()):
            commented.append('{}:{}'.format(path, lineno))
print('    条件断言: {} 处  断言被 except 吞掉: {} 处  注释掉的断言: {} 处  过度容差: {} 处'.format(
    len(conditional), len(swallowed), len(commented), len(loose)))
if conditional:
    fail('断言被 if 包住，条件不成立时整段校验会被跳过: {}'.format(conditional))
if swallowed:
    fail('断言在 try 里但 except 没有 raise，失败被吞掉: {}'.format(swallowed))
if commented:
    fail('断言被注释掉: {}'.format(commented))
if loose:
    fail('数值容差大于 1（金额/次数是整数，容忍到个位以上等于不校验）: {}'.format(loose))
# skip 数量只提醒不判失败：功能下线确实会新增 skip，但「用 skip 躲开失败」也是这个形态，
# 数量变了就让人看一眼理由（基线：装饰器 8 个、运行时 skipTest 3 处）
skip_marks = len(re.findall(r'@unittest\.skip', blob))
skip_runtime = len(re.findall(r'skipTest\(', blob))
print('    skip 装饰器: {} 个  运行时 skipTest: {} 处（基线 8 / 3）'.format(skip_marks, skip_runtime))
if (skip_marks, skip_runtime) != (8, 3):
    warn('skip 数量偏离基线（{} / {}，基线 8 / 3）：确认是功能下线，不是用 skip 躲失败'.format(
        skip_marks, skip_runtime))

# ---------- 8. 密钥泄露 ----------
# 凭据一旦随提交进仓库，就永久留在 git 历史里：删掉当前文件也没用，谁 clone 都能翻出来，
# 只能重新生成来作废。已经踩过两次：企微 webhook key 写死在 Robot.py；GitHub PAT 被写进
# 服务器的 remote URL 后随截图外传。这类值只允许走环境变量或本地凭据存储。
print('\n[8] 密钥泄露（凭据不入库）')
# 文档里给人看的占位符不算泄露：<key>、YOUR_TOKEN 这类紧跟尖括号的写法都放过
SECRET_PATTERNS = [
    ('GitHub token', re.compile(r'\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})')),
    ('企微 webhook key', re.compile(r'webhook/send\?key=(?!<)[0-9a-fA-F-]{16,}')),
    ('私钥', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    # 排除尖括号：文档里给人看的 `https://<user>:<token>@host` 是占位符，不算泄露；
    # 真令牌不会带尖括号，两者不会误判
    ('URL 内嵌凭据', re.compile(r'://[^/\s:@<>]+:[^@\s<>]{6,}@')),
    ('app_secret', re.compile(r'app_secret=(?!<)[A-Za-z0-9]{12,}')),
]
# 扫 .py 之外也要扫 .md：写进文档的 key 同样泄露；但跳过本文件，它自己就写着这些规则
scanned = {path: text for path, text in sources.items() if path != SELF}
for name in sorted(os.listdir('.')):
    if name.endswith('.md') and os.path.isfile(name):
        with io.open(name, encoding='utf-8', errors='replace') as handle:
            scanned[name] = handle.read()
leaks = []
for path, text in scanned.items():
    for lineno, line in enumerate(text.splitlines(), 1):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                leaks.append('{}:{} {}'.format(path, lineno, label))
print('    扫描 {} 个文件（.py + .md），疑似密钥 {} 处'.format(len(scanned), len(leaks)))
if leaks:
    fail('发现疑似密钥（凭据只能走环境变量或本地凭据存储，不要写进仓库）: {}'.format(leaks))

# ---------- 9. 场景族登记 ----------
# 推送和日志都按场景族汇总，靠的是 common/case_groups.py 这张表。新增用例文件时
# 忘了加一行，它不会报错，只会让那一类悄悄归到「未分组」——而「未分组」这一行
# 没人会去看，等于这类用例从统计里消失了。
print('\n[9] 场景族登记（用例模块 → 业务场景族）')
from common import case_groups

case_modules = set()
for package in CASE_PACKAGES:
    if not os.path.isdir(package):
        continue
    for name in os.listdir(package):
        if name.startswith('test_') and name.endswith('.py'):
            case_modules.add(name[:-3])
missing = sorted(set(case_modules) - set(case_groups.GROUPS))
print('    用例模块 {} 个，已登记 {} 个，未登记 {}'.format(
    len(case_modules), len(case_groups.GROUPS), len(missing)))
if missing:
    fail('用例模块未登记场景族，会归到「{}」而不出现在分类统计里: {}'.format(
        case_groups.UNGROUPED, missing))
# 反向也要查：表里留着已经删掉的模块，说明这张表已经没人维护，早晚会失真
stale = sorted(set(case_groups.GROUPS) - case_modules)
if stale:
    warn('分组表里有不存在的用例模块: {}'.format(stale))

# ---------- 10. 未定义名字 ----------
# compileall 只查语法：删掉 `import time` 之后 `time.sleep(0.5)` 照样编译通过，
# 只有真跑到那一行才会 NameError。这类错误如果落在 skip 用例或异常分支里，
# 可能好几轮全量都碰不到，等碰到时又很容易被当成「偶发」。
print('\n[10] 未定义名字（NameError 预防）')
BUILTIN_NAMES = set(dir(builtins)) | {
    '__file__', '__name__', '__doc__', '__package__', '__spec__', '__builtins__', 'WindowsError',
}
_STAR_CACHE = {}


def star_import_names(module_name):
    """`from X import *` 带来的名字：静态看不出，直接问模块要

    返回 None 表示这个模块导不进来——此时无从得知星号带进了什么，
    该文件宁可跳过不查，也不要把一堆正常名字误报成未定义。
    """
    if module_name not in _STAR_CACHE:
        try:
            module = importlib.import_module(module_name)
            _STAR_CACHE[module_name] = {name for name in dir(module) if not name.startswith('_')}
        except Exception:
            _STAR_CACHE[module_name] = None
    return _STAR_CACHE[module_name]


def bind_target(node, names):
    """赋值目标绑定的名字，含解包与星号写法"""
    if isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for item in node.elts:
            bind_target(item, names)
    elif isinstance(node, ast.Starred):
        bind_target(node.value, names)


def scope_bindings(nodes):
    """一段语句体里绑定的名字；不深入嵌套函数/类的内部（那是另一个作用域）"""
    names = set()
    stack = list(nodes)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for item in node.names:
                if item.name != '*':
                    names.add(item.asname or item.name.split('.')[0])
            continue
        if isinstance(node, ast.Assign):
            for item in node.targets:
                bind_target(item, names)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            bind_target(node.target, names)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            bind_target(node.target, names)
        elif isinstance(node, ast.comprehension):
            # 推导式/生成器的循环变量（`[x for x in ...]` 里的 x）也是绑定，
            # 漏了它会把全仓 dozens 处 i / row / item 全报成未定义
            bind_target(node.target, names)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    bind_target(item.optional_vars, names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.NamedExpr):
            bind_target(node.target, names)
        stack.extend(ast.iter_child_nodes(node))
    return names


def undefined_names(path, tree, module_names):
    """逐作用域找出「用到了但找不到绑定」的名字，返回 [(行号, 名字)]"""
    found = []

    def walk_scope(body, outer):
        local = scope_bindings(body)
        for node in body:
            walk_node(node, [local] + outer)

    def walk_node(node, scopes):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 装饰器、默认值在**外层**求值，必须用外层作用域
            for sub in node.decorator_list + list(node.args.defaults):
                walk_node(sub, scopes)
            for sub in node.args.kw_defaults:
                if sub is not None:
                    walk_node(sub, scopes)
            args = {a.arg for a in node.args.args + node.args.kwonlyargs}
            args |= {a.arg for a in (node.args.vararg, node.args.kwarg) if a is not None}
            walk_scope(node.body, [args] + scopes)   # 函数体还能看到外层（闭包）
            return
        if isinstance(node, ast.ClassDef):
            for sub in node.decorator_list + node.bases + [k.value for k in node.keywords]:
                walk_node(sub, scopes)
            walk_scope(node.body, scopes)
            return
        if isinstance(node, ast.Lambda):
            args = {a.arg for a in node.args.args + node.args.kwonlyargs}
            args |= {a.arg for a in (node.args.vararg, node.args.kwarg) if a is not None}
            walk_node(node.body, [args] + scopes)
            return
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in module_names and not any(node.id in scope for scope in scopes):
                found.append((node.lineno, node.id))
            return
        for child in ast.iter_child_nodes(node):
            walk_node(child, scopes)

    walk_scope(tree.body, [])
    return found


undefined = []
skipped_star = []
for path, tree in trees.items():
    if path == SELF:
        continue
    module_names = set(BUILTIN_NAMES) | scope_bindings(tree.body)
    unresolvable = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(item.name == '*' for item in node.names):
            names = star_import_names(node.module or '')
            if names is None:
                unresolvable = True
            else:
                module_names |= names
    if unresolvable:
        skipped_star.append(path)
        continue
    for lineno, name in undefined_names(path, tree, module_names):
        undefined.append('{}:{} {}'.format(path, lineno, name))
print('    扫描 {} 个文件，未定义名字 {} 处{}'.format(
    len(trees), len(undefined),
    '（{} 个文件因星号导入解析不了而跳过）'.format(len(skipped_star)) if skipped_star else ''))
if undefined:
    fail('用到了但找不到绑定的名字（编译不报错，运行到才 NameError）: {}'.format(undefined))

# ---------- 11. 调用点实参与签名 ----------
# 第 3 类只管「方法还在不在」。改了参数名或位置却漏改调用点，方法还在、
# compileall 也过，要等跑到那一行才 TypeError——而这正是重构公共助手
# （tools / Assert / conMysql 方法）时最容易出的错。这里拿真实函数对象
# 的签名去 bind_partial，只校验实参能不能安放，不看默认值。
print('\n[11] 调用点实参与签名')
REPO_PREFIXES = ('common.', 'caseSlp.', 'caseXsg.', 'caseStress.')


def repo_function(obj):
    """只认仓库内定义的普通函数/方法；类、内置、第三方不管"""
    module = getattr(obj, '__module__', '') or ''
    if not module.startswith(REPO_PREFIXES) or inspect.isclass(obj) or not callable(obj):
        return None
    return obj


signature_bad = []
signature_calls = 0
for path in sorted(trees):
    if path.split('/')[0] not in CASE_PACKAGES:
        continue
    module_name = path[:-3].replace('/', '.')
    try:
        module = importlib.import_module(module_name)
    except Exception:
        continue   # 导不进来已在第 1 类报过，这里不重复
    namespace = vars(module)
    # 同名被本地赋值过（可能是个可调用对象别名）就不查，宁可漏报不误报
    rebound = set()
    for node in ast.walk(trees[path]):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            rebound.add(node.id)
    for node in ast.walk(trees[path]):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id not in rebound:
            target = repo_function(namespace.get(node.func.id))
            label = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                and node.func.value.id in ('mysql', 'conMysql', 'conRedis'):
            owner = namespace.get(node.func.value.id)
            target = repo_function(getattr(owner, node.func.attr, None))
            label = '{}.{}'.format(node.func.value.id, node.func.attr)
        else:
            continue
        if target is None:
            continue
        # *args / **kwargs 写法静态定不下来，交给运行期
        if any(isinstance(a, ast.Starred) for a in node.args):
            continue
        if any(kw.arg is None for kw in node.keywords):
            continue
        signature_calls += 1
        args = [0] * len(node.args)
        kwargs = {kw.arg: 0 for kw in node.keywords}
        try:
            inspect.signature(target).bind_partial(*args, **kwargs)
        except TypeError as error:
            signature_bad.append('{}:{} {} -> {}'.format(path, node.lineno, label, error))
print('    可校验调用 {} 处，实参与签名不符 {} 处'.format(signature_calls, len(signature_bad)))
if signature_bad:
    fail('调用点实参与函数签名不符（编译不报错，运行到才 TypeError）: {}'.format(signature_bad))

# ---------- 12. format 占位符与实参 ----------
# 编译不报错、前十一类也抓不到：写 print('{} {}'.format(a)) 就是运行时 IndexError。
# 它发生在断言之前时，那条用例报的是 ERROR 而不是真正的验证结果（并发用例就这么翻过车），
# 所以这里按字面量占位符个数静态对一遍。
print('\n[12] format 占位符与实参')
format_bad = []
for path, tree in trees.items():
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'format'):
            continue
        literal = node.func.value
        if not (isinstance(literal, ast.Constant) and isinstance(literal.value, str)):
            continue
        # *args / **kwargs 静态定不下来，交给运行期
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            continue
        if any(keyword.arg is None for keyword in node.keywords):
            continue
        try:
            slots = list(string.Formatter().parse(literal.value))
        except ValueError as error:
            format_bad.append('{}:{} 占位符写法非法: {}'.format(path, node.lineno, error))
            continue
        auto, indexes, names = 0, set(), set()
        for _, field, _, _ in slots:
            if field is None:
                continue
            base = field.split('[')[0].split('.')[0]
            if base == '':
                auto += 1
            elif base.isdigit():
                indexes.add(int(base))
            else:
                names.add(base)
        where = '{}:{}'.format(path, node.lineno)
        if auto and (indexes or names):
            format_bad.append('{} 自动编号与手动编号混用'.format(where))
        elif auto and len(node.args) < auto:
            format_bad.append('{} 占位符 {} 个，位置实参只有 {} 个'.format(where, auto, len(node.args)))
        elif not auto and indexes and max(indexes) >= len(node.args):
            format_bad.append('{} 用到第 {} 个位置实参，但只有 {} 个'.format(
                where, max(indexes), len(node.args)))
        elif not auto:
            missing = names - {keyword.arg for keyword in node.keywords}
            if missing:
                format_bad.append('{} 缺少关键字实参 {}'.format(where, sorted(missing)))
print('    占位符与实参不符: {} 处'.format(len(format_bad)))
if format_bad:
    fail('format 占位符与实参个数不匹配（编译不报错，运行到直接 IndexError/KeyError）: {}'.format(format_bad))

# ---------- 结论 ----------
print('\n' + '=' * 60)
if warnings:
    print('提醒（不影响结论，但要看一眼）：')
    for item in warnings:
        print('  -', item)
if problems:
    print('审查未通过，{} 个问题：'.format(len(problems)))
    for item in problems:
        print('  -', item)
    sys.exit(1)
print('审查通过：可以提交并推送')
sys.exit(0)
