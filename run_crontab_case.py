# coding=utf-8
"""
定时任务入口：执行指定 App 的全量用例并推送结果。
与 run_all_case.py 的区别：不拉取代码分支、不逐条播报通过用例，只关注结果汇总与失败/异常通知。

推送形态（PUSH_WX=1 时，cron 里就是这个用法）：
    全部通过 -> 两行：一行绿色结论 + 一行灰色尾注（跳过/重试/耗时/版本）
    有未通过 -> 结论行 + 编号清单（文件::方法 / 用例描述 / 一行原因）
    0 条用例 -> 红色「0 条用例被执行」，退出码 2。这不是通过
    环境不可用 -> 红色「环境不可用，本轮未执行」，退出码 3。一条用例都不跑
    执行中断 -> 一条红色「执行中断」消息，说明用例没跑完，不能安静退出

整个仓库只有自己看这条推送，所以排版以「扫一眼就能判断今天要不要动手」为准：
没事的时候刻意只留两行——天天刷屏的长消息，人会在第三天开始不看它。

用法：
    python run_crontab_case.py slp
    PUSH_WX=1 python run_crontab_case.py slp
"""
import os
import subprocess
import sys
import time
import traceback

from common import Logs, preflight, runflow
from common.Config import config
from common.report import (AllTestRunner, build_suite, duration_text, fail_kind_line, group_lines,
                           parse_app, push_fail_lines, retry_digits)

APP_SUPPORTED = (config.appName['SLP'], config.appName['XSG'])
# 是否推送到企业微信群：默认关闭，cron 命令里显式写 PUSH_WX=1 打开。
# 不给默认值 1 是为了本地手工验证时不会往群里发测试消息
PUSH_WX = os.environ.get('PUSH_WX', '0') == '1'
# 只跑指定用例：不设则全量（与 run_all_case 同一套写法）。
# 定时任务的汇总/落盘/退出码逻辑与全量入口是两份代码，没有这个开关就只能跑 137 条
# 才能验证它们，实际成本高到没人会去验证——留个口子，改汇总逻辑后用它快速过一遍
CASE = os.environ.get('CASE', '').strip()
# 体检不通过时 main 返回这个标记，而不是 counts：没有一轮用例结果可报
ENV_DOWN = 'env_down'


