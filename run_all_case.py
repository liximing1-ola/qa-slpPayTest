# coding=utf-8
import unittest
from time import time, sleep

from Robot import robot
from autoGitPull import updateTime, updateCode
from common import Logs, method, Consts
from common.Config import config


def main(appInfo):
	if appInfo == config.appName['不夜星球'] or appInfo == config.appName['小拾光']:
		to = 'slack'
		print("*" * 50)
		print(f"消息推送到:{to}")
		print("*" * 50)
		if updateCode.autoGitPull('slp_php', bot='slp', to=to, env=appInfo) | updateCode.autoGitPull('slp_common_rpc', bot='slp', to=to, env=appInfo):
			updateTime('write', now=str(int(time())))
			test_result = unittest.TextTestRunner(verbosity=3).run(all_case(appInfo))
			Consts.endTime = time()
			des = "用例总数: {}, 失败用例数: {}, 异常用例数: {}" \
				.format(test_result.testsRun, len(test_result.failures), len(test_result.errors))
			Logs.get_log('caseResult.log').info(des)
			case_list = method.dictToList(Consts.case_list)
			case_list_2 = method.dictToList(Consts.case_list_b)
			case_list_3 = method.dictToList(Consts.case_list_b2)
			use_time = str(int(Consts.endTime - Consts.startTime)) + 's'
			if len(test_result.failures) == 0 and len(test_result.errors) == 0:
				des = "{}\n".format(case_list)
				des_2 = "{}\n".format(case_list_2)
				des_3 = "{}\n用例数: {}, 失败数: {}, 总耗时: {}, 代码分支：{}".format(
					case_list_3, test_result.testsRun,
					len(test_result.failures) + len(test_result.errors),
					use_time,
					config.codeInfo['slp_git_branch'])
				robot('slack', des, bot='slp', to=to) if to == 'slack' else robot('markdown', des, bot='slp')
				sleep(0.1)
				robot('slack', des_2, bot='slp', to=to) if to == 'slack' else robot('markdown', des_2, bot='slp')
				sleep(0.1)
				robot('slack', des_3, bot='slp', to=to) if to == 'slack' else robot('markdown', des_3, bot='slp')
			if len(test_result.failures) >= 1:
				Logs.get_log('failCase.log').error("failures: {}".format(test_result.failures))
				robot('slack', des, bot='slp', to=to) if to == 'slack' else robot('fail', des, bot='slp')
				for case, reason in test_result.failures:
					robot('slack', Consts.fail_case_reason[0], title=case.id(), color='danger', bot='slp', to=to) if to == 'slack' \
						else robot('fail', Consts.fail_case_reason[0], title=case.id(), color='danger', bot='slp')
					break
			if len(test_result.errors) >= 1:
				Logs.get_log('failCase.log').error("error: {}".format(test_result.errors))
				for case, reason in test_result.errors:
					robot('slack', reason, case.id(), color='danger', bot='slp', to=to) if to == 'slack' \
						else robot('fail', reason, case.id(), color='danger', bot='slp')
					break
		else:
			Logs.get_log('runCode.log').info('NoRun')
	else:
		Logs.get_log('runCode.log').error('{} 执行异常'.format(appInfo))


def all_case(appInfo):
	case_dir = config.BASE_PATH
	if appInfo == config.appName['不夜星球']:
		case_dir += '/caseSlp'
	elif appInfo == config.appName['小拾光']:
		case_dir += '/caseXsg'
	else:
		return

	testcase = unittest.TestSuite()
	# discover = unittest.defaultTestLoader.discover(case_dir,  # 指定待执行用例的目录
	#                                                pattern="test_pt_cnArea.py",
	#                                                top_level_dir=None)
	discover = unittest.defaultTestLoader.discover(case_dir,  # 指定待执行用例的目录
	                                               # pattern="test_*.py",
	                                               pattern="test_gs_other_broker_slporder_room_new.py",
	                                               # pattern="test_gs_room_pay_self.py",
	                                               # pattern="test_naming_song.py",
	                                               # pattern="test_001.py",
	                                               # pattern="test_002.py",
	                                               # pattern="test_coupon.py",
	                                               top_level_dir=None)
	testcase.addTests(discover)
	return testcase


if __name__ == "__main__":
	import sys

	if len(sys.argv) >= 2:
		arg = sys.argv[1].strip().lower()
	else:
		arg = None

	if arg == config.appName['不夜星球'] or arg == 'slp':
		main(config.appName['不夜星球'])
	elif arg == config.appName['小拾光'] or arg == 'xsg':
		main(config.appName['小拾光'])
	else:
		main(config.appName['不夜星球'])
