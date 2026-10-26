# -*- coding = UTF-8 -*-
# Describe : 失败用例重跑
import sys
import functools
import traceback
import inspect
import time


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

    def __new__(cls, func_or_cls=None, max_n=1, func_prefix="test"):
        self = object.__new__(cls)
        if func_or_cls:
            self.__init__(func_or_cls, max_n, func_prefix)
            time.sleep(1)
            return self(func_or_cls)
        else:
            time.sleep(1)
            return self

    def __init__(self, func_or_cls=None, max_n=1, func_prefix="test"):
        self.pay_url = None
        self._prefix = func_prefix
        self._max_n = max_n

    def __call__(self, func_or_cls=None):
        if inspect.isfunction(func_or_cls):
            @functools.wraps(func_or_cls)
            def wrapper(*args, **kwargs):
                n = 0
                while n <= self._max_n:
                    try:
                        n += 1
                        func_or_cls(*args, **kwargs)
                        return
                    except Exception as error:
                        if n <= self._max_n:
                            trace = sys.exc_info()
                            traceback_info = str()
                            for trace_line in traceback.format_exception(trace[0], trace[1], trace[2], 3):
                                traceback_info += trace_line
                            print(traceback_info, error)  # 输出组装错误信息
                            args[0].tearDown()
                            args[0].setUp()
                        else:
                            raise

            return wrapper
        elif inspect.isclass(func_or_cls):
            for name, func in list(func_or_cls.__dict__.items()):
                if inspect.isfunction(func) and name.startswith(self._prefix):
                    setattr(func_or_cls, name, self(func))
            return func_or_cls
        else:
            raise AttributeError
