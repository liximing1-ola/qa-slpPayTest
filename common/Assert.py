"""
封装assert方法
"""
import json
import platform
import time
from common import Consts
from common.Config import config


def assert_code(actual_code, expected_code=200):
    """
    验证response状态码
    :param actual_code: 实际结果
    :param expected_code: 预期结果
    """
    if platform.node() != config.linux_node['ali']:
        time.sleep(0.3)  # rpc接口延迟，防止结果失败！！！
    try:
        assert actual_code == expected_code
        return True
    except:
        reason = 'Actual Code: {}, Expected Code: {}, 验证结果不一致，估计服务器开小差�?'.format(actual_code, expected_code)
        Consts.fail_case_reason.append(reason)
        raise


def assert_len(actual_len, expect_len):
    """
    :param actual_len: 实际结果
    :param expect_len: 预期结果
    """
    try:
        assert actual_len >= expect_len
        return True
    except:
        reason = '实际结果: {}, 预期结果: {}, 验证结果不一致，用例执行失败，望严查!'.format(actual_len, expect_len)
        Consts.fail_case_reason.append(reason)
        raise


def assert_equal(actual_result, expect_result, tolerance=0.0001):
    """
    :param actual_result: 实际结果
    :param expect_result: 预期结果
    :param tolerance: 数值类型的允许误差，默�?.0001，设�?则严格相�?    """
    try:
        # 对数值类型允许误差，覆盖int/float/Decimal混合比较场景
        if isinstance(actual_result, (int, float)) and isinstance(expect_result, (int, float)):
            if tolerance == 0:
                assert actual_result == expect_result
            else:
                assert abs(float(actual_result) - float(expect_result)) <= tolerance
        else:
            assert actual_result == expect_result
        return True
    except:
        reason = '实际结果: {}, 预期结果: {}, 验证结果不一致，用例执行失败，望严查!'.format(actual_result, expect_result)
        print("*"*30)
        print(f"{actual_result}!={expect_result}")
        print("*"*30)
        Consts.fail_case_reason.append(reason)
        raise


def assert_in_text(body, expected_msg):
    """
    :param body: 返回�?    :param expected_msg: 预期结果
    """
    try:
        text = json.dumps(body, ensure_ascii=False)
        assert expected_msg in text
        return True
    except:
        Consts.fail_case_reason.append('fail')
        raise


def assert_body(body, body_msg, expected_msg, reason):
    """
    验证response状态码
    :param body: 返回�?    :param body_msg: 参数
    :param expected_msg: 预期结果
    :param reason: 原因
    """
    try:
        # msg = body[body_msg]
        msg = body.get(body_msg, None)
        assert msg == expected_msg
        return True
    except:
        Consts.fail_case_reason.append(reason)
        raise


def assert_between(actual_result, lower_limit, upper_limit):
    try:
        assert int(lower_limit) <= int(actual_result) <= int(upper_limit)
        return True
    except:
        reason = f'实际结果: {actual_result}, 预期结果: {int(lower_limit)} �?{int(upper_limit)}, 验证结果不一致，用例执行失败，望严查!'
        Consts.fail_case_reason.append(reason)
        raise
