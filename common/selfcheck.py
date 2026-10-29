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


def check_flow_wait_stable():
    """等流水：条数不再增长才返回；一直没有流水时要把空结果交回，不能抛也不能死等

    只看「至少 1 行」会漏掉后半段：一笔订单先写主播那行、再写厅和公会长，
    读到 1 行就收工，后面两条写路径就不会被验——而报告上看不出来。
    """
    from caseStress import tools

    old_read = tools.read_gift_flows
    old_timeout = tools.WAIT_TIMEOUT
    old_interval = tools.WAIT_INTERVAL
    try:
        tools.WAIT_TIMEOUT = 0.5
        tools.WAIT_INTERVAL = 0.01

        # 分两段写：前两次只读到 1 行，之后才补齐 3 行
        rounds = [[1], [1], [1, 2, 3], [1, 2, 3], [1, 2, 3]]
        calls = []

        def staged(after_id, gid):
            calls.append(1)
            return rounds.pop(0) if rounds else [1, 2, 3]

        tools.read_gift_flows = staged
        rows = tools.wait_flows_stable(0, 69, least=1, quiet=3)
        assert len(rows) == 3, '应等到 3 行落完再返回，实际 {}'.format(rows)
        assert len(calls) >= 5, '分两段写时不能读到第一段就返回，实际只读了 {} 次'.format(len(calls))

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
    _check('响应四分类、非 dict body 不崩', check_classify_responses)

    print('框架自检：本机环境配置（common.envLocal）')
    _check('模板覆盖所需项、环境变量优先级最高', check_env_config_shape)

    if _FAILED:
        print('\n自检未通过 {} / {} 项：{}'.format(len(_FAILED), len(_TOTAL), '、'.join(_FAILED)))
        return 1
    print('\n自检全部通过（{} 项）'.format(len(_TOTAL)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
