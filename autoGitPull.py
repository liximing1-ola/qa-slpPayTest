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
        Session.getSession(env)  # 更新userToken
        # commit_log = repo.git.log('--pretty={"commit":"%h","author":"%an","summary":"%s","date":"%cd"}', max_count=3,
        #                           date='format:%Y-%m-%d %H:%M:%S')
        commit_log = str(datetime.datetime.now())
        log_list = commit_log.split("\n")
        # Logs.get_log('gitCommitPull.log').info(
        #     '当前分支: {}, 最新一条commit: {}'.format(repo.active_branch, log_list[0]))
        # if str(repo.active_branch) == git_branch:  # 当前线上分支
        if "dev" == git_branch:  # 当前线上分支
            # times = int(
            #    mktime(strptime([eval(item) for item in log_list][0]['date'], "%Y-%m-%d %H:%M:%S")))  # commit更新时间
            times = 9999999999
            lastTime = int(updateTime('read'))  # 上次脚本执行时间
            if times > lastTime:
                Logs.get_log('updateGitCode.log').info(
                    '最新代码提交时间: {}, 上次代码更新时间: {}'.format(times, lastTime))
                # 不发送 git commit 通知消息
                # if appInfo == 'pt':
                #     robot('slack_pt', log_list[0], bot=bot)
                # elif appInfo in ['slp_php', 'slp_common_rpc']:
                #     robot('slack', log_list[0], bot=bot, to=to) if to == 'slack' else robot('markdown', log_list[0], bot=bot, to=to)
                # else:
                #     robot('slack', log_list[0], bot=bot)
                return True
            else:
                # Logs.get_log('updateGitCode.log').info("未拉取到{}分支代码，最近代码提交时间: {}, 上次代码更新时间: {}"
                #                                        .format(repo.active_branch, times, lastTime))
                return False
        else:
            # Logs.get_log('gitBranchError.log').error("git branch error： {}".format(repo.active_branch))
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
