# coding=utf-8
"""失败现场快照：把「这条用例发了什么请求、回了什么、相关账户现在是什么值」留下来

原来用例失败只有一条 AssertionError 堆栈，请求体只在控制台滚过去一次。这几天定位
test_exp.test_001 的 6100、test_gs_pay_self.test_004 的频控响应，全靠人肉从截图里翻，
翻不到就得再复现一轮——一轮全量 7 分钟，成本太高。

这里在用例执行期间缓存最近几次请求/响应，失败时按用例归档，由 report.fail_detail_text
拼进 log/failCase.log。三条自我约束：

1. 只做观测：不参与任何断言，不改变用例行为，不额外发请求；
2. 快照自身出任何错都吞掉：绝不能把 FAIL 变成 ERROR，也不能影响用例结论；
3. 只在失败时读库：通过的用例一次额外查询都不发。
"""
import datetime
import json

# 每个用例保留最近几次请求/响应：够覆盖「下单 + 中途一次查询」这类链路
MAX_EXCHANGES = 5
# 账号快照最多查几个 uid，多人场景不把日志撑爆
MAX_UIDS = 6
# 单条请求/响应的截断长度
MAX_CHARS = 1500

_current_case = None
_exchanges = []
_archive = {}


def begin_case(case_name):
    """用例开始：清空当前缓冲

    重试轮不调用（@Retry 在同一个用例内重跑），所以首轮与重试轮发出的请求都会留下，
    失败现场能看到「首轮被拒、重试被拒」这种完整序列。
    """
    global _current_case, _exchanges
    _current_case = case_name
    _exchanges = []


def now_text():
    """墙上时刻（毫秒），用于和服务端日志对齐——这是双方唯一对得上的锚点"""
    return datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]


def current_case():
    """当前正在执行的用例名，供 5xx 台账记录归属"""
    return _current_case


def record_exchange(payload, pay_uid, code, body, at=None, elapsed_ms=None):
    """记录一次请求/响应，由 Request.post_request_session 调用

    :param payload: 请求入参（encodeData 的结果）
    :param pay_uid: 本次请求使用的账号
    :param code: HTTP 状态码
    :param body: 已解析的响应体（非 json 时是原始文本）
    :param at: 请求发出时刻（HH:MM:SS.mmm）。服务端排障第一个问题就是「几点几分」，
               以前只有失败后的库内快照，时刻得靠人回忆
    :param elapsed_ms: 本次请求耗时（毫秒）。耗时正常 = 服务端快速拒绝，
                       耗时暴涨 = 上游在等超时，两者对应的排查方向完全不同
    """
    if len(_exchanges) >= MAX_EXCHANGES:
        _exchanges.pop(0)
    _exchanges.append({'payload': payload, 'pay_uid': pay_uid, 'code': code, 'body': body,
                       'at': at, 'elapsed_ms': elapsed_ms})


def archive(case_name):
    """用例失败时调用：把当前缓冲 + 账户快照归档，供报告拼装"""
    if not case_name:
        return
    try:
        _archive[case_name] = _render(case_name)
    except Exception:
        # 快照只服务排查，任何异常都不该影响报告与用例结论
        _archive[case_name] = ''


def archived(case_name):
    """取已归档的失败现场，没有则返回空串"""
    return _archive.get(case_name, '')


def _render(case_name):
    lines = ['---- 失败现场：{}（归档 {}）----'.format(case_name, now_text())]
    if not _exchanges:
        # 常见于用例在发请求之前就失败（造数断言、前置校验），或失败发生在读断言阶段
        lines.append('（本用例期间未记录到接口请求）')
    uids = []
    for index, item in enumerate(_exchanges, 1):
        lines.append(_exchange_head(index, item))
        lines.append('  入参: {}'.format(_short(item['payload'])))
        lines.append('  HTTP {}'.format(item['code']))
        lines.append('  响应: {}'.format(_short(item['body'])))
        for uid in _uids_from(item['payload'], item['pay_uid']):
            if uid not in uids:
                uids.append(uid)
    snapshot = _account_snapshot(uids[:MAX_UIDS])
    if snapshot:
        lines.append('[账户快照]（失败时刻的库内值，用于区分“没扣”与“扣多了”）')
        lines.extend('  ' + line for line in snapshot)
    return '\n'.join(lines)


def _exchange_head(index, item):
    """一行标题：账号 + 发出时刻 + 耗时（有才写，老调用方/假响应没有这两项）"""
    head = '[请求 {}] pay_uid={}'.format(index, item['pay_uid'])
    if item.get('at'):
        head += '  发出 {}'.format(item['at'])
    if item.get('elapsed_ms') is not None:
        head += '  耗时 {:.0f}ms'.format(item['elapsed_ms'])
    return head


def _short(value):
    """单行化 + 截断：现场是给日志看的，不能把 failCase.log 撑爆"""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            text = str(value)
    text = text.replace('\r', ' ').replace('\n', ' ')
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + '...(已截断)'


def _uids_from(payload, pay_uid):
    """从请求入参里提取涉及的账号：打赏者 + 收礼人（多人场景 to/uids 都可能是列表）"""
    uids = []

    def _add(value):
        if isinstance(value, (list, tuple, set)):
            for one in value:
                _add(one)
            return
        if value is None:
            return
        text = str(value).strip()
        if text.isdigit() and text != '0' and text not in uids:
            uids.append(text)

    _add(pay_uid)
    if isinstance(payload, dict):
        _add(payload.get('uid'))
        params = payload.get('params')
        if isinstance(params, dict):
            for key in ('to', 'uid', 'uids'):
                _add(params.get(key))
    return uids


def _account_snapshot(uids):
    """读账户行做快照。延迟 import + 全吞异常：这里任何问题都不该影响用例结论"""
    if not uids:
        return []
    try:
        from common.conSlpXsgMysql import conMysql as mysql
    except Exception:
        return []
    # 先探一下数据库：连不上就只报一句，不能让 12 笔查询各撞一次连接超时，
    # 把报告卡住几分钟（DB 挂了的时候用例已经全红，现场本来也没意义）
    try:
        mysql.selectRawDict('select 1')
    except Exception as error:
        return ['（账户快照跳过：数据库不可用 {}）'.format(error)]
    lines = []
    for uid in uids:
        for label, sql in (
            ('xs_user_money', 'select * from xs_user_money where uid={}'.format(uid)),
            ('xs_user_profile', 'select * from xs_user_profile where uid={}'.format(uid)),
        ):
            try:
                rows = mysql.selectRawDict(sql)
            except Exception as error:
                lines.append('uid={} {}: 读取失败 {}'.format(uid, label, error))
                continue
            if not rows:
                lines.append('uid={} {}: 无记录'.format(uid, label))
                continue
            for row in rows:
                lines.append('uid={} {}: {}'.format(uid, label, _short(row)))
    return lines
