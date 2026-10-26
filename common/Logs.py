# coding=utf-8
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from common.Config import config


def get_log(log_name, level=logging.DEBUG, when='midnight', back_count=0):
    """
    :param log_name:
    :param level:
    :param when:
    :param back_count:
    :return:
    """
    logs = logging.getLogger(log_name)
    logs.setLevel(level)  # log打印级别
    # 同名 logger 是全局单例，重复调用时再挂 handler 会让同一条日志被打印 N 次，
    # 且每次都会新建 TimedRotatingFileHandler，造成文件句柄泄漏
    if logs.handlers:
        return logs
    LOG_PATH = os.path.join(config.BASE_PATH, 'log')
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)
    log_file_path = os.path.join(LOG_PATH, log_name)
    formatter = logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(level='INFO')
    ch.setFormatter(formatter)  # 设置日志输出格式
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
    logs.addHandler(ch)
    logs.addHandler(fh)
    return logs
