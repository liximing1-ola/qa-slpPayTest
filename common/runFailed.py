# -*- coding = UTF-8 -*-
# Describe : 失败用例重跑
import functools
import inspect
import os
import time
import unittest

from common import Consts, Request

# 重试间隔（秒）：分成/人气等结算走异步，断言失败后立刻重跑往往读到同一份旧数据，
# 白白烧掉重试次数。按轮次退避（第 n 次等 n × 间隔），用 RETRY_SLEEP 可调，设 0 回到立即重试
RETRY_SLEEP = float(os.environ.get('RETRY_SLEEP') or '1')


class Retry(object):
    """
类装饰器, 功能与Retry一样
# example_1: test_001默认重试1次
class ClassA(unittest.TestCase):
    @Retry
    def test_001(self):
        raise AttributeError

# example_2: max_n=2,test_001重试2次
class ClassB(unittest.TestCase):
    @Retry(max_n=2)
    def test_001(self):
        raise AttributeError

# example_3: test_001重试3次; test_002重试3次
@Retry(max_n=3)
class ClassC(unittest.TestCase):
    def test_001(self):
        raise AttributeError
    def test_002(self):
        raise AttributeError

# example_4: test_102重试2次, test_001不参与重试机制
@Retry(max_n=2, func_prefix="test_1")
class ClassD(unittest.TestCase):
    def test_001(self):
        raise AttributeError
    def test_102(self):
        raise AttributeError
    """

    def __new__(cls, func_or_cls=None, max_n=1, func_prefix="test", sleep=None):
        self = object.__new__(cls)
        if func_or_cls:
            self.__init__(func_or_cls, max_n, func_prefix, sleep)
            return self(func_or_cls)
        else:
            return self

    def __init__(self, func_or_cls=None, max_n=1, func_prefix="test", sleep=None):
        self._prefix = func_prefix
        self._max_n = max_n
        # sleep=None 表示用全局默认 RETRY_SLEEP，传 0 才是“不等待”
        self._sleep = RETRY_SLEEP if sleep is None else sleep

    def __call__(self, func_or_cls=None):
        if inspect.isfunction(func_or_cls):
            @functools.wraps(func_or_cls)
            def wrapper(*args, **kwargs):
                # 新用例开始：清掉上一个用例的重试缓存与重试态
                Request.begin_case()
                for n in range(1, self._max_n + 2):
                    # 记录重试前的失败原因位置：上一轮断言产生的失败原因不能留在报告里，
                    # 否则用例最终通过时仍会被计入失败原因。
                    # 注意：该清理方式依赖用例串行执行（当前两个入口都是单线程 discover），
                    # 若后续改为多线程并发跑用例，需改为按用例实例隔离失败原因容器
                    reason_mark = len(Consts.fail_case_reason)
                    try:
                        return func_or_cls(*args, **kwargs)
                    except unittest.SkipTest:
                        # skipTest 抛出的也是异常，不能被当成失败重试（否则 skip 会被打印多次堆栈）
                        raise
                    except AssertionError as error:
                        # 只重试断言失败：这类失败多为环境抖动（异步结算延迟、频控、缓存未刷新），重跑有意义；
                        # TypeError/KeyError 等代码或数据问题重跑也不会变好，直接抛出保留真实堆栈。
                        # DbQueryError（连库失败/SQL 错）同样不重试：连接层已有 ping 自动重连，
                        # 自愈不了的故障重跑同一条语句也没用，交给框架记成 ERROR 更醒目
                        if n > self._max_n:
                            raise
                        # 断言库把失败明细写进了 fail_case_reason，裸 assert 的 str(error) 是空串，
                        # 所以优先用明细打日志，再把本轮产生的失败原因清掉
                        new_reasons = Consts.fail_case_reason[reason_mark:]
                        del Consts.fail_case_reason[reason_mark:]
                        detail = new_reasons[-1] if new_reasons else repr(error)
                        print('[Retry {}/{}] {}: {}'.format(n, self._max_n, func_or_cls.__name__, detail))
                        # 先等一会再重跑：异步结算、缓存刷新都有耗时，刚失败就重试大概率还是旧值
                        if self._sleep > 0:
                            time.sleep(self._sleep * n)
                        # 下一轮：下单类写请求复用上一轮的响应、非幂等的数据准备跳过，
                        # 让重试只重新做"读库断言"，避免每次重试都多下一单
                        Request.begin_replay()

            return wrapper
        elif inspect.isclass(func_or_cls):
            for name, func in list(func_or_cls.__dict__.items()):
                if inspect.isfunction(func) and name.startswith(self._prefix):
                    setattr(func_or_cls, name, self(func))
            return func_or_cls
        else:
            raise AttributeError
