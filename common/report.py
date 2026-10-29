# coding=utf-8
"""
用例执行结果汇总

run_all_case.py（全量执行、逐条播报）与 run_crontab_case.py（定时任务、只报失败）
都需要两件事：按 App 名装配用例集、收集每条用例的 des 并在结束后统一列出未通过用例。
放在一处实现，避免两个入口的装配口径与展示口径各自跑偏。
"""
import inspect
import os
import sys
import time
import unittest

from common import Assert, Logs, Scene, runFailed
from common.case_groups import CASE_PACKAGES, group_of
from common.Config import config


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
        self.index = 0          # 已结束的用例数，用于进度日志的 [37/136]
        self.total_cases = 0    # 总用例数，由 AllTestRunner 从 suite 上取后注入
        self._case_started = 0.0
        self.retried = {}       # 用例 id -> 该用例“重试后才通过”的记录
        self._retry_mark = 0

    def startTest(self, test):
        super().startTest(test)
        # 防御性清理：重试回放态与缓存按用例隔离。@Retry 的 wrapper 开头也会清一次，
        # 这里收住"没加 @Retry 的用例"这种将来可能出现的入口，避免继承上一条用例的回放态
        from common import Request
        Request.begin_case()
        # 失败现场也按用例隔离：清掉上一条的请求缓存，开始录本条的
        Scene.begin_case(test.id())
        self._case_started = time.time()
        # 记下重试计数基线：用例结束时做差就是它重试了几轮
        self._retry_mark = runFailed.retry_event_count()
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
        self._collect_retries(test)
        self._progress(test, 'PASS')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._collect_retries(test)
        # 先把现场归档再记进度：归档要在缓冲被下一条用例清掉之前完成
        Scene.archive(test.id())
        self._progress(test, 'FAIL')

    def addError(self, test, err):
        super().addError(test, err)
        self._collect_retries(test)
        Scene.archive(test.id())
        self._progress(test, 'ERROR')

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._progress(test, 'SKIP')

    def _collect_retries(self, test):
        """把这条用例期间发生的重试归档，供 retry_report 拼清单

        重试成功后用例在报告里的状态是 PASS，和一次就过的用例长得一模一样。
        实测一轮全量 54 次重试，也就是 54 次真实断言失败被重试掩盖了——它们才是最
        值得看的线索：重试能救回来只能说明“等一会儿就对”，不代表被测逻辑没问题。
        """
        start = self._retry_mark
        events = runFailed.retry_events()[start:]
        # 推进基线：同一条用例不会重复统计（如 addFailure 后又进 addError 的异常路径）
        self._retry_mark = start + len(events)
        if not events or not getattr(test, '_testMethodName', None):
            return 0
        self.retried[test.id()] = {
            'case': case_name(test),
            'des': self.test_des_map.get(test, ''),
            'events': events,
        }
        return len(events)

    def _progress(self, test, status):
        """实时进度落盘：另开窗口 tail -f log/progress.log 就能看到跑到第几条、每条多久

        控制台本来就逐条打，但一旦 `python run_all_case.py slp | tail -60`，tail 要等 EOF
        才输出，整个运行期间看不到任何东西，看着就像卡死。写文件绕开了这一层。
        """
        self.index += 1
        elapsed = time.time() - self._case_started
        # 重试过的用例在行尾标出来：耗时里含重试轮，只看 PASS 会误以为它一次就过
        retries = len((self.retried.get(test.id()) or {}).get('events', []))
        line = '[{:>3}/{}] {:<5} {:>7.2f}s  {}{}'.format(
            self.index, self.total_cases or '?', status, elapsed, case_name(test),
            '  [重试×{}]'.format(retries) if retries else '')
        try:
            Logs.get_log('progress.log', console=False, back_count=30,
                         fmt='%(asctime)s  %(message)s').info(line)
        except Exception:
            # 进度只是观测手段，写日志失败不能影响用例执行
            pass

    def printErrors(self):
        """
        unittest 默认会在结束前把每条失败的完整堆栈再打一遍（FAIL: / ERROR: 段落），
        而失败多时这一步会刷满屏幕、淹没真正要看的结论。
        控制台只保留 not_pass_report() 输出的清单，完整堆栈统一写进 log/failCase.log。
        """
        pass


