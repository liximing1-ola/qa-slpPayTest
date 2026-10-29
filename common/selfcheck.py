# coding=utf-8
"""框架自身守卫逻辑的自检：不连服务端、不连数据库

为什么需要这个：频控退避、失败现场快照这类逻辑，在真实全量里可能一整轮都触发不到
（2026-10-27 那轮 137 条全绿、没有一次频控、没有一次失败），于是「写了」和
「真的按预期工作」之间始终差一步。等真需要它的时候才发现坏了，代价就是一次假红 + 一轮复现。

自检只验证框架行为，不碰业务预期值：
  1. 频控命中后退避重试、次数耗尽后把响应交回用例、非频控响应不误判；
  2. 失败现场能拼出入参/响应/账户快照，且自己出任何错都不影响用例结论；
  3. 读账户表用的轮询版真的会重读，超时也会把「等了多少秒」写进失败原因。
     全仓 567 处余额/统计断言都靠它，它一旦退化成「只读一次」，全量会重新回到
     37% 的用例靠重试才有结果的状态。
4. 频控退避不跟着请求间隔缩水（降默认间隔是为了提速，不能顺带把退避调弱）。

运行：python -m common.selfcheck
"""
import sys
import time

from common import Scene


class _FakeResponse(object):
    """够 post_request_session 用的最小响应体"""

    def __init__(self, body, code=200, text=None):
        self._body = body
        self.status_code = code
        self.text = text if text is not None else str(body)
        # 真响应一定有 headers，post_request_session 会把它带进 result 供排查用；
        # 这里给一个带实例标识的假头，让自检也走一遍那条取值路径
        self.headers = {'X-Backend-Server': 'fake-node-1', 'Content-Type': 'application/json'}

        class _Elapsed(object):
            @staticmethod
            def total_seconds():
                return 0.01

        self.elapsed = _Elapsed()

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class _ScriptedRequests(object):
    """替换 requests 模块：按预设序列返回响应，并记下实际发了几次"""

    def __init__(self, bodies):
        import requests
        self._bodies = list(bodies)
        self.calls = []
        self.RequestException = requests.RequestException

    def post(self, url=None, data=None, headers=None, verify=None, timeout=None):
        self.calls.append(data)
        body = self._bodies.pop(0) if self._bodies else {'success': True}
        return _FakeResponse(body)


class _FakeTime(object):
    """把 sleep 换成记账，跑得快且能断言退避是递增的

    sleep 必须同时推进虚拟时钟：_wait_for_interval 是「只补足与上次请求的差额」，
    如果睡完时间不动，下一轮会认为间隔还没到，凭空多记一次等待（自检自己先红）。
    """

    def __init__(self):
        self.sleeps = []
        self._offset = 0.0

    def time(self):
        return time.time() + self._offset

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self._offset += seconds


_FAILED = []
_TOTAL = []


def _check(name, func):
    """跑一项自检，打印结果，不在中间抛

    除了 AssertionError 还要接其它异常：检查函数自己写崩（KeyError / AttributeError /
    连库超时）同样是一条要报的结果。只接 AssertionError 的话，一项崩了会中断整轮，
    后面那些项看上去就像「没报错」。
    """
    _TOTAL.append(name)
    try:
        func()
        print('  OK   {}'.format(name))
    except AssertionError as error:
        _FAILED.append(name)
        print('  FAIL {} -> {}'.format(name, error))
    except SystemExit as error:
        # 被检查的代码自己 sys.exit 了（比如 build_suite 拒绝加载写错的用例名）：
        # 这也是一条结果，不能让整轮自检在这里就断掉
        _FAILED.append(name)
        print('  FAIL {} -> 检查过程中退出（SystemExit {}）'.format(name, error.code))
    except Exception as error:
        _FAILED.append(name)
        print('  FAIL {} -> {}: {}'.format(name, type(error).__name__, error))


def _with_scripted(bodies, interval=2.0, frequent_retry=2, backoff=2.0):
    """装好假 requests / 假 token / 假 sleep，返回 (request 模块, 假 requests, 假 time)"""
    from common import Request

    fake_requests = _ScriptedRequests(bodies)
    fake_time = _FakeTime()
    # 退避基数也要固定：它现在与环境变量解耦，若本机 export 了 FREQUENT_BACKOFF，
    # 自检会拿着别的值去比 2.0/4.0 而假红
    old = (Request.requests, Request.time, Request.Session, Request.REQUEST_INTERVAL,
           Request.FREQUENT_RETRY, Request.FREQUENT_BACKOFF)
    Request.requests = fake_requests
    Request.time = fake_time
    Request.REQUEST_INTERVAL = interval
    Request.FREQUENT_RETRY = frequent_retry
    Request.FREQUENT_BACKOFF = backoff
    Request._last_request_at.clear()

    class _FakeSession(object):
        @staticmethod
        def checkUserToken(operate, app_name='dev', uid=None, token=''):
            return 'fake-token'

    Request.Session = _FakeSession
    return Request, fake_requests, fake_time, old


