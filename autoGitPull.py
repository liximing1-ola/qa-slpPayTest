import datetime
import os
import git
from time import time, mktime, strptime
from git.repo import Repo
from Robot import robot
from common import Logs, Consts
from common.Config import config
from common.Session import Session


class updateCode:

    @staticmethod
    def autoGitPull(appInfo, env='dev', bot='BB', to='slack'):
        env=env if env else 'slp'
        bot=bot if bot else 'slp'
        if appInfo == 'bb_php':
            gtr_path = config.codeInfo['bb_php_path']
            git_branch = config.codeInfo['bb_git_branch']
        elif appInfo == 'slp_php':
            gtr_path = config.codeInfo['slp_php_path']
            git_branch = config.codeInfo['slp_git_branch']
        elif appInfo == 'slp_common_rpc':
            gtr_path = config.codeInfo['slp_common_rpc_path']
            git_branch = config.codeInfo['slp_git_branch']
        else:
            Logs.get_log('gitBranchError.log').error("{} error".format(appInfo))
            return

        Consts.startTime = time()
        Session.getSession(env)
        commit_log = str(datetime.datetime.now())
        log_list = commit_log.split("\n")
        if "dev" == git_branch:
            times = 9999999999
            lastTime = int(updateTime('read'))
            if times > lastTime:
                Logs.get_log('updateGitCode.log').info(
                    '\u6700\u65b0\u4ee3\u7801\u63d0\u4ea4\u65f6\u95f4: {}, \u4e0a\u6b21\u4ee3\u7801\u66f4\u65b0\u65f6\u95f4: {}'.format(times, lastTime))
                return True
            else:
                return False
        else:
            return False


def updateTime(operate, now=''):
    default_time = '1600000000'
    txtPath = os.path.split(os.path.realpath(__file__))[0] + '/time.txt'
    if operate == 'write':
        with open(txtPath, 'w') as f:
            f.write(now)
            f.flush()
    elif operate == 'read':
        if not os.path.exists(txtPath):
            os.system(r"touch {}".format(txtPath))
            with open(txtPath, 'r+') as f:
                f.write(default_time)
                f.flush()
        with open(txtPath, 'r') as f:
            f = f.read()
            return f
    elif operate == 'change':
        with open(txtPath, 'w') as f:
            f.write(default_time)
            f.flush()



if __name__ == '__main__':
    updateTime('change')