class AllTestRunner(unittest.TextTestRunner):
    """自定义测试运行器，返回 AllTestResult"""
    resultclass = AllTestResult

    def run(self, test):
        # 进度日志要显示「第几条/共几条」，总数只能从 suite 上取
        self._total_cases = test.countTestCases()
        # 重试记录按轮次隔离：同一进程里多次 run 时不会把上轮的重试算进本轮
        runFailed.reset_retry_events()
        # 开跑前先把本轮生效的环境参数打出来：补偿/间隔这类值一旦被环境变量改动又忘了改回，
        # 光看报告只会觉得「这轮快得反常」，说不清到底按什么参数跑的
        for line in Assert.environment_summary():
            print(line, flush=True)
        return super().run(test)

    def _makeResult(self):
        result = super()._makeResult()
        result.total_cases = getattr(self, '_total_cases', 0)
        return result


def build_suite(app_info, case_expr='', case_dir_name=''):
    """按 App 名装配用例集

    :param app_info: config.appName 的取值（SLP / XSG）；不支持时抛 ValueError，让入口显式报错
    :param case_expr: 逗号分隔的混合写法，空则全量执行（run_crontab_case 不传，行为与全量一致）
        省略：test_check                             只跑 caseSlp/test_check.py
        带点：test_check.TestPayCreate.test_002      按完整用例名加载（可只写到类）
        带点带前缀：caseSlp.test_check.TestPayCreate.test_002 也行，见下面注释
    :param case_dir_name: 用例目录名，空则按 App 映射（caseSlp / caseXsg）。并发与幂等用例放在
        平级的 caseStress，由 run_stress_case 传进来——不能建成 caseSlp 的子目录：discover 是
        递归的，子目录里的用例会被日常全量回归自动收进去
    unittest 的 discover 只能按**文件名** glob，写用例名是匹配不到文件的，所以两种写法分开处理

    两种写法都收（名字前缀可带可不带）：同一个「用例名」在两个入口都得能用——
    run_reproduce.py 是把名字直接喂给 `python -m unittest <全名>`，那边必须带目录前缀；
    而这里原本会无条件再拼一次，于是 `CASE=caseStress.test_pay_concurrent...` 变成
    `caseStress.caseStress.test_pay_concurrent...`，跑出来是一条 "No module named
    'caseStress.caseStress'" 的假失败用例（实测踩过）。不要求人记住两套写法。
    """
    if app_info not in (config.appName['SLP'], config.appName['XSG']):
        raise ValueError('不支持的 App: {}, 仅支持 {}'.format(app_info, config.appName))

    if case_dir_name:
        case_dir = '{}/{}'.format(config.BASE_PATH, case_dir_name)
    elif app_info == config.appName['SLP']:
        case_dir = config.BASE_PATH + '/caseSlp'
    else:
        case_dir = config.BASE_PATH + '/caseXsg'

    testcase = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    if case_expr:
        app_dir = os.path.basename(case_dir)  # caseSlp / caseXsg，拼完整用例名时要带上前缀
        for item in case_expr.split(','):
            item = item.strip()
            if not item:
                continue
            if '.' in item:
                # 目录前缀可带可不带：带了就用剩下的部分，免得拼成 caseStress.caseStress.xxx
                head, rest = item.split('.', 1)
                if head in CASE_PACKAGES:
                    if head != app_dir:
                        print('[CASE] 前缀 {} 与实际用例目录 {} 不一致：本轮只跑 {} 下的用例，'
                              '写 caseSlp / caseXsg / caseStress 时别混用'.format(
                                  head, app_dir, app_dir), flush=True)
                        sys.exit(2)
                    item = rest
                # 找不到时 unittest 会造一条报错用例，不会静默跳过
                testcase.addTests(loader.loadTestsFromName('{}.{}'.format(app_dir, item)))
                continue
            name = item if item.endswith('.py') else '{}.py'.format(item)
            testcase.addTests(loader.discover(case_dir,
                                              pattern=name if name.startswith('test_') else 'test_' + name,
                                              top_level_dir=config.BASE_PATH))
        return testcase

    testcase.addTests(loader.discover(case_dir, pattern='test_*.py', top_level_dir=config.BASE_PATH))
    return testcase