def _restore(old):
    from common import Request
    (Request.requests, Request.time, Request.Session, Request.REQUEST_INTERVAL,
     Request.FREQUENT_RETRY, Request.FREQUENT_BACKOFF) = old


def check_frequent_retry_then_success():
    """命中一次频控 -> 退避后重试 -> 最终拿到成功响应"""
    Request, fake_requests, fake_time, old = _with_scripted([
        {'success': False, 'msg': '请勿频繁操作'},
        {'success': True, 'msg': ''},
    ])
    try:
        res = Request.post_request_session('test.local/frequent', {'a': 1}, tokenName='slp', pay_uid=1)
    finally:
        _restore(old)
    assert len(fake_requests.calls) == 2, '应发 2 次请求，实际 {}'.format(len(fake_requests.calls))
    assert res['body']['success'] is True, '重试后应拿到成功响应'
    assert fake_time.sleeps == [2.0], '退避应为 1 倍间隔 2.0，实际 {}'.format(fake_time.sleeps)


def check_frequent_exhausted_returns_response():
    """连续命中至重试上限：必须把频控响应原样交回，不能抛异常、也不能假装成功"""
    Request, fake_requests, _, old = _with_scripted([
        {'success': False, 'msg': '请勿频繁操作'},
        {'success': False, 'msg': '请求太慢了，请稍后重试'},
        {'success': False, 'msg': '请勿频繁操作'},
        {'success': True},
    ], frequent_retry=2)
    try:
        res = Request.post_request_session('test.local/frequent', {'a': 1}, tokenName='slp', pay_uid=1)
    finally:
        _restore(old)
    assert len(fake_requests.calls) == 3, '上限 2 次重试应共发 3 次，实际 {}'.format(len(fake_requests.calls))
    assert res['body']['success'] is False, '耗尽重试后应返回最后一次的失败响应，不能被吞成成功'


def check_no_frequent_single_call():
    """正常响应不能被当成频控：只发一次，不退避"""
    Request, fake_requests, fake_time, old = _with_scripted([{'success': True, 'msg': 'ok'}])
    try:
        Request.post_request_session('test.local/normal', {'a': 1}, tokenName='slp', pay_uid=1)
    finally:
        _restore(old)
    assert len(fake_requests.calls) == 1, '正常响应不应重试，实际发了 {} 次'.format(len(fake_requests.calls))
    assert fake_time.sleeps == [], '正常响应不应有退避，实际 {}'.format(fake_time.sleeps)


def check_all_keywords():
    """每种实测见过的频控文案都要能命中（只认一种文案会漏判，把频控丢给用例断言成假红）"""
    for msg in ('请勿频繁操作', '请求太慢了，请稍后重试', '请求太快', '请稍后重试'):
        Request, fake_requests, _, old = _with_scripted([
            {'success': False, 'msg': msg},
            {'success': True},
        ])
        try:
            Request.post_request_session('test.local/kw', {'a': 1}, tokenName='slp', pay_uid=1)
        finally:
            _restore(old)
        assert len(fake_requests.calls) == 2, '文案「{}」未被识别为频控'.format(msg)


def check_backoff_is_increasing():
    """退避要递增：固定间隔容易连着撞同一个防重窗口"""
    Request, _, fake_time, old = _with_scripted([
        {'success': False, 'msg': '请勿频繁操作'},
        {'success': False, 'msg': '请勿频繁操作'},
        {'success': True},
    ], interval=2.0, frequent_retry=2)
    try:
        Request.post_request_session('test.local/backoff', {'a': 1}, tokenName='slp', pay_uid=1)
    finally:
        _restore(old)
    # 退避把时间推过去之后，_wait_for_interval 不会再补间隔，所以这里只会剩退避这两次
    backoffs = [s for s in fake_time.sleeps if s >= 2.0]
    assert backoffs == [2.0, 4.0], '退避应递增 2.0/4.0，实际 {}'.format(fake_time.sleeps)


def check_backoff_independent_of_interval():
    """调小请求间隔不能顺带把频控退避也调弱

    退避原本写的是 REQUEST_INTERVAL × n，把默认间隔从 2 降到 1 之后，
    频控退避会悄悄变成 1s/2s——提速的代价就变成了「撞频控后更容易再撞」。
    这条锁住两者解耦：间隔 1 秒时退避仍必须是 2.0/4.0。
    """
    Request, _, fake_time, old = _with_scripted([
        {'success': False, 'msg': '请勿频繁操作'},
        {'success': False, 'msg': '请勿频繁操作'},
        {'success': True},
    ], interval=1.0, frequent_retry=2, backoff=2.0)
    try:
        Request.post_request_session('test.local/decouple', {'a': 1}, tokenName='slp', pay_uid=1)
    finally:
        _restore(old)
    backoffs = [s for s in fake_time.sleeps if s >= 2.0]
    assert backoffs == [2.0, 4.0], '间隔 1s 时退避仍应为 2.0/4.0，实际 {}'.format(fake_time.sleeps)