def git_revision():
    """当前这份代码是哪一版，形如 master@b91b736

    原来这里读 config.codeInfo['slp_git_branch']。那个值标的是**被测服务端**
    （slp-php / slp-common-rpc）的分支，默认写死 "dev"，跟「本轮跑的是哪份测试
    代码」没有关系；服务器实际 clone 的是 master，推送里却写 dev，等于每天报一次
    假信息，而且没人会去核对。直接问 git，读到什么就是什么。
    """
    cwd = os.path.dirname(os.path.abspath(__file__))

    def read(args):
        return subprocess.check_output(args, cwd=cwd, stderr=subprocess.DEVNULL,
                                       universal_newlines=True, timeout=5).strip()

    try:
        branch = read(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
        commit = read(['git', 'rev-parse', '--short', 'HEAD'])
    except Exception:
        # 没装 git、不在仓库里、或者 git 卡住：宁可这行显示「未知」，也不能让推送失败
        return ''
    if not commit:
        return ''
    # detached HEAD 时 --abbrev-ref 返回字面量 HEAD，这时只报提交号
    return commit if branch in ('', 'HEAD') else '{}@{}'.format(branch, commit)


def push_message(counts, test_result, app_info, elapsed):
    """企微消息正文：第一行只放结论，剩下的全部降级到灰字

    三种形态：
        0 条     -> 红色「0 条用例被执行」。套件加载失败、CASE 写错都会走到这里，
                    当成「全部通过」发出去比红的还危险
        全通过   -> 绿色「通过 125 / 137」
        有未通过 -> 橙色「2 失败　1 异常」+ 灰色通过数，再附编号清单
    第一行不放应用名：之前「slp 通过 125/137」两个粗体挤在一起，屏幕上最先
    看到的是「slp」，真正需要的数字反而被压住了。
    """
    rev = git_revision() or '版本未知'

    if not counts['total']:
        # 0 条时「跳过/重试」都是无意义数据（还可能带上一轮的残留），只报耗时和版本
        return ['<font color="warning">**本轮 0 条用例被执行**</font>　套件为空或 CASE 写错，不算通过',
                '<font color="comment">{}　{}　{}</font>'.format(app_info, duration_text(elapsed), rev)]

    tail = '<font color="comment">{}</font>'.format('　'.join([
        app_info,
        '跳过 {}'.format(counts['skip']),
        retry_digits(test_result),
        duration_text(elapsed),
        rev,
    ]))

    if not (counts['fail'] or counts['error']):
        # 不写「137 条全部通过」：137 里含 12 条跳过，写成全部通过就不准了
        return ['<font color="info">**通过 {} / {}**</font>'.format(counts['pass'], counts['total']),
                tail]

    # 只列非零的那几项：写「0 失败　2 异常」既占位又没信息量
    bad = '　'.join([item for item in (
        '{} 失败'.format(counts['fail']) if counts['fail'] else '',
        '{} 异常'.format(counts['error']) if counts['error'] else '',
    ) if item])
    lines = ['<font color="warning">**{}**</font>　<font color="comment">通过 {} / {}</font>'.format(
                 bad, counts['pass'], counts['total']),
             tail]
    # 先给性质（要不要重跑/看数据），再给场景（哪一类在退化），最后才是逐条清单
    lines.extend(fail_kind_line(test_result))
    lines.extend(group_lines(test_result))
    lines.extend(push_fail_lines(test_result))
    return lines


def notify(test_result, app_info, elapsed=0):
    """汇总执行结果：未通过清单完整写到控制台与 log/notPassCase.log

    PUSH_WX=1 时再推一条企微消息，形态见 push_message。
    """
    counts = runflow.log_counts(test_result, app_info)
    # 清单、失败性质、场景族统计、完整堆栈：与全量入口走同一段，避免两边各改各的
    runflow.console_reports(test_result, app_info)

    if not PUSH_WX:
        print('企业微信推送已关闭（PUSH_WX=0），完整结果见上方输出与 log/notPassCase.log', flush=True)
        return counts

    # 只推一条（超过企微单条上限才拆）：全通过时就是两行，有未通过时把编号清单
    # 附在后面。不再逐条发 icon —— 每条都会 @all，失败几条就刷几次屏，
    # 而清单本来就在这条消息里，提醒和内容分开反而是多一次打扰
    runflow.push_lines(push_message(counts, test_result, app_info, elapsed), app_info)
    return counts


def main(app_info):
    """执行指定 App 的全部用例，返回 result_counts 的计数（供退出码判断）"""
    if app_info not in APP_SUPPORTED:
        Logs.get_log('runCode.log').error('{} 执行异常'.format(app_info))
        return None

    # 开跑前先确认环境可用。环境不通时继续跑，结果是 137 条逐条失败——它不是
    # 回归信号，而且会把「真的全挂了」这个信号提前用掉。不可用就不跑，明说
    # app_info 就是 slp / xsg（parse_app 返回 config.appName 的值），正好是 config.appInfo 的键
    ok, rows, hint = preflight.gate(app_info)
    if not ok:
        runflow.env_down_notify(app_info, rows, hint, PUSH_WX)
        return ENV_DOWN

    # 定时任务是长期运行场景，先刷新一次 token，避免 token 过期导致全量失败
    runflow.refresh_token(app_info)

    started = time.time()
    test_result = AllTestRunner(verbosity=2).run(build_suite(app_info, CASE))
    elapsed = time.time() - started
    # 重试后才通过的用例：最终状态是 PASS，但每条背后都是一次真实的断言失败。
    # 定时任务场景控制台没人看，所以完整清单落 log/retryCase.log，推送里只带一行摘要
    runflow.log_retry(test_result)
    return notify(test_result, app_info, elapsed)


def run(argv):
    """命令行入口：返回退出码（0 全通过 / 1 有失败或异常 / 2 没跑完 / 3 环境不可用）

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
            runflow.push_lines(['<font color="warning">**执行中断**</font>　本轮用例没有跑完，不能当成通过',
                                '<font color="comment">{}: {}　完整堆栈 log/runCode.log</font>'.format(
                                    type(error).__name__, error)], app)
        return 2
    if counts is None:
        # parse_app 已经拦了错误参数，这里只防配置里的 App 名与支持列表不一致
        print('[{}] 不在支持列表，未执行'.format(app), flush=True)
        return 2
    if counts == ENV_DOWN:
        # 与 1（有用例失败）区分：没跑和跑了但红是两件事，日志里要能一眼分清
        return preflight.EXIT_ENV_DOWN
    if not counts['total']:
        # 0 条用例不是「全部通过」：套件加载失败、CASE 过滤器写错、模块被注释掉都会
        # 走到这里。退出码仍给 0 的话，cron 和群里看到的都是「没事」，比红的更危险
        print('[{}] 本轮执行了 0 条用例，视为异常'.format(app), flush=True)
        return 2
    # 有失败/异常返回 1，便于 cron、调度平台或 cmd && 后续命令感知本轮失败
    return 1 if (counts['fail'] or counts['error']) else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv))