def parse_app(argv):
    """解析命令行传入的 App，支持 slp / xsg（大小写不敏感），缺省为 slp

    两个入口共用一份：口径分家会出现「同一个参数在两个脚本里行为不同」的问题。
    传错参数（如 slpp）时显式报错退出，不能静默回落到某个 App，
    否则会悄悄地跑一轮并覆盖日志。
    """
    arg = argv[1].strip().lower() if len(argv) >= 2 else 'slp'
    if arg in (config.appName['SLP'], 'slp'):
        return config.appName['SLP']
    if arg in (config.appName['XSG'], 'xsg'):
        return config.appName['XSG']
    print('未知参数: {}，可用取值: slp / xsg'.format(arg), flush=True)
    sys.exit(2)


def case_name(case):
    """用例名称：去掉 caseSlp./caseXsg. 这类目录前缀，保留 模块.类.方法"""
    case_id = case.id()
    # setUpClass/tearDownClass 报错时 unittest 抛给结果的是 _ErrorHolder，
    # 它的 id 形如 "setUpClass (模块.类)"，没有方法名也没有可裁剪的目录前缀，
    # 按模块拆分只会得到 "S)" 这种碎片，直接用它的 description
    if not getattr(case, '_testMethodName', None):
        return getattr(case, 'description', case_id)
    return case_id.split('.', 1)[-1] if '.' in case_id else case_id


def case_des(result, case):
    """用例描述：优先取方法签名里 des 的默认值，取不到时退回 docstring 中的用例描述"""
    des = getattr(result, 'test_des_map', {}).get(case)
    if des:
        return des
    return extract_des_from_docstring(getattr(case, '_testMethodDoc', None)) or ''


def _des_fallback(case):
    """des 取不到时的兜底说明：区分类级钩子报错与普通用例"""
    if not getattr(case, '_testMethodName', None):
        return '类级钩子（setUpClass/tearDownClass）报错，该类下的用例全部未执行'
    return '(未取到用例描述)'


def push_case_label(case):
    """推送清单里的用例标识：文件名 · 方法名

    case_name 给的是「模块.类.方法」，在手机上太长；类名对定位没有帮助（同一个
    文件里的用例都在同一个类里），只留文件名和方法名。跨文件的同名 test_001
    靠这一行就能区分开，不用再翻日志去猜是哪个文件。
    """
    name = case_name(case)
    parts = name.split('.')
    if len(parts) < 3:
        return name
    return '{} · {}'.format(parts[0] + '.py', parts[-1])


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
    if not raw_lines:
        return ''
    last_line = raw_lines[-1]
    # 异常末行自带 message 时（如 "AssertionError: 实际结果: 1999, 预期结果: 2000"）信息量最大，优先用它；
    # 空的 "AssertionError" 则退回下面的断言语句
    if ': ' in last_line and last_line.split(': ', 1)[0].endswith(('Error', 'Exception')):
        return last_line[:max_len]
    for line in raw_lines:
        # 覆盖 assert_x(...) / self.assert_x(...) / Assert.assert_x(...) 三种写法
        if line.startswith(('assert', 'self.assert', 'Assert.')):
            return line[:max_len]
    return last_line[:max_len]


def not_pass_count(result):
    """未通过用例数量：失败 + 异常 + 跳过"""
    return len(result.failures) + len(result.errors) + len(result.skipped)


# ---------- 失败性质：让「几条红」变成「红在哪一层」 ----------
# 同样是 3 条红，处置完全不同：环境挂→重跑；造数挂→看数据；接口 500→告警服务端；
# 断言不符→分成算错，要查代码。不分层的话，这三种情况在报告里长得一模一样。
FAIL_ENV = '环境'
FAIL_DATA = '造数'
FAIL_API = '接口'
FAIL_ASSERT = '断言'
FAIL_OTHER = '其他'
# 展示顺序固定：越靠前越应该先处理
FAIL_KINDS = (FAIL_ENV, FAIL_DATA, FAIL_API, FAIL_ASSERT, FAIL_OTHER)