def check_non_json_body_not_frequent():
    """网关返回 html 时 body 是字符串，不能因此崩掉或误判成频控"""
    Request, fake_requests, _, old = _with_scripted([ValueError('no json')])
    try:
        res = Request.post_request_session('test.local/html', {'a': 1}, tokenName='slp', pay_uid=1)
    finally:
        _restore(old)
    assert len(fake_requests.calls) == 1, '非 json 响应不该重试'
    assert isinstance(res['body'], str), '非 json 响应应保留原始文本，实际 {}'.format(type(res['body']))


def _with_fake_assert_time():
    """把 common.Assert 的 time 换成假时钟，让轮询自检既快又能数出读了几次"""
    from common import Assert
    fake = _FakeTime()
    old = Assert.time
    Assert.time = fake
    return Assert, fake, old


def check_eventually_polls_until_match():
    """分成是异步落库的：第一次读到 0 不能就此定论，必须继续读到预期值"""
    from common import Consts
    Assert, _, old = _with_fake_assert_time()
    values = [0, 0, 60]
    reads = []

    def read():
        reads.append(1)
        return values.pop(0) if values else 60

    mark = len(Consts.fail_case_reason)
    try:
        Assert.assert_equal_eventually(read, 60, timeout=10, interval=1)
    finally:
        Assert.time = old
    assert len(reads) == 3, '应读到第 3 次才达标，实际读了 {} 次'.format(len(reads))
    assert len(Consts.fail_case_reason) == mark, '中间态不能留下失败原因，否则报告里会堆一串 0'


def check_eventually_timeout_reports_waited():
    """一直读不到时，失败原因里必须能看出「等过多久」——结算变慢和分账算错是两种问题"""
    from common import Consts
    Assert, _, old = _with_fake_assert_time()
    mark = len(Consts.fail_case_reason)
    try:
        try:
            Assert.assert_equal_eventually(lambda: 0, 60, timeout=0.3, interval=0.1)
        except AssertionError as error:
            text = str(error)
            assert '预期结果: 60' in text, '失败信息应带预期值: {}'.format(text)
            assert len(Consts.fail_case_reason) == mark + 1, '只应留一条失败原因，实际多出 {} 条'.format(
                len(Consts.fail_case_reason) - mark)
            assert '已轮询' in Consts.fail_case_reason[-1], '应说明轮询次数与等待时长: {}'.format(
                Consts.fail_case_reason[-1])
        else:
            raise AssertionError('一直读不到就该失败，不能静默通过')
    finally:
        Assert.time = old
        del Consts.fail_case_reason[mark:]


def check_eventually_first_hit_single_read():
    """首轮就命中时只读一次：打赏方扣款本来就是同步的，不该被多读一遍拖慢"""
    Assert, fake, old = _with_fake_assert_time()
    reads = []

    def read():
        reads.append(1)
        return 60

    try:
        Assert.assert_equal_eventually(read, 60)
    finally:
        Assert.time = old
    assert len(reads) == 1, '首轮命中就该收手，实际读了 {} 次'.format(len(reads))
    assert fake.sleeps == [], '首轮命中不该有等待，实际 {}'.format(fake.sleeps)


def check_scene_render():
    """失败现场要能看到本次入参、响应，以及从入参里提出来要查的账号"""
    Scene.begin_case('demo.test_001')
    Scene.record_exchange({'uid': '200255399', 'params': {'to': '200255399', 'uids': '1,2'}},
                          200254777, 200, {'success': False, 'msg': '余额不足'})
    text = Scene._render('demo.test_001')
    for expect in ('[请求 1] pay_uid=200254777', '入参:', 'HTTP 200', '余额不足'):
        assert expect in text, '现场缺少「{}」'.format(expect)
    uids = Scene._uids_from({'uid': '200255399', 'params': {'to': '200255399'}}, 200254777)
    assert uids == ['200254777', '200255399'], '提取的账号不对: {}'.format(uids)


def check_scene_buffer_limit():
    """现场只保留最近几次请求，不能把 failCase.log 撑爆"""
    Scene.begin_case('demo.test_002')
    for index in range(Scene.MAX_EXCHANGES + 3):
        Scene.record_exchange({'seq': index}, 1, 200, {'success': False})
    assert len(Scene._exchanges) == Scene.MAX_EXCHANGES, '缓冲应只留 {} 条'.format(Scene.MAX_EXCHANGES)
    assert Scene._exchanges[-1]['payload']['seq'] == Scene.MAX_EXCHANGES + 2, '应保留最新的那几条'


