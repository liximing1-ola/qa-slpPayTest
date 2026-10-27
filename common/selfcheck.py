# coding=utf-8
"""框架自身守卫逻辑的自检：不连服务端、不连数据库

为什么需要这个：频控退避、失败现场快照这类逻辑，在真实全量里可能一整轮都触发不到
（2026-10-27 那轮 137 条全绿、没有一次频控、没有一次失败），于是「写了」和
「真的按预期工作」之间始终差一步。等真需要它的时候才发现坏了，代价就是一次假红 + 一轮复现。

自检只验证框架行为，不碰业务预期值：
  1. 频控命中后退避重试、次数耗尽后把响应交回用例、非频控响应不误判；
  2. 失败现场能拼出入参/响应/账户快照，且自己出任何错都不影响用例结论。

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


def _check(name, func):
    try:
        func()
        print('  OK   {}'.format(name))
    except AssertionError as error:
        _FAILED.append(name)
        print('  FAIL {} -> {}'.format(name, error))


def _with_scripted(bodies, interval=2.0, frequent_retry=2):
    """装好假 requests / 假 token / 假 sleep，返回 (request 模块, 假 requests, 假 time)"""
    from common import Request

    fake_requests = _ScriptedRequests(bodies)
    fake_time = _FakeTime()
    old = (Request.requests, Request.time, Request.Session, Request.REQUEST_INTERVAL, Request.FREQUENT_RETRY)
    Request.requests = fake_requests
    Request.time = fake_time
    Request.REQUEST_INTERVAL = interval
    Request.FREQUENT_RETRY = frequent_retry
    Request._last_request_at.clear()

    class _FakeSession(object):
        @staticmethod
        def checkUserToken(operate, app_name='dev', uid=None, token=''):
            return 'fake-token'

    Request.Session = _FakeSession
    return Request, fake_requests, fake_time, old


def _restore(old):
    from common import Request
    (Request.requests, Request.time, Request.Session,
     Request.REQUEST_INTERVAL, Request.FREQUENT_RETRY) = old


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


def check_non_json_body_not_frequent():
    """网关返回 html 时 body 是字符串，不能因此崩掉或误判成频控"""
    Request, fake_requests, _, old = _with_scripted([ValueError('no json')])
    try:
        res = Request.post_request_session('test.local/html', {'a': 1}, tokenName='slp', pay_uid=1)
    finally:
        _restore(old)
    assert len(fake_requests.calls) == 1, '非 json 响应不该重试'
    assert isinstance(res['body'], str), '非 json 响应应保留原始文本，实际 {}'.format(type(res['body']))


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


def main():
    print('框架自检：频控退避（common.Request）')
    _check('命中频控后退避重试并拿到成功响应', check_frequent_retry_then_success)
    _check('重试耗尽后把频控响应交回用例', check_frequent_exhausted_returns_response)
    _check('正常响应不重试', check_no_frequent_single_call)
    _check('实测见过的频控文案都能命中', check_all_keywords)
    _check('退避间隔递增', check_backoff_is_increasing)
    _check('非 json 响应不误判、不崩溃', check_non_json_body_not_frequent)

    print('框架自检：失败现场（common.Scene）')
    _check('现场包含入参/响应/账号', check_scene_render)
    _check('现场缓冲有上限', check_scene_buffer_limit)
    _check('空现场与快照异常都不影响结论', check_scene_empty_and_archive)

    if _FAILED:
        print('\n自检未通过 {} 项：{}'.format(len(_FAILED), '、'.join(_FAILED)))
        return 1
    print('\n自检全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