# 判据全部来自实际见过的失败文本，不是猜的：
#   接口  assert_code 抛的「Actual Code: 500, Expected Code: 200」
#   断言  assert_equal/assert_body 抛的「实际结果: x, 预期结果: y」及其变体
#   环境  连不上库/缓存/接口：Can't connect、timed out、Max retries exceeded 等
#   造数  pymysql 的非连接类报错（表不存在、唯一键冲突），发生在用例前置阶段
#   其他  脚本自身（KeyError/TypeError）或没见过的形态
ENV_KEYWORDS = (
    "Can't connect", 'timed out', 'Timeout', 'Max retries exceeded',
    'HTTPConnectionPool', 'Connection refused', 'Name or service not known',
    'requests.exceptions', 'ConnectionError', 'ConnectionResetError',
    'BrokenPipeError', 'redis.exceptions',
)
ASSERT_KEYWORDS = ('实际结果:', '实际返回值', '预期返回内容包含')


def failure_kind(reason_text):
    """把一条未通过原因归到五个性质之一

    判断顺序有讲究：先认「Actual Code」再认断言关键字，最后才看连接类关键字。
    反过来会误判：一条断言失败的现场里也可能带着请求 URL（timed out 不会，但
    Max retries exceeded 这类文案会出现在网络失败里），宁可先认断言这种确定性文案。
    """
    text = str(reason_text or '')
    if 'Actual Code:' in text:
        return FAIL_API
    if any(keyword in text for keyword in ASSERT_KEYWORDS):
        return FAIL_ASSERT
    if any(keyword in text for keyword in ENV_KEYWORDS):
        return FAIL_ENV
    if 'pymysql' in text:
        return FAIL_DATA
    return FAIL_OTHER


def fail_kind_counts(result):
    """[(性质, 条数), ...]，只含出现过的性质，按 FAIL_KINDS 固定顺序"""
    counts = {}
    for items in (result.failures, result.errors):
        for _case, reason in items:
            kind = failure_kind(reason)
            counts[kind] = counts.get(kind, 0) + 1
    return [(kind, counts[kind]) for kind in FAIL_KINDS if counts.get(kind)]


def fail_kind_line(result):
    """推送用：只在有「非断言」失败时给一行性质分布

    全是断言失败时不加：那是这个仓库的常态（服务端算错了），单列一行「断言 3」
    只是把上面那句「3 失败」换个说法。混合时必给，否则「3 条里有 1 条是连不上库」
    这件事在群里看不出来——而它恰好决定要不要重跑。
    """
    pairs = fail_kind_counts(result)
    if not pairs or all(kind == FAIL_ASSERT for kind, _count in pairs):
        return []
    return ['<font color="comment">{}</font>'.format(
        '　'.join('{} {}'.format(kind, count) for kind, count in pairs))]


def fail_kind_report(result):
    """控制台/日志用：不论什么性质都完整列一行，作为这一轮的存档"""
    pairs = fail_kind_counts(result)
    if not pairs:
        return ''
    return '失败性质: {}'.format('，'.join('{} {} 条'.format(kind, count) for kind, count in pairs))


def result_counts(result):
    """
    执行结果计数。setUpClass/tearDownClass 报错时 unittest 把它记进 errors 但**不计入** testsRun，
    直接用 testsRun - 失败 - 异常 - 跳过 会把「通过」算成负数（实测 -1），
    或在总数上出现「用例总数: 0, 异常: 1」这种自相矛盾的输出，所以把这类类级报错补进总数。
    :return: {'total', 'pass', 'fail', 'error', 'skip'}
    """
    holder_errors = sum(1 for case, _reason in result.errors
                        if not getattr(case, '_testMethodName', None))
    return {'total': result.testsRun + holder_errors,
            # successes 是我们自己的 AllTestResult 新增的属性，取不到时用默认值
            'pass': len(getattr(result, 'successes', [])),
            'fail': len(result.failures),
            'error': len(result.errors),
            'skip': len(result.skipped)}


