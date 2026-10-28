# coding=utf-8
import os
import sys
from time import time

from autoGitPull import updateTime, updateCode
from common import Logs, Consts, preflight, runflow
from common.Config import config
from common.report import AllTestRunner, build_suite, not_pass_summary, parse_app

# 是否推送到企业微信群：默认关闭。当前直接在云服务器上看日志，企业微信的 markdown 展示效果不理想，
# 需要恢复推送时用 PUSH_WX=1
PUSH_WX = os.environ.get('PUSH_WX', '0') == '1'
# 只跑指定用例（调试用）：不设则全量执行。
#   CASE=test_check                                          只跑 caseSlp/test_check.py
#   CASE=test_check.TestPayCreate.test_002,test_check.TestPayCreate.test_012
# unittest 的 discover 只能按**文件名** glob，写用例名是匹配不到文件的，所以两种写法分开处理
CASE = os.environ.get('CASE', '').strip()
# 推送时是否额外逐条列出通过的用例：默认关闭，通过用例动辄上百条，会把真正要看的失败清单挤到后面
LIST_PASS = os.environ.get('LIST_PASS', '0') == '1'
# 环境不可用时 main 返回这个标记而不是 counts：没有一轮用例结果可报
ENV_DOWN = 'env_down'


def main(appInfo):
	if appInfo == config.appName['SLP'] or appInfo == config.appName['XSG']:
		# 开跑前先确认环境可用：环境不通时用例会一条条失败到结束，那不是回归信号，
		# 而且会把「真的全挂了」这个信号提前用掉。不可用就不跑，退出码 3
		ok, rows, hint = preflight.gate(appInfo)
		if not ok:
			runflow.env_down_notify(appInfo, rows, hint, PUSH_WX)
			return ENV_DOWN

		to = 'wx'
		print("*" * 50)
		# 开关关掉时不要再打"消息推送到:wx"，否则日志里会和后面的"推送已关闭"互相矛盾
		print('消息推送: {}'.format('{}（PUSH_WX=1）'.format(to) if PUSH_WX else '已关闭（PUSH_WX=0），结果只输出到控制台与日志'))
		print("*" * 50)
		# 刷新 Token（只调用一次）
		# 与 run_crontab_case 保持一致：token 服务异常时不直接带着 traceback 退出，记日志后继续跑，
		# 用例会逐条报错，比"一条都没跑"更容易定位
		runflow.refresh_token(appInfo)

		# 检查代码更新（不阻塞测试执行）
		updateCode.autoGitPull('slp_php')
		updateCode.autoGitPull('slp_common_rpc')
		updateTime('write', now=str(int(time())))

		# 执行测试
		test_result = AllTestRunner(verbosity=2).run(build_suite(appInfo, CASE))
		Consts.endTime = time()

		# result_counts 会把 setUpClass/tearDownClass 报错补进总数，避免「总数: 0, 异常: 1」或「通过: -1」
		# 结算行、重试行、清单、失败性质、场景族统计、完整堆栈都与定时任务入口共用同一段代码
		counts = runflow.log_counts(test_result, appInfo)
		des = runflow.counts_text(counts, appInfo)

		# 固定行：重试率是「被 @Retry 兜住的服务端问题」唯一的存在证明。没有这一行，
		# 「全绿」就分不出「真的没问题」和「有问题但被重试掉了」。
		runflow.log_retry(test_result)
		runflow.console_reports(test_result, appInfo)

		if PUSH_WX:
			# 推送时才拼消息：未通过用例放在最前面，避免末尾结论被截断
			lines = ["des: {}".format(des), "", not_pass_summary(test_result)]
			if LIST_PASS:
				lines.append("")
				lines.append("通过用例：")
				for case in test_result.successes:
					lines.append("{} - PASS".format(test_result.test_des_map.get(case, case.id())))
			# 仍然超长时按字节拆成多条推送
			runflow.push_lines(lines, appInfo)
		else:
			print('企业微信推送已关闭（PUSH_WX=0），完整结果见上方输出与 log/notPassCase.log', flush=True)

		return counts
	else:
		Logs.get_log('runCode.log').error('{} 执行异常'.format(appInfo))
		return None


if __name__ == "__main__":
	counts = main(parse_app(sys.argv))
	if counts == ENV_DOWN:
		# 与 1（有用例失败）区分：没跑和跑了但红是两件事，日志里要能一眼分清
		sys.exit(preflight.EXIT_ENV_DOWN)

	# 退出码：有失败/异常时返回 1，便于 cron、调度平台或 cmd && 后续命令感知本轮失败
	sys.exit(1 if counts and (counts['fail'] or counts['error']) else 0)
