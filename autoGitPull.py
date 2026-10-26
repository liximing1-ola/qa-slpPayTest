import os
from time import time

from common import Logs, Consts
from common.Config import config


class updateCode:
    # 两个仓库的判断结果完全一致，用该标记保证同一条日志只打印一次
    _time_logged = False

    @staticmethod
    def autoGitPull(appInfo, env='dev', bot='BB', to='slack'):
        env=env if env else 'slp'
        bot=bot if bot else 'slp'
        if appInfo == 'bb_php':
            Logs.get_log('gitBranchError.log').error("bb_php 相关配置已废弃，codeInfo 中不存在 bb_php_path/bb_git_branch")
            return
        elif appInfo == 'slp_php':#todo
            gtr_path = config.codeInfo['slp_php_path']
            git_branch = config.codeInfo['slp_git_branch']
        elif appInfo == 'slp_common_rpc':
            gtr_path = config.codeInfo['slp_common_rpc_path']
            git_branch = config.codeInfo['slp_git_branch']
        else:
            Logs.get_log('gitBranchError.log').error("{} error".format(appInfo))
            return

        # g = git.cmd.Git(gtr_path)
        # g.pull() if not appInfo.startswith("slp") else print(f"{appInfo}不拉代码!")
        # repo = Repo(gtr_path)
        Consts.startTime = time()
        if "dev" == git_branch:  # 当前线上分支
            # slp_php 与 slp_common_rpc 共用同一个"上次执行时间"，判断结果完全一致，
            # 只打印一次，避免同一条日志重复刷屏
            if not updateCode._time_logged:
                updateCode._time_logged = True
                Logs.get_log('updateGitCode.log').info(
                    '上次代码更新时间: {}'.format(updateTime('read')))
            return True
        else:
            return False


def updateTime(operate, now=''):
    default_time = '1600000000'  # 默认时间戳
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