def group_stats(result):
    """按场景族统计本轮结果：{组名: {'total': 执行数, 'bad': 未通过数}}

    total 不含跳过：跳过的是已确认下线的功能，算进分母会让通过率失真，也会把
    「这一类最近在退化」的信号稀释掉。
    """
    stats = {}

    def touch(case, bad=0):
        item = stats.setdefault(group_of(case), {'total': 0, 'bad': 0})
        item['total'] += 1
        item['bad'] += bad

    for case in getattr(result, 'successes', []) or []:
        touch(case)
    for items in (result.failures, result.errors):
        for case, _reason in items:
            touch(case, 1)
    return stats


def group_lines(result, max_groups=5):
    """推送用：只列有未通过的场景族，按未通过数倒序；全绿时返回空

    全绿不列：每天把 24 个场景刷一遍，人就不看了。失败时这几行能直接回答
    「是某一类集中出问题，还是散落在多处」——两种情况的处置完全不同。
    """
    bad = [(name, item) for name, item in group_stats(result).items() if item['bad']]
    if not bad:
        return []
    bad.sort(key=lambda pair: (-pair[1]['bad'], pair[0]))
    lines = ['', '<font color="warning">未通过涉及 {} 个场景</font>'.format(len(bad))]
    for name, item in bad[:max_groups]:
        lines.append('　{}　{} 条中 {} 条'.format(name, item['total'], item['bad']))
    if len(bad) > max_groups:
        lines.append('　…另有 {} 个场景，见 log/notPassCase.log'.format(len(bad) - max_groups))
    return lines


def group_report(result):
    """控制台/日志用：列出本轮所有场景族（含零失败的），看全局用

    中文宽度不等宽，不追求列对齐——对齐不了反而更乱，宁可简单拼接。
    """
    stats = group_stats(result)
    if not stats:
        return ''
    lines = ['', LINE_SEP, '按场景族统计（不含跳过）', LINE_SEP]
    for name, item in sorted(stats.items(), key=lambda pair: (-pair[1]['bad'], pair[0])):
        mark = '' if not item['bad'] else '   ← {} 条未通过'.format(item['bad'])
        lines.append('{}　{} 条{}'.format(name, item['total'], mark))
    total = sum(item['total'] for item in stats.values())
    bad = sum(item['bad'] for item in stats.values())
    lines.append(LINE_SEP)
    lines.append('共 {} 个场景，{} 条执行，{} 条未通过'.format(len(stats), total, bad))
    lines.append(LINE_SEP)
    return '\n'.join(lines)


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
        # 0 条用例时写「全部用例通过」是自相矛盾的：套件没加载出来、CASE 写错都会是 0 条，
        # 这时候说「通过」等于把「什么都没跑」报成「没事」
        if not result_counts(result)['total']:
            return '{}\n本轮执行了 0 条用例'.format(header)
        return '{}\n无，全部用例通过'.format(header)
    return '{}\n{}'.format(header, '\n'.join(lines))


# 推送里最多列多少条：再多就不适合塞在聊天窗口里了，完整清单在 log/notPassCase.log
PUSH_FAIL_MAX = 10


def push_fail_lines(result, max_items=PUSH_FAIL_MAX):
    """推送用的未通过清单：编号 + 文件名·方法 + 用例描述 + 一行原因（灰字）

    层级靠缩进做，不靠分隔符：编号顶格且加粗，描述和原因各缩进两个全角空格，
    在手机上自然形成一个块、一眼能扫完。不用反引号：等宽字体夹在中文里显得格外生硬。
    """
    items = [(status, case, reason)
             for status, group in (('FAIL', result.failures), ('ERROR', result.errors))
             for case, reason in group]
    if not items:
        return []

    lines = []
    for index, (status, case, reason) in enumerate(items[:max_items], 1):
        # 标签只给「需要看的人一眼分开」的情形：异常与失败不同（用例没跑完 vs 跑完算错），
        # 非断言失败也不同（要重跑/看数据 vs 查代码）。普通断言失败不加标签，保持清单干净
        marks = ([] if status == 'FAIL' else ['异常'])
        kind = failure_kind(reason)
        if kind != FAIL_ASSERT:
            marks.append(kind)
        lines.append('')
        lines.append('**{}.**　{}{}'.format(index, push_case_label(case),
                                            '　({})'.format('·'.join(marks)) if marks else ''))
        des = case_des(result, case)
        if des:
            lines.append('　　{}'.format(des))
        detail = reason_brief(reason, max_len=200)
        if detail:
            lines.append('　　<font color="comment">{}</font>'.format(detail))
    if len(items) > max_items:
        lines.append('')
        lines.append('<font color="comment">　另有 {} 条未列出，完整清单 log/notPassCase.log</font>'.format(
            len(items) - max_items))
    return lines


