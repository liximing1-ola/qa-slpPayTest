# coding=utf-8
import unittest
from common import Logs, method, Consts
from Robot import robot
from common.Config import config
import platform


def all_case(appInfo):
    case_dir = config.BASE_PATH
    if appInfo == config.appName['伴伴']:
        case_dir += '/case'
        case_name = 'test_pay_punish.py'
    elif appInfo == config.appName['Partying']:
        case_dir += '/caseLuckyPlay'
        case_name = 'test_*.py'
    else:
        return
    testcase = unittest.TestSuite()
    discover = unittest.defaultTestLoader.discover(case_dir,  # 指定待执行用例的目录
                                                   pattern=case_name,
                                                   top_level_dir=None)
    testcase.addTests(discover)
    return testcase


def main(appInfo):
    if appInfo == config.appName['Partying']:
        test_result = unittest.TextTestRunner(verbosity=3).run(all_case(appInfo))
        des = "用例总数: {}, 失败用例数: {}, 异常用例数: {}" \
            .format(test_result.testsRun, len(test_result.failures), len(test_result.errors))
        Logs.get_log('caseResult_2.log').info(des)
        case_list = method.dictToList(Consts.case_list_c)
        if len(test_result.failures) == 0 and len(test_result.errors) == 0:
            des = "{}：\n{}\n用例数: {}, 失败数: {}, 代码分支：{}".format(
                '定时任务',
                case_list, test_result.testsRun,
                len(test_result.failures) + len(test_result.errors),
                config.codeInfo['pt_git_branch'])
            robot('markdown', des, bot='PT')
        elif len(test_result.failures) >= 1:
            Logs.get_log('failCase.log').error("failures: {}".format(test_result.failures))
            for case, reason in test_result.failures:
                robot('icon', case.id().split('.')[2], bot='PT')
        elif len(test_result.errors) >= 1:
            Logs.get_log('failCase.log').error("error: {}".format(test_result.errors))
            for case, reason in test_result.errors:
                robot('icon', case.id().split('.')[2], bot='PT')
    elif appInfo == config.appName['伴伴']:
        test_result = unittest.TextTestRunner(verbosity=3).run(all_case(appInfo))
        des = "用例总数: {}, 失败用例数: {}, 异常用例数: {}" \
            .format(test_result.testsRun, len(test_result.failures), len(test_result.errors))
        Logs.get_log('caseResult_2.log').info(des)
        case_list = method.dictToList(Consts.case_list_c)
        if len(test_result.failures) == 0 and len(test_result.errors) == 0:
            des = "{}: \n{}\n用例数: {}, 失败数: {}, 代码分支：{}".format(
                '定时任务',
                case_list, test_result.testsRun,
                len(test_result.failures) + len(test_result.errors),
                config.codeInfo['bb_git_branch'])
            robot('markdown', des)
        elif len(test_result.failures) >= 1:
            Logs.get_log('failCase.log').error("failures: {}".format(test_result.failures))
            for case, reason in test_result.failures:
                robot('icon', case.id().split('.')[2])
        elif len(test_result.errors) >= 1:
            Logs.get_log('failCase.log').error("error: {}".format(test_result.errors))
            for case, reason in test_result.errors:
                robot('icon', case.id().split('.')[2])
    else:
        Logs.get_log('runCode.log').error('{} 执行异常'.format(appInfo))


if __name__ == "__main__":
    if platform.node() == config.linux_node['ali']:
        main(config.appName['Partying'])
    else:
        main(config.appName['伴伴'])