def check_scene_empty_and_archive():
    """无请求、快照自身抛错这两种情况都不能影响用例结论"""
    Scene.begin_case('demo.test_003')
    text = Scene._render('demo.test_003')
    assert '未记录到接口请求' in text, '无请求时应明确写出来，否则会被误读成「没发过请求」还是「没记上」'

    from common.conSlpXsgMysql import conMysql as mysql
    old = mysql.selectRawDict

    def boom(sql):
        raise RuntimeError('db down')

    mysql.selectRawDict = staticmethod(boom)
    try:
        Scene.record_exchange({'uid': '1'}, 1, 200, {'success': False})
        Scene.archive('demo.test_004')
        text = Scene.archived('demo.test_004')
    finally:
        mysql.selectRawDict = old
    assert '数据库不可用' in text, 'DB 不可用时应给一句提示而不是静默'
    assert Scene.archived('不存在的用例') == '', '未归档的用例应返回空串'


def check_seed_checks_shape():
    """种子清单的结构守卫：SQL 恰好一个 {} 占位、期望项非空无重复、能真的格式化

    体检写错了会天天误拦整轮回归，比不做体检更糟，所以清单本身也要能被机器检查。
    这里只验结构（不连库），数据到底在不在由 preflight 在服务器上查。
    """
    from common.envData import seed_checks

    items = seed_checks()
    assert items, '种子清单不能为空'
    names = [item[0] for item in items]
    assert len(names) == len(set(names)), '种子项名称重复：{}'.format(names)
    for name, sql, expected, hint, blocking in items:
        assert sql.count('{}') == 1, '{} 的 SQL 必须恰好一个占位符'.format(name)
        assert expected, '{} 的期望项不能为空'.format(name)
        assert len(set(expected)) == len(expected), '{} 的期望项有重复'.format(name)
        assert hint, '{} 缺少缺失时的修复提示'.format(name)
        assert isinstance(blocking, bool), '{} 的阻断标记必须是 bool'.format(name)
        # 占位符真的能填进去：格式写错要到服务器上才发现就太晚了
        filled = sql.format(','.join(str(item) for item in expected))
        assert 'in (' in filled, '{} 格式化后不像 in 查询：{}'.format(name, filled)
        assert '{}' not in filled, '{} 格式化后仍有未填的占位符'.format(name)