# 推送里最多列几条跳过：跳过的理由基本一句话，5 条够看清趋势；再多就看日志
PUSH_SKIP_MAX = 5


def push_skip_lines(result, max_items=PUSH_SKIP_MAX):
    """推送用的「本轮没验」清单：跳过必须带理由，不能只留一个数字

    跳过 = 这条用例一条断言都没验。只报「跳过 3」的话，群里既看不到是哪三条、
    更看不到为什么：「探针没成交」「流水不带 gid 导致筛选失效」这类理由会天天一样，
    某条用例就这样安静地跳一整月，而报告一直是绿的。
    """
    items = list(result.skipped)
    if not items:
        return []
    lines = ['', '<font color="comment">**跳过 {} 条（不算通过，本轮这几条没验）**</font>'.format(
        len(items))]
    for case, reason in items[:max_items]:
        detail = ' '.join(str(reason).split()) or '无原因'
        if len(detail) > 80:
            detail = detail[:80] + '…'
        lines.append('　· {}　<font color="comment">{}</font>'.format(push_case_label(case), detail))
    if len(items) > max_items:
        lines.append('<font color="comment">　另有 {} 条未列出，完整清单 log/notPassCase.log</font>'.format(
            len(items) - max_items))
    return lines


def retry_digits(result):
    """推送尾部用的重试计数：只报条数，没有重试时明确写 0

    不写「3 条/4 次」：条数已经能回答「有没有用例被重试兜住」，次数留给
    log/retryCase.log。尾注挤到折行反而更难读。
    """
    records = getattr(result, 'retried', None) or {}
    return '重试 {}'.format(len(records))


