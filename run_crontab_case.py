# coding=utf-8
"""
定时任务入口：执行指定 App 的全量用例并推送结果。
与 run_all_case.py 的区别：不拉取代码分支、不逐条播报通过用例，只关注结果汇总与失败/异常通知。

用法：
    python run_crontab_case.py slp
    python run_crontab_case.py xsg
"""
import os
import sys
import unittest

from Robot import robot
from common import Logs
from common.Config import config
from common.Session import Session
from common.report import (AllTestRunner, fail_detail_text, not_pass_report,
                           not_pass_summary, result_counts, split_message)

APP_SUPPORTED = (config.appName['不夜星球'], config.appName['小拾光'])
# 是否推送到企业微信群：默认关闭。当前直接在云服务器上看日志，需要推送时用 PUSH_WX=1
PUSH_WX = os.environ.get('PUSH_WX', '0') == '1'
# 失败/异常逐条播报的条数上限：每条 icon 都会 @all 并在外网拉一次图，
# 失败较多时刷屏又慢，完整清单在汇总消息里，这里只做提醒
MAX_ICON_ALERT = 3


def all_case(app_info):
    """按 App 名组装对应用例目录下的全部用例"""
    case_dir = config.BASE_PATH
    if app_info == config.appName['不夜星球']:
        case_dir += '/caseSlp'
    elif app_info == config.appName['小拾光']:
        case_dir += '/caseXsg'
    else:
        raise ValueError('不支持的 App: {}, 仅支持 {}'.format(app_info, APP_SUPPORTED))

    discover = unittest.defaultTestLoader.discover(case_dir,
                                                   pattern='test_*.py',
                                                   top_level_dir=config.BASE_PATH)
    testcase = unittest.TestSuite()
    testcase.addTests(discover)
    return testcase


def notify(test_result, app_info):
    """汇总执行结果：未通过用例完整打到控制台与 log/notPassCase.log，企业微信推送默认关闭"""
    failures = test_result.failures
    errors = test_result.errors
    skipped = test_result.skipped
    # 用 result_counts 而不是 testsRun - 失败 - 异常 - 跳过：
    # setUpClass 报错时 testsRun 不含这条，相减会把「通过」算成负数
    counts = result_counts(test_result)
    pass_count = counts['pass']

    des = "[{}] 用例总数: {}, 通过: {}, 失败: {}, 异常: {}, 跳过: {}".format(
        app_info, counts['total'], pass_count, counts['fail'], counts['error'], counts['skip'])
    # flush=True：stdout 重定向到文件时是块缓冲，不刷会延迟到进程退出才落盘
    print(des, flush=True)
    Logs.get_log('caseResult.log', console=False).info(des)

    # 完整清单：编号 + 用例名称 + des + 失败明细，同时写一份到 log/notPassCase.log
    report_text = not_pass_report(test_result, title='[{}] 未通过用例'.format(app_info))
    print(report_text, flush=True)
    Logs.get_log('notPassCase.log', console=False, back_count=30).info(report_text)

    # 失败/异常的完整堆栈只写文件、不打控制台（控制台已有上面带编号的完整清单）
    if failures or errors:
        Logs.get_log('failCase.log', console=False, back_count=30).error(fail_detail_text(test_result))
        print('失败/异常完整堆栈: log/failCase.log', flush=True)

    if not PUSH_WX:
        print('企业微信推送已关闭（PUSH_WX=0），完整结果见上方输出与 log/notPassCase.log', flush=True)
        return counts

    # 失败与异常分别遍历推送，不能用 elif 串起来，否则有失败时异常用例永远不会通知
    not_pass_cases = [case for case, _reason in failures + errors]
    for case in not_pass_cases[:MAX_ICON_ALERT]:
        robot('icon', '[{}] {}'.format(app_info, case.id().split('.')[-1]), bot='slp')
    if len(not_pass_cases) > MAX_ICON_ALERT:
        print('失败/异常共 {} 条，逐条播报只发前 {} 条，完整清单见汇总消息'.format(
            len(not_pass_cases), MAX_ICON_ALERT), flush=True)

    # 最后统一推一条汇总：未通过用例（失败/异常/跳过）逐条列出用例名称、des 与失败明细；
    # 不夜星球与小拾光共用同一个机器人，消息里必须带上 App 标识，否则无法区分是哪个应用的结果
    branch = config.codeInfo.get('slp_git_branch', '') if app_info == config.appName['不夜星球'] else '-'
    lines = [
        "定时任务[{}]：".format(app_info),
        des,
        not_pass_summary(test_result),
        "代码分支: {}".format(branch),
    ]
    # 失败用例多时消息会超过企微单条上限，按字节拆成多条推送，避免结论被截断
    for chunk in split_message(lines):
        robot('markdown', chunk, bot='slp')
    return counts


def main(app_info):
    """执行指定 App 的全部用例，返回 result_counts 的计数（供退出码判断）"""
    if app_info not in APP_SUPPORTED:
        Logs.get_log('runCode.log').error('{} 执行异常'.format(app_info))
        return None

    # 定时任务是长期运行场景，先刷新一次 token，避免 token 过期导致全量失败
    try:
        Session.getSession(app_info)
    except Exception as error:
        # console=False：否则会先给 caseResult.log 挂上控制台 handler，导致 notify 里同名的 console=False 失效
        Logs.get_log('caseResult.log', console=False).error('[{}] 刷新 token 失败: {}'.format(app_info, error))

    test_result = AllTestRunner(verbosity=2).run(all_case(app_info))
    return notify(test_result, app_info)


def parse_app(argv):
    """解析命令行传入的 App，支持中文名与 slp/xsg 简写，默认 slp"""
    arg = argv[1].strip().lower() if len(argv) >= 2 else 'slp'
    if arg in (config.appName['不夜星球'], 'slp'):
        return config.appName['不夜星球']
    if arg in (config.appName['小拾光'], 'xsg'):
        return config.appName['小拾光']
    # 手滑传错参数（如 slpp）时不能静默回落到某个 App，否则会悄悄地跑一轮并覆盖日志
    print('未知参数: {}，可用取值: slp / xsg'.format(arg), flush=True)
    sys.exit(2)


if __name__ == "__main__":
    counts = main(parse_app(sys.argv))
    # 退出码：有失败/异常时返回 1，便于 cron、调度平台或 cmd && 后续命令感知本轮失败
    sys.exit(1 if counts and (counts['fail'] or counts['error']) else 0)
