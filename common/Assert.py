"""
封装assert方法
"""
import json
import numbers
import os
import platform
import time
from common import Consts
from common.Config import config

# rpc 接口延迟补偿：除阿里测试机外，每次校验状态码前先等一会，避免刚操作完就去读导致结果不一致。
# 全量跑一遍每个用例都等一次，累计 40 秒左右，用环境变量 ASSERT_SLEEP 调整，设为 0 直接关闭。
# 用 or 兜底：变量存在但为空（如 export ASSERT_SLEEP=）时不能被 float('') 抛错，那会让所有用例在 import 阶段就失败
ASSERT_SLEEP = float(os.environ.get('ASSERT_SLEEP') or '0.3')
# 轮询等待参数（见 assert_equal_eventually）：最多等多久、每次间隔多久
WAIT_TIMEOUT = float(os.environ.get('WAIT_TIMEOUT') or '3')
WAIT_INTERVAL = float(os.environ.get('WAIT_INTERVAL') or '0.2')
_ON_ALI_NODE = platform.node() == config.linux_node['ali']


def _settle_before_assert():
    """
    :return:
    """
    if ASSERT_SLEEP > 0 and not _ON_ALI_NODE:
        time.sleep(ASSERT_SLEEP)


def assert_code(actual_code, expected_code=200):
    """
    验证response状态码
    :param actual_code: 实际结果
    :param expected_code: 预期结果
    """
    _settle_before_assert()
    try:
        assert actual_code == expected_code
        return True
    except Exception:
        reason = 'Actual Code: {}, Expected Code: {}, 验证结果不一致，估计服务器开小差啦!'.format(actual_code, expected_code)
        Consts.fail_case_reason.append(reason)
        # from None：不链式展开原来的 AssertionError，否则堆栈会多一层"During handling..."；
        # 带上 message 才能让日志里直接看到实际值/预期值
        raise AssertionError(reason) from None


def assert_equal(actual_result, expect_result, tolerance=0.0001):
    """
    :param actual_result: 实际结果
    :param expect_result: 预期结果
    :param tolerance: 数值类型的允许误差，默认0.0001，设为0则严格相等
    """
    try:
        # 对数值类型允许误差，覆盖 int/float/Decimal 混比场景
        # （pymysql 对 DECIMAL 列返回 Decimal，不能用 isinstance(x, (int, float)) 判定）
        if isinstance(actual_result, numbers.Number) and isinstance(expect_result, numbers.Number):
            if tolerance == 0:
                assert actual_result == expect_result
            else:
                assert abs(float(actual_result) - float(expect_result)) <= tolerance
        else:
            assert actual_result == expect_result
        return True
    except Exception:
        reason = '实际结果: {}, 预期结果: {}, 验证结果不一致，用例执行失败，望严查!'.format(actual_result, expect_result)
        # 不再在这里 print 实际值：失败明细会由 report 统一汇总（控制台清单 + log/failCase.log），
        # 用例一多这里会刷屏且打断 unittest 的进度行；但必须把值带进异常 message，
        # 否则堆栈末行只有空的 AssertionError，日志里看不到实际值
        Consts.fail_case_reason.append(reason)
        raise AssertionError(reason) from None


def assert_in_text(body, expected_msg):
    """
    :param body: 返回值
    :param expected_msg: 预期结果
    """
    try:
        text = json.dumps(body, ensure_ascii=False)
        assert expected_msg in text
        return True
    except Exception:
        detail = '预期返回内容包含: {}, 实际返回: {}'.format(expected_msg, str(body)[:300])
        Consts.fail_case_reason.append(detail)
        raise AssertionError(detail) from None


def assert_equal_eventually(actual_func, expect_result, timeout=None, interval=None, tolerance=0.0001):
    """
    轮询等待读值达到预期，用于分成/人气这类异步结算

    assert_equal 只读一次。而服务端分账是分批写的：实测带券多人打赏时，0.5s 到账
    另外两个收礼人、0.7s 到账用券那 1 笔、0.9s 才补齐剩余 9 笔，全量约 0.9 秒。
    固定睡一觉再读，很容易撞在“432 已到、4320 未到”这种中间态上。

    :param actual_func: 无参函数，每次调用返回一次当前读值（不能是提前读好的值）
    :param expect_result: 预期结果
    :param timeout: 最长等待秒数，默认 WAIT_TIMEOUT（环境变量可调）
    :param interval: 轮询间隔，默认 WAIT_INTERVAL
    :return: 达到预期返回 True；超时仍不达标则按最后一次实际值报错
    """
    timeout = WAIT_TIMEOUT if timeout is None else timeout
    interval = WAIT_INTERVAL if interval is None else interval
    mark = len(Consts.fail_case_reason)
    deadline = time.time() + timeout
    while True:
        actual_result = actual_func()
        if time.time() >= deadline:
            # 最后一轮走正常断言：失败时把实际值/预期值写进报告，免得只剩一个空断言
            return assert_equal(actual_result, expect_result, tolerance)
        try:
            return assert_equal(actual_result, expect_result, tolerance)
        except AssertionError:
            # 中间态不算失败：清掉本轮刚写入的原因，否则报告里会堆一串 432、4320
            del Consts.fail_case_reason[mark:]
            time.sleep(interval)


def assert_body(body, body_msg, expected_msg, reason):
    """
    验证response状态码
    :param body: 返回值
    :param body_msg: 参数
    :param expected_msg: 预期结果；传 list/tuple/set 表示多套文案任一命中即通过
    :param reason: 原因
    """
    try:
        # msg = body[body_msg]
        msg = body.get(body_msg, None)
        # 同一个语义在不同链路上可能文案不同（甚至暂时不回文案），预期写成集合就能逐条兼容，
        # 但仍在“返回值不在集合里”时报错，不会退化成完全不校验
        if isinstance(expected_msg, (list, tuple, set)):
            assert msg in expected_msg
        else:
            assert msg == expected_msg
        return True
    except Exception:
        detail = '{}：实际返回值 {}, 预期 {}'.format(reason, body.get(body_msg, None) if isinstance(body, dict) else body, expected_msg)
        Consts.fail_case_reason.append(detail)
        raise AssertionError(detail) from None


def assert_between(actual_result, lower_limit, upper_limit):
    """
    :param actual_result: 实际结果
    :param lower_limit: 区间下界（含）
    :param upper_limit: 区间上界（含）
    """
    try:
        # 必须用 float 比较：int() 会把 0.9~1.0 截断成 0~1，导致区间断言恒真
        assert float(lower_limit) <= float(actual_result) <= float(upper_limit)
        return True
    except Exception:
        reason = f'实际结果: {actual_result}, 预期结果: {lower_limit} 至 {upper_limit}, 验证结果不一致，用例执行失败，望严查!'
        Consts.fail_case_reason.append(reason)
        raise AssertionError(reason) from None