def duration_text(seconds):
    """执行耗时：不足一分钟按秒，超过按「分秒」，避免出现 372.4s 这种要心算的写法"""
    seconds = int(round(seconds))
    if seconds < 60:
        return '{}s'.format(seconds)
    return '{}m{:02d}s'.format(seconds // 60, seconds % 60)


# 控制台 / 日志用的分隔线，宽度不用太长，云服务器上 80 列终端也能完整显示
LINE_SEP = '-' * 88


def not_pass_records(result):
    """
    把未通过用例整理成结构化列表，供控制台与日志输出使用
    :return: [{'status': 'FAIL', 'case': '模块.类.方法', 'des': '用例描述', 'detail': '一行明细'}, ...]
    """
    records = []
    for status, items in (('FAIL', result.failures),
                          ('ERROR', result.errors),
                          ('SKIP', result.skipped)):
        for case, reason in items:
            if status == 'SKIP':
                detail = ' '.join(str(reason).split())  # 跳过原因可能多行，压成一行
            else:
                detail = reason_brief(reason, max_len=500)
            records.append({
                'status': status,
                'case': case_name(case),
                'des': case_des(result, case) or _des_fallback(case),
                'detail': detail,
            })
    return records


def fail_detail_text(result):
    """
    失败/异常的完整堆栈（保留真实换行，直接写文件用）
    注意不要用 unittest 的 failures 列表直接 format：那是带 \n 转义的 repr，
    整串会挤成一行，日志里根本看不清堆栈。
    :return: 多行字符串，每段为 [FAIL] 用例名 | des 后接完整堆栈
    """
    sections = []
    for status, items in (('FAIL', result.failures), ('ERROR', result.errors)):
        for case, reason in items:
            text = '[{}] {} | {}\n{}'.format(
                status, case_name(case), case_des(result, case) or _des_fallback(case), str(reason).strip())
            # 失败现场：入参 / 响应体 / 账户快照。原来这些只在控制台滚一次，
            # 看不到了就只能重新跑一轮，全量 7 分钟的成本全花在复现上
            scene = Scene.archived(case.id())
            if scene:
                text += '\n' + scene
            sections.append(text)
    return '\n{}\n'.format(LINE_SEP).join(sections) if sections else ''


def not_pass_report(result, title='未通过用例'):
    """
    控制台 / 日志用的未通过用例完整清单：编号 + 状态 + 用例名称 + des + 失败明细
    与 not_pass_summary 的区别：这里不带 4096 字节限制，有多少列多少，适合直接看日志
    :return: 多行字符串
    """
    records = not_pass_records(result)
    counts = {status: sum(1 for record in records if record['status'] == status)
              for status in ('FAIL', 'ERROR', 'SKIP')}
    lines = ['', LINE_SEP,
             '{}（共 {} 条）  失败 {} / 异常 {} / 跳过 {}'.format(
                 title, len(records), counts['FAIL'], counts['ERROR'], counts['SKIP']),
             LINE_SEP]
    if not records:
        # 0 条用例时不能写「全部通过」：套件没加载出来、CASE 写错都会落到这里，
        # 这时说「通过」等于把「什么都没跑」报成「没事」
        lines.append('本轮执行了 0 条用例' if not result_counts(result)['total'] else '无，全部用例通过')
        lines.append(LINE_SEP)
        return '\n'.join(lines)
    for index, record in enumerate(records, 1):
        lines.append('[{:>3}] {:<5} {}'.format(index, record['status'], record['case']))
        lines.append('     用例: {}'.format(record['des'] or '(未取到用例描述)'))
        if record['detail']:
            lines.append('     原因: {}'.format(record['detail']))
    lines.append(LINE_SEP)
    return '\n'.join(lines)


def retry_report(result, title='重试后才通过的用例'):
    """列出「重试后才通过」的用例：最终状态是 PASS，但每条背后都是一次真实断言失败

    一轮全量实测 54 次重试。它们不会出现在 failCase.log（最终没失败），也不会被
    notPassCase.log 提到，此前唯一的痕迹是控制台里滚过的那行 print——一轮全量上千行，
    没人会盯着找。而这条清单恰恰是最该看的：同一个断言第一轮读到 0、第二轮读到正确值，
    要么是等得不够，要么被测逻辑真的有时序问题，两种都不是「通过」可以盖过的。
    """
    records = getattr(result, 'retried', None) or {}
    if not records:
        return ''
    total = sum(len(item['events']) for item in records.values())
    lines = ['', LINE_SEP,
             '{}（共 {} 条用例，累计重试 {} 次）'.format(title, len(records), total),
             LINE_SEP]
    # 重试次数多的排前面：重试 2 次才过的比 1 次的更值得先看
    for item in sorted(records.values(), key=lambda one: -len(one['events'])):
        lines.append('[重试 {} 次] {}'.format(len(item['events']), item['case']))
        lines.append('     用例: {}'.format(item['des'] or '(未取到用例描述)'))
        for _, round_no, detail in item['events']:
            lines.append('     第 {} 轮失败: {}'.format(round_no, str(detail).replace('\n', ' ')))
    lines.append(LINE_SEP)
    return '\n'.join(lines)


def retry_summary(result):
    """推送/控制台用的一行摘要：没有重试时也要明确写「无」，否则分不清是没重试还是没统计

    带上占比是为了看趋势：重试率高说明有稳定存在的服务端问题（实测约 8%，集中在
    naming_song 的「房间类型错误」）。这类失败被 @Retry 兜住后报告永远是全绿，
    这个百分比就是它唯一的存在证明——服务端修好会掉到 0，恶化会涨。
    """
    records = getattr(result, 'retried', None) or {}
    if not records:
        return '重试后才通过: 无'
    total = sum(len(item['events']) for item in records.values())
    count = result_counts(result)['total']
    rate = '（{:.1f}%）'.format(len(records) * 100.0 / count) if count else ''
    return '重试后才通过: {} 条 / 共 {} 次{}，明细见 log/retryCase.log'.format(
        len(records), total, rate)


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
