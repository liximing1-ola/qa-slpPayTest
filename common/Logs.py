# coding=utf-8
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from common.Config import config


def _apply_console(logs, formatter=None):
    """给 logger 挂上一个控制台 handler（已挂则不重复挂）"""
    if any(type(handler) is logging.StreamHandler for handler in logs.handlers):
        return
    ch = logging.StreamHandler()
    ch.setLevel(level='INFO')
    if formatter is None:
        formatter = logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    ch.setFormatter(formatter)
    logs.addHandler(ch)


def _drop_console(logs):
    """摘掉控制台 handler（只保留写文件），已摘过则什么也不做"""
    for handler in [h for h in logs.handlers if type(h) is logging.StreamHandler]:
        logs.removeHandler(handler)


def get_log(log_name, level=logging.DEBUG, when='midnight', back_count=0, console=True):
    """
    :param log_name:
    :param level:
    :param when:
    :param back_count:
    :param console: 是否同时打到控制台；False 时只写文件（比如已经自己 print 过的完整清单，避免重复输出）
    :return:
    """
    logs = logging.getLogger(log_name)
    logs.setLevel(level)  # log打印级别
    # 同名 logger 是全局单例，重复调用时再挂 handler 会让同一条日志被打印 N 次，
    # 且每次都会新建 TimedRotatingFileHandler，造成文件句柄泄漏，所以 handler 只建一次；
    # 但 console 是调用方每次都可能变的语义，必须每次都真正生效：
    # 否则先 get_log(x) 再 get_log(x, console=False) 会因为提前 return 而继续往控制台打
    if logs.handlers:
        if console:
            _apply_console(logs)
        else:
            _drop_console(logs)
        return logs
    LOG_PATH = os.path.join(config.BASE_PATH, 'log')
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)
    log_file_path = os.path.join(LOG_PATH, log_name)
    formatter = logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    # when: S=秒/M=分/H=小时/D=天/W=每星期/midnight=每天凌晨
    # backupCount: 备份文件保留个数，超过就自动删除
    fh = TimedRotatingFileHandler(
        filename=log_file_path,
        when=when,
        backupCount=back_count,
        encoding='UTF-8')
    fh.setLevel(level)
    fh.setFormatter(formatter)
    #  添加到logger对象里
    if console:
        _apply_console(logs, formatter)
    logs.addHandler(fh)
    return logs
