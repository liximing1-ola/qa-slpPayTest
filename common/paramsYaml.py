# coding=utf-8
import os

import yaml

from common.Config import config


class Yaml:
    @staticmethod
    def read_yaml(yaml_fileName, yaml_name):
        """
        读取 yaml 中指定 key 的内容
        :param yaml_fileName: yaml 文件名，位于 common 目录下
        :param yaml_name: 要读取的 key
        :return: yaml_data[yaml_name]
        """
        yaml_path = os.path.join(config.BASE_PATH, 'common', yaml_fileName)
        # 原实现是 return FileExistsError / return TypeError（返回异常类而不是抛出），
        # 调用方拿到的是 class 对象，问题被彻底掩盖，这里改为直接抛出
        if not os.path.exists(yaml_path):
            raise FileNotFoundError('yaml 文件不存在: {}'.format(yaml_path))
        with open(yaml_path, 'r', encoding='utf-8') as f:
            # 固定使用 safe_load，避免不同 PyYAML 版本下 yaml.load 缺 Loader 参数直接报错
            yaml_data = yaml.safe_load(f)
        if not isinstance(yaml_data, dict) or yaml_name not in yaml_data:
            raise KeyError('yaml 中不存在 key: {} ({})'.format(yaml_name, yaml_path))
        return yaml_data[yaml_name]
