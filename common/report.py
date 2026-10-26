# coding=utf-8
"""
用例执行结果汇总

run_all_case.py（全量执行、逐条播报）与 run_crontab_case.py（定时任务、只报失败）
都需要两件事：收集每条用例的 des、执行结束后统一列出所有未通过的用例。
放在一处实现，避免两个入口的展示口径不一致。
"""
import inspect
import unittest


def extract_des_from_docstring(docstring):
    """从测试方法 docstring 中提取用例描述（用例描述：与脚本步骤：之间的第一行非空文本）"""
    if not docstring:
        return None
    lines = docstring.splitlines()
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('用例描述'):
            capture = True
            # 如果 "用例描述：" 同行后面有内容，直接取
            after_colon = stripped.split('：', 1)[-1].strip()
            if after_colon:
                return after_colon
            continue
        if capture and stripped.startswith('脚本步骤'):
            break
        if capture and stripped:
            return stripped
    return None


class AllTestResult(unittest.TextTestResult):
    """自定义测试结果类：记录每条用例的 des，并收集通过的用例"""

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.successes = []
        self.test_des_map = {}  # 记录每个测试的 des 值

    def startTest(self, test):
        super().startTest(test)
        # 优先从方法签名的 des 默认参数获取，其次从 docstring 提取
        try:
            method = getattr(test, test._testMethodName)
            sig = inspect.signature(method)
            des_param = sig.parameters.get('des', None)
            if des_param is not None and des_param.default is not inspect.Parameter.empty:
                self.test_des_map[test] = des_param.default
                return
            des = extract_des_from_docstring(test._testMethodDoc)
            if des:
                self.test_des_map[test] = des
        except Exception:
            pass

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test)


class AllTestRunner(unittest.TextTestRunner):
    """自定义测试运行器，返回 AllTestResult"""
    resultclass = AllTestResult


def case_name(case):
    """用例名称：去掉 caseSlp./caseXsg. 这类目录前缀，保留 模块.类.方法"""
    case_id = case.id()
    return case_id.split('.', 1)[-1] if '.' in case_id else case_id


def case_des(result, case):
    """用例描述：优先取方法签名里 des 的默认值，取不到时退回 docstring 中的用例描述"""
    des = getattr(result, 'test_des_map', {}).get(case)
    if des:
        return des
    return extract_des_from_docstring(getattr(case, '_testMethodDoc', None)) or ''


# 企微机器人单条 markdown 内容上限 4096 字节，超过会被静默截断，
# 长消息必须在发送前拆成多条，否则末尾的结论会被切掉
MAX_MSG_BYTES = 3900


def reason_brief(reason_text, max_len=300):
    """
    从 unittest 的失败/异常文本中取最有信息量的一行
    优先取断言语句（如 assert_equal(...)），能直接看出哪条断言挂了；
    取不到时退回最后一个非空行（如 KeyError: 'xxx'）
    :param reason_text: unittest 给出的 failures/errors 文本
    :param max_len: 单行最大长度
    """
    raw_lines = [line.strip() for line in str(reason_text).splitlines() if line.strip()]
    for line in raw_lines:
        # 覆盖 assert_x(...) / self.assert_x(...) / Assert.assert_x(...) 三种写法
        if line.startswith(('assert', 'self.assert', 'Assert.')):
            return line[:max_len]
    return raw_lines[-1][:max_len] if raw_lines else ''


def not_pass_count(result):
    """未通过用例数量：失败 + 异常 + 跳过"""
    return len(result.failures) + len(result.errors) + len(result.skipped)


def not_pass_lines(result, with_detail=True):
    """
    列出所有未通过的用例：失败、异常、跳过，每条展示 用例名称 + des
    :param result: unittest 测试结果对象
    :param with_detail: 是否附带一行明细（失败取断言语句、异常取异常末行、跳过取跳过原因）
    :return: ['[FAIL] 模块.类.方法 | 用例描述', ...]
    """
    lines = []
    for status, items in (('FAIL', result.failures),
                          ('ERROR', result.errors),
                          ('SKIP', result.skipped)):
        for case, reason in items:
            des = case_des(result, case)
            # des 取不到时不要留下一个空的分隔符
            lines.append('[{}] {}{}'.format(status, case_name(case), ' | {}'.format(des) if des else ''))
            if not with_detail:
                continue
            if status == 'SKIP':
                detail = str(reason).strip()
            else:
                detail = reason_brief(reason)
            if detail:
                lines.append('    {}'.format(detail))
    return lines


def not_pass_summary(result, title='未通过用例', with_detail=True):
    """
    未通过用例的完整段落（表头 + 明细）；全部通过时给出一句提示，可直接拼进通知
    """
    lines = not_pass_lines(result, with_detail=with_detail)
    header = '{}（共 {} 条）'.format(title, not_pass_count(result))
    if not lines:
        return '{}\n无，全部用例通过'.format(header)
    return '{}\n{}'.format(header, '\n'.join(lines))


def _split_long_line(text, limit):
    """单行就超过上限时按字符硬切（不按字节切，否则会把中文切成半个字符）"""
    pieces, buffer, used = [], [], 0
    for char in text:
        size = len(char.encode('utf-8'))
        if buffer and used + size > limit:
            pieces.append(''.join(buffer))
            buffer = []
            used = 0
        buffer.append(char)
        used += size
    if buffer:
        pieces.append(''.join(buffer))
    return pieces


def split_message(lines, limit=MAX_MSG_BYTES):
    """
    按字节上限把消息拆成多条（保持行完整，不把一个用例的明细拆到两条消息里）
    :param lines: 消息行列表，单条元素可以是多行字符串（会先在行内展开）
    :param limit: 单条消息字节上限
    :return: ['第一条消息', '第二条消息', ...]
    """
    chunks = []
    buffer = []
    used = 0

    def flush():
        nonlocal used
        if buffer:
            chunks.append('\n'.join(buffer))
            buffer.clear()
            used = 0

    for line in lines:
        # 传入的元素可能是 not_pass_summary() 这种多行字符串，不展开的话整段只能当一个元素，
        # 长度超过 limit 时既无法拆分，又会撞上企微 4096 字节上限被静默截断
        for sub_line in str(line).splitlines() or ['']:
            size = len(sub_line.encode('utf-8')) + 1  # +1 算换行符
            if size > limit:
                # 极端情况：单行就超上限（如异常堆栈被压成一行），按字符硬切
                flush()
                chunks.extend(_split_long_line(sub_line, limit))
                continue
            if buffer and used + size > limit:
                flush()
            buffer.append(sub_line)
            used += size
    flush()
    return chunks