def check_env_config_shape():
    """本机环境配置的两条一致性：模板覆盖所需项、环境变量优先级最高

    模板少一项，照着填的人也配不出这一项，然后 preflight 报「缺少 XXX」，
    而人明明按模板填过了——这种自相矛盾最难查。
    优先级反过来同样麻烦：env_local.py 盖过环境变量，运维在 crontab 里改的值就不生效了。
    """
    import ast
    import os

    from common import envLocal

    template = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env_local.example.py')
    with open(template, encoding='utf-8') as handle:
        tree = ast.parse(handle.read())
    written = {node.targets[0].id for node in tree.body
               if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    absent = [name for name in envLocal.REQUIRED if name not in written]
    assert not absent, 'env_local.example.py 缺模板项：{}'.format(absent)

    # 临时改一个环境变量，确认它盖过本地文件里的值；改完要原样还原，不能污染后续检查
    probe = '__selfcheck_probe__'
    old = os.environ.get('APP_HOST')
    os.environ['APP_HOST'] = probe
    try:
        assert envLocal.get('APP_HOST') == probe, '环境变量没能盖过其它来源'
        assert probe not in envLocal.missing(), '缺项判断没认环境变量'
    finally:
        if old is None:
            del os.environ['APP_HOST']
        else:
            os.environ['APP_HOST'] = old


def check_flow_split():
    """流水聚合：付款行单独拎出来，收款行按（uid, op）合并成条数与金额

    这里算错，「少写一笔」会被另一个收款人的行抵掉，付款行还会和收款行互相抵消，
    红和绿都会失去意义。

    付款行按 **付款方 uid** 认，不按 op 名认：现场实测这个厅写的是 op='consume'，
    op='pay' 一次都没出现过。按 op 名认会把付款行当成一条「收款写路径」，
    探针 1 个付款账号、并发 4 个，两边键集合永远不相等，报出来的红是假的；
    更糟的是「付款行数 = 成功笔数」那道校验因为探针付款行为空而整段跳过（实测踩过）。
    """
    from caseStress.tools import split_flows

    rows = [
        {'id': 1, 'uid': 200254777, 'money': 100, 'op': 'pay'},
        {'id': 2, 'uid': 200255399, 'money': 71, 'op': 'income'},
        {'id': 3, 'uid': 200258475, 'money': 6, 'op': 'income'},
        {'id': 4, 'uid': 200255399, 'money': 71, 'op': 'income'},
        {'id': 5, 'uid': 200255209, 'money': 3, 'op': 'tax'},
        {'id': 6, 'uid': 200255399, 'money': 1, 'op': 'income'},
    ]
    income, pay = split_flows(rows)
    assert len(pay) == 1, '付款行应只有 1 行，实际 {}'.format(len(pay))
    assert income[(200255399, 'income')] == [3, 143], \
        '同一收款人的多行应合并成 3 行 143，实际 {}'.format(income.get((200255399, 'income')))
    assert income[(200258475, 'income')] == [1, 6], '厅长的 income 行应单独成一条写路径'
    # 同一个 uid 换个 op 就是另一条写路径：把 tax 并进 income 会隐藏「税多写一行」
    assert income[(200255209, 'tax')] == [1, 3], 'op 不同不能合并'
    assert (200254777, 'pay') not in income, '付款行不能进收款聚合'
    assert split_flows([]) == ({}, []), '没有流水时应返回 ({}, [])'

    # 实测形态：付款方写的是 op='consume'，必须按 uid 认出来
    real = [
        {'id': 11, 'uid': 200254777, 'money': 100, 'op': 'consume'},
        {'id': 12, 'uid': 200250759, 'money': 100, 'op': 'consume'},
        {'id': 13, 'uid': 200255399, 'money': 80, 'op': 'income'},
    ]
    income, pay = split_flows(real, payers=(200254777, 200250759))
    assert len(pay) == 2, '付款方名下的行不论 op 叫什么都要算付款行，实际 {}'.format(pay)
    assert income == {(200255399, 'income'): [1, 80]}, \
        '付款行不能混进收款聚合，实际 {}'.format(income)

    # 自刷场景：付款方恰好也是收款人时不能把收款行吞掉——所以 payers 由调用方自己传，
    # 只传本轮下单的账号，不能把收款人一并塞进来
    income, pay = split_flows(real, payers=())
    assert (200254777, 'consume') in income, '不传付款方时退回按 op 名认，不能凭空造付款行'


def check_flow_wait_stable():
    """等流水：条数不再增长才返回；一直没有流水时要把空结果交回，不能抛也不能死等

    只看「至少 1 行」会漏掉后半段：一笔订单先写主播那行、再写厅和公会长，
    读到 1 行就收工，后面两条写路径就不会被验——而报告上看不出来。

    行数静默也不等于写完了：现场实测「4 笔分成都到了、付款行只到 3 行」，然后行数
    静默了 0.6 秒。所以多了 await_uids 这个下界——它只延长等待，不放宽断言。
    """
    from caseStress import tools

    old_read = tools.read_gift_flows
    old_timeout = tools.WAIT_TIMEOUT
    old_interval = tools.WAIT_INTERVAL
    try:
        tools.WAIT_TIMEOUT = 0.5
        tools.WAIT_INTERVAL = 0.01

        # 分两段写：前两次只读到 1 行，之后才补齐 3 行
        rounds = [[{'uid': 1}], [{'uid': 1}], [{'uid': 1}, {'uid': 2}, {'uid': 3}]]
        rounds += [[{'uid': 1}, {'uid': 2}, {'uid': 3}]] * 3
        calls = []

        def staged(after_id, gid):
            calls.append(1)
            return rounds.pop(0) if rounds else [{'uid': 1}, {'uid': 2}, {'uid': 3}]

        tools.read_gift_flows = staged
        rows = tools.wait_flows_stable(0, 69, least=1, quiet=3)
        assert len(rows) == 3, '应等到 3 行落完再返回，实际 {}'.format(rows)
        assert len(calls) >= 5, '分两段写时不能读到第一段就返回，实际只读了 {} 次'.format(len(calls))

        # 行数早就静默了，但第 4 个付款账号的行后到：光看行数会把它当成没写
        early = [{'uid': 1}, {'uid': 2}, {'uid': 3}]
        later = early + [{'uid': 4}]
        rounds[:] = [early] * 6 + [later] * 6
        tools.read_gift_flows = staged
        rows = tools.wait_flows_stable(0, 69, least=1, quiet=2, await_uids=(4,))
        assert len(rows) == 4, \
            '付款账号还没落行时，不能因为行数静默就返回，实际 {}'.format(len(rows))

        # 真没写时也要到超时才放手：不能死等，也不能刚超时就把半截结果当成完整
        rounds[:] = [early] * 1000
        tools.read_gift_flows = staged
        started = time.time()
        rows = tools.wait_flows_stable(0, 69, least=1, quiet=2, await_uids=(9,))
        waited = time.time() - started
        assert len(rows) == 3, '等不到时应把已有结果交回，实际 {}'.format(rows)
        assert waited >= 0.4, '等不到时应到超时才返回，实际 {:.2f}s'.format(waited)

        tools.read_gift_flows = lambda after_id, gid: []
        started = time.time()
        rows = tools.wait_flows_stable(0, 69, least=1)
        waited = time.time() - started
        assert rows == [], '没有流水时应返回空列表'
        assert waited >= 0.4, '应在超时后才返回，实际 {:.2f}s'.format(waited)
    finally:
        tools.read_gift_flows = old_read
        tools.WAIT_TIMEOUT = old_timeout
        tools.WAIT_INTERVAL = old_interval


def check_income_scaled():
    """分成按成功笔数放大：多写一行、少一条写路径、金额偏差都必须比得出来

    收款侧的断言就是「并发批次 == 探针值 × 成功笔数」。这一步算错或比得太粗，
    「少一笔分成」会变成绿：只比总行数时「主播多一行、厅长少一行」互相抵消；
    只比金额时「一条写路径掰成两条写」看不出来（两边总额一样）。

    所以这里不光验乘法，还要验比较本身能区分四种错法——只验「乘法对」等于
    验了一段永远绿的代码。
    """
    from caseStress.tools import expected_rows, scale_income

    # 实测形态：这个厅只给主播分，一笔写 1 行 80 元
    probe = {(200255399, 'income'): [1, 80]}
    assert scale_income(probe, 4) == {(200255399, 'income'): [4, 320]}, \
        '4 笔成交应放大成 4 行 320 元，实际 {}'.format(scale_income(probe, 4))

    # 71:6:3 形态：三条写路径各自放大，比例不能混
    three = {(200255399, 'income'): [1, 71],
             (200258475, 'income'): [1, 6],
             (200255209, 'tax'): [1, 3]}
    assert scale_income(three, 4) == {(200255399, 'income'): [4, 284],
                                      (200258475, 'income'): [4, 24],
                                      (200255209, 'tax'): [4, 12]}, \
        '三条写路径要各自放大，实际 {}'.format(scale_income(three, 4))

    # 一笔都没成交：写路径和条数都应放大成 0，任何一行都不该存在
    assert scale_income(probe, 0) == {(200255399, 'income'): [0, 0]}, \
        'success=0 时条数与金额都该是 0'
    assert scale_income({}, 4) == {}, '探针没读到写路径时不能凭空造出 key'

    # 四种错法都必须与放大值不等，否则断言抓不到
    cases = [
        ({(200255399, 'income'): [5, 400]}, probe, 4, '多写一行'),
        ({(200255399, 'income'): [4, 320], (200258475, 'income'): [4, 24]}, probe, 4,
         '凭空多一条写路径'),
        ({(200255399, 'income'): [4, 360]}, probe, 4, '金额偏差'),
        ({(200255399, 'income'): [1, 80]}, probe, 0, '一笔没成交却发了分成'),
    ]
    for batch, base, success, why in cases:
        assert batch != scale_income(base, success), \
            '{} 必须与放大值不等，否则漏写/多写都抓不到'.format(why)

    # 71:6:3 下少一条写路径：键集合缺一个，整体比较必须不相等
    missing = {(200255399, 'income'): [4, 284], (200258475, 'income'): [4, 24]}
    assert missing != scale_income(three, 4), '少一条写路径必须与放大值不等'

    # 等待下界：探针行数 × 成功笔数。它也不写死「一笔几行」
    assert expected_rows(probe, [{'uid': 1}], 4) == 8, '1 行收款 + 1 行付款 × 4 笔 应是 8 行'
    assert expected_rows(probe, [], 4) == 4, '探针没有付款行时只算收款行，不能多算期望'
    assert expected_rows(three, [], 4) == 12, '71:6:3 一笔三行，四笔应是 12 行'
    assert expected_rows(probe, [{'uid': 1}], 0) == 0, '一笔都没成交时期望 0 行'


def check_window_tested():
    """同账号连发多笔：全被频控挡下必须认成「没验到」，不能算绿

    频控在请求层就被挡下，那一笔没走到余额与幂等校验。四个账号各挡一笔时，扣款侧
    仍然「各扣一笔、全对」，报告上是一条通过——但「同账号重复提交」这个场景一次
    都没验到。2026-10-29 的 test_003 就是这样绿的（4 次频控）。
    """
    from caseStress.tools import concurrent_window_tested

    assert concurrent_window_tested({'a': ['limited', 'success']}) == [], \
        '两笔里有一笔被频控挡下，这一对不算验到'
    assert concurrent_window_tested({'a': ['success', 'limited']}) == [], '两笔顺序无关'
    assert concurrent_window_tested({'a': ['success', 'rejected']}) == ['a'], \
        '没被限流的账号才算真的走到业务校验'
    assert concurrent_window_tested({'a': ['limited', 'limited'],
                                     'b': ['rejected', 'success']}) == ['b'], \
        '只要有一对真的送到校验，本轮就不是「什么都没验到」'
    assert concurrent_window_tested({'a': ['limited', 'limited']}) == [], \
        '全被挡下时必须返回空，否则调用方不会跳'
    assert concurrent_window_tested({}) == [], '没有账号时返回空'


def check_classify_responses():
    """响应四分类：成功 / 频控 / 业务拒绝 / 服务端异常

    并发用例的「绿」全靠这个判断：把频控当成功会假绿，把业务拒绝当异常会假红。
    网关返回 HTML 时 body 是字符串（common.Request 会原样带回），直接 .get 会抛
    AttributeError，用例就变成 ERROR——报告里看不出是服务端丢了个 502。
    """
    from caseStress.tools import classify

    cases = [
        ({'code': 200, 'body': {'success': True}}, 'success', '布尔真'),
        ({'code': 200, 'body': {'success': '1'}}, 'success', '字符串 1'),
        ({'code': 200, 'body': {'success': False, 'msg': '请勿频繁操作'}}, 'limited', '频控文案'),
        ({'code': 200, 'body': {'success': False, 'msg': ''}}, 'rejected', '实测出现的空 msg 拒绝'),
        ({'code': 200, 'body': {'success': 0, 'msg': '余额不足'}}, 'rejected', '余额不足'),
        ({'code': 500, 'body': {'msg': '内部错误'}}, 'broken', 'HTTP 500'),
        ({'code': 200, 'body': '<html>502 Bad Gateway</html>'}, 'broken', '网关返回 HTML'),
        ({'code': -1, 'body': {'msg': 'timeout'}, 'error': True}, 'broken', '请求层抛错'),
    ]
    for res, expect, label in cases:
        got = classify(res)
        assert got == expect, '{} 应判为 {}，实际 {}'.format(label, expect, got)


def check_push_skip_lines():
    """跳过的用例必须带理由进推送：只留一个数字等于没报

    跳过 = 这条用例一条断言都没验。只在尾部报「跳过 3」，群里看不到是哪三条、
    更看不到为什么；而「探针没成交」「流水不带 gid」这类理由是长期稳定的，
    某条用例会就这样安静地跳一整月，报告一直是绿的。
    """
    from common import report

    class _Case(object):
        # case_name 靠它区分「普通用例」与「类级钩子报错」，没有它日期拼出来的名字是错的
        _testMethodName = True

        def __init__(self, method):
            self._method = method

        def id(self):
            return 'caseStress.test_pay_concurrent.TestConcurrentPay.' + self._method

    class _Result(object):
        failures = []
        errors = []
        skipped = []

    result = _Result()
    result.skipped = [
        (_Case('test_005'), '探针未成交（rejected），本轮没做流水对账'),
        (_Case('test_006'), '流水筛选失效，本轮没做对账：按 uid 查到 2 行但不带 gid'),
    ]
    text = '\n'.join(report.push_skip_lines(result))
    assert '跳过 2 条' in text and '不算通过' in text, '标题必须说清「跳过不算通过」: ' + text
    assert 'test_pay_concurrent.py · test_005' in text, '要点到文件名·方法，不能只给类名: ' + text
    assert '探针未成交（rejected），本轮没做流水对账' in text, '理由必须原样带出来: ' + text

    assert report.push_skip_lines(_Result()) == [], '没有跳过时不能凭空多出一行'

    # 超过上限只列前 N 条，但必须说明还有多少、完整清单在哪
    result.skipped = [(_Case('test_%03d' % index), '原因 {}'.format(index))
                      for index in range(1, 9)]
    text = '\n'.join(report.push_skip_lines(result, max_items=3))
    assert '跳过 8 条' in text, '标题要报总数而不是只列出来的条数: ' + text
    assert '原因 1' in text and '原因 3' in text and '原因 4' not in text, '超限时应只列前 3 条: ' + text
    assert '另有 5 条未列出' in text, '截断后必须交代还有多少条: ' + text

    # 空理由不能变成一个空白块：报告里得看得出「没写原因」，否则会被当成格式丢了
    result.skipped = [(_Case('test_001'), '   ')]
    assert '无原因' in '\n'.join(report.push_skip_lines(result)), '空理由要显式写成无原因'


def check_case_expr_prefix():
    """CASE 这个名字，带不带用例目录前缀都得能跑

    现场踩过：CASE=caseStress.test_pay_concurrent.TestConcurrentPay.test_005 跑出
    一条 "No module named 'caseStress.caseStress'" 的报错用例——看着像用例挂了，
    其实是名字被拼了两遍。而 run_reproduce.py 的 --case 恰恰要求全名（它直接喂
    python -m unittest），同一个名字两个入口两套写法，人必然写错一次。

    这里钉四件事：两种写法装出同一批用例、不产出 _FailedTest、前缀与实际用例
    目录不一致时明确退出、名字真写错时当场报名字+原因（不能变成报告里一条「异常」，
    否则看报告的人会去翻用例代码，而问题在命令行的 CASE 上）。
    """
    import contextlib
    import io
    import unittest

    from common import report

    def _cases(suite):
        out = []
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                out.extend(_cases(item))
            else:
                out.append(item)
        return out

    def _ids(expr):
        cases = _cases(report.build_suite('slp', expr, 'caseStress'))
        broken = [case for case in cases if type(case).__name__ == '_FailedTest']
        assert not broken, '{} 应能正常加载，实际产出 _FailedTest'.format(expr)
        assert cases, '{} 一条用例都没装出来'.format(expr)
        return [case.id() for case in cases]

    # 只写到模块：两种前缀装出来的必须是同一批用例。不写死条数——加一条用例不该让自检红
    plain = _ids('test_pay_concurrent')
    prefixed = _ids('caseStress.test_pay_concurrent')
    assert plain == prefixed, '带不带前缀装出来的用例不一致：\n{}\n{}'.format(plain, prefixed)

    # 只写到类：缩到几条用例时也要两边一致（类名写错也要在这里暴露，而不是等跑一轮才报错）
    cls = 'test_pay_concurrent.TestConcurrentPay'
    assert _ids('caseStress.' + cls) == _ids(cls), '只写到类时，两种前缀装出来的用例不一致'

    def _refused(expr, expect):
        """应在装配阶段就退出，且提示要把问题说清楚"""
        said = io.StringIO()
        try:
            with contextlib.redirect_stdout(said):
                report.build_suite('slp', expr, 'caseStress')
        except SystemExit as stop:
            assert stop.code == 2, '{} 应以 2 退出，实际 {}'.format(expr, stop.code)
        else:
            raise AssertionError('{} 必须报错退出，不能拼出一个必然找不到的模块名'.format(expr))
        text = said.getvalue()
        assert expect in text, '{} 的提示没点出问题所在：{}'.format(expr, text)

    # 前缀写成了别的用例目录：继续拼下去只会得到 "No module named ..."
    _refused('caseSlp.test_check', '不一致')
    # 前缀重复（截图里那条）：现在要当场说清是名字写错，而不是跑出一条 _FailedTest
    _refused('caseStress.caseStress.test_pay_concurrent', "No module named 'caseStress.caseStress'")
    # 方法名、模块名写错：报告里的「异常」只应留给真正跑失败，名字写错属于命令行
    _refused('test_pay_concurrent.TestConcurrentPay.test_999', "has no attribute 'test_999'")
    _refused('test_pay_concurrent.NoSuchClass', "has no attribute 'NoSuchClass'")


def main():
    print('框架自检：频控退避（common.Request）')
    _check('命中频控后退避重试并拿到成功响应', check_frequent_retry_then_success)
    _check('重试耗尽后把频控响应交回用例', check_frequent_exhausted_returns_response)
    _check('正常响应不重试', check_no_frequent_single_call)
    _check('实测见过的频控文案都能命中', check_all_keywords)
    _check('退避间隔递增', check_backoff_is_increasing)
    _check('退避不受请求间隔影响', check_backoff_independent_of_interval)
    _check('非 json 响应不误判、不崩溃', check_non_json_body_not_frequent)

    print('框架自检：失败现场（common.Scene）')
    _check('现场包含入参/响应/账号', check_scene_render)
    _check('现场缓冲有上限', check_scene_buffer_limit)
    _check('空现场与快照异常都不影响结论', check_scene_empty_and_archive)

    print('框架自检：异步读值轮询（common.Assert）')
    _check('读不到时继续读到达标', check_eventually_polls_until_match)
    _check('超时失败要说明等了多久', check_eventually_timeout_reports_waited)
    _check('首轮命中只读一次', check_eventually_first_hit_single_read)

    print('框架自检：环境种子清单（common.envData）')
    _check('清单结构合法、SQL 可填、无重复项', check_seed_checks_shape)

    print('框架自检：并发用例工具（caseStress.tools）')
    _check('流水聚合：付款与收款分开、同人同 op 合并', check_flow_split)
    _check('等流水：条数稳定才返回、没流水时超时带回空', check_flow_wait_stable)
    _check('分成放大：多写一行、少一条写路径都能比出来', check_income_scaled)
    _check('同账号重复提交：全被频控挡下要认成未测到', check_window_tested)
    _check('响应四分类、非 dict body 不崩', check_classify_responses)

    print('框架自检：本机环境配置（common.envLocal）')
    _check('模板覆盖所需项、环境变量优先级最高', check_env_config_shape)

    print('框架自检：报告推送（common.report）')
    _check('跳过的用例带理由进推送、超限交代还剩几条', check_push_skip_lines)
    _check('CASE 带不带用例目录前缀都能跑、前缀写错要拦下', check_case_expr_prefix)

    if _FAILED:
        print('\n自检未通过 {} / {} 项：{}'.format(len(_FAILED), len(_TOTAL), '、'.join(_FAILED)))
        return 1
    print('\n自检全部通过（{} 项）'.format(len(_TOTAL)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
