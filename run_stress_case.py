# coding=utf-8
"""并发与幂等用例入口：上线前跑一轮，不进日常全量回归

为什么必须单独一个进程、单独一个目录：

1. 节流是 App 级全局锁（common/Request 的 _interval_lock 按 tokenName 排队），同进程多线程
   会被塞进同一个节流窗口，每个请求至少隔 REQUEST_INTERVAL——那样写出来的「并发」其实是
   串行，测的是限流而不是服务端。所以在 import 任何 common 模块之前把间隔归零。
2. 用例会把账号余额、订单、分成数据搅乱，和日常那 137 条共用账号会互相污染。
3. 它们回答的是「服务端会不会超扣 / 重复扣费」，不是「这版改坏了哪条业务」，上线前跑一轮
   足够，不需要跟着每次 cron 跑。

用法：
	python run_stress_case.py slp
	PUSH_WX=1 python run_stress_case.py slp
	CASE=test_pay_concurrent python run_stress_case.py slp
"""
import os

# 必须在 import common.Request 之前：Request 在 import 阶段就把 REQUEST_INTERVAL 读成常量，
# 之后再改环境变量不会生效
os.environ.setdefault('REQUEST_INTERVAL', '0')

# 频控重试同样会毁掉并发：命中后请求层退避 2 秒再发，同一账号的两个请求就被拉成串行。
# 实测 test_002 / test_004 每轮都命中 1 次，那两条「通过」都是串行之后的假绿。
# 这里不重试：频控响应原样返回，classify 按文案计成业务拒绝，请求保持同时到达，
# 真并发到底能不能复现缺陷才看得出来。
os.environ.setdefault('FREQUENT_RETRY', '0')

import sys
from time import time

from common import Logs, preflight, runflow
from common.Config import config
from common.report import AllTestRunner, build_suite, not_pass_summary, parse_app

STRESS_DIR = 'caseStress'
CASE = os.environ.get('CASE', '').strip()
PUSH_WX = os.environ.get('PUSH_WX', '0') == '1'
# 环境不可用时返回这个标记而不是 counts：没有一轮用例结果可报
ENV_DOWN = 'env_down'


def main(appInfo):
	if appInfo not in (config.appName['SLP'], config.appName['XSG']):
		Logs.get_log('runCode.log').error('{} 执行异常'.format(appInfo))
		return None

	# 并发用例一样依赖 MySQL / Redis / 支付接口，环境不通时一条条报错到底没有任何信息量
	ok, rows, hint = preflight.gate(appInfo)
	if not ok:
		runflow.env_down_notify(appInfo, rows, hint, PUSH_WX)
		return ENV_DOWN

	print('*' * 50)
	print('并发与幂等用例（{}）：会改动账号余额与订单，不与日常回归混跑'.format(STRESS_DIR))
	print('消息推送: {}'.format('已开启（PUSH_WX=1）' if PUSH_WX else '已关闭（PUSH_WX=0），结果只输出到控制台与日志'))
	print('*' * 50)

	start = time()
	# 换目录而不是在 caseSlp 下加子目录：discover 是递归的，放进 caseSlp 的子目录会被
	# 日常全量回归自动收进去
	test_result = AllTestRunner(verbosity=2).run(build_suite(appInfo, CASE, STRESS_DIR))

	# 结算、重试、清单、失败性质、场景族统计与两个日常入口共用同一段代码
	counts = runflow.log_counts(test_result, appInfo)
	runflow.log_retry(test_result)
	runflow.console_reports(test_result, appInfo)
	print('本轮耗时: {:.1f}s'.format(time() - start), flush=True)

	if PUSH_WX:
		lines = ['des: {}'.format(runflow.counts_text(counts, appInfo)), '', not_pass_summary(test_result)]
		runflow.push_lines(lines, appInfo)
	else:
		print('企业微信推送已关闭（PUSH_WX=0），完整结果见上方输出与 log/notPassCase.log', flush=True)

	return counts


if __name__ == '__main__':
	counts = main(parse_app(sys.argv))
	if counts == ENV_DOWN:
		# 与 1（有用例失败）区分：没跑和跑了但红是两件事
		sys.exit(preflight.EXIT_ENV_DOWN)
	if counts and not counts['total']:
		# 0 条用例和「都通过了」也是两件事，别让空跑混进全绿
		sys.exit(2)
	sys.exit(1 if counts and (counts['fail'] or counts['error']) else 0)
