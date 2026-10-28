# coding=utf-8
"""
定时任务入口：执行指定 App 的全量用例并推送结果。
与 run_all_case.py 的区别：不拉取代码分支、不逐条播报通过用例，只关注结果汇总与失败/异常通知。

推送形态（PUSH_WX=1 时，cron 里就是这个用法）：
    全部通过 -> 一条消息：标题 + 总数/通过/失败/异常/跳过 + 重试摘要 + 分支
    有未通过 -> 同一条消息后面附上失败与异常清单（跳过不列，见 fail_summary）
    执行中断 -> 一条「执行异常」消息，说明用例没跑完，不能安静退出

用法：
    python run_crontab_case.py slp
    PUSH_WX=1 python run_crontab_case.py slp
"""
import os
import sys
import traceback

from Robot import robot
from common import Logs
from common.Config import config
from common.Session import Session
from common.report import (AllTestRunner, build_suite, fail_detail_text, fail_summary,
                           not_pass_report, parse_app, result_counts, retry_report, retry_summary,
                           split_message)

APP_SUPPORTED = (config.appName['不夜星球'], config.appName['小拾光'])
# 是否推送到企业微信群：默认关闭，cron 命令里显式写 PUSH_WX=1 打开。
# 不给默认值 1 是为了本地手工验证时不会往群里发测试消息
PUSH_WX = os.environ.get('PUSH_WX', '0') == '1'
# 只跑指定用例：不设则全量（与 run_all_case 同一套写法）。
# 定时任务的汇总/落盘/退出码逻辑与全量入口是两份代码，没有这个开关就只能跑 137 条
# 才能验证它们，实际成本高到没人会去验证——留个口子，改汇总逻辑后用它快速过一遍
CASE = os.environ.get('CASE', '').strip()


def push_lines(lines, app_info):
    """按企微单条上限拆分后逐条推送，返回是否全部发送成功

    推送失败不能改变本轮结论：网络抖动时 requests 会抛异常，这时只记日志、
    退出码仍然只表达「用例过没过」。但必须留下痕迹——群里没消息很容易被当成
    「今天没跑」，而不是「推送坏了」。
    """
    ok = True
    for chunk in split_message(lines):
        try:
            # robot 内部已经兜住了网络异常，这里再包一层是防以后改动把异常漏出去
            sent = robot('markdown', chunk, bot='slp')
        except Exception as error:
            sent = False
            print('[{}] 企业微信推送异常: {}'.format(app_info, error), flush=True)
        if sent:
            continue
        ok = False
        # 最可能是 WX_BOT_SLP 没设：群里没消息，日志里必须能查到原因
        Logs.get_log('runCode.log', console=False).error(
            '[{}] 企业微信消息未发出（检查 WX_BOT_SLP），内容前 80 字: {}'.format(app_info, chunk[:80]))
    return ok


def notify(test_result, app_info):
    """汇总执行结果：未通过清单完整写到控制台与 log/notPassCase.log

    PUSH_WX=1 时再推一条企微消息：全通过只发计数，有失败/异常把清单附在同一条里。
    """
    failures = test_result.failures
    errors = test_result.errors
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

    # 只推一条（超过企微单条上限才拆）：全通过时就是几行结果，有未通过时把清单
    # 附在后面。不再逐条发 icon —— 每条都会 @all，失败几条就刷几次屏，
    # 而清单本来就在这条消息里，提醒和内容分开反而是多一次打扰
    branch = config.codeInfo.get('slp_git_branch', '') if app_info == config.appName['不夜星球'] else '-'
    lines = [
        "**{}** 定时任务结果".format(app_info),
        "总数 {}, 通过 {}, 失败 {}, 异常 {}, 跳过 {}".format(
            counts['total'], pass_count, counts['fail'], counts['error'], counts['skip']),
        retry_summary(test_result),
        "代码分支: {}".format(branch),
    ]
    # 失败与异常全部列出；跳过的只在上面那行里给个数（已知下线，每天列一遍是噪音）
    fail_text = fail_summary(test_result)
    if fail_text:
        lines.append(fail_text)
    # 失败用例多时消息会超过企微单条上限，按字节拆成多条推送，避免结论被截断
    push_lines(lines, app_info)
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

    test_result = AllTestRunner(verbosity=2).run(build_suite(app_info, CASE))
    # 重试后才通过的用例：最终状态是 PASS，但每条背后都是一次真实的断言失败。
    # 定时任务场景控制台没人看，所以完整清单落 log/retryCase.log，推送里只带一行摘要
    retry_text = retry_report(test_result)
    # 摘要固定打一行（不管有没有重试）：只看 runCode.log 时也能看出「这轮有没有被重试兜住的问题」
    # console=False：否则会给这个 logger 再挂一个控制台 handler，同一行会被打两次
    retry_line = retry_summary(test_result)
    print(retry_line, flush=True)
    Logs.get_log('runCode.log', console=False).info(retry_line)
    if retry_text:
        print(retry_text, flush=True)
        Logs.get_log('retryCase.log', console=False, back_count=30).info(retry_text)
    return notify(test_result, app_info)


def run(argv):
    """命令行入口：返回退出码（0 全通过 / 1 有失败或异常 / 2 没跑完）

    退出码的判定单独成函数，否则只能靠真起一个进程去验证「执行中断」这种分支，
    而它恰好是最不希望在生产里才第一次生效的分支。
    """
    app = parse_app(argv)
    try:
        counts = main(app)
    except Exception as error:
        # 用例没跑完就断了（连库失败、suite 构造异常、磁盘满等）：这时一条用例结论都没有。
        # 群里不能安静——「没消息」会被当成「全部通过」，这比推错消息更糟
        print('定时任务执行异常: {}: {}'.format(type(error).__name__, error), flush=True)
        Logs.get_log('runCode.log', console=False).error('定时任务执行异常\n' + traceback.format_exc())
        if PUSH_WX:
            push_lines(['**{}** 定时任务执行异常'.format(app),
                        '执行中断，本轮用例没有跑完：{}: {}'.format(type(error).__name__, error),
                        '完整堆栈: log/runCode.log'], app)
        return 2
    if counts is None:
        # parse_app 已经拦了错误参数，这里只防配置里的 App 名与支持列表不一致
        print('[{}] 不在支持列表，未执行'.format(app), flush=True)
        return 2
    # 有失败/异常返回 1，便于 cron、调度平台或 cmd && 后续命令感知本轮失败
    return 1 if (counts['fail'] or counts['error']) else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv))
