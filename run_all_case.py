# coding=utf-8
import unittest
from time import time

from Robot import robot
from autoGitPull import updateTime, updateCode
from common import Logs, Consts
from common.Config import config


class AllTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.successes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test)


class AllTestRunner(unittest.TextTestRunner):
    resultclass = AllTestResult


def main(appInfo):
    if appInfo == config.appName[chr(19981)+chr(22812)+chr(26143)+chr(29699)] or appInfo == config.appName[chr(23567)+chr(25342)+chr(20809)]:
        to = 'wx'
        print('*' * 50)
        print('消息推送到:{}'.format(to))
        print('*' * 50)

        updateCode.autoGitPull('slp_php', bot='slp', to=to, env=appInfo)
        updateCode.autoGitPull('slp_common_rpc', bot='slp', to=to, env=appInfo)
        updateTime('write', now=str(int(time())))

        test_result = AllTestRunner(verbosity=0).run(all_case(appInfo))
        Consts.endTime = time()
        des = '用例总数: {}, 失败用例数: {}, 异常用例数: {}'.format(
            test_result.testsRun, len(test_result.failures), len(test_result.errors))
        Logs.get_log('caseResult.log').info(des)

        lines = []
        lines.append('des: {}'.format(des))
        lines.append('')

        pass_count = len(test_result.successes)
        fail_count = len(test_result.failures)
        error_count = len(test_result.errors)

        lines.append('通过: {}  失败: {}  异常: {}'.format(pass_count, fail_count, error_count))
        lines.append('')

        for case in test_result.successes:
            lines.append('PASS - {}'.format(case.id()))

        for case, reason in test_result.failures:
            lines.append('FAIL - {}'.format(case.id()))

        for case, reason in test_result.errors:
            lines.append('ERROR - {}'.format(case.id()))

        message = chr(10).join(lines)
        robot('markdown', message, bot='slp')

        if fail_count >= 1:
            Logs.get_log('failCase.log').error('failures: {}'.format(test_result.failures))
        if error_count >= 1:
            Logs.get_log('failCase.log').error('error: {}'.format(test_result.errors))
    else:
        Logs.get_log('runCode.log').error('{} 执行异常'.format(appInfo))


def all_case(appInfo):
    case_dir = config.BASE_PATH
    if appInfo == config.appName[chr(19981)+chr(22812)+chr(26143)+chr(29699)]:
        case_dir += '/caseSlp'
    elif appInfo == config.appName[chr(23567)+chr(25342)+chr(20809)]:
        case_dir += '/caseXsg'
    else:
        return

    testcase = unittest.TestSuite()
    discover = unittest.defaultTestLoader.discover(case_dir,
                                                   pattern='test_*.py',
                                                   top_level_dir=None)
    testcase.addTests(discover)
    return testcase


if __name__ == '__main__':
    import sys

    if len(sys.argv) >= 2:
        arg = sys.argv[1].strip().lower()
    else:
        arg = None

    if arg == config.appName[chr(19981)+chr(22812)+chr(26143)+chr(29699)] or arg == 'slp':
        main(config.appName[chr(19981)+chr(22812)+chr(26143)+chr(29699)])
    elif arg == config.appName[chr(23567)+chr(25342)+chr(20809)] or arg == 'xsg':
        main(config.appName[chr(23567)+chr(25342)+chr(20809)])
    else:
        main(config.appName[chr(19981)+chr(22812)+chr(26143)+chr(29699)])
